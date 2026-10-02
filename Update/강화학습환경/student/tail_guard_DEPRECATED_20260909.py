# -*- coding: utf-8 -*-
"""[MOD-TAILGUARD] 꼬리 가드 — 후방 접근 중 스로틀만 규칙으로 제한한다. (실험 단계)

빼는 법
  1) env_config["tail_guard"] = False  (기본값이 False 라 아무것도 안 한다)
  2) 완전히 지우려면 이 파일 + single_agent_env.py 의 [MOD-TAILGUARD] 블록만 삭제

왜 만들었나 — 전부 실측 (2026-09-08~09)
  · 뒤로 접근할 때 접근율 중앙 113 m/s, 거리 1,228 m, 남은 시간 6.8초
  · 그 국면의 뱅크각 중앙 75° (60° 이상이 62%) → 깊은 선회 중이다
  · 스로틀 계단 응답:  수평 직진 아이들 Δv −27 m/s / 선회 70° 아이들 Δv −130 m/s
                      시정수 12~13초 · 무효시간 0.5초
  · 뒤를 잡아도 3.3초만 유지하고 놓친다 (격추엔 1.56초 연속 조준 필요)

왜 규칙인가
  스로틀 시정수가 12초인데 LSTM 기억창과 BPTT 는 3.2초다. 지금 줄인 대가가
  12초 뒤에 나오므로 기울기가 닿지 않는다 — 보상을 어떻게 짜도 정책이 배울 수 없다.
  반면 12초 앞을 내다보는 건 물리 계산이라 규칙으로 정확히 된다. 덱 가드와 같은 논리다.

왜 일찍 발동하나
  거리 구간별로 "후방 접근 조건 성립 → 20초 안에 사거리 안 조준"까지 이어진 비율:
    400~800 m 87% · 800~1200 m 95% · 1200~1600 m 97% · 1600~3000 m 100%
  멀수록 오히려 확실하게 이어진다. 헛발동이 아니다.

주의
  · 정책 좌표계 [-1, 1] 에서 자른다. 제출 경로의 (x+1)/2 변환 **이전**이다.
  · 서버는 state[0:9] 만 채운다. ALT(44)·KCAS(12)·HEALTH(45) 는 0 이므로 안 읽는다.
"""
from __future__ import annotations

import math

# --- 발동 범위 (실측 기반) --------------------------------------------------
AIM_ON_DEG = 40.0        # 적을 향해 가는 중
AIM_OFF_DEG = 55.0
FOE_REAR_DEG = 110.0     # 적의 후방 반구에 있다
FOE_REAR_OFF_DEG = 90.0
DIST_MIN_M = 400.0       # 이보다 가까우면 이미 늦었다 — 개입하지 않는다
DIST_MAX_M = 3000.0      # 표본이 충분한 상한 (3 km 위는 7판뿐이라 제외)
CLOSE_ON_MPS = 40.0      # 이보다 빨리 접근하면 지나칠 위험

# --- 목표 접근율: 멀면 빨리, 가까우면 천천히 --------------------------------
TGT_K = 20.0             # 목표 = 거리 / 20
TGT_MIN_MPS = 25.0
TGT_MAX_MPS = 45.0       # 실전 접근율 중앙 113 m/s 대비 문턱이 높아 90 -> 45 (2026-09-09)

# --- 스로틀 응답 (계단 실측) ------------------------------------------------
TAU_S = 12.0             # 시정수
DV_TURN_MPS = 130.0      # 뱅크 >= 45° 에서 아이들이 만드는 최대 감속
DV_LEVEL_MPS = 27.0      # 수평 직진에서
TURN_BANK_DEG = 45.0
BAND_CENTER_M = 533.0    # 사거리 152~914 의 중앙

SPEED_FLOOR_MPS = 150.0  # 이 아래로는 개입하지 않는다 (에너지 방어)

FIRE_COUNT = [0]          # [측정용] 발동 스텝 수
CHECK_COUNT = [0]         # [측정용] 호출 횟수 (조건 무관)


def reset_counter():
    FIRE_COUNT[0] = 0
    CHECK_COUNT[0] = 0


_ROLL, _PITCH, _YAW = 3, 4, 5
_U, _V, _W = 6, 7, 8


def _t_nb(s):
    r, p, y = (math.radians(float(s[_ROLL])), math.radians(float(s[_PITCH])),
               math.radians(float(s[_YAW])))
    cr, sr = math.cos(r), math.sin(r)
    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    return ((cp * cy, cp * sy, -sp),
            (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, sr * cp),
            (cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp))


def _ned_velocity(s):
    t = _t_nb(s)
    b = (float(s[_U]), float(s[_V]), float(s[_W]))
    return tuple(sum(t[k][i] * b[k] for k in range(3)) for i in range(3))


def _ata_deg(me, foe):
    r = [float(foe[i]) - float(me[i]) for i in range(3)]
    d = math.sqrt(sum(x * x for x in r))
    if d < 1e-6:
        return 0.0
    fwd = _t_nb(me)[0]
    c = sum(fwd[i] * r[i] for i in range(3)) / d
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def geometry(own, tgt):
    """(거리, 내 조준각, 적 기수각, 접근율, 내 속도, 내 뱅크절대값)."""
    r = [float(tgt[i]) - float(own[i]) for i in range(3)]
    d = math.sqrt(sum(x * x for x in r))
    los = [x / max(d, 1e-6) for x in r]
    vo, vt = _ned_velocity(own), _ned_velocity(tgt)
    closure = -sum((vt[i] - vo[i]) * los[i] for i in range(3))
    spd = math.sqrt(sum(x * x for x in vo))
    bank = abs(((float(own[_ROLL]) + 180.0) % 360.0) - 180.0)
    return d, _ata_deg(own, tgt), _ata_deg(tgt, own), closure, spd, bank


def guard_step(action, own_state, target_state, active=0,
               throttle_range=(-1.0, 1.0)):
    """스로틀만 제한한다. (action, active') 반환. action 은 [롤, 피치, 요, 스로틀]."""
    CHECK_COUNT[0] += 1
    lo, hi = float(throttle_range[0]), float(throttle_range[1])
    d, aim, foe_aim, closure, spd, bank = geometry(own_state, target_state)

    if spd < SPEED_FLOOR_MPS or not (DIST_MIN_M <= d <= DIST_MAX_M):
        return action, 0
    if active:
        on = aim <= AIM_OFF_DEG and foe_aim >= FOE_REAR_OFF_DEG
    else:
        on = aim <= AIM_ON_DEG and foe_aim >= FOE_REAR_DEG and closure > CLOSE_ON_MPS
    if not on:
        return action, 0

    target_closure = max(TGT_MIN_MPS, min(TGT_MAX_MPS, d / TGT_K))
    if closure <= target_closure:
        return action, 0

    # 남은 시간 동안 아이들이 만들 수 있는 감속량 (1차 지연)
    t_go = max((d - BAND_CENTER_M) / max(closure, 1e-6), 0.1)
    dv_max = DV_TURN_MPS if bank >= TURN_BANK_DEG else DV_LEVEL_MPS
    reachable = dv_max * (1.0 - math.exp(-t_go / TAU_S))
    need = closure - target_closure
    k = max(0.0, min(1.0, need / max(reachable, 1e-6)))   # 필요/가능 비율

    out = list(action)
    out[3] = min(float(out[3]), hi - k * (hi - lo))
    FIRE_COUNT[0] += 1
    return out, 1
