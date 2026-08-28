# -*- coding: utf-8 -*-
"""관측 정의 — student12.

설계 원칙 (하나뿐)
------------------
**서버가 주는 9/9 패킷 밖은 절대 읽지 않는다.**

대회 Unreal 서버가 보내는 것은 기체당 9개 float 뿐이다(실측 2026-08-02):
    PLANE_INFO_STRUCT = "<iQb3f3f3f"
    = 위치(N,E,D) + 자세(Roll,Pitch,Yaw) + 동체속도(u,v,w)
나 + 적 = 18개. `plane_info_to_state()` 는 `np.zeros(51)` 에 `[0:9]` 만 채우고
나머지 42칸은 0으로 둔다. 따라서 `StateIndex.ALT`(44) / `KCAS`(12) / `HEALTH`(45)
/ `AOA`(13) 같은 인덱스를 읽으면 대회에서 상수 0이 들어온다.
고도는 `-own[2]`, 받음각은 `atan2(w,u)` 로 **직접 계산**해야 한다.

주최측 확인: "Unreal에서 송신한 패킷을 수신하면 모두 계산해서 넣을 수 있는 값입니다."

이 모듈이 읽는 것: `own[0:9]`, `tgt[0:9]`. 그게 전부다.
`geo_info`(GeoMathUtil) 의 `_get_distance` / `_get_los_angle` /
`_get_antenna_train_angle` 도 `[0:6]` 만 읽으므로 계약 안이다.

왜 이 12개인가 — 실측 근거
--------------------------
6/6 격추하는 손수 짠 비례추적 제어기의 궤적 12,000 스텝(교사 5종)을 모아,
후보 32개 중 어느 것이 그 행동을 예측하는지 작은 MLP 로 쟀다(시드 3개).

  * **조준을 절댓값으로 두면 안 된다.** 부호 있는 los_az/los_el 은 MSE 0.0245±0.0007,
    절댓값 ata 한 칸(= 이전 obs38 방식)은 0.0620±0.0052 로 **2.5배 나쁘다.**
    |ATA| 는 0에서 미분 불연속이고 그 0이 바로 작동점이라, 조준점을 지나칠 때
    기울기 부호가 뒤집혀 떨린다. 측정된 실패 양상(체류 중앙 4스텝, 30 초과 0회)과 일치.
  * `los_rate_az/el` 은 빼면 0.0245 -> 0.0306 으로 나빠진다. 필요하다.
  * `ata2d`(롤 불변 2D 방위각)는 넣으면 0.0260 -> 0.0226. 역전 기동에서 쓰인다.
  * 이 측정은 **총 개수를 정하지 못한다** — 지도학습 회귀는 입력이 많을수록 잘 맞는다.
    그래서 개수는 "빼면 죽는 것"만 남기는 쪽으로 정했다.

측정이 볼 수 없어서 물리로 넣은 것 (전문가가 그 상황을 안 만든다):
  * `pitch`  — 없으면 60° 급강하와 수평비행의 관측 차이가 2.22e-16. 강하 시 12.4초 뒤 추락
  * `alt`    — 1,000 ft 이하 즉사
  * `threat_ata` — 없으면 내가 맞고 있는지 **원리상** 알 수 없다(적 자세가 관측에 안 들어감).
                   정면 통과 1회가 양쪽에 0.762 HP 를 준다. 전방위 공격 컨셉의 핵심 신호

빼고 나중에 되돌릴 순서 (사전 등록):
  `speed` -> `time_norm`(WEZ 가 100초 ±2°, 150초 ±3° 로 넓어짐) -> `rel_dir` 3개 -> `aoa`/`aos`

정규화
------
전부 선형(`normalize` 가 클립까지 한다). 범위는 실측 분포에서 잡았다:
`closure` ±700(±400 은 사격구간 36.2% 잘림), `alt` 0~14,000(0~10,000 은 27.6% 잘림).
`los_az` 는 ±15° 로 좁혀 조준 해상도를 확보하고(1°가 전체의 6.7%), 그 밖의 큰 방위각은
`ata2d`(±180°, 롤 불변)가 담당한다 — 두 축이 역할을 나눈다.
"""
from __future__ import annotations

import math

import numpy as np

from dogfight.envs.observation import normalize
from dogfight.sim.state_schema import StateIndex


OBSERVATION_MODE = "student16"
OBSERVATION_SIZE = 16
OBSERVATION_LOW = -1.0
OBSERVATION_HIGH = 1.0

_D2R = math.pi / 180.0

# 9/9 패킷 안의 동체속도 인덱스 (StateIndex 에 이름이 없다)
IDX_U, IDX_V, IDX_W = 6, 7, 8

_FEATURE_NAMES: tuple[str, ...] = ()

# ── 경과 시간 추적 (9/9 패킷에 시간이 없으므로 직접 센다) ──────────────────
# 대회 WEZ 는 100초에 +-2도, 150초에 +-3도로 **넓어진다**. 시간을 모르면
# t=160초에 ATA 2.5도가 확실한 격추인데도 "아직 부족하다"며 더 조이려다 놓친다.
#
# 학습에서는 `StateIndex.SIM_TIME`(41) 을 읽을 수 있지만 대회에서는 0이다.
# 그래서 **양쪽 모두 호출 횟수로 센다** — 그래야 학습과 대회가 같은 값을 본다.
#
# 호출 주기가 양쪽에서 같음을 확인했다: 대회 추론(`unreal/policies.py`)은
# `pair_count % action_repeat == 0` 일 때만 관측을 만든다 = 6프레임마다 =
# 60 Hz 기준 0.1초. 학습의 정책 스텝(step_ratio 6)과 동일하다.
#
# 리셋 감지는 위치 불연속으로 한다. 0.1초에 최대 이동은 약 40 m(400 m/s)인데
# 에피소드 리셋은 수백~수천 m 순간이동이라 확실히 구분된다.
# 러너당 env 1개(num_envs_per_env_runner=1)라 모듈 전역으로 안전하다 —
# my_reward.py 의 전역 상태와 같은 전제.
# [MOD-HZ] 2026-08-19: 결정 주기가 바뀌면 여기도 같이 바뀌어야 한다.
# `_elapsed_s` 는 **호출 횟수**를 세서 `cnt * _DT_S` 로 경과시간을 만든다.
# 20 Hz(step_ratio=3)면 관측이 0.05 초마다 만들어지는데 _DT_S 가 0.1 로 남아
# 있으면 **시간이 2 배 빨리 흐른다** — 200 초 경기를 100 초로 인식해 WEZ
# 페이즈 경계(100 초 +-2도 / 150 초 +-3도)를 통째로 잘못 읽는다.
# [되돌림 2026-08-20] 20 Hz 시도를 접고 10 Hz 고정으로 복귀.
# 환경변수 경로를 없애 20 Hz 로 새는 길을 막는다. 값은 종전과 동일한 0.1 초.
_DT_S = 6 / 60.0                      # 10 Hz = 0.1 초
_RESET_JUMP_M = 300.0

# [2026-08-17 버그 수정] 전역 카운터 1개 -> **관측자별 슬롯**.
#
# 바로 위 "러너당 env 1개라 모듈 전역으로 안전하다" 는 전제는 **env 여러 개**
# 에는 맞지만 **한 env 안의 두 기체**에는 틀렸다. 적기가 RL 정책이면 그쪽도
# 자기 관측을 만들려고 이 함수를 부른다(student/rl_opponent.py `_obs16`).
# 두 기체는 760~3,048 m 떨어져 있으니 번갈아 호출될 때마다 _RESET_JUMP_M(300 m)
# 을 넘어 **매 스텝 리셋**됐다.
#
# 실측 (2026-08-17):
#   적기=고정 표적 -> build_observation 1.0 회/스텝, time_norm 0->10->20->30 초 정상
#   적기=RL 정책   -> build_observation 2.2 회/스텝, time_norm **영원히 0초**
# 즉 self-play 도입 뒤로 이 피처는 죽어 있었다. 반대로 대회에서는 우리가
# 클라이언트 하나라 호출자가 1개뿐 -> 살아난다. **학습에 없던 신호가 본선에서만
# 들어오는** 방향이라 더 나쁘다(정책 민감도 실측 8.7%, 16개 입력 중 최하위).
#
# 슬롯은 **명시적 이름표**로 나눈다. 처음엔 id(state) + 위치 근접으로 짝지어
# 봤는데, 두 기체가 300 m 안으로 붙으면 서로의 슬롯을 훔쳐 카운터가 튀었다
# (실측: 경과초가 0.3 -> 0.1 -> 0.5 로 뒤섞임). 하필 근접이 도그파이트의
# 본무대라 이 방식은 못 쓴다.
#
# 호출자는 셋뿐이고 적기만 우리 파일이다:
#   src/dogfight/envs/single_agent_env.py  아군 (학습)   -> 기본값
#   src/dogfight/unreal/policies.py        아군 (대회)   -> 기본값
#   student/rl_opponent.py `_obs16`        적기          -> observer="target"
# 그래서 선택 인자 하나로 충분하고 플랫폼 파일은 건드리지 않는다.
_slots: dict[str, tuple[np.ndarray, int]] = {}   # 이름표 -> (직전 위치, 스텝수)


def _elapsed_s(own, observer: str = "ownship") -> float:
    pos = np.array([float(own[0]), float(own[1]), float(own[2])])
    prev = _slots.get(observer)
    if prev is None or float(np.linalg.norm(pos - prev[0])) > _RESET_JUMP_M:
        cnt = 0                      # 에피소드 리셋(수백~수천 m 순간이동)
    else:
        cnt = prev[1] + 1
    _slots[observer] = (pos, cnt)
    return cnt * _DT_S


def reset_episode_state() -> None:
    """평가 도구가 명시적으로 리셋하고 싶을 때 쓴다(선택)."""
    _slots.clear()


def _t_nb(state) -> np.ndarray:
    """NED->동체 회전행렬. GeoMathUtil 규약(Tx@Ty@Tz)과 동일해야 한다."""
    roll = float(state[StateIndex.ROLL]) * _D2R
    pitch = float(state[StateIndex.PITCH]) * _D2R
    yaw = float(state[StateIndex.YAW]) * _D2R
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    tx = np.array([[1.0, 0.0, 0.0], [0.0, cr, sr], [0.0, -sr, cr]])
    ty = np.array([[cp, 0.0, -sp], [0.0, 1.0, 0.0], [sp, 0.0, cp]])
    tz = np.array([[cy, sy, 0.0], [-sy, cy, 0.0], [0.0, 0.0, 1.0]])
    return tx @ ty @ tz


def _ata_deg(own, tgt) -> float:
    """기수와 상대 사이 각 (0~180). **플랫폼 3D ATA 를 쓰면 안 된다.**

    `GeoMathUtil._get_antenna_train_angle(..., proj=False)` 결함:

        elif -0.01 < p_unit_t[1] < 0.01:
            sign = np.sign(p_unit_t[2])      # np.sign(0.0) == 0
        _angle = sign * arccos(...)          # 0 * 180 = 0

    상대가 **정후방이고 고도가 정확히 같으면** 180도가 **0도로** 읽힌다.
    실측(2026-08-02): 정후방 정확히 -> 0.00, 정후방 1 m 옆 -> 0.00 (참값 180).
    우리 스폰이 `[거리,0,-7000]` 대 `[0,0,-7000]` 이라 고도가 정확히 같아
    **에피소드 시작마다 걸린다.**

    무작위 기하 20만 개 대조에서 이 함수는 플랫폼의 정상 구간과 최대 9.0e-04 차이로
    일치하고, 결함 구간에서만 올바른 값을 낸다. `proj=True`(2D, arctan2)는 결함이
    없으므로 `ata2d` 는 플랫폼 함수를 그대로 쓴다.
    """
    roll = float(own[StateIndex.ROLL]) * _D2R
    pitch = float(own[StateIndex.PITCH]) * _D2R
    yaw = float(own[StateIndex.YAW]) * _D2R
    rn = float(tgt[0]) - float(own[0])
    re = float(tgt[1]) - float(own[1])
    rd = float(tgt[2]) - float(own[2])
    n = math.sqrt(rn * rn + re * re + rd * rd)
    if n < 1e-9:
        return 0.0
    rn, re, rd = rn / n, re / n, rd / n
    # T = Tx @ Ty @ Tz 의 x 성분만 필요하다 (Tx 는 x 를 바꾸지 않는다).
    x1 = math.cos(yaw) * rn + math.sin(yaw) * re
    bx = math.cos(pitch) * x1 - math.sin(pitch) * rd
    return math.degrees(math.acos(max(-1.0, min(1.0, bx))))


def _ned_velocity(state) -> np.ndarray:
    """동체속도 [u,v,w] 를 NED 로 (동체->NED = T_nb^T).

    state[6:9] 가 **동체 좌표** 속도임은 실측 확인: NED 위치 미분과 비교해
    회전 후 오차 1.59 m/s, 회전 없이 37.08 m/s. 주최측 표기 Velocity(u,v,w) 와 일치.
    """
    body = np.array([float(state[IDX_U]), float(state[IDX_V]), float(state[IDX_W])])
    return _t_nb(state).T @ body


def build_observation(ownship_state, target_state, geo_info, wez_config=None,
                      observer: str = "ownship"):
    # observer: 경과시간 카운터의 슬롯 이름표. 기본값이 아군이라
    # 플랫폼 호출부(학습 env / 대회 추론)는 그대로 두면 된다.
    # 적기 경로(student/rl_opponent.py)만 "target" 을 넘긴다.
    own = ownship_state
    tgt = target_state

    # --- 9/9 안에서만 계산 -------------------------------------------------
    distance = float(geo_info._get_distance(own, tgt))
    az, el = geo_info._get_los_angle(own, tgt)          # 동체 기준, 부호 있음
    az, el = float(az), float(el)
    ata2d = float(geo_info._get_antenna_train_angle(own, tgt, True))   # 롤 불변
    threat_ata = _ata_deg(tgt, own)          # 플랫폼 3D ATA 결함 회피 (위 참조)

    rel = np.array([float(tgt[0]) - float(own[0]),
                    float(tgt[1]) - float(own[1]),
                    float(tgt[2]) - float(own[2])])
    d_safe = max(distance, 1e-6)
    los_unit = rel / d_safe
    v_rel = _ned_velocity(tgt) - _ned_velocity(own)

    # 접근할 때 **양수**. GeoMathUtil 의 rel 은 (적 - 나) 이므로 v_rel·los 는
    # 접근 시 음수 -> 부호를 뒤집는다. 이 규약을 바꾸면 정책이 조용히 반대로 배운다.
    closure_rate = -float(v_rel @ los_unit)

    # LOS 각속도를 동체축으로. z 성분 = 방위(좌우), y 성분 = 고각(상하).
    # 유도: du/dt = w x u, u ~ (1,0,0) 이면 w_z -> +y 드리프트, w_y -> -z 드리프트.
    omega_body = _t_nb(own) @ (np.cross(rel, v_rel) / (d_safe * d_safe)) / _D2R

    feats: list[float] = []
    names: list[str] = []

    def add(name: str, value: float) -> None:
        names.append(name)
        feats.append(float(value))

    # ① 적기가 어디 있나 --------------------------------------------------
    add("distance", normalize(distance, 0.0, 3000.0))
    # 롤 불변 수평 방위각. **sin/cos 로 준다 — 원값 ±180 은 불연속이다.**
    # 실측(115,988 스텝): |ata2d| > 170도 인 스텝이 **7.44%**. 적이 정후방을 지날 때
    # 180.00 -> +1.0000, 180.01 -> -0.9999 로 입력이 **2.0 만큼 점프**한다.
    # 0.01도 차이에 입력이 통째로 뒤집히면 신경망이 근처 상태를 전혀 다르게 본다.
    # (옛 기록의 "15초간 뱅크 +169 <-> -177 왕복, 6km 이탈"이 이 경계다.)
    # sin: 좌우 부호(정면·정후방에서 0) / cos: 앞뒤 크기. 둘 다 연속이다.
    add("sin_ata2d", math.sin(ata2d * _D2R))
    add("cos_ata2d", math.cos(ata2d * _D2R))

    # ② 얼마나 정확히 겨누나 (부호 있음 — 측정상 절댓값보다 2.5배 낫다) ----
    add("los_az", normalize(az, -15.0, 15.0))           # 1° = 전체의 6.7%
    add("los_el", normalize(el, -45.0, 45.0))

    # ③ 적기가 어떻게 움직이나 -------------------------------------------
    add("closure_rate", normalize(closure_rate, -700.0, 700.0))
    add("los_rate_az", normalize(float(omega_body[2]), -30.0, 30.0))
    add("los_rate_el", normalize(float(omega_body[1]), -30.0, 30.0))

    # ④ 내가 위험한가 -----------------------------------------------------
    add("threat_ata", normalize(threat_ata, 0.0, 30.0))

    # ⑤ 내 상태 -----------------------------------------------------------
    add("sin_roll", math.sin(float(own[StateIndex.ROLL]) * _D2R))
    add("cos_roll", math.cos(float(own[StateIndex.ROLL]) * _D2R))
    add("pitch", normalize(float(own[StateIndex.PITCH]), -90.0, 90.0))
    add("alt", normalize(-float(own[StateIndex.D]), 0.0, 14000.0))
    # 내 속도. 선회율이 속도에 반비례한다: omega = g*sqrt(n^2-1)/V.
    # 빠르면 크게 돌고 느리면 작게 돈다 — 자기 선회 능력을 알아야 한다.
    add("speed", normalize(
        math.sqrt(float(own[IDX_U]) ** 2 + float(own[IDX_V]) ** 2
                  + float(own[IDX_W]) ** 2), 50.0, 400.0))
    # 적과 나의 고도 차. 후보 20개를 기준선에 하나씩 더해 잰 실험에서
    # **유일하게 잡음(+-0.013)을 넘은 개선**이었다(+0.026).
    add("delta_alt", normalize(
        (-float(tgt[StateIndex.D])) - (-float(own[StateIndex.D])), -2000.0, 2000.0))

    # ⑥ 시간 -----------------------------------------------------------
    add("time_norm", normalize(_elapsed_s(own, observer), 0.0, 200.0))

    assert len(feats) == OBSERVATION_SIZE, (
        f"OBSERVATION_SIZE({OBSERVATION_SIZE}) != 활성 특징 개수({len(feats)})"
    )
    global _FEATURE_NAMES
    _FEATURE_NAMES = tuple(names)
    return np.asarray(feats, dtype=np.float32)


# 피처 이름은 **정적으로도** 알 수 있어야 한다. `_FEATURE_NAMES` 는
# `build_observation` 이 한 번 돌아야 채워지는데, 학습 스크립트는 env 를 만들기
# 전에 `describe_observation()` 을 불러 번들 metadata 의 observation_summary 로
# 기록한다. 그대로 두면 **features 가 빈 채로 기록된다**(실측 확인).
# 순서는 build_observation 의 add() 호출 순서와 반드시 같아야 한다.
FEATURE_NAMES: tuple[str, ...] = (
    "distance", "sin_ata2d", "cos_ata2d", "los_az", "los_el",
    "closure_rate", "los_rate_az", "los_rate_el", "threat_ata",
    "sin_roll", "cos_roll", "pitch", "alt", "speed", "delta_alt", "time_norm",
)
assert len(FEATURE_NAMES) == OBSERVATION_SIZE, (
    f"FEATURE_NAMES({len(FEATURE_NAMES)}) != OBSERVATION_SIZE({OBSERVATION_SIZE})"
)


def describe_observation():
    return {
        "mode": OBSERVATION_MODE,
        "size": OBSERVATION_SIZE,
        "features": list(_FEATURE_NAMES) if _FEATURE_NAMES else list(FEATURE_NAMES),
        "description": (
            "student 16-D: 대회 9/9 패킷에서만 유도. 부호 있는 조준 오차 + "
            "LOS 각속도 + 위협각 + 최소 자기상태."
        ),
    }
