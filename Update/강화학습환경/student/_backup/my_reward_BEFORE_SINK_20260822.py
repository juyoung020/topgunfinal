# -*- coding: utf-8 -*-
"""[학생 파일] 공격 전용 보상 — 5항.

원칙
----
**공격항만 둔다. 방어항은 없다.**

이전 버전(ADT 논문 Aggressive Shooter 4항 이식)에는 `gunsnap_red`(적이 나를
겨눌 때의 벌점)가 있었는데, 정면 머지에서 실측하면 이렇게 나온다:

    gunsnap_blue  +3.58   (내가 쏨)
    gunsnap_red   -3.46   (내가 맞음)
    ----------------------------
    합            +0.12   <- 거의 상쇄

**공격항과 방어항이 서로 싸운다.** 우리 컨셉은 전방위 공격이고, 정면 머지에서
양쪽이 각각 0.762 HP 를 주고받는 교환을 **먼저 겨눠서** 이기는 것이다. 물러서게
만드는 항은 그 교환을 회피하게 한다. 그래서 뺐다.

`gunsnap_blue` 도 뺐다 — WEZ 안에서만 켜지는데 `damage` 가 같은 조건에서
실제 데미지에 비례해 지불하므로 **중복**이다. 두 개를 두면 어느 쪽이 효과를
냈는지 구분할 수 없다.

남은 5항
--------
    aim      기수를 적에게 향하게        (연속, 사거리 게이트)
    range    사격 범위 안에 붙어 있게
    damage   실제로 맞히기 = 격추 그 자체
    deck     지면 회피                  (전술적 방어가 아니라 물리)
    terminal 격추 / 패배 / 추락 / 판정

`deck` 은 방어항이 아니다. 1,000 ft 이하는 규칙상 즉사이고, 이 기체는 중립
조종에서 활강한다(실측). 적과 무관한 물리 제약이다.

단위·상수
---------
WEZ: 152.4 <= d <= 914.4 m 이고 |ATA| <= 1도. 데미지 = (914.4-d)/762 per second.
HP 는 1.0 이라 425 m 에서 스텝당 0.0642 -> **격추까지 15.6 스텝**(실측).

학습에서만 돈다(대회엔 보상이 없다). 그래서 51칸 상태의 HEALTH/SIM_TIME 을
읽어도 전이 문제가 없다 — 관측(`my_observation.py`)과 달리 9/9 제약을 안 받는다.
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


MY_REWARD_CONFIG = {
    # ── 1. 조준 ─────────────────────────────────────────────────────────
    # (1 - (ATA/180)^0.2). 지수 0.2 는 ADT 논문(arXiv:2105.00990) 식 9 의
    # lambda = 1/5 그대로 — 0도 근처에서 가파르고 먼 각도에서 완만하다.
    #   ATA   0도 -> 1.000   1도 -> 0.646   30도 -> 0.301   180도 -> 0.000
    # **항상 0 이상**이다. 논문 원식은 음수인데, PPO + gamma 0.995 에서는
    # "못 싸울 바엔 일찍 추락"이 3배 이득이 되는 자살유인이 생긴다(실측).
    "w_aim": 0.08,
    "aim_lambda": 0.2,
    # 거리 게이트: 이게 없으면 5 km 밖에서 기수만 두는 것이 근접 교전보다
    # 높게 나온다(실측 290 대 80). 2,000 m 중심으로 부드럽게 끈다.
    "aim_range_gate_m": 2000.0,

    # ── 1b. 광각 유도 (2026-08-03) ──────────────────────────────────────
    # 등돌린 스폰(양쪽 ATA 180도)이 기본 시작 조건이 되면서 필요해졌다.
    # 위 곡선은 lambda 0.2 라 0도 근처만 가파르고 150~180도가 사실상 평평하다:
    #   ATA 180 -> 0.000,  170 -> 0.0114,  150 -> 0.0358
    # 즉 등을 돌린 채 10도를 돌아도 스텝당 +0.0009 (w_aim 의 1.1%) — "적 쪽으로
    # 돌아서라"는 신호가 없다. 실제로 back_to_back 스테이지만 BC 0/10, WEZ 3.3
    # 으로 유일하게 못 푸는 구간이었다(다른 스테이지는 전부 격추).
    # 선형은 기울기가 전 각도에서 균일하다(스텝당 w/180 per deg). 정밀 조준은
    # 위 곡선이, 큰 각도의 방향 전환은 이 항이 담당한다. 같은 거리 게이트를
    # 공유해 "멀리서 기수만 두기" 파밍은 이미 막혀 있다. 공격항이다 —
    # 적을 향해 도는 것 외에는 아무것도 지불하지 않는다.
    "w_aim_wide": 0.08,

    # ── 2. 사거리 ───────────────────────────────────────────────────────
    # 사격 범위 안에 붙어 있는 것 자체를 지불한다. 격추엔 밴드 안에서 15.6
    # 스텝이 필요한데, 조준까지 돼야 나오는 항만 있으면 파고들 유인이 없다.
    "w_range": 0.04,

    # ── 3. 데미지 = 격추 그 자체 ────────────────────────────────────────
    # 총량이 w_damage x HP(1.0) 로 **유계**라 파밍이 불가능하다.
    # 스텝당 지불하므로 "머무는 것"을 사는 유일한 항이기도 하다
    # (포텐셜 항은 텔레스코프해서 체류를 못 산다).
    "w_damage": 300.0,
    # 맞는 것에 대한 벌점은 **0**. 정면 머지에서 물러서게 만들면 안 된다.
    "w_damage_taken": 0.0,

    # 최소사거리 침범 벌점.
    # 데미지 항이 다른 모든 항을 압도한다 — 2026-08-03 실측, WEZ 안에서 조준이
    # 맞을 때 스텝당 `w_damage x damage` 는
    #     900m 0.57 / 500m 16.3 / 200m 28.1  이고 같은 지점의 aim+range 는 0.119.
    # 200 m 에서 236배다. 데미지는 가까울수록 커지므로 정책은 하한(152 m)까지
    # 밀고 들어가고, 거기서 보상이 절벽처럼 0 으로 떨어진다. 실제로 최소거리가
    # stage 1 의 603 m 에서 52 m 까지 내려갔고 WEZ 체류가 72 -> 13 으로 무너졌다
    # (`range` 항의 하한 감쇠를 6배 세워도 236배 차이 앞에서는 무의미했다).
    # 그 거리에서는 각속도가 추적 한계를 넘어(152~250 m 구간 28.8 deg/s) 조준을
    # 유지할 수 없다.
    # 규칙(실제 데미지 계산)은 건드리지 않는다. 하한을 넘어 들어가는 행동에만
    # 데미지와 같은 스케일의 벌점을 주어 유인을 상쇄한다.
    # 가중치는 **에피소드 누적**으로 잡아야 한다. 스텝당 균형만 보고 30 으로
    # 뒀더니 침범 스텝이 수백 개 쌓여 에피소드당 -2,148 이 나왔고(데미지 +107 의
    # 20배), 전체 보상을 -2,121 로 만들어 다른 신호를 전부 삼켰다. damage 는
    # 총량이 w x HP = 300 으로 유계지만 이 항은 무계다. 격추 1회(=300)를 넘지
    # 않도록 1.0 으로 둔다(같은 궤적 기준 약 -72).
    # 형태가 중요하다. 선형 램프로는 스텝당 균형(데미지 28 을 이겨야 함)과
    # 에피소드 누적(격추 300 을 안 넘어야 함)이 동시에 만족되지 않는다:
    # w 30 이면 누적 -2,148 로 모든 신호를 삼키고, w 1 이면 스텝당 -0.76 이라
    # 데미지 앞에서 무의미해 최적점이 다시 하한(160 m)에 붙는다.
    # 그래서 **데미지를 거리로 게이팅**한다 - 하한 근처에서 데미지 보상 자체를
    # 깎으면 유인이 사라지고, 새 항을 더하지 않으니 누적 폭주도 없다.
    "damage_near_gate_m": 250.0,  # 이 거리 아래로 데미지 보상이 감쇠
    "damage_near_floor": 0.15,    # 하한에서 남는 비율

    # 3c. 정면샷 우대 (2026-08-05, 사용자 지시: "정면샷이나 다방면 샷을 해야").
    # 데미지는 각도 불문 같은 값인데 정면 머지는 체류가 ~1초뿐이라 실질
    # 총액이 작아 후미 추적이 늘 유리했다 — RL 쌍이 서로 꼬리를 노리며
    # 나선 상승하는 원인. 벌점으로 꼬리를 막으면 격추 자체와 싸우는
    # 방어항이 되므로, 대신 **적 기수가 나를 향한 상태에서 넣은 데미지**에
    # 배수를 건다: 정면 교환("먼저 겨눠서 이기기")이 후미 추적과 경쟁 가능한
    # 보상이 된다. 후미샷은 x1 그대로 — 여전히 정당한 격추다.
    # front = 1 - min(적ATA, 90)/90  (적이 정면으로 마주볼 때 1, 옆/뒤면 0)
    # 배수 = 1 + w_headon_mult * front  (기본 x2 까지)
    "w_headon_mult": 1.0,

    # 3d. 근접 과속 벌점 (2026-08-05, ADT 영상 HUD 실측 기반).
    # 대회 영상의 교전은 전부 109~200 m/s (212~389 kts) 에서 벌어진다 — 같은
    # 기체가 상시 4~6g 를 당겨 에너지를 태우기 때문. 속도가 절반이면 선회
    # 반경이 1/4 이라 원이 겹쳐 "제자리 싸움 = 딜이 무조건 나는" 기하가 된다.
    # 우리 정책은 스로틀 0.95+ 고정(BC 씨앗 + 빠름이 안전한 기울기)이라 근접
    # 에서도 300+ m/s -> 스침만 반복. 근접(<1.5 km)에서 220 m/s 초과분에만
    # 완만한 벌점을 걸어 "머지에서 에너지를 태워 체류를 사는" ADT 방정식을
    # 보상에 새긴다. 원거리 추격 속도는 건드리지 않는다(게이트 밖 0).
    "w_overspeed": 0.3,
    "overspeed_ref_mps": 220.0,
    "overspeed_gate_m": 1500.0,
    # 3d-2. 선회 필요 게이트 (2026-08-10 사용자 지시 "속도를 줄이고 선회하면
    # 더 빨리 도는 이점이 반영 안 됐다").
    # iter_0120 실측: 근접속도 중앙 206~294 m/s 로 머지를 관통(최소거리 12~91 m)
    # → 그 속도의 선회 반경 ~1.6 km 때문에 되돌아오는 동안 2.5~4 km 로 벌어짐.
    # 감속(180 m/s → 반경 660 m)해야 붙어서 돌 수 있는데, 기존 벌점은 조준
    # 상태와 무관해 "꺾어야 할 때 감속"의 신호가 아니었다.
    # >0 이면 벌점에 need = min(ATA/이 값, 1) 을 곱한다: 적이 기수 안이면
    # (추격 부스트) 고속 무벌점, 기수 밖(선회 필요)일수록 벌점 만개.
    # 0 = 기존 동작 그대로.
    "overspeed_turn_ata_deg": 0.0,

    # 3f. 원거리 배회 벌점 (2026-08-10 사용자 지시 "완전 근접 강제").
    # 멀리 있으면 그동안은 기회비용(수입 0)뿐이라 배회가 공짜였다.
    # far_start 부터 로지스틱으로 벌점 — 멀수록 스텝당 -w 까지.
    # 자살 유인 방지: 에피소드 만점 벌점(w x 2000)이 crash_reward(-250)보다
    # 절대값이 작아야 한다 → w 0.12 x 2000 = -240 < 250. 상한 준수.
    "w_far": 0.0,
    "far_start_m": 1200.0,
    "far_ramp_m": 800.0,

    # 3g. 콘-게이트 WEZ 셰이핑 (2026-08-10 사용자 지시 "적어도 조준콘 안에
    # 있어야 하고, 데미지가 가장 좋은 최소지점에 붙을수록 좋다").
    # 실제 데미지 물리(single_agent_env._wez_damage)를 그대로 보상 모양으로 옮긴다:
    #   데미지 = (914-d)/762 x Δt, 조건 |ATA|<=1° AND 152<=d<=914.
    #   즉 914 m 에서 0, 가까울수록 선형 증가, 152 m 미만은 0(언더런).
    # 곱 구조 cone(ATA) x prox(d) 라 **콘 밖 근접 배회는 한 푼도 못 받는다** —
    # w_range 단독일 때 생기던 "조준 없는 근접 선회" 퇴화를 막는다.
    #   cone = max(0, 1 - ATA/cone_deg): 콘 안으로 들어올 기울기를 15°부터 제공
    #   prox = 914 m 에서 0 → wez_best_m 까지 선형 상승 → [152, best] 평탄역
    #          → 152 m 밑 급감(기존 range 하한 감쇠와 동일 형태)
    # 최적점을 152 가 아닌 260 m 평탄역으로 두는 이유(실측): 152~250 m 는 LOS
    # 각속도 28.8°/s 로 추적 한계를 넘어 조준 유지가 불가(파고들다 WEZ 체류
    # 72→13 붕괴 전례). 260~300 m 는 데미지 0.81~0.86/s(최대의 86%)를 유지하며
    # 추적 가능 — "기체를 꺾어 공격 가능한" 실효 최대 데미지 지점.
    # 파밍 상한: w 0.20 x 2000스텝 = 400 이지만 완전정조준 200초 체류는 데미지
    # 격추(WEZ ±1° 즉시 딜)와 물리적으로 양립 불가, 실효는 격추 300 미만.
    "w_wez": 0.0,
    "wez_cone_deg": 15.0,
    "wez_best_m": 260.0,

    # 3h. 스냅락 — 밴드 내 정밀 조준 보너스 (2026-08-11, mutualclose 정체 실측).
    # 콘 15° 체류는 최대 47스텝까지 만들어졌는데 딜이 0 — 15°→1° 마지막
    # 구간의 수입 기울기가 ~0.07/step 뿐이라(aim λ0.2 곡선 + wez cone 선형)
    # 정밀 조준이 잠기지 않았다. damage 는 |ATA|<=1° 절벽 안에서만 지불되므로
    # 문턱까지 끄는 항이 따로 필요하다. gunsnap_blue 삭제 사유였던 "damage 와
    # 중복"과 다르다: 이 항은 damage 가 0 인 1~3° 구간을 산다.
    # 파밍 상한: 이론상 w x 2000 이지만 기동 상대에 1~3° 유지 실측 최대 47스텝
    # — 격추(300+시간보너스200)가 압도. 밴드 밖·3° 밖 0.
    "w_snap": 0.0,
    "snap_ata_deg": 3.0,

    # 3j. 미스거리(NMD) 사격 셰이핑 — 2026-08-15 실측으로 도입.
    # NMD = d x sin(ATA) = 기수 연장선이 적기를 **몇 미터** 빗나가는가.
    # 각도항(aim/wez/snap)의 결함: 같은 1도라도 3 km 에서는 52 m 빗나가고
    # 425 m 에서는 7.4 m 다. 각도로 보상하면 데미지가 물리적으로 불가능한
    # 원거리 대충 조준에 기울기가 몰린다. 실제로 그렇게 됐다 —
    # signalclean_iter1420 본선 8판 실측: 사거리 안 822 스텝의 NMD 중앙값이
    # **235 m** 인데 규칙이 요구하는 값은 425 m 에서 7.4 m 다. p1 조차 9.6 m.
    # 판당 머지 4.9 회로 기회는 있는데 패스당 딜이 0.009 (클린 패스 이론값 0.69).
    # 미터로 보상하면 거리와 무관하게 "사선에 올려라" 하나가 되고, near 가중이
    # 실제 데미지 곡선 (hi-d)/(hi-lo) 과 같아 근거리 선호가 자동으로 붙는다.
    # 쌍곡선 1/(1+NMD/h) 를 쓰는 이유: 가우시안은 235 m 에서 기울기가 0 이라
    # 현재 정책 위치에서 배울 게 없다. 쌍곡선은 미분이 -h/(h+NMD)^2 라
    # 235 m 에서도 살아있고(1.7e-4/m) 10 m 에서 150 배 가팔라진다.
    # 파밍 상한: 밴드 안에서만, w x 2000 스텝이 상한이나 NMD<=10 m 를 200초
    # 유지하는 것은 곧 격추라 실효 상한은 격추 보상에 흡수된다.
    "w_nmd": 0.0,
    "nmd_half_m": 10.0,

    # 3k. 예측 최근접거리(CPA) 사전 조향 — 3j 와 짝. 사거리 **밖**에서만 켠다.
    # t_cpa = -(rel . v_rel)/|v_rel|^2, d_cpa = |rel + v_rel x t_cpa|
    # = 지금 침로를 그대로 유지하면 몇 미터를 두고 스쳐 지나가는가.
    # 머지는 접근 속도 500 m/s 대라 사거리 밴드 통과가 1.2 초(12 스텝)뿐이다.
    # 밴드에 들어간 뒤 조준을 만들 시간이 없다 — **들어가기 전에** 충돌코스가
    # 만들어져 있어야 한다. 3j 는 밴드 안에서만 켜지므로 그 사전 구간이 비어
    # 있었다. 지평선(기본 8 초) 안에 최근접이 예정된 경우만 지불.
    # 충돌코스(d_cpa=0)는 LOS 각속도가 0 이라 10 Hz 제어로도 조준 유지가 되는
    # 유일한 기하다. 반대로 d_cpa 50 m 면 425 m 에서 LOS 가 11.7 deg/s 로 돌아
    # 스텝당 1.2 도 — ±1 도 원뿔 폭보다 커서 원리적으로 유지 불가.
    "w_cpa": 0.0,
    "cpa_half_m": 40.0,
    "cpa_horizon_s": 8.0,

    # 3i. 접근 포텐셜 (2026-08-12 사용자 지시 "접근할수록 보상. 전면전으로").
    # r = Phi(s') - Phi(s), Phi = -w x d/1000. 거리를 1 km 좁히면 누계 +w,
    # 다시 벌어지면 같은 만큼 회수 — 텔레스코프라 배회·왕복 파밍이 불가하고,
    # 머지 후 상호 이탈 루프(스치고 2~4 km 벌어짐)에 직접 벌점이 걸린다.
    # 리셋 감지는 고도 포텐셜(4b)과 동일: SIM_TIME 되감김.
    "w_close_pot": 0.0,

    # 3e. 퍼치(유지 추격) — 2026-08-06 대회 결승 프레임 실측에서 이식.
    # 상위권 득점은 "0.7~1.8 km 후방에서 LOS 한 자릿수를 수 초 유지"에서
    # 나왔다(FalconAI: 1,442 m·LOS 5.5°·조준유지 누적 14.1 s vs 우리 0.2 s).
    # 우리 보상은 사거리 밴드(152~914 m) 밖 유지 위치에 0 이라 정책이 600 m/s
    # 관통 머지만 시도했다(iter150 리플레이: 최소거리 28~68 m, 원뿔 유지 0).
    # 밴드 어깨(700~1,800 m)에서 ATA 10° 미만일 때만 스텝 보상 — WEZ 진입
    # 대기 자세를 만든다. 기본 0 = 기존 스테이지 무영향.
    "w_perch": 0.0,
    "perch_ata_deg": 10.0,
    "perch_near_m": 700.0,
    "perch_far_m": 1800.0,

    # ── 4. 지면 ─────────────────────────────────────────────────────────
    "w_deck": 4.0,
    "deck_ft": 1300.0,          # 실제 사망 바닥은 1,000 ft. 여유를 둔다.

    # 4c. 천장 (2026-08-05 실측으로 추가). 자가대전 리플레이에서 미러 쌍이
    # 고도 14,200 m(47,000 ft)까지 상승 — "높이 올라가면 안 맞는다"는 퇴화
    # 균형이다. 그 고도에선 공기밀도가 1/4 이라 선회가 안 돼 아무도 못 쏜다.
    # deck 의 거울상: 36,000 ft 위로 완만히 벌점. 전투 고도(7 km = 23,000 ft)
    # 에는 정확히 0 이라 기존 스테이지에 영향 없다. 방어항이 아니라 물리다.
    "w_ceil": 4.0,
    "ceil_ft": 40000.0,   # 36k -> 40k: 램프를 넓히니 전투고도(23k ft)에
                          # -0.148/step 상시 세금이 생겨 중심을 올렸다.
                          # 40k/3k 프로파일: 23k ft -0.014(무시 가능),
                          # 46k ft 기울기 -0.46/km(하강 신호 유효).
    # 램프 폭. 1,000 ft 로 뒀더니 46,000 ft(자가대전 실측 고도)에서 로지스틱이
    # 포화해 **정상부에 기울기가 0** — 내려올 국소 신호가 없었다(reward -2,400
    # 40 iter 평평, 구 워크스페이스 고도천장 포화 함정과 동일). 4,000 ft 면
    # 기울기가 30k~50k ft 전역에 걸친다.
    "ceil_ramp_ft": 3000.0,

    # 고도 포텐셜. `w_deck` 은 **400 m 아래에서만** 켜진다(실측: 7,000~500 m
    # 구간의 스텝당 벌점이 정확히 0.0000). 7,000 m 에서 내려오는 내내 정책은
    # 아무 신호도 못 받고, 종료 보상은 감마 0.995 x 600 스텝에 짓눌린다 —
    # 에피소드 시작 시점에서 "생존 +30"의 현재가치는 +1.48, "추락 -250"은
    # -12.35 다. 유효 지평(1/(1-gamma) = 200 스텝)이 에피소드보다 훨씬 짧아
    # 앞 400 스텝에서는 강하와 수평비행이 구별되지 않는다. 그래서 BC 로 심은
    # 비행을 유지할 이유가 보상에 없었고, 크리틱을 고쳐도(explained_var
    # 0.45 -> 0.98) 추락률이 0.21 -> 0.60 으로 계속 올랐다.
    #
    # 포텐셜 기반이라 (gamma_shape = 1) 텔레스코프한다: 한 에피소드 총합이
    # w * (끝 고도 - 시작 고도) / ceiling 으로, 오르내림의 **차이**만 지불하고
    # 최적 정책은 바뀌지 않는다. 이전 워크스페이스의 `w_phi_alt`(stage 0 에서
    # 200)와 같은 구실을 한다.
    "w_alt": 0.0,               # 0 = 끔. 비행 스테이지에서만 켠다.
    "alt_ceiling_m": 6300.0,

    # ── 4c. 고공 벌점 포텐셜 (2026-08-15 실측으로 신설) ──────────────────
    # 위 `w_alt` 는 6,300 m 에서 **클립**돼 그 위로는 기울기가 0 이다. 그런데
    # 실측(alt_trace.py 8판)에서 정책은 7,000 m 스폰에서 시작해 **중앙 8,167 m,
    # p90 11,581 m** 까지 올라간다(8판 중 7판이 9,000~13,300 m 로 종료).
    # 그 구간에는 값을 매기는 항이 아예 없었다 — w_ceil 은 45,000 ft
    # (13,716 m) 위에만 물어서 12,000 m 까지 공짜였다.
    #
    # 왜 고공이 손해인가 (turn_radius_alt.py 실측, 뱅크85 풀당김 스로0.3):
    #     고도      선회율    선회지름   180도 반전
    #    3,000 m   15.9°/s   1,985 m    12.0 s
    #    7,000 m   11.1°/s   2,907 m    16.9 s   <- 스폰
    #    8,167 m    9.6°/s   3,434 m    19.4 s   <- 실측 중앙
    #   11,500 m    6.7°/s   5,225 m    26.0 s   <- 실측 p90
    # 7,000 -> 11,500 m 상승은 선회 지름을 **2배**로, 선회율을 **반토막**으로
    # 만든다. 200 초 교전의 반전 횟수가 11 회에서 7 회로 준다. 사거리 밴드가
    # 914 m 인데 선회 지름이 5 km 면 사격 기하에 들어갈 기회 자체가 없다.
    #
    # 왜 올라가나: BC 교사가 뱅크 72°에 기수를 든 채 돌아 **반전마다 +628 m**
    # 상승한다(maxturn.py 실측). 정책이 그 습관을 물려받았고 200 초에 누적된다.
    # 물리 법칙이 아니라 학습된 습관이므로 고칠 수 있다.
    #
    # 형태: 포텐셜(gamma_shape=1)이라 에피소드 총합 = -w x (끝-시작) 정규초과분.
    # 오르내림의 **차이**만 지불하므로 파밍 불가이고 최적 정책을 바꾸지 않는다.
    # `w_ceil` 같은 스텝 벌점으로 하지 않는 이유: 그 형태가 2026-08-14 에
    # 딜 신호를 53:1 로 덮어 6,000 iteration 을 날렸다.
    # floor 위로만 물고 span 만큼 가서 포화 — 14,000 m 위는 어차피 안 간다.
    "w_high": 0.0,
    "high_floor_m": 6000.0,
    "high_span_m": 8000.0,

    # ── 4d. 선회 최적고도 선호 (2026-08-16 사용자 아이디어) ──────────────
    # "선회가 잘 되는 고도에서 싸우면 사격 기회가 많아 타격을 더 배운다."
    # 실측 선회율(turn_radius_alt.py, 뱅크85 풀당김 스로0.3):
    #     1,200 m 18.0 deg/s   1,500 m 17.5   3,000 m 15.9   5,000 m 13.4
    #     7,000 m 11.1         8,167 m  9.6  11,500 m  6.7
    # 낮을수록 빠르지만 추락 하한이 305 m 다. 2,000~3,500 m 가 선회 15~16 deg/s
    # 를 쓰면서 지면과 1.7 km 이상 떨어지는 구간이라 기본값을 3,000 m 로 잡는다.
    #
    # 왜 기존 항으로는 안 되는가: `w_deck` 은 1,300 ft 아래만, `w_high` 는
    # 6,000 m 위만 문다. **그 사이는 완전히 평평**해서 3,000 m 와 6,000 m 가
    # 정책에게 똑같다 — 선호가 생길 수 없다. 실측: 어느 고도에 스폰해도
    # 200 초 안에 2,000~2,300 m 를 올라간다(1,500 -> 3,241 / 7,000 -> 9,262).
    # 스폰만 낮추는 것으로는 해결이 안 되는 이유가 이것이다.
    #
    # 형태: 포텐셜(gamma_shape=1). Phi = -w * clip(|alt - pref| / span, 0, 1)
    # 목표 고도에서 0, 멀어질수록 -w 까지. 위아래 **양쪽**에서 당기므로 봉우리가
    # 생긴다. 텔레스코프라 에피소드 총합이 (끝 - 시작)뿐 = 파밍 불가.
    #
    # ⚠ `w_high` 와 같이 켜지 말 것 — 6,000 m 위에서 이중으로 물어 균형이 깨진다.
    # ⚠ 추락률과 직접 맞바꾸는 항이다. w_deck 을 4 -> 8 로 올려서 겨우 0.00~0.06
    #    으로 잡은 전례가 있으므로, 켤 때는 추락률을 같이 볼 것.
    "w_turnalt": 0.0,
    "turnalt_pref_m": 3000.0,
    "turnalt_span_m": 6000.0,

    # ── 4e. 무교전 벌점 (2026-08-16 사용자 지시) ──────────────────────────
    # 왜 필요한가: `w_turnalt` 를 켰더니 **보상 해킹**이 났다. 그 항은 적과
    # 무관하게 만족되므로(2,000 m 유지는 혼자서도 된다) 정책이 교전 대신
    # 제 고도에서 선회만 했다 — 리플레이 관측 "각자 고도에서 빙글빙글",
    # 지표로는 WEZ 체류 30 -> 20, 딜 400 -> 350.
    #
    # 해법: 고도 선호는 그대로 두고 **안 쫓는 것을 비싸게** 만든다. 그러면
    # "고도만 지키고 버티기"의 값이 음수가 되어 해킹이 성립하지 않는다.
    #
    # 형태: 마지막 교전 이후 경과 시간에 비례하는 스텝 벌점.
    #   idle = 마지막으로 `idle_reset_m` 안에 들어간 뒤 흐른 시간(초)
    #   벌점 = -w * clip((idle - grace) / ramp, 0, 1)
    # grace 안에는 0 이라 정상적인 재접근(머지 후 선회 반전 ~15 초)은 벌하지
    # 않는다. 그 뒤로 ramp 초에 걸쳐 최대까지 오른다.
    #
    # **포텐셜이 아니다** — 일부러 그렇게 만들었다. 포텐셜은 텔레스코프해서
    # 최적 정책을 안 바꾸는데, 여기서는 최적 정책을 바꾸는 것이 목적이다.
    # 대신 착취 방향이 하나뿐이다: 교전하면 0 이 되므로 피하는 길이 곧 목표다.
    #
    # ⚠ 무모한 돌격을 유발할 수 있다. 켤 때는 피딜과 추락률을 같이 볼 것.
    # ⚠ `idle_reset_m` 을 사거리(914 m)로 잡으면 적이 도주할 때 우리가 벌받는다.
    #    1,500 m 로 여유를 둬서 "쫓고는 있다"를 인정한다.
    "w_idle": 0.0,
    "idle_reset_m": 1500.0,
    "idle_grace_s": 15.0,
    "idle_ramp_s": 30.0,

    # ── 2c-2. 원거리 벌점의 **시간 램프** (2026-08-16) ───────────────────
    # 사용자 요구: "시간에 따라 붙게 해야 한다."
    # `w_idle`(마지막 교전 이후 시간)은 관측에 없어서 MDP 를 깼다. 반면
    # **에피소드 경과 시간은 관측 16 차원에 있다**(`time_norm`). 그래서
    # 경과 시간으로 스케일하는 것은 완전히 유효하다 — 정책이 그 값을 본다.
    #
    #   far 벌점 = -w_far * far_shape(거리) * clip((t - start)/(full - start), 0, 1)
    #
    # 초반에는 0 이라 접근·선회 반전에 필요한 시간을 벌하지 않고, full 이후로는
    # 온전히 문다. 대회 규칙과도 맞는다 — 데미지 계수가 100 초 뒤 0.3, 150 초 뒤
    # 0.1 로 떨어지므로 **전반에 붙어야** 하고, 늦게까지 멀리 있으면 이길 길이 없다.
    #
    # 기본값 full=0 이면 램프를 끄고 곱수 1 (기존 스테이지 동작 불변).
    "far_time_start_s": 0.0,
    "far_time_full_s": 0.0,

    # ── 5. 종료 ─────────────────────────────────────────────────────────
    "win_reward": 300.0,
    "win_time_bonus": 200.0,    # 빨리 죽일수록 큼
    "loss_reward": -150.0,
    "draw_reward": -10.0,
    "draw_health_scale": 100.0, # 대회는 200초 후 데미지 우위도 승리
    # 추락은 **가장 나쁜 결과**여야 한다. 격추당하는 경로보다 낮게 둔다.
    "crash_reward": -250.0,
    "target_crash_reward": 0.0, # 적 추락은 격추가 아니다

    "max_engage_time": 200.0,
    "step_penalty": 0.0,
}


# 고도 포텐셜의 직전 값. env 는 num_envs_per_env_runner = 1 이 전제라
# 모듈 전역으로 충분하다(프로젝트 규약).
_PREV_ALT_PHI: dict = {}
# 접근 포텐셜(3i)의 직전 값 — 같은 규약.
_PREV_CLOSE_PHI: dict = {}
# 고공 벌점 포텐셜(4c)의 직전 값 — 같은 규약.
_PREV_HIGH_PHI: dict = {}
# 선회 최적고도 선호(4d)의 직전 값 — 같은 규약.
_PREV_TURNALT_PHI: dict = {}
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
    같은 이유로 `teachers.py` / `obs_features38.py` 에도 각자 두고 있다.
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

    # 2. 사거리 — 밴드 안은 평평, 밖은 감소.
    # 하한(152 m) 아래는 가파르게 끊는다. 완만한 감쇠(1/30, lo-60)로는 파고드는
    # 것을 못 막았다 — 2026-08-03 실측, ATA 0도에서 aim+range 합이
    #   250m 0.1190(최대) / 152m 0.1144 / 60m 0.0895 / 40m 0.0853
    # 로 최대 대비 28%밖에 안 떨어져서, 데미지가 근거리에서 커지는 것과 합쳐지면
    # 계속 파고드는 것이 이득이었다. 실제로 최소거리가 stage 1 의 609 m 에서
    # 61 m 까지 내려갔고(WEZ 하한의 40%), 그 거리에서는 각속도가 추적 한계를 넘어
    # (152~250 m 구간 28.8 deg/s) 조준을 유지할 수 없어 WEZ 체류가 68 -> 1.9 로
    # 무너졌다. 중심을 하한 위(lo+20)로 올리고 기울기를 6배 세운다.
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

    # 2h. 예측 최근접거리 사전 조향 — 3k 주석 참조. 사거리 **밖**에서만 켠다
    #     (밴드 안은 2g 가 담당 — 두 항이 같은 구간에서 겹치면 어느 쪽이
    #     효과를 냈는지 못 가른다. gunsnap_blue 를 뺀 것과 같은 이유).
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

    # 3. 데미지 — 격추 그 자체. 총량이 w x HP 로 유계
    comp["damage"] = (C("w_damage") * float(target_damage)
                      - C("w_damage_taken") * float(ownship_damage))

    # 3c. 정면샷 우대 — 적 기수가 나를 향할수록 데미지 배수 (최대 1+w 배)
    hm = C("w_headon_mult")
    if hm > 0.0 and comp["damage"] > 0.0:
        tgt_ata = _ata_deg(target_state, ownship_state)
        front = 1.0 - min(tgt_ata, 90.0) / 90.0
        comp["damage"] *= 1.0 + hm * front

    # 3b. 근접 게이트 — 데미지 **보상**을 하한 근처에서 깎는다.
    #     규칙(실제 데미지)은 그대로다. 보상만 거리로 게이팅해서 "더 파고들라"는
    #     유인을 없앤다. 새 항이 아니라 기존 항의 축소라 누적이 폭주하지 않는다.
    gate_m = C("damage_near_gate_m")
    if gate_m > 0.0 and comp["damage"] > 0.0 and d_m < gate_m:
        floor = C("damage_near_floor")
        t = max(0.0, min(1.0, (d_m - lo) / max(gate_m - lo, 1.0)))
        comp["damage"] *= floor + (1.0 - floor) * t


    # 4. 지면
    comp["deck"] = -C("w_deck") * (1.0 - _S(alt_ft, 1.0 / 20.0, C("deck_ft")))

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

    # 4b. 고도 포텐셜 (potential-based shaping, gamma_shape = 1)
    #     r = Phi(s') - Phi(s),  Phi = w * clip(alt / ceiling, 0, 1)
    #     텔레스코프하므로 에피소드 총합 = w * (끝-시작)/ceiling. 정책 불변.
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
        if "ownship altitude" in ec:
            terminal = C("crash_reward")
        elif "target altitude" in ec:
            terminal = C("target_crash_reward")
        elif tgt_hp <= 0.0 < own_hp:
            terminal = C("win_reward") + C("win_time_bonus") * max(
                0.0, 1.0 - sim_t / max_t)
        elif own_hp <= 0.0 < tgt_hp:
            terminal = C("loss_reward")
        else:
            terminal = C("draw_reward") + C("draw_health_scale") * (own_hp - tgt_hp)
    comp["terminal"] = terminal

    return float(sum(comp.values())), comp


__all__ = ["MY_REWARD_CONFIG", "compute_reward"]
