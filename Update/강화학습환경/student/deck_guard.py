# -*- coding: utf-8 -*-
"""저고도 추락 방지 가드 (2026-08-31).

정책 행동의 pitch 채널만 강제로 당긴다(pitch −1 = 기수 들기, 실측:
cmd +1 → pitch −71° 강하 / cmd −1 → pitch +68.6° 상승).

발동 조건(모두 만족):
 - 고도 < guard_alt_m (기본 457.2 m = 1,500 ft; 추락 판정은 304.8 m = 1,000 ft)
 - 침하율 vz < sink_gate_mps (기본 −10 m/s)
 - |roll| <= roll_gate_deg (기본 100°; 배면에서는 당기면 지면 방향 가속이라 개입하지 않는다)

발동 중 throttle (2026-08-31): 기수가 수평 아래(pitch<0)면 최소 — 당김 선회
반경은 V^2 에 비례하므로 감속이 고도 손실을 줄인다. 기수가 수평 위로 올라오면
최대 — 빠른 이탈·에너지 회복. roll·rudder 는 정책 출력 그대로 둔다.
침하율은 호출 간 고도 미분으로 추정한다(dt: info.frame_index/60 이 있으면 그것,
없으면 0.1 s = 10 Hz 정책 주기).
"""
from __future__ import annotations

import math

import numpy as np

GUARD_ALT_M = 457.2       # 1,500 ft
SINK_GATE_MPS = -10.0
ROLL_GATE_DEG = 100.0
FLOOR_M = 304.8           # 추락 판정선 1,000 ft
RELEASE_ALT_M = 609.6     # 해제 조건 1: 고도 >= 2,000 ft (관측 램프 무릎과 동일)
RELEASE_DIST_M = 800.0    # 해제 조건 2: 적기 거리 >= 800 m (WEZ 914 m 근방 밖)
CLIMB_PITCH_DEG = 25.0    # 유지 단계 목표 상승각
HARD_FLOOR_M = 350.0      # [2026-09-04 사용자 지시] 2차 가드. 이 고도 아래면 침하율과 무관하게
                          #   무조건 발동하고, 위로 올라와 더 안 내려가면 즉시 해제한다.
                          #   1차 가드는 vz < -10 m/s 를 요구해 완만한 강하에는 안 켜졌다.
TF_GATE_S = 4.0           # 예측 트리거: 지면 도달 예상 < 4 s 면 고도 무관 발동.
                          # 실측 ep9(-165 m/s 급강하): 457 m 고정 발동 -> 바닥 301 m 추락(5 m 차),
                          # 게이트 3 s(785 m 발동) -> 바닥 301 m 로 마진 0. 발동~바닥까지 고도
                          # 소모 약 480 m(풀당김 침하율 감쇠 ~45 m/s^2 + 자세 전환 지연) -> 4 s 로 여유.
_ALT_IDX = 44             # StateIndex.ALT (m)
_ROLL_IDX = 3             # StateIndex.ROLL (deg)
_PITCH_IDX = 4            # StateIndex.PITCH (deg)


def guard_pitch(action, alt_m, vz_mps, roll_deg, pitch_deg=0.0,
                guard_alt_m=GUARD_ALT_M, sink_gate_mps=SINK_GATE_MPS,
                roll_gate_deg=ROLL_GATE_DEG, throttle_range=(0.0, 1.0)):
    """(action, fired). 발동 시 회복 조종 사본을 돌려준다 — 실기 GCAS 순서.

    - roll: 수평 복귀 P 제어 clip(−roll/30) (실측: roll_cmd +1 → roll 증가).
      뱅크 70~85° 강하는 양력 수직성분이 cos(bank) 로 죽어 당김이 안 먹힌다
      (실측 ep9: 뱅크 −65~−85° 에서 457/785/966 m 발동 전부 바닥 ~301 m).
    - pitch: 날개가 선 뒤(|roll|<=roll_gate_deg)에만 −1.0 최대 당김.
      배면에서 당기면 지면 방향 가속이므로 그때는 정책 pitch 유지.
    - throttle: pitch_deg<0(기수 수평 아래)면 throttle_range[0](최소 — 당김 반경 ∝ V^2),
      아니면 [1](최대 — 빠른 이탈). 제출 경로는 (0.0, 1.0), env 원시 경로는 (-1.0, 1.0).
    """
    signed_roll = ((float(roll_deg) + 180.0) % 360.0) - 180.0
    roll = abs(signed_roll)
    alt = float(alt_m); vz = float(vz_mps)
    low = alt < guard_alt_m or (alt - FLOOR_M) < TF_GATE_S * max(-vz, 0.0)
    if low and vz < sink_gate_mps:
        out = np.asarray(action, dtype=np.float32).copy()
        out[0] = float(np.clip(-signed_roll / 30.0, -1.0, 1.0))
        if roll <= roll_gate_deg:
            out[1] = -1.0
        out[3] = throttle_range[0] if float(pitch_deg) < 0.0 else throttle_range[1]
        return out, True
    return action, False


# ── [MOD-GUARDPHYS 2026-09-05 사용자 지시] 물리식 단일 가드 ─────────────────────
#   "가드 2단 말고 하나로, 추락이 확정일 때만 켜져라 — 아래 적을 잡는 강하를 방해하면 안 된다."
#   발동 조건을 고정 고도가 아니라 **지금 이 강하에서 빠져나오는 데 드는 고도**로 판단한다.
#     H_needed = V·sinγ·T_REACT + V²(1−cosγ) / (g·(n−1)),   n = N_A + N_B·V
#   계수는 시뮬 실측(student/tools/dive_calib.py, 15개 조건)으로 피팅했다: rms 16 m.
#     V 227 γ16° →  27 m   /  V 258 γ30° → 159 m  /  V 264 γ45° → 328 m
#     V 253 γ74° → 709 m   /  V 331 γ73° → 1,002 m
#   같은 식이 완만한 강하(16°: 335 m 에서 발동)와 급강하(74°: 1,000 m 에서 발동)를 다 덮으므로
#   하드플로어 2단이 필요 없다. γ 는 피치가 아니라 실제 비행경로각(sinγ = −vz/V)을 쓴다.
#   해제: 침하가 멈추면(vz ≥ 0) 바로 손을 뗀다 — 재강하가 과해지면 다시 켜진다.
G_MPS2 = 9.80665
T_REACT_S = 0.20          # 롤 수평·G 상승 반응 지연 (피팅)
N_A, N_B = 3.0, 0.020     # 유효 G = N_A + N_B·V  (V 150→6G · 250→8G · 350→10G, 피팅)
N_MIN, N_MAX = 2.0, 12.0
GUARD_MARGIN = 0.15       # 식 대비 여유 15% (피팅 rms 16 m 의 약 2배). 검증에서 조정한다.
GUARD_ABS_MARGIN_M = 15.0 # 절대 여유. 완만각(5~10°)은 필요 고도가 ~30 m 라 15% 가 4 m 뿐이었고
                          #   검증에서 바닥을 1~4 m 스쳤다(1,200 m 시작 · 6조건 · 추락 0 이나 여유 −1~−4 m).
                          #   급강하(700 m+)에선 2% 라 개입 시점에 영향 없다.
LATENCY_S = 0.10          # 결정 주기 1스텝 — 그동안 떨어지는 고도 |vz|·0.1 을 더한다
LOW_ENERGY_MPS = 150.0    # 이 속도 아래면 회복에 에너지가 부족 -> 기수 방향과 무관하게 풀 추력.
                          #   실측(재기동 후 저속 추락 103판): 발동시 V 중앙 99 m/s · 받음각 12°(실속 아님) ·
                          #   가드 스로틀 idle · 회복 내내 감속 · 바닥 8 m 관통. 양력(∝V²)을 회복하려면
                          #   당김이 아니라 속도가 필요하다. 고속(>150)은 기존대로 기수 아래면 idle(선회 반경 축소).
T_LEAD_S = 0.50           # 기수 회전 선행. 검증(dive_validate 2차): 가드가 바닥 ~450 m 에서 풀린 뒤 정책이
                          #   즉시 다시 숙이면 기수가 회전 중(q ≈ −30°/s)인 채로 재발동 -> 회전을 멈추는
                          #   시간이 캘리브(정상 강하, q≈0)에 없어 바닥 2~5 m 모자라 추락(7/21).
                          #   γ_eff = γ + max(−q, 0)·T_LEAD 로 0.5 s 뒤 강하각으로 판단한다.


def h_needed_m(speed_mps, gamma_deg):
    """이 속도·강하각에서 수평까지 빠져나오는 데 드는 고도(m). γ ≤ 0 이면 0."""
    v = max(float(speed_mps), 1.0)
    g = math.radians(max(float(gamma_deg), 0.0))
    n = min(max(N_A + N_B * v, N_MIN), N_MAX)
    return v * math.sin(g) * T_REACT_S + v * v * (1.0 - math.cos(g)) / (G_MPS2 * (n - 1.0))


# ── [MOD-GUARDPHYS 2026-09-06] 실측 엔벨로프 표 ───────────────────────────────
#   수식(n=3+0.02V)은 200~330 m/s·롤0 15점에만 맞춰 저속을 외삽했고, 실측(envelope_map.py,
#   JSBSim 이분탐색 56칸)과 대조하니 저속에서 10배 낮았다(V100 γ30: 식 66 / 실측 749).
#   2차 양력한계 G + 롤 항 + 속도의존 반응시간 4상수 식도 전 칸을 덮으려면 전투속도(200~350)
#   에서 칸당 100~200 m 과잉 발동 → 공격 강하 방해. 그래서 발동선은 **실측 표 보간**으로 잡는다.
#   표 = 가드 자신의 회복 제어로 살아남는 바닥 위 최소 고도(m). 격자 안은 외삽 없음.
_ENV_V = (100.0, 130.0, 160.0, 200.0, 250.0, 300.0, 350.0)
_ENV_G = (30.0, 45.0, 60.0, 75.0)
_ENV_H = {  # roll -> [V][γ]
    0.0: ((749, 1145, 1436, 1900),    # V100 γ75 는 1,700 m 에서도 실패(X) → 1,900 으로 둔다
          (631, 987, 1264, 1528),
          (446, 789, 1013, 1251),
          (168, 446, 565, 776),
          (182, 340, 538, 749),
          (208, 393, 631, 895),
          (248, 499, 789, 1132)),
    90.0: ((657, 1027, 1278, 1660),
           (591, 921, 1238, 1436),
           (485, 749, 1027, 1317),
           (261, 538, 763, 881),
           (208, 380, 578, 789),
           (248, 459, 697, 947),
           (300, 565, 868, 1198)),
}
ENV_MARGIN = 0.10         # 표 자체가 가드 제어 실측이라 여유는 10% + 절대 15 m 만 둔다
ROLL_RATE_DPS = 250.0     # 배면(>90°)은 90° 표값 + 수평까지 도는 동안의 침하 V·sinγ·(φ−90)/p


def _interp1(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


def h_table_m(speed_mps, gamma_deg, roll_deg):
    """실측 엔벨로프 보간. γ ≤ 0 이면 0. 격자 밖은 안전 쪽으로 늘린다."""
    v = float(speed_mps); g = float(gamma_deg); phi = abs(float(roll_deg))
    if g <= 0.0:
        return 0.0
    def at_roll(tab):
        # γ 축: 30° 아래는 (0,0)~(30,H30) 선형, 75° 위는 60→75 기울기로 연장
        cols = []
        for row in tab:
            if g < _ENV_G[0]:
                cols.append(row[0] * g / _ENV_G[0])
            elif g > _ENV_G[-1]:
                cols.append(row[-1] + (row[-1] - row[-2]) * (g - _ENV_G[-1]) / (_ENV_G[-1] - _ENV_G[-2]))
            else:
                cols.append(_interp1(_ENV_G, row, g))
        # V 축: 100 아래는 100 행(회복 거의 불가), 350 위는 (V/350)² 스케일
        if v <= _ENV_V[0]:
            return cols[0]
        if v >= _ENV_V[-1]:
            return cols[-1] * (v / _ENV_V[-1]) ** 2
        return _interp1(_ENV_V, cols, v)
    h0 = at_roll(_ENV_H[0.0]); h90 = at_roll(_ENV_H[90.0])
    if phi <= 90.0:
        return h0 + (h90 - h0) * (phi / 90.0)
    extra = v * math.sin(math.radians(min(g, 89.0))) * ((phi - 90.0) / ROLL_RATE_DPS)
    return h90 + extra


def guard_step(action, alt_m, vz_mps, roll_deg, pitch_deg, dist_m, active,
               throttle_range=(0.0, 1.0), enemy_alt_m=None, speed_mps=None,
               pitch_rate_dps=None):
    """상태 있는 가드 한 스텝. (action, active') 를 돌려준다. active' 는 0/1 (정수).

    OFF -> ON: 침하 중이고 (고도 − 추락선) < H_needed(V, γ)·(1+여유) + |vz|·지연.
    ON  -> OFF: vz ≥ 0 (침하가 멈춤).
    ON 동안: 롤 수평 P 제어 → 날개가 서면 최대 당김, throttle 은 기수 아래 최소 / 위 최대.
    speed_mps 가 없으면 vz 와 피치로 근사한다(V ≈ |vz| / sin|pitch|).
    dist_m / enemy_alt_m 은 호환용으로 받기만 한다(더 이상 안 쓴다).
    """
    signed_roll = ((float(roll_deg) + 180.0) % 360.0) - 180.0
    roll = abs(signed_roll)
    alt = float(alt_m); vz = float(vz_mps); pitch = float(pitch_deg)
    if speed_mps is not None and float(speed_mps) > 1.0:
        v = float(speed_mps)
    else:
        sp = math.sin(math.radians(abs(pitch)))
        v = abs(vz) / sp if sp > 0.05 else 200.0
    gamma = math.degrees(math.asin(max(-1.0, min(1.0, -vz / max(v, 1.0)))))   # 강하면 +
    if pitch_rate_dps is not None:
        gamma = min(gamma + max(-float(pitch_rate_dps), 0.0) * T_LEAD_S, 89.0)   # 숙이는 중이면 선행
    need = (h_table_m(v, gamma, roll) * (1.0 + ENV_MARGIN) + GUARD_ABS_MARGIN_M
            + abs(min(vz, 0.0)) * LATENCY_S)
    on = bool(active)
    if on:
        if vz >= 0.0:
            on = False
    else:
        on = (vz < 0.0) and ((alt - FLOOR_M) < need)
    if not on:
        return action, 0
    out = np.asarray(action, dtype=np.float32).copy()
    out[0] = float(np.clip(-signed_roll / 30.0, -1.0, 1.0))
    if roll <= ROLL_GATE_DEG:
        out[1] = -1.0
    # 저속이면 항상 풀 추력(에너지 회복), 고속이면 기수 아래일 때만 idle(선회 반경 축소).
    if v < LOW_ENERGY_MPS or pitch >= 0.0:
        out[3] = throttle_range[1]
    else:
        out[3] = throttle_range[0]
    return out, 1


class DeckGuardProvider:
    """ActionProvider 래퍼: 내부 provider 의 행동에 guard_pitch 를 덧씌운다."""

    def __init__(self, inner, verbose=False):
        self.inner = inner
        self.verbose = verbose
        self.fired_steps = 0
        self._active = False
        self._last_alt = None
        self._last_t = None
        self._last_pitch = None
        self._step = 0

    def reset(self, context=None):
        self._active = False
        self._last_alt = None
        self._last_t = None
        self._last_pitch = None
        self._step = 0
        return self.inner.reset(context)

    def compute_action(self, context):
        result = self.inner.compute_action(context)
        state = getattr(context, "ownship_state", None)
        if state is None:
            return result
        # [MOD-GUARDPHYS 2026-09-05] 실서버 패킷은 기체당 9개(위치·자세·속도)뿐이라
        # plane_info_to_state(policies.py:267) 는 state[0:9] 만 채운다 -> state[44](ALT) 는 0.
        # 그대로 읽으면 alt=0 -> vz=0 -> 가드가 서버에서 영원히 안 켜진다(지금까지 그랬다).
        # my_observation [MOD-SRVZ] 와 같은 판별(ALT==0 and KCAS==0 = 서버 경로)로
        # 패킷 z(=고도 m, 위 양수; 실측 z=4572.021 m=15,000 ft)를 쓴다.
        if float(state[_ALT_IDX]) == 0.0 and float(state[12]) == 0.0:
            alt = float(state[2])
        else:
            alt = float(state[_ALT_IDX])
        fi = None
        if isinstance(getattr(context, "info", None), dict):
            fi = context.info.get("frame_index")
        t = (float(fi) / 60.0) if fi is not None else self._step * 0.1
        self._step += 1
        vz = 0.0
        q = 0.0
        pitch_now = float(state[_PITCH_IDX])
        if self._last_alt is not None and t > self._last_t:
            vz = (alt - self._last_alt) / (t - self._last_t)
            _dp = ((pitch_now - self._last_pitch + 180.0) % 360.0) - 180.0
            q = _dp / (t - self._last_t)
        self._last_alt, self._last_t, self._last_pitch = alt, t, pitch_now
        tgt = getattr(context, "target_state", None)
        dist = None
        if tgt is not None:
            d = np.asarray(tgt[0:3], dtype=np.float64) - np.asarray(state[0:3], dtype=np.float64)
            dist = float(np.linalg.norm(d))  # NED (N,E,D) 미터
        # [MOD-GUARDPHYS] 속도(동체속도 크기)를 넘겨 실제 비행경로각으로 계산한다.
        spd = float(np.linalg.norm(np.asarray(state[6:9], dtype=np.float64)))
        action, fired = guard_step(result.action, alt, vz, float(state[_ROLL_IDX]),
                                   float(state[_PITCH_IDX]), dist, self._active,
                                   throttle_range=(0.0, 1.0),
                                   enemy_alt_m=None if tgt is None else float(tgt[_ALT_IDX]),
                                   speed_mps=spd, pitch_rate_dps=q)
        self._active = fired
        if fired:
            self.fired_steps += 1
            result.action = action
            result.info["deck_guard"] = True
            if self.verbose:
                print(f"[DeckGuard] fired alt={alt:.0f}m vz={vz:.1f}m/s")
        return result

    def close(self):
        return self.inner.close()
