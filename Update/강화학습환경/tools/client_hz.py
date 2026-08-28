# -*- coding: utf-8 -*-
"""정책을 붙이면서 서버 틱 주기를 동시에 잰다 (Ray 없이).

사용:
  python tools/client_hz.py <bundle_dir> <team_name> [port]

왜 필요한가: --action-repeat 6 은 '서버 60 Hz' 전제다. 서버가 30 Hz 면
6프레임이 0.2초가 되어 우리 정책은 10 Hz 가 아니라 5 Hz 로 조종한다.
반응이 절반으로 느려져 학습 때처럼 못 싸운다.

my_submission.py 의 Ray-free 로더를 그대로 쓴다(기동 빠름, 제출 경로와 동일).
"""
import os, sys, time
os.environ.pop("AIP_STEP_RATIO", None)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "src"))

import student.my_submission as SUB
from dogfight.ai.rl_action_provider import RLActionProvider
from dogfight.ai.student_hooks import load_observation_hook
from dogfight.unreal import AIType, ProviderCommandPolicy, UnrealAIPilotUDPClient
from dogfight.unreal.policies import plane_info_to_state
from GeoMathUtil import GeometryInfo
import student.my_observation as OBSMOD
import numpy as _np
_GEO = GeometryInfo()
_NAMES = OBSMOD.describe_observation()["features"]

# 대회 WEZ 데미지 모델 (single_agent_env._wez_damage / _active_wez_envelopes 와 동일).
# 패킷에 HP 필드가 없어(<iQb3f3f3f> = 위치·자세·속도뿐) 서버 체력을 직접 못 본다.
# 그래서 기하로 **양방향 딜을 우리가 적분**한다. 뷰어 HP 바와 대조하면
# 서버 데미지 모델이 학습과 같은지 확인된다.
_WEZ_PHASES = [   # (경과초 이상, 반각(도), 최소m, 최대m, 배율)
    (0.0,   1.0, 152.4, 914.4,  1.0),
    (100.0, 2.0, 152.4, 1066.8, 0.3),
    (150.0, 3.0, 152.4, 1219.2, 0.1),
]
_DT = 1.0 / 60.0


def _wez_dmg(t_s, dist_m, ata_deg):
    for after, half, lo, hi, scale in _WEZ_PHASES:
        if t_s < after:
            continue
        if not (lo <= dist_m <= hi):
            continue
        if abs(ata_deg) > half:
            continue
        return (hi - dist_m) / (hi - lo) * _DT * scale
    return 0.0

BUNDLE = sys.argv[1]
TEAM = sys.argv[2] if len(sys.argv) > 2 else "AeroFryer"
PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 9998
IP = sys.argv[4] if len(sys.argv) > 4 else "127.0.0.1"
REPEAT = 6

oh = load_observation_hook("student.my_observation")
provider = RLActionProvider(bundle_dir=BUNDLE,
                            algorithm_factory=SUB._algorithm_factory,
                            policy_id="default_policy", explore=False)


class HzPolicy(ProviderCommandPolicy):
    """PlaneInfo 쌍마다 1회 불린다 -> 호출 빈도 = 서버 틱."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._n = 0
        self._t0 = None
        self._last_report = 0.0
        self._wez = 0          # WEZ 안 결정스텝 (152.4~914.4 m 이고 |ATA|<=1)
        self._band = 0         # 사거리 안에는 있었던 스텝
        self._dsteps = 0       # 전체 결정스텝
        self._best_ata = 999.0
        self._min_d = 1e9
        self._obs = []          # 16채널 전수 기록
        self._raw = []          # 원시 9+9 + 16채널
        self._hp_me = 1.0       # 우리가 기하로 적분한 체력
        self._hp_foe = 1.0

    def reset(self, context):
        if getattr(self, "_obs", None):
            self._dump_obs()
        super().reset(context)
        self._n = 0
        self._t0 = None
        print("[HZ] 리셋 (새 판 시작)", flush=True)

    def _dump_obs(self):
        M = _np.array(self._obs)
        print("[OBS] ===== 16채널 전수 (%d스텝, 실서버) =====" % len(M), flush=True)
        print("[OBS] %-14s %8s %8s %8s %8s %7s" % ("채널", "평균", "표준", "최소", "최대", "포화%"),
              flush=True)
        for _i, _nm in enumerate(_NAMES):
            c = M[:, _i]
            print("[OBS] %-14s %8.3f %8.3f %8.3f %8.3f %7.1f"
                  % (_nm, c.mean(), c.std(), c.min(), c.max(),
                     100.0 * _np.mean(_np.abs(c) > 0.99)), flush=True)
        self._obs = []
        if self._raw:
            import csv as _csv
            fn = os.environ.get("OBS_DUMP", "obs_dump.csv")
            with open(fn, "w", newline="", encoding="utf-8") as f:
                w = _csv.writer(f)
                w.writerow(["a_roll","a_pitch","a_yaw","a_thr",
                            "ox","oy","oz","oroll","opitch","oyaw","ou","ov","ow",
                            "ex","ey","ez","eroll","epitch","eyaw","eu","ev","ew"] + _NAMES)
                w.writerows(self._raw)
            print("[OBS] 원시덤프 저장 %s (%d행)" % (fn, len(self._raw)), flush=True)
            self._raw = []

    def compute_command(self, context):
        now = time.perf_counter()
        if self._t0 is None:
            self._t0 = now
            self._last_report = now
            print("[HZ] 첫 PlaneInfo 쌍 수신", flush=True)
            op = context.own_plane.plane_info
            ep = context.enemy_plane.plane_info
            if op is not None and ep is not None:
                import math as _m
                d = _m.dist((op.position.x, op.position.y, op.position.z),
                            (ep.position.x, ep.position.y, ep.position.z))
                sp = _m.sqrt(op.velocity.x**2 + op.velocity.y**2 + op.velocity.z**2)
                # LOS 방위 (월드 XY) 대비 내 yaw -> 초기 ATA
                los = _m.degrees(_m.atan2(ep.position.y - op.position.y,
                                          ep.position.x - op.position.x))
                ata = (los - op.rotation.yaw + 180.0) % 360.0 - 180.0
                print("[IC] 거리 %.0f m | 고도 %.0f / %.0f m | 속도 %.1f m/s"
                      % (d, op.position.z, ep.position.z, sp), flush=True)
                print("[IC] yaw 나 %.1f / 적 %.1f | pitch %.1f / %.1f | roll %.1f / %.1f"
                      % (op.rotation.yaw, ep.rotation.yaw, op.rotation.pitch,
                         ep.rotation.pitch, op.rotation.roll, ep.rotation.roll), flush=True)
                print("[IC] 초기 ATA %.1f deg  (0=정면조준, 90=측면, 180=등짐)"
                      % ata, flush=True)
        self._n += 1
        # HP 적분은 **매 프레임**(60 Hz) 한다 — 서버 틱과 같은 주기여야 맞다.
        _op = context.own_plane.plane_info
        _ep = context.enemy_plane.plane_info
        if _op is not None and _ep is not None and self._t0 is not None:
            import math as _m2
            _dx = _ep.position.x - _op.position.x
            _dy = _ep.position.y - _op.position.y
            _dz = _ep.position.z - _op.position.z
            _d = _m2.sqrt(_dx*_dx + _dy*_dy + _dz*_dz)
            if _d > 1e-6:
                _t = self._n / 60.0
                _az = _m2.degrees(_m2.atan2(_dy, _dx))
                _el = _m2.degrees(_m2.asin(max(-1.0, min(1.0, _dz / _d))))
                _a1 = _m2.hypot((_az - _op.rotation.yaw + 180) % 360 - 180,
                                _el - _op.rotation.pitch)
                _a2 = _m2.hypot((_az + 180 - _ep.rotation.yaw + 180) % 360 - 180,
                                -_el - _ep.rotation.pitch)
                self._hp_foe -= _wez_dmg(_t, _d, _a1)
                self._hp_me -= _wez_dmg(_t, _d, _a2)
        # 결정스텝마다 WEZ 판정 (학습과 같은 기준: 152.4~914.4 m, |ATA| <= 1도)
        if self._n % REPEAT == 1:
            op = context.own_plane.plane_info
            ep = context.enemy_plane.plane_info
            if op is not None and ep is not None:
                import math as _m
                dx = ep.position.x - op.position.x
                dy = ep.position.y - op.position.y
                dz = ep.position.z - op.position.z
                d = _m.sqrt(dx*dx + dy*dy + dz*dz)
                los_az = _m.degrees(_m.atan2(dy, dx))
                los_el = _m.degrees(_m.asin(max(-1.0, min(1.0, dz / d)))) if d > 0 else 0.0
                daz = (los_az - op.rotation.yaw + 180.0) % 360.0 - 180.0
                dele = los_el - op.rotation.pitch
                ata = _m.hypot(daz, dele)
                self._dsteps += 1
                self._min_d = min(self._min_d, d)
                # 정책과 동일한 경로로 관측을 만들어 기록한다
                try:
                    os_ = plane_info_to_state(op)
                    ts_ = plane_info_to_state(ep)
                    # [계측 오염 방지] build_observation 은 호출될 때마다
                    # my_observation._slots 의 경과시간 카운터를 올린다.
                    # 계측용으로 한 번 더 부르면 정책이 보는 time_norm 이
                    # **2배 속도**로 흐른다(실측: 100초에 +1.0 포화).
                    # 관측 모듈은 학습본 그대로 두고, 여기서 슬롯을
                    # 저장/복원해 정책 쪽 카운터를 건드리지 않는다.
                    _saved = {k: (v[0].copy(), v[1]) for k, v in OBSMOD._slots.items()}
                    v16 = oh["build_observation"](os_, ts_, _GEO)
                    OBSMOD._slots.clear()
                    OBSMOD._slots.update(_saved)
                    self._obs.append(_np.asarray(v16, _np.float64).copy())
                    # 원시 9+9 와 그때의 16채널을 같이 남긴다.
                    # 나중에 학습 경로로 같은 9+9 를 넣어 관측이 동일한지 대조한다.
                    _act = self._cached_action
                    _a4 = list(_np.asarray(_act, _np.float64).reshape(-1)[:4]) if _act is not None else [0.0]*4
                    self._raw.append(_a4 + [
                        op.position.x, op.position.y, op.position.z,
                        op.rotation.roll, op.rotation.pitch, op.rotation.yaw,
                        op.velocity.x, op.velocity.y, op.velocity.z,
                        ep.position.x, ep.position.y, ep.position.z,
                        ep.rotation.roll, ep.rotation.pitch, ep.rotation.yaw,
                        ep.velocity.x, ep.velocity.y, ep.velocity.z,
                    ] + list(_np.asarray(v16, _np.float64)))
                except Exception as _e:
                    if len(self._obs) == 0:
                        print("[OBS] 관측 계산 실패: %s" % _e, flush=True)
                if 152.4 <= d <= 914.4:
                    self._band += 1
                    self._best_ata = min(self._best_ata, ata)
                    if ata <= 1.0:
                        self._wez += 1
        if now - self._last_report >= 3.0:
            dt = now - self._t0
            hz = self._n / dt if dt > 0 else 0.0
            op = context.own_plane.plane_info
            ep = context.enemy_plane.plane_info
            extra = ""
            if op is not None and ep is not None:
                import math as _m
                spd = _m.sqrt(op.velocity.x**2 + op.velocity.y**2 + op.velocity.z**2)
                esp = _m.sqrt(ep.velocity.x**2 + ep.velocity.y**2 + ep.velocity.z**2)
                dist = _m.dist((op.position.x, op.position.y, op.position.z),
                               (ep.position.x, ep.position.y, ep.position.z))
                extra = ("  속도 %5.1f (적 %5.1f)  거리 %6.0f m  고도 %6.0f m"
                         % (spd, esp, dist, op.position.z))
            wz = ("  사거리 %d/%d스텝  WEZ %d스텝  최소거리 %.0f m  밴드내 최소ATA %.1f도"
                  % (self._band, self._dsteps, self._wez, self._min_d,
                     self._best_ata if self._best_ata < 900 else -1))
            print("[HZ] %6.1f초  %5.1f Hz%s%s" % (dt, hz, extra, wz), flush=True)
            print("[HP] 내 체력 %.3f   적 체력 %.3f   (기하로 적분, 뷰어 HP바와 대조)"
                  % (max(0.0, self._hp_me), max(0.0, self._hp_foe)), flush=True)
            if len(self._obs) > 30:
                M = _np.array(self._obs)
                dead = []
                for _i, _nm in enumerate(_NAMES):
                    c = M[:, _i]
                    sat = 100.0 * _np.mean(_np.abs(c) > 0.99)
                    if c.std() < 0.02 or sat > 90.0:
                        dead.append("%s(std %.3f, 포화 %.0f%%)" % (_nm, c.std(), sat))
                print("[OBS] %d스텝  죽은채널: %s"
                      % (len(self._obs), ", ".join(dead) if dead else "없음"), flush=True)
            self._last_report = now
        return super().compute_command(context)


policy = HzPolicy(
    action_provider=provider,
    observation_mode=oh["mode"],
    observation_fn=oh["build_observation"],
    ownship_force_side=1,
    target_force_side=2,
    action_repeat=REPEAT,
    debug_action_repeat=False,
)

import hashlib as _hl
_wh = _hl.sha256(open(os.path.join(BUNDLE, "policy_weights.pkl.gz"), "rb").read()).hexdigest()[:16]
print("=== %s ===" % TEAM)
print("bundle : %s" % BUNDLE)
print("weights sha256[:16] : %s   <- 오프라인 평가와 같아야 한다" % _wh)
print("server : %s:%d   action-repeat=%d" % (IP, PORT, REPEAT))
# client._receive_loop 은 OSError(윈도우 UDP ICMP port-unreachable)에서 즉시
# break 한다 -> 판이 끝나거나 서버가 잠깐 안 받으면 클라이언트가 조용히 죽는다.
# 여기서 새 소켓으로 다시 붙여 계속 살아있게 한다.
try:
    while True:
        client = UnrealAIPilotUDPClient(
            command_policy=policy, server_ip=IP, server_port=PORT, team_name=TEAM,
            ai_type=AIType.AI_RL if hasattr(AIType, "AI_RL") else 1,
            heartbeat_interval_sec=1.0, command_delay_sec=0.0,
            recv_timeout_sec=0.2, enable_terminal_monitor=False,
        )
        try:
            client.run()
        except Exception as exc:
            print("[HZ] 접속 예외: %s" % exc, flush=True)
        try:
            if getattr(policy, "_obs", None):
                policy._dump_obs()
        except Exception as _e:
            print("[OBS] 덤프 실패 %s" % _e, flush=True)
        print("[HZ] 접속 끊김 — 2초 뒤 재접속", flush=True)
        time.sleep(2.0)
except KeyboardInterrupt:
    pass
finally:
    provider.close()
