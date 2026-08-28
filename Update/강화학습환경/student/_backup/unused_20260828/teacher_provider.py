# -*- coding: utf-8 -*-
"""[학생 파일] 스크립트 교사를 플랫폼 수정 없이 상대로 붙이는 어댑터.

왜 이게 필요한가
----------------
`student/scripted_opponents.py`(구 teachers.py) 의 교사들은 **자동조종 명령**을 낸다
(`{lat_mode, lon_mode, spd_mode, phi_deg, psi_deg, gamma_deg, altitude_m, speed_mps}`).
이전 워크스페이스는 이걸 쓰려고 플랫폼 파일 두 개를 고쳤다:
  * `FighterSim.py`      : `step_auto_cmd()` 24줄 추가        [MOD-TEACHER]
  * `single_agent_env.py`: `target_mode == "teacher"` 분기 추가 [MOD-TEACHER]

여기서는 **플랫폼을 건드리지 않는다.** 원본 env 가 이미 `target_action_provider` 를
받으므로(`single_agent_env._step_target_aircraft` 503-511행), 자동조종을 파이썬으로
구현해 조종면으로 바꿔서 그 훅에 꽂는다. 제출 경로 파일이 하나도 안 바뀐다.

조종면 규약 (`FighterSim.step`)
  action[0] 롤 스틱   -1 왼쪽 / +1 오른쪽
  action[1] 피치 스틱 **-1 당김(기수 위) / +1 밀기(기수 아래)**
  action[2] 러더      -1 왼쪽 / +1 오른쪽
  action[3] 스로틀    0 ~ 1

속도에 대한 주의 — 주석을 믿지 말고 실측할 것
---------------------------------------------
`scripted_opponents.py` 의 `SPD_ACHIEVED_MPS = 225.0` 주석("실제로 나는 속도")은 **틀렸다.**
이전 워크스페이스의 `[MOD-TEACHER]` 경로에서 60초씩 실측한 결과:

    straight 396 / turn 396 / pursuit 399 / defensive 398 / ace 394  m/s

즉 교사는 지령한 400 m/s 를 거의 그대로 낸다. 처음에 주석을 믿고 225 로 맞췄더니
교사가 37% 느려져 훨씬 잡기 쉬운 상대가 됐다 — 커리큘럼 난이도가 통째로 달라진다.
그래서 여기서는 **지령 속도를 그대로 추종**한다.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from dogfight.ai.action_provider import ActionContext, ActionProvider, ActionResult
from dogfight.sim.state_schema import StateIndex

from student import scripted_opponents as T  # 2026-08-28 파일명 변경: teachers.py -> scripted_opponents.py

_D2R = math.pi / 180.0
_R2D = 180.0 / math.pi

# 캐스케이드 이득. 60 Hz 물리 기준.
K_PSI = 2.0        # 방위 오차(deg) -> 뱅크 지령(deg)
PHI_MAX = 75.0     # 뱅크 상한 (수직 넘으면 교사가 뒤집힌다)
K_PHI = 0.055      # 뱅크 오차(deg) -> 롤 스틱
K_ALT = 0.010      # 고도 오차(m) -> 경로각 지령(deg)
GAMMA_MAX = 25.0   # 경로각 상한
K_GAM = 0.10       # 경로각 오차(deg) -> 피치 스틱
K_TURN = 0.45      # 선회 중 고도 유지용 추가 당김 (하중 보상)
K_SPD = 0.010      # 속도 오차(m/s) -> 스로틀
TRIM_THR = 0.55    # 순항 스로틀


def _wrap180(deg: float) -> float:
    return (deg + 180.0) % 360.0 - 180.0


def _clip(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


class TeacherActionProvider(ActionProvider):
    """교사의 자동조종 명령을 조종면으로 바꿔 상대기를 조종한다."""

    def __init__(self, spec: Any = None, seed: int = 0, sim_hz: float = 60.0):
        self._spec = spec
        self._teacher = T.make_teacher(spec)
        self._dt = 1.0 / float(sim_hz)
        self._rng = np.random.default_rng(seed)

    @property
    def teacher(self) -> T.Teacher:
        return self._teacher

    def reset(self, context: ActionContext | None = None) -> None:
        self._teacher = T.make_teacher(self._spec)
        own = getattr(context, "ownship_state", None) if context else None
        foe = getattr(context, "target_state", None) if context else None
        self._teacher.reset(self._rng, own, foe)

    def compute_action(self, context: ActionContext) -> ActionResult:
        # 상대측 provider 이므로 context.ownship_state 가 '교사 자신'이다.
        own = context.ownship_state
        foe = context.target_state
        if own is None or foe is None:
            return ActionResult(action=np.zeros(4, dtype=np.float32),
                                source="teacher", info={"mode": ""})

        geo = getattr(context.sim, "_geo_info", None)
        if geo is None:
            from GeoMathUtil import GeometryInfo
            geo = GeometryInfo()
            context.sim._geo_info = geo

        cmd = self._teacher.command(own, foe, geo, self._dt)
        act = self._autopilot(own, cmd)
        return ActionResult(action=act, source="teacher",
                            info={"mode": self._teacher.mode})

    # ── 자동조종: 명령 dict -> 조종면 ─────────────────────────────────
    def _autopilot(self, own, cmd: dict) -> np.ndarray:
        roll = float(own[StateIndex.ROLL])
        pitch = float(own[StateIndex.PITCH])
        yaw = float(own[StateIndex.YAW])
        alt = -float(own[StateIndex.D])

        # 현재 속도와 경로각 (동체속도를 NED 로 돌려서)
        v_ned = T._ned_velocity(own)
        speed = float(np.linalg.norm(v_ned))
        gamma = math.degrees(math.asin(_clip(-float(v_ned[2]) / max(speed, 1e-6),
                                             -1.0, 1.0)))

        # --- 가로: 방위 또는 뱅크 지령 -> 롤 스틱 ---
        if int(cmd.get("lat_mode", T.LAT_HEADING)) == T.LAT_BANK:
            phi_cmd = float(cmd.get("phi_deg", 0.0))
        else:
            psi_err = _wrap180(float(cmd.get("psi_deg", yaw)) - yaw)
            phi_cmd = _clip(K_PSI * psi_err, -PHI_MAX, PHI_MAX)
        phi_cmd = _clip(phi_cmd, -PHI_MAX, PHI_MAX)
        aileron = _clip(K_PHI * _wrap180(phi_cmd - roll), -1.0, 1.0)

        # --- 세로: 고도/경로각/피치 지령 -> 피치 스틱 ---
        lon = int(cmd.get("lon_mode", T.LON_ALT))
        if lon == T.LON_PITCH:
            gam_cmd = float(cmd.get("theta_deg", 0.0))
        elif lon == T.LON_GAMMA:
            gam_cmd = float(cmd.get("gamma_deg", 0.0))
        else:
            gam_cmd = _clip(K_ALT * (float(cmd.get("altitude_m", alt)) - alt),
                            -GAMMA_MAX, GAMMA_MAX)
        # 뱅크가 깊으면 같은 경로각을 유지하는 데 더 당겨야 한다(하중 1/cos phi).
        turn_comp = K_TURN * (1.0 / max(math.cos(_clip(roll, -85.0, 85.0) * _D2R), 0.2) - 1.0)
        elevator = _clip(-(K_GAM * (gam_cmd - gamma) + turn_comp), -1.0, 1.0)

        # --- 속도: 지령을 그대로 추종 (실측상 옛 교사는 396~399 m/s 로 난다) ---
        spd_cmd = float(cmd.get("speed_mps", T.SPD_CMD_STABLE))
        throttle = _clip(TRIM_THR + K_SPD * (spd_cmd - speed), 0.0, 1.0)

        return np.array([aileron, elevator, 0.0, throttle], dtype=np.float32)


def make_teacher_provider(spec: Any = None, seed: int = 0) -> TeacherActionProvider:
    return TeacherActionProvider(spec, seed=seed)
