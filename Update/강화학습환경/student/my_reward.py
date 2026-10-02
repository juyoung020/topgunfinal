# -*- coding: utf-8 -*-
"""[학생 파일] 학습 보상. 켜진 14항(종단·딜·조준·접근·고도) + 꺼진 항(0). 값 = stage 35 = final_sp/live_tune.json.
동시격추·시간종료·패배 = 0, 승리 +600(+시간보너스), 추락 -700 (8/29 결정, 다음 재기동부터). 자세한 이력은 변경사항.md.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for _p in (ROOT, SRC):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from dogfight.sim.state_schema import StateIndex

_D2R = math.pi / 180.0
M_TO_FT = 1.0 / 0.3048


# ── 보상 크기 (0 = 그 항 꺼짐). 값 = stage 35 = final_sp/live_tune.json — 바꾸면 live_tune 도 같이. 순서 = 효과(배치 간 std) 큰 순.
MY_REWARD_WEIGHTS: dict[str, float] = {
    # 종단 (승리만 양수; 패배·동시격추·시간종료 0)
    "win_reward": 300.0,
    "win_time_bonus": 0.0,   # [2026-09-05 사용자 지시] 200 -> 0 (빠른 결착 보너스 제거)
    "crash_reward": -700.0,
    # 딜
    "w_damage": 300.0,
    "w_damage_taken": 50.0,  # 피딜(맞은 HP) 벌점 (8/29 0 -> 50)
    "w_precision_mult": 1.0,  # 정밀 조준 배수: 내 ATA 0도 x2 -> precision_ata_deg(1도)에서 x1 (선형)
    # 저고도선
    "w_deck": 12.0,
    # [MOD-TAILSLOW 2026-09-09] 후방에서 감속하면 주는 항. 기본 0 (live_tune 로 켠다).
    "w_tailslow": 0.0,
    "tailslow_rear_deg": 120.0,      # 적 기수각이 이보다 크면 후방 점유
    "tailslow_aim_deg": 5.0,         # 내 조준 5도 이내
    "tailslow_range_m": 1500.0,      # 사거리 근방까지
    "tailslow_target_mps": 30.0,     # 이 접근율 이하면 만점, 두 배 넘으면 0
    # 미스거리
    "w_nmd": 8.0,
    # 거리
    "w_range": 0.1,
    # 멀어짐 — [2026-09-05 사용자 지시] 제거.
    #   접근 포텐셜과 같은 일(붙으라고 미는 것)을 하는데 상쇄가 없어 더 강했다.
    "w_far": 0.0,
    # 조준각
    "w_aim": 0.16,
    "w_aim_wide": 0.08,
    # 최근접점
    "w_cpa": 1.5,
    # 접근 포텐셜 — [2026-09-05 사용자 지시] 제거
    "w_close_pot": 0.0,
    # 천장
    "w_ceil": 1.0,

    # ───────────── 꺼진 항 (전부 0) ─────────────
    "loss_reward": 0.0,  # 패배 (먼저 격추당함)
    "draw_reward": 0.0,  # 시간종료 기본값
    "draw_health_scale": 0.0,  # 시간종료 시 x(내HP-적HP)
    "target_crash_reward": 300.0,  # 적이 스스로 추락 = 대회 규칙상 승리 (2026-09-05 사용자 지시)
    "timeout_penalty": 0.0,  # 시간종료 벌점(HP 무관)
    "step_penalty": 0.0,  # 매 스텝 고정 벌점
    "w_headon_mult": 0.0,  # 정면 배수: 적 기수가 나를 향할 때 딜 배수
    "w_high": 0.0,  # 고고도 벌점 (high_floor_m 위)
    "w_overspeed": 0.0,  # 과속 벌점 (overspeed_ref_mps 초과)
    # [2026-09-05 사용자 지시] WEZ 원뿔 안 체류 보상 0 -> 1.0.
    #   실측(v4 114판) w_wez=1 일 때 판당 적분 중앙 1.75 / 상위10% 12.66.
    #   이긴 판 2.94 vs 진 판 0.43 으로 승패와 갈리는 신호다. 분산이 커서
    #   (중앙 대비 상위10% 가 7배) 크게 잡으면 배치 간 표준편차가 딜을 덮는다 —
    #   작게 시작한다.
    "w_wez": 1.0,  # WEZ 콘 안 체류 보상
    "w_snap": 0.0,  # snap_ata_deg 안 정밀 조준 보너스
    "w_perch": 0.0,  # 적 후방 perch 위치 보상
    # [MOD-SIX 2026-09-05 사용자 지시] 후방 포지션 유지 (rear x near, 조준 없음). 2c 주석 참조.
    # [2026-09-06] 0.17 은 판당 6(옆구리 중앙) = 딜의 2% 로 "부적" 수준이라 딜과 경쟁이 안 됐다.
    #   리플레이 108판 실측으로 크기를 잡았다(옆구리 71 / 꼬리잡기 37 분리):
    #     w0.17 gate0.25       옆구리  5.7 ( 2%) · 꼬리 12.6 ( 4%)
    #     w0.80 gain1.5 gate.45 옆구리 30.9 (11%) · 꼬리 63.8 (22%)   <- 채택
    #     w1.00                 옆구리 38.6 (13%) · 꼬리 79.8 (28%)   꼬리가 과하다
    #   gate 0.45 를 쓰는 이유: 0.25 면 꼬리/옆구리 비가 3.7배(거저 먹음), 0.45 면 2.1배.
    "w_six": 0.80,
    "w_alt": 0.0,  # 고도 유지 포텐셜
    "w_nodmg": 0.0,  # nodmg_deadline_s 까지 무딜이면 벌점
    "w_sink": 0.05,   # 2026-08-31 0.03 -> 0.05 (final_v2r7 iter ~2360)  # 강하율 벌점 (sink_free_mps 초과) x 저고도 게이트(sink_gate_ft 아래), 2026-08-29
    "w_recover": 0.0,  # 5G 회복 불가에 가까운 강하 벌점 — 2026-08-29 final_v2r1 에서 5 로 30 iter 시험 후 0 (무효)
    "w_tti": 0.0,  # 격추까지 남은 시간 추정 보상
    "w_turnalt": 0.0,  # 선회 고도 turnalt_pref_m 유지 보상
    "w_idle": 0.0,  # 교전 회피(멀리서 배회) 벌점
}

# ── 적용 조건 (거리 m · 고도 ft · 각도 deg · 시간 s · 속도 mps). 짝인 가중치가 0 이면 무효.
MY_REWARD_PARAMS: dict[str, float] = {
    # 종단 (승리만 양수; 패배·동시격추·시간종료 0)
    "max_engage_time": 200.0,
    # 딜
    "precision_ata_deg": 1.0,
    "damage_near_gate_m": 250.0,
    "damage_near_floor": 0.15,
    # 저고도선
    "deck_ft": 1640.42,       # [2026-09-05 사용자 지시] 2,500 ft -> 500 m
    "deck_floor_ft": 1000.0,  # 선형 deck 의 최대점(추락선), 2026-08-29
    # 미스거리
    "nmd_half_m": 5.0,   # 2026-08-30 10 -> 5 (final_v2r7 부터; 이전 실행 번들 metadata 는 10)
    # 멀어짐
    "far_start_m": 1800.0,
    "far_ramp_m": 1000.0,
    "far_time_start_s": 0.0,
    "far_time_full_s": 0.0,
    # 조준각
    "aim_lambda": 0.2,
    "aim_range_gate_m": 4500.0,
    # 최근접점
    "cpa_half_m": 40.0,
    "cpa_horizon_s": 8.0,
    # 천장
    "ceil_ft": 45000.0,
    "ceil_ramp_ft": 2000.0,

    # ───────────── 꺼진 항의 조건 (무효) ─────────────
    "high_floor_m": 6000.0,
    "high_span_m": 8000.0,
    "overspeed_ref_mps": 190.0,
    "overspeed_gate_m": 1200.0,
    "overspeed_turn_ata_deg": 30.0,
    "wez_cone_deg": 15.0,
    "wez_best_m": 260.0,
    "snap_ata_deg": 3.0,
    "perch_ata_deg": 10.0,
    "perch_near_m": 700.0,
    "perch_far_m": 1800.0,
    # [MOD-SIX] 후방 포지션 — 2c 주석 참조
    "six_rear_start_deg": 90.0,    # 적ATA 여기서 0
    "six_rear_full_deg": 180.0,    # 여기서 1 (꼬리)
    "six_near_far_m": 1800.0,      # 거리 여기서 0
    "six_near_flat_m": 700.0,      # 여기서 1, 안쪽 평탄 (추월 방지)
    # [MOD-SIXMERGE] 머지 초반 가중 — 2c 주석 참조
    "six_merge_boost": 1.0,        # 0초에 x(1+이 값)
    "six_merge_window_s": 30.0,    # 이 시각 이후 배수 1
    # [MOD-POSPOT 2026-09-06 사용자 지시 "기존 보상 잔재보다 새롭게 만들어라"]
    #   후방 포지션을 **포텐셜 셰이핑**으로 다시 설계한다. six(비포텐셜)의 문제 셋을 한 번에 푼다:
    #     (1) 뒤에 있기만 하면 계속 줘서 파밍 가능      -> 텔레스코프(총합 = Φ끝 − Φ시작)라 불가
    #     (2) 놓쳐도 벌점이 없어 추월을 안 막음          -> 놓치면 Φ 가 떨어져 자동으로 음수
    #     (3) 판당 48~161 로 편차가 큼(정체 원인)        -> 크기가 W 로 유계
    #   그리고 포텐셜 정리로 **최적정책이 안 바뀐다**(벌점 4개 전패 전례를 피한다).
    #     Φ = w_pos x rear(적ATA) x range(d)
    #       rear  = clip((적ATA − 90)/90, 0, 1)          정측 0, 순수 꼬리 1
    #       range = 원거리감쇠 x 근접감쇠
    #         원거리 clip((1800 − d)/1100, 0, 1)          700 m 안에서 1
    #         근접   clip((d − 120)/230, 0, 1)            350 m 위에서 1, 120 m 에서 0
    #       -> Φ 는 350~700 m 에서 최대. WEZ(152~914 m) 안이면서 추월권 밖이다.
    #   실측 근거(36_34): 378 m 까지 파고들어 추월했다. 근접감쇠가 그 구간에서 Φ 를 깎아
    #   파고들 유인을 없앤다. 별도 벌점이 필요 없다.
    #   "계속 패는" 유인은 딜이 맡는다 — 포텐셜은 자리로 **밀어주기만** 하고, 머무를 이유는
    #   딜에서 나온다. 그래서 딜이 최우선인 구조가 유지된다.
    "w_pos": 50.0,                 # Φ 최대값(판당 기여는 |Φ끝 − Φ시작| 이라 이보다 작다)
    "pos_rear_start_deg": 90.0,
    "pos_rear_full_deg": 180.0,
    "pos_far_m": 1800.0,           # 여기서 원거리감쇠 0
    "pos_flat_m": 700.0,           # 여기 안쪽 원거리감쇠 1
    "pos_close_zero_m": 120.0,     # 이보다 가까우면 Φ 0 (추월권)
    "pos_close_full_m": 350.0,     # 여기 위에서 근접감쇠 1
    # [MOD-TAILHOLD 2026-09-06 사용자 지시 "상대 꼬리를 계속 따라가면 보상 · 기존 보상 지우고"]
    #   앞선 두 항([MOD-SIX] 비포텐셜, [MOD-POSPOT] 포텐셜)이 모두 실패해서 성격을 바꾼다.
    #   실패 이유가 서로 달랐다:
    #     six    "적 뒤쪽 어딘가"(ATA>90, 1800 m)면 줬다 -> 사격 불가 자리에서도 벌어 신호가 흐렸다
    #     pospot 텔레스코프라 **머무는 시간에 값을 안 준다**. 사용자가 원한 "계속 따라감"이 무보상
    #   이번 항은 정반대다: **사격 가능한 꼬리 자리에 있는 매 스텝** 준다. 머물수록 쌓인다.
    #   파밍 걱정이 적은 이유: 게이트가 WEZ 사거리(152~914 m)와 꼬리각(150도)이라
    #   보상을 버는 자리가 곧 딜이 들어가는 자리다. "뒤에서 뭉개기"로는 못 번다.
    #   실측 근거(리플레이 3판 36_34/46_16/2_3): 완벽 조준을 잡고도 2~3초 만에 속도차로 놓친다.
    #   사격 자리 체류가 판당 1.1~1.8초뿐인데 격추엔 1.56초가 필요하다. 체류 자체에 값을 매긴다.
    "w_tail": 0.0,                 # 스텝당 보상 (live_tune 으로 켠다)
    "tail_rear_start_deg": 130.0,  # 적ATA 여기서 0
    "tail_rear_full_deg": 165.0,   # 여기서 1 (꼬리)
    "tail_near_m": 152.4,          # WEZ 최소 사거리 — 이보다 가까우면 0 (추월권)
    "tail_far_m": 914.4,           # WEZ 최대 사거리
    "tail_edge_m": 200.0,          # 사거리 경계에서 이만큼 완만하게 감쇠
    # [MOD-TAILSPD 2026-09-06 사용자 지적 "뒤에서 속도관리를 안 해"] 꼬리 보상에 곱하는 속도 정합.
    #   실측(리플레이 3판): 완벽 조준을 잡고도 2~3초 만에 놓치는데, 그때 우리가 상대보다
    #     36_34 +49 m/s · 46_16 +38 m/s · 2_3 +30 m/s 빨랐다. 감속을 안 해 안쪽으로 밀려
    #     조준선을 넘어간다. 격추엔 1.56초 연속 조준이 필요한데 딱 그 언저리에서 놓친다.
    #   사거리 안에서만 건다 — 멀리서 접근할 때는 빨라야 맞다. 게이트가 152~914 m 라 자동으로 그렇다.
    #   벌점이 아니라 **배수**다. 붙어 있어도 과속하면 덜 받는다. 비포텐셜 벌점 전패 전례를 피한다.
    "tail_spd_tol_mps": 10.0,      # 이만큼 빠른 건 봐준다(접근에 필요)
    "tail_spd_span_mps": 60.0,     # tol 초과분이 이만큼이면 배수 0
    # [MOD-POSDEF 2026-09-06 03:30 실측 판정 후 추가] 포텐셜의 빠진 조각.
    #   pospot 만으로는 실패 모드를 못 건드린다 — 옆구리 스폰 교전의 **91~100% 가 정면 맞교환**인데
    #   정면에서는 양쪽 rear 항이 둘 다 0 이라 Φ 가 침묵한다(실측: 후방점유 42.9->42.5,
    #   추월 0.59->0.68, 동시도달 91->100%, 우리선취 6->2%. 개선 항목 0).
    #   그래서 "상대의 총구 앞에 있는 것"을 Φ 에서 뺀다:
    #     danger = clip((def_cone_deg − 적이우리를겨눈각)/def_cone_deg, 0, 1) x 사거리안
    #     Φ = w_pos x 후방이득 − w_pos x w_def x danger
    #   정면 머지로 들어가면 danger 1 -> Φ 하락 -> 음수. 우리가 뒤를 잡으면 적ATA 가 커져 danger 0.
    #   쫓길 때도 danger 가 커서 음수 — 방어까지 같은 항으로 덮인다.
    #   **포텐셜이라 최적정책 불변**(회피 학습으로 굳을 위험이 비포텐셜 벌점보다 훨씬 낮다).
    #   기본 0 — live_tune 으로 켠다. 재기동은 이 설치 1회로 끝이다.
    "w_def": 0.0,                  # Φ 에서 빼는 위험 항의 배수 (1.0 이면 후방이득과 같은 크기)
    "def_cone_deg": 30.0,          # 적이 우리를 이 각 안에서 겨누면 위험
    "def_far_m": 1200.0,           # 이보다 멀면 위험 0 (사거리 914 + 여유)
    # [MOD-SIXHOLD 2026-09-06 사용자 지시 "후방 선점하고 안 놔주는 걸 배우면 다 이긴다"]
    #   연속 유지 시간에 비례해 배수를 키운다. 놓치면 누적이 0 으로 끊기므로
    #   **추월이 자동으로 벌받는다**(별도 벌점 없이). 비포텐셜 벌점을 안 쓰는 이유:
    #   벌점 4개가 전부 실패한 전례가 있다.
    #   실측 근거(리플레이 36_34): 7.5초에 622 m·ATA 0.4도로 완벽 선점 -> 12초 추월(4.5초만 유지).
    #   옆구리 스폰 유지시간 중앙 3.2~3.7초. full_s 6초면 그 위로 갈 이유가 생긴다.
    "six_hold_gain": 1.5,          # 배수 1 -> 2.5 (6초 유지). 2.0 은 꼬리잡기가 과해진다
    "six_hold_full_s": 6.0,        # 이 시간 유지하면 배수 최대 (옆구리 유지 중앙 3.2~3.7초)
    "six_hold_gate": 0.45,         # rear x near 임계. 0.25 는 느슨해 "뒤쪽 어딘가"도 세어준다
    "alt_ceiling_m": 6300.0,
    "nokill_hp_thresh": 0.0,
    "nodmg_deadline_s": 30.0,
    "sink_free_mps": 15.0,
    "sink_gate_ft": 3000.0,   # 2026-08-31 2000 -> 3000 ft (5000 은 과하다는 사용자 판단): 추락 6판 전부 1,000~1,500 m 에서 -130~-190 m/s 강하 시작 -> 게이트를 결정 지점 위로       # 침하율 벌점이 온전히 붙는 고도 (아래), 2026-08-29
    "sink_gate_ramp_ft": 1000.0,   # 2026-08-31 200 -> 1000   # 그 위 200 ft 에서 0 으로 램프
    "recover_g": 5.0,
    "recover_ratio_k": 3.0,
    "recover_min_gamma_deg": 5.0,
    "tti_ref_s": 15.0,
    "turnalt_pref_m": 3000.0,
    "turnalt_span_m": 6000.0,
    "idle_reset_m": 1500.0,
    "idle_grace_s": 15.0,
    "idle_ramp_s": 30.0,
}

MY_REWARD_CONFIG: dict[str, float] = {**MY_REWARD_WEIGHTS, **MY_REWARD_PARAMS}


# 고도 포텐셜의 직전 값. env 는 num_envs_per_env_runner = 1 이 전제라
# 모듈 전역으로 충분하다(프로젝트 규약).
_PREV_ALT_PHI: dict = {}
# 접근 포텐셜(3i)의 직전 값 — 같은 규약.
_PREV_CLOSE_PHI: dict = {}
_NODMG_STATE: dict = {}          # [MOD-NODMG] 판별 1회 부과용 (러너별 프로세스 전역)
_SIXHOLD_STATE: dict = {}        # [MOD-SIXHOLD] 후방 연속 유지 타이머 (판 시작 시 되감기로 초기화)
# 고공 벌점 포텐셜(4c)의 직전 값 — 같은 규약.
_PREV_HIGH_PHI: dict = {}
# 선회 최적고도 선호(4d)의 직전 값 — 같은 규약.
_PREV_TURNALT_PHI: dict = {}
# [MOD-POSPOT] 후방 포지션 포텐셜의 직전 값 — 같은 규약.
_PREV_POS_PHI: dict = {}
# 무교전 벌점(4e)의 "마지막 교전 시각" — 같은 규약.
_PREV_IDLE: dict = {}


def _S(x: float, alpha: float, x0: float) -> float:
    """로지스틱. 오버플로 클램프 포함."""
    z = -alpha * (x - x0)
    if z > 60.0:
        return 0.0
    if z < -60.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(z))


def _ned_velocity(state) -> tuple[float, float, float]:
    """동체속도 [u,v,w] 를 NED 로 (동체->NED = T_nb^T).

    `my_observation._ned_velocity` 와 같은 값이지만 여기 따로 둔다 — 보상이
    관측 모듈에 의존하면 관측 교체 때 보상이 조용히 같이 바뀐다. 이 저장소는
    같은 이유로 `scripted_opponents.py` 에도 따로 두고 있다.
    회전 규약 Tx@Ty@Tz 는 `GeoMathUtil` 과 동일해야 한다.
    """
    roll = float(state[StateIndex.ROLL]) * _D2R
    pitch = float(state[StateIndex.PITCH]) * _D2R
    yaw = float(state[StateIndex.YAW]) * _D2R
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    u, v, w = float(state[6]), float(state[7]), float(state[8])
    # (Tx@Ty@Tz)^T @ [u,v,w] 를 전개한 것 (numpy 없이).
    return (
        u * cp * cy + v * (sr * sp * cy - cr * sy) + w * (cr * sp * cy + sr * sy),
        u * cp * sy + v * (sr * sp * sy + cr * cy) + w * (cr * sp * sy - sr * cy),
        -u * sp + v * sr * cp + w * cr * cp,
    )


def _ata_deg(own, tgt) -> float:
    """기수와 상대 사이 각 (0~180). **플랫폼 3D ATA 를 쓰면 안 된다.**

    `GeoMathUtil._get_antenna_train_angle(..., proj=False)` 결함:
        elif -0.01 < p_unit_t[1] < 0.01:
            sign = np.sign(p_unit_t[2])   # np.sign(0.0) == 0
        _angle = sign * arccos(...)       # 0 * 180 = 0
    상대가 정후방이고 **고도가 정확히 같으면** 180도가 0도로 읽힌다.
    우리 스폰이 `[거리,0,-7000]` 대 `[0,0,-7000]` 이라 매 에피소드 시작마다 걸린다.
    무작위 20만 개 대조에서 이 구현은 플랫폼 정상 구간과 최대 9.0e-04 차이.
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
    x1 = math.cos(yaw) * rn + math.sin(yaw) * re
    bx = math.cos(pitch) * x1 - math.sin(pitch) * rd
    return math.degrees(math.acos(max(-1.0, min(1.0, bx))))


def compute_reward(
    ownship_state,
    target_state,
    ownship_damage: float,
    target_damage: float,
    geo_info,
    wez_config: dict,
    reward_config: dict,
    terminated: bool,
    truncated: bool,
    end_condition: str,
) -> tuple[float, dict]:
    cfg = reward_config if reward_config else MY_REWARD_CONFIG

    def C(k: str) -> float:
        v = cfg.get(k, MY_REWARD_CONFIG.get(k))
        return float(v) if v is not None else 0.0

    d_m = float(geo_info._get_distance(ownship_state, target_state))
    ata = _ata_deg(ownship_state, target_state)
    alt_ft = -float(ownship_state[StateIndex.D]) * M_TO_FT
    try:
        lo = float(wez_config["min_range_m"])
        hi = float(wez_config["max_range_m"])
    except Exception:
        lo, hi = 152.4, 914.4

    comp: dict[str, float] = {}

    # 1. 조준 — 0 이상, 거리 게이트
    gate = 1.0 - _S(d_m, 1.0 / 400.0, C("aim_range_gate_m"))
    comp["aim"] = C("w_aim") * gate * (
        1.0 - (min(ata, 180.0) / 180.0) ** C("aim_lambda"))

    # 1b. 광각 유도 — 선형이라 ATA 180도에서도 기울기가 있다.
    #     등돌린 스폰에서 "적 쪽으로 돌아서라"를 만드는 유일한 신호.
    w_wide = C("w_aim_wide")
    if w_wide:
        comp["aim_wide"] = w_wide * gate * (1.0 - min(ata, 180.0) / 180.0)

    if d_m < lo:
        band = _S(d_m, 1.0 / 5.0, lo + 20.0)
    elif d_m > hi:
        band = 1.0 - _S(d_m, 1.0 / 150.0, hi + 250.0)
    else:
        band = 1.0
    comp["range"] = C("w_range") * band

    # 2c. 원거리 배회 벌점 — 3f 주석 참조. 멀수록 스텝당 -w 까지.
    w_far = C("w_far")
    if w_far:
        # 2c-2. 시간 램프. 경과 시간은 관측(time_norm)에 있으므로 MDP 유효하다.
        #       full <= start 면 램프를 끄고 곱수 1 (기존 스테이지 동작 불변).
        t_full = C("far_time_full_s")
        t_start = C("far_time_start_s")
        if t_full > t_start:
            t_now = float(ownship_state[StateIndex.SIM_TIME])
            tmul = min(max((t_now - t_start) / (t_full - t_start), 0.0), 1.0)
        else:
            tmul = 1.0
        comp["far"] = -w_far * _S(d_m, 1.0 / C("far_ramp_m"), C("far_start_m")) * tmul

    # 2b. 퍼치 — 유지 추격 창(700~1,800 m × ATA<10°). 3e 주석 참조.
    w_perch = C("w_perch")
    if w_perch:
        window = (_S(d_m, 1.0 / 100.0, C("perch_near_m"))
                  * (1.0 - _S(d_m, 1.0 / 150.0, C("perch_far_m"))))
        ang = max(0.0, 1.0 - ata / C("perch_ata_deg"))
        comp["perch"] = w_perch * window * ang

    # 2c. [MOD-SIX 2026-09-05 사용자 지시] 적 후방 포지션 유지 보상.
    #   six = w_six x rear x near   (조준 인자 없음)
    #     rear = clip((적ATA - six_rear_start_deg) / (six_rear_full_deg - start), 0, 1)
    #            옆(90도)에서 0 -> 꼬리(180도)에서 1. 원형(120도 포화)보다 꼬리를 더 우대.
    #     near = clip((six_near_far_m - d) / (far - six_near_flat_m), 0, 1)
    #            1,800 m 에서 0 -> 700 m 에서 1, 그 안쪽은 평탄.
    #            **평탄인 이유**: 더 파고들수록 커지면 추월(오버슛)을 부추긴다.
    #            가까울수록 큰 보상은 damage 가 이미 준다.
    #   조준을 안 보는 이유: 기수 방향은 aim/wez/nmd/damage 네 항이 맡는다. 곱하면
    #     신호가 희박해지고(실측 v4 185판: 조준 포함 시 중앙 0.14, 제외 시 10.3),
    #     더하면 살아난다. 상태 변수(연속 체류 카운터)는 관측에 없어 안 쓴다 —
    #     스텝당 기하만 쓰면 오래 유지할수록 자연히 누적된다.
    #   크기(실측 v5 iter 0~39, w_six=1): 판당 평균 113 = 딜(179)의 63%.
    #     사전 추정(리플레이 적분 16)은 CSV 가 이미 10 Hz 인데 6배 솎아 계산한 오류였다.
    #     합의한 목표 "딜의 ~9%" 에 맞춰 w_six 0.17 (판당 ~19). 승패 구분 6.5배,
    #     신호>0 인 판 92% 는 비율이라 유효.
    # 2b-0. [MOD-TAILHOLD] 사격 가능한 꼬리 자리 체류 보상. 파라미터 주석은 위 정의부 참조.
    w_tail = C("w_tail")
    if w_tail:
        _trs, _trf = C("tail_rear_start_deg"), C("tail_rear_full_deg")
        _ta = _ata_deg(target_state, ownship_state)          # 적이 우리를 겨눈 각(크면 우리가 꼬리)
        _tr = min(max((_ta - _trs) / max(_trf - _trs, 1e-3), 0.0), 1.0)
        _lo, _hi, _ed = C("tail_near_m"), C("tail_far_m"), max(C("tail_edge_m"), 1.0)
        if d_m < _lo:
            _tg = max(0.0, 1.0 - (_lo - d_m) / _ed)          # 너무 붙으면 감쇠(추월권)
        elif d_m > _hi:
            _tg = max(0.0, 1.0 - (d_m - _hi) / _ed)
        else:
            _tg = 1.0
        # [MOD-TAILSPD] 속도 정합 배수. 상대보다 과속한 만큼 깎는다.
        _su = math.sqrt(sum(float(ownship_state[k]) ** 2 for k in (6, 7, 8)))
        _st_ = math.sqrt(sum(float(target_state[k]) ** 2 for k in (6, 7, 8)))
        _tol, _span = C("tail_spd_tol_mps"), max(C("tail_spd_span_mps"), 1.0)
        _excess = max(0.0, (_su - _st_) - _tol)
        _sm = min(max(1.0 - _excess / _span, 0.0), 1.0)
        comp["tail"] = w_tail * _tr * _tg * _sm

    # 2b-1. [MOD-POSPOT] 후방 포지션 포텐셜. 파라미터 주석은 위 정의부 참조.
    w_pos = C("w_pos")
    if w_pos:
        _prs, _prf = C("pos_rear_start_deg"), C("pos_rear_full_deg")
        _tata = _ata_deg(target_state, ownship_state)   # 적이 우리를 겨눈 각(크면 우리가 적 뒤)
        _r = min(max((_tata - _prs) / max(_prf - _prs, 1e-3), 0.0), 1.0)
        _far = min(max((C("pos_far_m") - d_m) / max(C("pos_far_m") - C("pos_flat_m"), 1.0), 0.0), 1.0)
        _cz, _cf = C("pos_close_zero_m"), C("pos_close_full_m")
        _cl = min(max((d_m - _cz) / max(_cf - _cz, 1.0), 0.0), 1.0)
        phi_p = w_pos * _r * _far * _cl
        # [MOD-POSDEF] 상대 총구 앞에 있는 위험을 뺀다. 정면 맞교환이 Φ 를 떨어뜨린다.
        _wd = C("w_def")
        if _wd:
            _cone = max(C("def_cone_deg"), 1e-3)
            # 주의: `ata` 는 **우리가** 적을 겨눈 각이다. 위험은 **적이 우리를** 겨눈 각으로 재야 한다.
            _dang = min(max((_cone - _tata) / _cone, 0.0), 1.0)
            _dang *= min(max((C("def_far_m") - d_m) / max(C("def_far_m") - 200.0, 1.0), 0.0), 1.0)
            phi_p -= w_pos * _wd * _dang
        t_p = float(ownship_state[StateIndex.SIM_TIME])
        prev_p = _PREV_POS_PHI.get("v")
        if prev_p is None or t_p < _PREV_POS_PHI.get("t", 0.0):
            prev_p = phi_p                       # 새 판 첫 스텝은 0
        # 종료 스텝에는 셰이핑을 주지 않는다. Φ(종료)=0 규약을 그대로 쓰면
        # 뒤를 잡은 채 격추했을 때 −Φ 를 물어 승리를 벌하게 된다.
        comp["pospot"] = 0.0 if (terminated or truncated) else (phi_p - prev_p)
        _PREV_POS_PHI["v"] = phi_p
        _PREV_POS_PHI["t"] = t_p
        if terminated or truncated:
            _PREV_POS_PHI.clear()

    w_six = C("w_six")
    if w_six:
        _rs, _rf = C("six_rear_start_deg"), C("six_rear_full_deg")
        _rear = min(max((_ata_deg(target_state, ownship_state) - _rs) / max(_rf - _rs, 1e-3), 0.0), 1.0)
        _nf, _nn = C("six_near_far_m"), C("six_near_flat_m")
        _near = min(max((_nf - d_m) / max(_nf - _nn, 1.0), 0.0), 1.0)
        _v = w_six * _rear * _near
        # [MOD-SIXHOLD] 연속 유지 시간 배수. rear x near 가 gate 아래로 떨어지면 0 으로 끊긴다.
        _hg = C("six_hold_gain")
        if _hg:
            _now = float(ownship_state[StateIndex.SIM_TIME])
            if _now < _SIXHOLD_STATE.get("t", 0.0):     # 시간이 되감기면 새 판
                _SIXHOLD_STATE.clear()
            _dt = max(0.0, _now - _SIXHOLD_STATE.get("t", _now))
            _SIXHOLD_STATE["t"] = _now
            if _rear * _near >= C("six_hold_gate"):
                _SIXHOLD_STATE["hold"] = _SIXHOLD_STATE.get("hold", 0.0) + _dt
            else:
                _SIXHOLD_STATE["hold"] = 0.0            # 놓치면 누적 소멸 = 추월 벌점
            _full = max(C("six_hold_full_s"), 1e-3)
            _v *= 1.0 + _hg * min(_SIXHOLD_STATE["hold"] / _full, 1.0)
        # [MOD-SIXMERGE 2026-09-05 사용자 지시] 머지 초반 가중.
        #   같은 후방 점유라도 **먼저** 잡는 쪽이 이긴다 — 실측(vs 25100): 첫 딜이 19.5초,
        #   그 구간 내 ATA 76.3도 vs 적 64.4도로 12도 밀렸다. 그런데 six 는 200초 내내
        #   같은 크기라 초반에 서두를 이유가 없었다.
        #   boost = 1 + w_merge * max(0, 1 - t/window). window 30초·w_merge 1.0 이면
        #   0초 x2.0 / 15초 x1.5 / 30초 이후 x1.0.
        #   대회 WEZ 페이즈(0~100초 배율 1.0, 이후 0.3/0.1)와 같은 방향이다.
        #   MDP 유효: 경과시간(time_norm)이 관측 16차원에 있어 정책이 t 를 안다.
        _wm = C("six_merge_boost")
        if _wm:
            _win_s = max(C("six_merge_window_s"), 1e-3)
            _t = float(ownship_state[StateIndex.SIM_TIME])
            _v *= 1.0 + _wm * max(0.0, 1.0 - _t / _win_s)
        comp["six"] = _v

    # 2d. 콘-게이트 WEZ 셰이핑 — 3g 주석 참조. cone(ATA) x prox(d) 곱이라
    #     콘 밖 근접은 0. prox 는 실제 데미지 곡선 모양(914 m 0 → best 평탄역).
    w_wez = C("w_wez")
    if w_wez:
        cone = max(0.0, 1.0 - ata / C("wez_cone_deg"))
        best = max(C("wez_best_m"), lo + 1.0)
        if d_m < lo:
            prox = _S(d_m, 1.0 / 5.0, lo + 20.0)   # 하한 밑 급감 (range 와 동일)
        elif d_m <= best:
            prox = 1.0                              # 평탄역 — 더 파고들 유인 없음
        else:
            prox = max(0.0, (hi - d_m) / max(hi - best, 1.0))
        comp["wez"] = w_wez * cone * prox

    # 2f. 접근 포텐셜 — 3i 주석 참조. 좁힌 거리만큼 지불, 벌어지면 회수.
    w_cp = C("w_close_pot")
    if w_cp:
        phi_c = -w_cp * d_m / 1000.0
        prev_c = _PREV_CLOSE_PHI.get("v")
        t_c = float(ownship_state[StateIndex.SIM_TIME])
        if prev_c is None or t_c < _PREV_CLOSE_PHI.get("t", 0.0):
            prev_c = phi_c
        comp["close"] = phi_c - prev_c
        _PREV_CLOSE_PHI["v"] = phi_c
        _PREV_CLOSE_PHI["t"] = t_c
        if terminated or truncated:
            _PREV_CLOSE_PHI.clear()

    # 2e. 스냅락 — 3h 주석 참조. 밴드 내 & ATA<3° 정밀 조준 전용 기울기.
    w_snap = C("w_snap")
    if w_snap and lo <= d_m <= hi:
        comp["snap"] = w_snap * max(0.0, 1.0 - ata / C("snap_ata_deg"))

    # 2g. 미스거리 사격 셰이핑 — 3j 주석 참조. 밴드 안에서만, 미터 단위.
    w_nmd = C("w_nmd")
    if w_nmd and lo <= d_m <= hi:
        nmd_m = d_m * math.sin(min(ata, 90.0) * _D2R)
        near = (hi - d_m) / max(hi - lo, 1.0)      # 실제 데미지 곡선과 동일
        comp["nmd"] = w_nmd * near / (1.0 + nmd_m / max(C("nmd_half_m"), 1e-3))

    w_cpa = C("w_cpa")
    if w_cpa and d_m > hi:
        rel = tuple(float(target_state[i]) - float(ownship_state[i]) for i in range(3))
        vo = _ned_velocity(ownship_state)
        vt = _ned_velocity(target_state)
        vr = (vt[0] - vo[0], vt[1] - vo[1], vt[2] - vo[2])
        vv = vr[0] * vr[0] + vr[1] * vr[1] + vr[2] * vr[2]
        if vv > 1e-6:
            t_cpa = -(rel[0] * vr[0] + rel[1] * vr[1] + rel[2] * vr[2]) / vv
            if 0.0 < t_cpa < C("cpa_horizon_s"):
                miss = tuple(rel[i] + vr[i] * t_cpa for i in range(3))
                d_cpa = math.sqrt(sum(m * m for m in miss))
                comp["cpa"] = w_cpa / (1.0 + d_cpa / max(C("cpa_half_m"), 1e-3))

    # 2h. [MOD-TAILSLOW 2026-09-09 사용자 지시] 후방에서 속도를 줄이면 준다.
    #
    # 왜: 뒤를 잡는 순간 우리는 상대보다 +62 m/s 빠르고(실측), 선회 반경이 848 m 대
    # 205~1,230 m 라 밖으로 밀려난다. 뒤를 잡아도 3.3초만 유지하고 놓친다.
    # 규칙 가드로 스로틀을 직접 줄여봤더니 접근율은 내려갔지만 못 붙어서 격추가
    # 줄었다(aimangle 상대 승률 0.88 -> 0.56). 그래서 강제하지 않고 보상으로 준다.
    #
    # 발동: 적의 후방 반구(적 기수각 > 120도) + 내 조준 5도 이내 + 사거리 근방.
    # 크기: 접근율이 목표(기본 30 m/s) 이하면 1, 그 두 배를 넘으면 0 으로 선형.
    # 주의: 비포텐셜 항이라 최적정책을 바꾼다. 그게 목적이지만 파밍 위험이 있어
    # 조준·후방·사거리 세 조건을 동시에 걸어 좁혔다. 기본 가중치 0 (live_tune 로 켠다).
    w_ts = C("w_tailslow")
    if w_ts:
        _tail_ata = _ata_deg(target_state, ownship_state)
        if (_tail_ata >= C("tailslow_rear_deg") and ata <= C("tailslow_aim_deg")
                and d_m <= C("tailslow_range_m")):
            _vo = _ned_velocity(ownship_state)
            _vt = _ned_velocity(target_state)
            _rel = [float(target_state[i]) - float(ownship_state[i]) for i in range(3)]
            _dn = max(math.sqrt(sum(x * x for x in _rel)), 1e-6)
            _cl = -sum((_vt[i] - _vo[i]) * _rel[i] / _dn for i in range(3))
            _tgt = max(C("tailslow_target_mps"), 1e-3)
            comp["tailslow"] = w_ts * min(max(1.0 - (_cl - _tgt) / _tgt, 0.0), 1.0)

    # 3. 데미지 — 격추 그 자체. 총량이 w x HP 로 유계
    comp["damage"] = (C("w_damage") * float(target_damage)
                      - C("w_damage_taken") * float(ownship_damage))

    # 3c. 정면샷 우대 — 적 기수가 나를 향할수록 데미지 배수 (최대 1+w 배)
    hm = C("w_headon_mult")
    if hm > 0.0 and comp["damage"] > 0.0:
        tgt_ata = _ata_deg(target_state, ownship_state)
        front = 1.0 - min(tgt_ata, 90.0) / 90.0
        comp["damage"] *= 1.0 + hm * front

    # 3c-2. [MOD-PRECISION] 정밀 조준 배수 — 2026-08-22 사용자 지시.
    #
    # 위 3c 는 **적 기수**(적이 나를 보는가)로 배수를 걸었다. 이건 **내 조준**으로 건다.
    # 대회 WEZ 는 0~100 초 구간이 ±1도로 가장 좁고 데미지 배율이 1.0 으로 가장 크다.
    # 그 좁은 창 안에서 맞히는 것이 실전에서 가장 값진 조준이므로 배수를 준다.
    #
    #   own_ata 0도  -> x(1+w)      정확히 겨눔
    #   own_ata 1도  -> x1          창 가장자리
    #   own_ata >1도 -> x1          넓은 페이즈(±2·±3도)에서 맞힌 것은 그대로
    #
    # 데미지 총량이 HP 로 유계이므로 이 배수를 걸어도 판당 상한은
    # w_damage x (1+w) x HP 로 유계다 -- 누적 폭주가 없다.
    wp = C("w_precision_mult")
    if wp > 0.0 and comp["damage"] > 0.0:
        _pa = max(C("precision_ata_deg"), 1e-3)
        _own_ata = _ata_deg(ownship_state, target_state)
        _prec = 1.0 - min(_own_ata, _pa) / _pa
        comp["damage"] *= 1.0 + wp * _prec

    gate_m = C("damage_near_gate_m")
    if gate_m > 0.0 and comp["damage"] > 0.0 and d_m < gate_m:
        floor = C("damage_near_floor")
        t = max(0.0, min(1.0, (d_m - lo) / max(gate_m - lo, 1.0)))
        comp["damage"] *= floor + (1.0 - floor) * t


    # 4. 지면
    # [2026-08-29 사용자 지시] 계단(로지스틱 폭 +-50 ft, 2,450 ft 아래 정액) -> 선형: deck_ft 에서 0, deck_floor_ft(추락선 1,000 ft)에서 -w_deck.
    #   이전: -w_deck * (1 - _S(alt_ft, 1/20, deck_ft))  — 2,400 ft 와 1,000 ft 가 같은 값이라 저고도에서 기울기 0 이었음
    comp["deck"] = -C("w_deck") * min(max((C("deck_ft") - alt_ft) / max(C("deck_ft") - C("deck_floor_ft"), 1.0), 0.0), 1.0)

    # 4b. [MOD-SINK] 2026-08-22 — 침하율 벌점. 기본값 0 이라 켜기 전엔 무동작.
    #
    # 왜 필요한가: `deck` 은 610 m 아래에서만 켜지는데, 실측 프로파일을 보면
    # 하강은 4,572 m 에서 시작해 140초에 걸쳐 진행된다. 벌점이 나오는 시점에는
    # 이미 되돌릴 수 없고, 되돌릴 수 있었던 시점(100초 전 선회)은 gamma 0.995 의
    # 시야(20초) 밖이다. **신호와 선택권이 다른 시점에 있어** 학습이 안 된다.
    #     crash_reward -1500 -> -5000   추락률 62% -> 56%  (거의 무반응)
    #     w_deck 20 -> 600              deck 이 보상의 92% 차지, 교전 신호를 묻음
    #
    # 침하율은 **지금 이 순간** 스로틀·피치로 바꿀 수 있는 양이다. 그래서
    # 신호가 선택권과 같은 시점에 놓인다. 고도와 무관하게 작동하므로
    # "낮게 싸우는 것"은 막지 않고 "빠르게 내리꽂는 것"만 벌한다.
    #
    # sink_free_mps 아래는 공짜다 — 선회 중 완만한 하강은 정상이다.
    w_sink = C("w_sink")
    if w_sink:
        _r = math.radians(float(ownship_state[StateIndex.ROLL]))
        _p = math.radians(float(ownship_state[StateIndex.PITCH]))
        _y = math.radians(float(ownship_state[StateIndex.YAW]))
        _cr, _sr = math.cos(_r), math.sin(_r)
        _cp, _sp = math.cos(_p), math.sin(_p)
        _cy, _sy = math.cos(_y), math.sin(_y)
        _u = float(ownship_state[6]); _v = float(ownship_state[7]); _w = float(ownship_state[8])
        # 동체 -> NED 의 D 성분 (아래가 양수) = 침하율
        _d = (-_sp) * _u + (_sr * _cp) * _v + (_cr * _cp) * _w
        _free = C("sink_free_mps")
        # [2026-08-29 사용자 지시] 저고도에서만: sink_gate_ft(2,000 ft) 아래 1.0, 그 위 sink_gate_ramp_ft 구간에서 0 으로 (고고도 정상 강하는 벌점 없음)
        _gate = min(max((C("sink_gate_ft") + C("sink_gate_ramp_ft") - alt_ft) / max(C("sink_gate_ramp_ft"), 1.0), 0.0), 1.0)
        comp["sink"] = -w_sink * max(0.0, _d - _free) * _gate

    # 3c-3. [MOD-RECOVER] 회복 여유고도 — 2026-08-22 실측으로 신설.
    #
    # 오늘 추락을 겨냥한 보상 다섯 개가 전부 실패했다. 공통 원인은 하나다:
    # **정상 비행과 겹치는 상태를 벌줬다.**
    #     w_deck  고도만        -> 정상 저공비행도 벌점
    #     w_sink  침하율만      -> 정상 강하도 벌점, 속도 139 m/s 로 죽음
    #     w_alt   고도만(포텐셜) -> 상승을 보상해 **교전 자체를 대체**(고도 5,054 m·148 m/s)
    #     w_tti   고도÷침하율   -> 기준을 스폰(4,572 m)으로 검산, 교전고도(800~2,000 m)에서 상시 발동
    #     crash   종단          -> 할인에 묻혀 결정 시점에 안 보임
    #
    # 필요한 것은 "위험해 보이는 상태"가 아니라 **회복이 물리적으로 불가능한 상태**다.
    # 강하각 γ, 속도 V 에서 n-G 로 뽑아낼 때 필요한 고도:
    #     h_need = V^2 (1 - cos γ) / (g (n-1))
    #     margin = alt - h_need
    #
    # 실측(리플레이 243 판) — **겹치는 구간이 없다**:
    #     아군 추락  최소 여유  -6 m       여유<300 m 인 판 5/5   (100%)
    #     비추락     최소 여유  +4,538 m   여유<300 m 인 판 0/238 (0%)
    #                최저값도 3,688 m 라 ref=1,500 m 는 정상 비행을 절대 못 건드린다.
    # 고고도 급강하(4,946 m·강하각 36도)도 여유 4,537 m 로 0 이다.
    # 저공 수평비행은 강하각 0 이라 h_need 0, 역시 0 이다.
    #
    # 튜닝 여지가 거의 없다 -- 파라미터가 n(기체 하중배수)과 ref 둘뿐이고
    # 둘 다 기체 성능에서 나온다. 크기를 키워도 정상 비행에는 영향이 없다.
    w_rec = C("w_recover")
    if w_rec:
        _rr = math.radians(float(ownship_state[StateIndex.ROLL]))
        _rp = math.radians(float(ownship_state[StateIndex.PITCH]))
        _cr2, _sr2 = math.cos(_rr), math.sin(_rr)
        _cp2, _sp2 = math.cos(_rp), math.sin(_rp)
        _u2 = float(ownship_state[6]); _v2 = float(ownship_state[7]); _w2 = float(ownship_state[8])
        _spd2 = math.sqrt(_u2 * _u2 + _v2 * _v2 + _w2 * _w2)
        # 동체 -> NED 의 D 성분(아래가 양수) = 침하율
        _dn2 = (-_sp2) * _u2 + (_sr2 * _cp2) * _v2 + (_cr2 * _cp2) * _w2
        if _spd2 > 1.0 and _dn2 > 0.0:
            _sg = min(max(_dn2 / _spd2, 0.0), 1.0)          # sin(강하각)
            _gam = math.asin(_sg)
            if math.degrees(_gam) >= C("recover_min_gamma_deg"):
                _ng = max(C("recover_g"), 1.001)
                _need = (_spd2 * _spd2 * (1.0 - math.cos(_gam))) / (9.81 * (_ng - 1.0))
                if _need > 1.0:
                    _alt2 = -float(ownship_state[StateIndex.D])
                    _ratio = _alt2 / _need
                    _k = max(C("recover_ratio_k"), 1e-3)
                    comp["recover"] = -w_rec * min(max(1.0 - _ratio / _k, 0.0), 1.0)

    # 3c-2. [MOD-TTI] 지면 충돌 잔여시간 — 실측(0822_clean 리플레이 24판)으로 신설.
    #
    # 추락/비추락을 가르는 것은 고도도 침하율도 **아니었다**:
    #     판 전체 |롤|>90 체류   추락 30.8%  vs  비추락 30.2%   <- 차이 없음
    #     마지막 8초 |롤|>90 & 피치<0  51.9%  vs  14.8%        <- 3.5배
    # 즉 뒤집히는 것 자체는 정상 기동이고, **뒤집힌 채 기수가 지평선 아래인
    # 상태가 지속되는 것**만 치명적이다. 그런데 그 상태의 본질은 자세가 아니라
    # "곧 땅에 닿는다"이다. 그래서 자세가 아니라 **잔여시간**에 값을 매긴다.
    #
    # 왜 기존 항으로 안 되는가 (전부 실측 실패):
    #     w_deck  위치만 본다 -> 고고도 급강하를 놓치고, 켜질 땐 이미 늦다
    #     w_alt   위치만 본다 -> 종료고도 811 -> 2,031 m 로 올렸는데 추락 32.7 -> 33.1
    #     w_sink  침하율만 본다 -> 고고도의 정상 강하까지 벌줘 속도가 139 m/s 로 죽었다
    # 둘을 곱해야 한다. tti = 고도 / 침하율.
    #     추락판  t-3  791 m / 149 m/s =  5.3 초   <- 켜짐
    #     비추락  t-3  946 m / 상승      =  무한    <- 안 켜짐
    #     스폰    4,572 m / 150 m/s     = 30.5 초  <- 안 켜짐 (고고도 급강하는 공짜)
    # 수평 저공비행(침하 ~0)도 안 켜진다. 오직 "곧 부딪힌다"만 값을 문다.
    w_tti = C("w_tti")
    if w_tti:
        _rt = math.radians(float(ownship_state[StateIndex.ROLL]))
        _pt = math.radians(float(ownship_state[StateIndex.PITCH]))
        _crt, _srt = math.cos(_rt), math.sin(_rt)
        _cpt, _spt = math.cos(_pt), math.sin(_pt)
        _sink = ((-_spt) * float(ownship_state[6])
                 + (_srt * _cpt) * float(ownship_state[7])
                 + (_crt * _cpt) * float(ownship_state[8]))
        if _sink > 1.0:
            _alt_now = -float(ownship_state[StateIndex.D])
            _tti = _alt_now / _sink
            _ref = max(C("tti_ref_s"), 1e-3)
            comp["tti"] = -w_tti * max(0.0, 1.0 - _tti / _ref)

    # 3d. 근접 과속 — 1.5 km 이내에서 220 m/s 초과분 완만 벌점
    w_over = C("w_overspeed")
    if w_over:
        spd = math.sqrt(float(ownship_state[6])**2 + float(ownship_state[7])**2
                        + float(ownship_state[8])**2)
        prox = 1.0 - _S(d_m, 1.0 / 200.0, C("overspeed_gate_m"))
        fast = _S(spd, 1.0 / 15.0, C("overspeed_ref_mps"))
        # 3d-2: 선회 필요 게이트 — 적이 기수 밖일수록 고속이 비싸진다
        turn_ata = C("overspeed_turn_ata_deg")
        need = min(ata / turn_ata, 1.0) if turn_ata > 0.0 else 1.0
        comp["overspeed"] = -w_over * prox * fast * need

    # 4c. 천장 — 36,000 ft 위 완만한 램프 (자가대전 고고도 퇴화 균형 차단)
    w_ceil = C("w_ceil")
    if w_ceil:
        ramp = max(C("ceil_ramp_ft"), 1.0)
        comp["ceil"] = -w_ceil * _S(alt_ft, 1.0 / ramp, C("ceil_ft"))

    w_alt = C("w_alt")
    if w_alt:
        alt_m = -float(ownship_state[StateIndex.D])
        ceil_m = max(C("alt_ceiling_m"), 1.0)
        phi = w_alt * min(max(alt_m / ceil_m, 0.0), 1.0)
        prev = _PREV_ALT_PHI.get("v")
        # 에피소드 경계는 SIM_TIME 이 되감기는 것으로 감지한다. env 는
        # num_envs_per_env_runner = 1 이 전제다(프로젝트 규약).
        t = float(ownship_state[StateIndex.SIM_TIME])
        if prev is None or t < _PREV_ALT_PHI.get("t", 0.0):
            prev = phi
        comp["alt"] = phi - prev
        _PREV_ALT_PHI["v"] = phi
        _PREV_ALT_PHI["t"] = t
        if terminated or truncated:
            _PREV_ALT_PHI.clear()

    # 4c. 고공 벌점 포텐셜 — 4c 주석 참조. Phi = -w * clip((alt-floor)/span,0,1)
    #     위로 갈수록 Phi 가 낮아지므로 상승은 벌점, 강하는 회수.
    w_high = C("w_high")
    if w_high:
        alt_h = -float(ownship_state[StateIndex.D])
        excess = (alt_h - C("high_floor_m")) / max(C("high_span_m"), 1.0)
        phi_h = -w_high * min(max(excess, 0.0), 1.0)
        prev_h = _PREV_HIGH_PHI.get("v")
        t_h = float(ownship_state[StateIndex.SIM_TIME])
        if prev_h is None or t_h < _PREV_HIGH_PHI.get("t", 0.0):
            prev_h = phi_h
        comp["high"] = phi_h - prev_h
        _PREV_HIGH_PHI["v"] = phi_h
        _PREV_HIGH_PHI["t"] = t_h
        if terminated or truncated:
            _PREV_HIGH_PHI.clear()

    # 4d. 선회 최적고도 선호 — 4d 주석 참조.
    #     Phi = -w * clip(|alt - pref| / span, 0, 1)  (위아래 양쪽에서 당긴다)
    w_ta = C("w_turnalt")
    if w_ta:
        alt_t = -float(ownship_state[StateIndex.D])
        dev = abs(alt_t - C("turnalt_pref_m")) / max(C("turnalt_span_m"), 1.0)
        phi_t = -w_ta * min(max(dev, 0.0), 1.0)
        prev_t = _PREV_TURNALT_PHI.get("v")
        t_t = float(ownship_state[StateIndex.SIM_TIME])
        if prev_t is None or t_t < _PREV_TURNALT_PHI.get("t", 0.0):
            prev_t = phi_t
        comp["turnalt"] = phi_t - prev_t
        _PREV_TURNALT_PHI["v"] = phi_t
        _PREV_TURNALT_PHI["t"] = t_t
        if terminated or truncated:
            _PREV_TURNALT_PHI.clear()

    # 4e. 무교전 벌점 — 4e 주석 참조. 마지막 교전 이후 경과 시간에 비례.
    #     `w_turnalt` 같은 자기상태 보상이 교전을 대체하는 것을 막는 짝 항이다.
    w_idle = C("w_idle")
    if w_idle:
        t_i = float(ownship_state[StateIndex.SIM_TIME])
        last = _PREV_IDLE.get("last")
        if last is None or t_i < _PREV_IDLE.get("t", 0.0):   # 에피소드 경계
            last = t_i
        if d_m <= C("idle_reset_m"):        # 쫓고 있다 -> 타이머 리셋
            last = t_i
        idle = max(0.0, t_i - last)
        ramp = max(C("idle_ramp_s"), 1e-3)
        comp["idle"] = -w_idle * min(max((idle - C("idle_grace_s")) / ramp, 0.0), 1.0)
        _PREV_IDLE["last"] = last
        _PREV_IDLE["t"] = t_i
        if terminated or truncated:
            _PREV_IDLE.clear()

    # [MOD-NODMG 2026-08-23] 마감시간까지 무딜이면 그 시점에 1회 벌점.
    w_nodmg = C("w_nodmg")
    if w_nodmg:
        sim_t = float(ownship_state[StateIndex.SIM_TIME])
        if sim_t < _NODMG_STATE.get("t", 0.0):     # 시간이 되감기면 새 판
            _NODMG_STATE.clear()
        _NODMG_STATE["t"] = sim_t
        deadline = C("nodmg_deadline_s")
        due = (sim_t >= deadline) if deadline > 0.0 else bool(terminated or truncated)
        if due and not _NODMG_STATE.get("fired"):
            if float(target_state[StateIndex.HEALTH]) > C("nokill_hp_thresh"):
                comp["nodmg"] = -w_nodmg
            _NODMG_STATE["fired"] = True           # 격추했으면 벌점 없이 소진
        if terminated or truncated:
            _NODMG_STATE.clear()

    if C("step_penalty"):
        comp["step"] = C("step_penalty")

    # 5. 종료
    terminal = 0.0
    if terminated or truncated:
        own_hp = float(ownship_state[StateIndex.HEALTH])
        tgt_hp = float(target_state[StateIndex.HEALTH])
        sim_t = float(ownship_state[StateIndex.SIM_TIME])
        max_t = max(C("max_engage_time"), 1.0)
        ec = str(end_condition or "")
        if "time out" in ec and C("timeout_penalty"):
            # [MOD-TIMEOUT] 시간초과는 확실한 손해로 만든다. HP 우위와 무관.
            terminal = -C("timeout_penalty")
        elif "ownship altitude" in ec:
            terminal = C("crash_reward")
        elif "target altitude" in ec:
            terminal = C("target_crash_reward")
        elif tgt_hp <= 0.0 < own_hp:
            terminal = C("win_reward") + C("win_time_bonus") * max(
                0.0, 1.0 - sim_t / max_t)
        elif own_hp <= 0.0 < tgt_hp:
            terminal = C("loss_reward")
        elif own_hp <= 0.0 and tgt_hp <= 0.0:
            if "ownship destroyed" in ec:
                terminal = C("loss_reward")
            elif "target destroyed" in ec:
                terminal = C("win_reward") + C("win_time_bonus") * max(0.0, 1.0 - sim_t / max_t)
            else:
                terminal = C("draw_reward") + C("draw_health_scale") * (own_hp - tgt_hp)
        else:
            terminal = C("draw_reward") + C("draw_health_scale") * (own_hp - tgt_hp)
    comp["terminal"] = terminal

    return float(sum(comp.values())), comp


__all__ = ["MY_REWARD_CONFIG", "MY_REWARD_WEIGHTS", "MY_REWARD_PARAMS", "compute_reward"]
