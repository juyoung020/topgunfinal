# -*- coding: utf-8 -*-
"""[학생 파일] 커리큘럼 12단계 — 이전 워크스페이스의 검증된 0~11 을 이식.

왜 새로 짜지 않고 이식하는가
----------------------------
이전 워크스페이스의 이 12단계는 **실제로 끝까지 통과한 이력**이 있다
(최종 게이트 150판 0.960, CI 0.915~0.982). 내가 새로 만든 8단계는 검증된 적이 없다.
검증된 구조를 버릴 이유가 없다.

이식하면서 바꾼 것은 두 가지뿐이다.
  1. `reward_overrides` 키를 **새 5항 보상**의 이름으로 다시 매핑
     (옛 보상은 포텐셜 기반이라 `w_phi_dist`/`w_phi_ata`/`w_phi_alt` 같은 키를 썼다)
  2. 스테이지 12(`competition_rehearsal`)는 제외 — `wez_phases` 가 필요한데
     원본 SDK 에 그 기능이 없다(플랫폼 `[MOD-WEZPHASE]` 추가분이었다)

가져오지 못한 것: 옛 13~49 단계. `target_pool`(36개 스테이지), Elo 리그,
self-play, `ownship_hp_deficit` 등 전부 플랫폼 `[MOD-*]` 추가분에 의존한다.

원뿔은 처음부터 대회 규격(±1도)이다 — 실측으로 결정
-----------------------------------------------------
이전 워크스페이스는 12도에서 8, 6, 5, 4, 3, 2도로 좁혀갔다. 그 설계를 이식할지
재보고 정했다. 손으로 짠 비례추적 제어기로 스테이지별 12 에피소드 실측:

    스테이지            원래 원뿔       2도(대회 규격)
    gun_saddle         0.50 (12도)    0.25
    gun_saddle_turn    0.92 ( 8도)    0.67
    approach           0.92 ( 6도)    1.00   <- 오히려 높음
    head_on_merge      0.75 ( 5도)    0.33

**2도에서도 전 스테이지가 격추를 낸다**(0.25~1.00). 배울 신호가 없어서 정체할
상황이 아니므로, 좁혀가는 단계를 두지 않고 **처음부터 대회 조건**으로 훈련한다.
넓은 원뿔로 배우면 그 폭에 맞춘 조준을 익히고 마지막에 다시 좁혀야 한다.

무행동 정책은 어느 원뿔에서도 격추 0.00 이다 — 공짜 격추가 없다는 확인.
(스폰 랜덤화를 끄면 0 도 나오는데, 그건 실제 학습 조건이 아니다.)

대회 WEZ 페이즈(0~100s ±1도 계수 1.0 / 100~150s ±2도 0.3 / 150~200s ±3도 0.1)는
넣지 않는다. 중첩 원뿔이라 **Phase 1 안에 넣으면 언제든 계수 1.0** 을 받고,
부피x계수가 1.00 : 1.91 : 2.14 로 비슷해 최적 전략이 시간과 무관하게 ±1도다.
넓은 페이즈에 맞춰 배우면 계수 0.1 짜리 사격에 안주할 위험만 있다.

교사는 `student/teachers.py` 5종이고 `train_curriculum.py` 의 [MOD-TEACHERHOOK]
가 `TeacherActionProvider` 로 붙인다. 플랫폼 파일은 수정하지 않는다.

전 단계 `step_ratio = 6` (10 Hz 결정). 빠지면 60 Hz 로 학습돼 평가와 어긋난다.

실행:
  python train_curriculum.py --stages-module student.my_curriculum \
      --observation-module student.my_observation --reward-module student.my_reward
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

from dogfight.ai.curriculum import CurriculumStage

# [MOD-HZ] 2026-08-19: 결정 주기를 환경변수로 뺐다. **기본값은 종전과 같은 6.**
#
# 왜: 밴드 첫 진입 875 m -> 첫 명중 693 m 로 182 m 를 흘린다. 그 구간의 최소
# ATA 중앙이 **1.16도** 인데 WEZ 는 <=1.0도 — **0.16도가 모자라** 놓친다.
# 400~914 m 의 LOS 각속도가 6.8도/s 라 10 Hz 는 결정 사이에 **0.68도**가 그냥
# 흐른다(원뿔이 +-1도인데). 같은 가중치로 붙인 맞대결에서 20 Hz 가
# **마진 +0.099, WEZ 체류 +27%** 로 이겼다(`student/tools/probe_hz.py`).
#
# 단, 제어 주기가 만드는 오차 하한은 10 Hz 0.34도 / 20 Hz 0.17도인데 관측
# 최소 ATA 가 1.16도라 **다른 오차원이 더 크다.** Hz 만으로 1도 아래로 간다는
# 보장은 없다. 기대치는 맞대결 실측(+0.099)까지로 잡는다.
#
# [되돌림 2026-08-20] 20 Hz 시도를 접고 **10 Hz 고정**으로 복귀했다.
#
# 접은 이유(실측):
#   * 위 "+27%" 는 **스텝 수**로 센 값이다. 시간으로 재면 20 Hz 의 WEZ 체류는
#     1.70초, 10 Hz 는 1.93초로 **오히려 12% 짧았다.** 전제가 뒤집혔다.
#   * 20 Hz 실행은 3,000 iteration 동안 최고가 -0.061 에 그쳤고 두 번 무너졌다.
#     같은 기간 10 Hz 의 snap_12241 은 고정 상대 3계열에 80판 무패였다.
#   * 게다가 20 Hz 배트에 넣은 `--gae-lambda 0.97468` 은 "10 Hz 의 0.95 를 환산"
#     한 값이었는데 **10 Hz 는 0.95 가 아니라 기본값 1.0** 이었다. 즉 그 실험은
#     Hz 외에 GAE 설정까지 달랐다. "20 Hz 가 나쁘다"는 결론은 낼 수 없다.
#
# 환경변수 경로를 없애 20 Hz 로 새는 길을 막는다. 값은 종전 10 Hz 와 동일하다.
# 다시 시도하려면 launch_hz20_DEPRECATED_*.bat 주석의 6가지를 함께 바꿔야 한다.
STEP_RATIO = 6                        # 60 Hz 물리 / 6 substep = 10 Hz 결정

# 60 Hz 물리 기준 결정 주기(초)와 10 Hz 대비 배율.
DECISION_DT_S = STEP_RATIO / 60.0
_HZ_SCALE = 1.0                       # 10 Hz 고정이므로 per-step 환산 없음


def _perstep(value: float) -> float:
    """**생짜 per-step 보상**을 결정 주기에 맞춰 환산한다.

    20 Hz 면 같은 벽시계 시간에 스텝이 2 배라 상수가 그대로면 누적이 2 배가 되고,
    승패 종단보상(+-1500) 대비 shaping 이 두 배 무거워진다. 이 프로젝트가 이미
    겪은 "보상 신호 침몰"과 같은 부류라 반드시 환산해야 한다.

    포텐셜 항(`close`/`alt`/`high`/`turnalt`)은 차분이라 텔레스코프되므로 **제외**.
    데미지 항도 실제 HP 변화에 비례해 총량이 보존되므로 **제외**.
    """
    return value * _HZ_SCALE

# 적기 속도 지령.
# 2026-08-03 실측: 이 값이 400 이면 교사가 374 m/s 로 난다. 우리 기체는
# 전속이면 471 m/s 지만 리드를 물고 선회하면 339 로 떨어져서, 적기가
# 10 m/s 빠른 상태가 된다. stage 1 은 "이미 사격 자세(적 6시 630 m)" 인데
# 거리가 630 -> 1150 m 로 계속 벌어졌고, 조준은 멀쩡한데(ATA 중앙값 0.92도,
# 스텝의 57%가 1도 이내) 사거리와 조준이 동시에 성립한 스텝은 6 개였다
# (격추엔 16 개 필요). stage 4 는 적기가 7,434 m 까지 이탈했다.
#
# 대회 규칙상 도주는 실격이므로, 도주하는 적기는 풀어야 할 과제가 아니라
# 잘못 배치된 상대다. 교사 자동조종의 속도 하한은 327.4 m/s 이고(지령을
# 300 밑으로 내려도 더 안 느려진다) 그 값이면 선회 중인 우리(339)가 빠르다.
FOE_SPEED = 300.0


def _rand(radius: float, heading: float, pitch: float = 8.0) -> dict:
    return {"enabled": True, "radius": radius,
            "r_roll": 10.0, "r_pitch": pitch, "r_heading": heading}


def _spawn(cfg: dict, own, tgt, wez_deg) -> dict:
    if own is not None:
        cfg["ownship"] = own
    if tgt is not None:
        cfg["target"] = tgt
    if wez_deg is not None:
        cfg["wez"] = {"angle_deg": wez_deg,
                      "min_range_m": 152.4, "max_range_m": 914.4}
    return cfg


def _env(teacher: str, params: dict, seconds: float,
         own=None, tgt=None, wez_deg: float | None = None) -> dict:
    return _spawn({
        "step_ratio": STEP_RATIO,
        "target_teacher": {"name": teacher, "params": params},
        "max_engage_time": seconds,
    }, own, tgt, wez_deg)


# ── 학습된 38차원 정책을 적기로 ────────────────────────────────────────────
# 이전 워크스페이스의 번들은 전부 관측 38차원이고 우리는 16차원이라 관측 벡터를
# 공유할 수 없다. `student/rl_opponent.py` 가 상대에게 자기 38차원 빌더를 붙여
# 준다 — 플랫폼의 RLActionProvider 훅이 원래 그러라고 만들어진 것이다.
# 2026-08-02 실측(stage 4): 챔피언이 30초에 기수 198도, 최대 74.5 도/초로
# 기동하고 7000 -> 9170 m 로 상승한다. 직진 표적이 아니라 진짜 상대다.
_OLD_ARTIFACTS = str(ROOT / "artifacts")  # [SLIM 2026-08-28] 구 워크스페이스 절대경로 제거 (league 번들을 artifacts/league 로 복사함)
RL_OPPONENTS = {
    # 구 워크스페이스 최종 챔피언. benchmark mean-jwin 0.948
    "champion": _OLD_ARTIFACTS + r"\league\mergerebal_s38_jwin0942",
    # 권위 Elo 1667.5, 리그 사다리 1위
    "elo1667": _OLD_ARTIFACTS + r"\league\league250_elo1667",
}


def _env_rl(bundle: str, seconds: float,
            own=None, tgt=None, wez_deg: float | None = None) -> dict:
    """적기를 파이썬 교사 대신 학습된 38차원 정책으로 둔다."""
    return _spawn({
        "step_ratio": STEP_RATIO,
        "target_rl_bundle": RL_OPPONENTS.get(bundle, bundle),
        "max_engage_time": seconds,
    }, own, tgt, wez_deg)


# 게이트에 격추 조건을 되살린 이유 (2026-08-03 실측)
# 초반 스테이지의 목적은 "조준을 배우는 것"이라 WEZ 체류를 주 조건으로 둔다. 그런데
# 조준만 보면 무너지는 정책이 통과한다: 0803_anchor2 의 stage 2 는 승률이 0.944 ->
# 0.278 로 붕괴하는 중이었는데 WEZ 가 13.8 이라 게이트(6.0)를 넘어 stage 3 으로
# 진급했고, 거기서 승률 0 · 추락 1.00 으로 500 iteration 을 태웠다. WEZ 는 10
# iteration 이동평균이라 무너지기 전의 좋은 값이 아직 창 안에 남아 있었다.
# 조준(주) AND 격추(보조)를 함께 요구하면 그 구멍이 막힌다.


_MODELS = Path(__file__).resolve().parents[1] / "artifacts" / "models" / "AeroFlyer"


def get_stages() -> list[CurriculumStage]:
    S: list[CurriculumStage] = []

    # ── 0: 비행. 전투 보상 전부 끄고 뜨는 것만 가르친다 ───────────────────
    # 중립 조종에서 활강하는 기체라 이 단계가 필요하다(실측).
    S.append(CurriculumStage(
        index=0, name="flight",
        description="Hold altitude and attitude. No combat reward at all.",
        target_mode="fixed",
        episode_step_limit=800, max_iterations=400, checkpoint_interval=20,
        reward_overrides={
            "w_aim": 0.0, "w_range": 0.0, "w_damage": 0.0,   # 전투 끔
            "w_deck": 20.0,                                   # 지면 회피
            # 옛 워크스페이스 stage 0 의 w_phi_alt 200 복원. w_deck 은 400 m
            # 아래에서만 켜져서 7,000 -> 500 m 구간에 신호가 전혀 없었다.
            "w_alt": 200.0, "alt_ceiling_m": 9000.0,
            # 천장은 스폰 상한 위에 둬야 한다. 6300(구 워크스페이스 값)이면
            # 스폰 7000 +-1500 = 5500~8500 m 가 대부분 천장 위라 포텐셜이
            # 포화해 기울기가 0 이었다(실측: 8357 m 에서 고도가 스텝당 3 m
            # 씩 떨어지는데 alt 항이 정확히 0.0).
            "win_reward": 0.0, "loss_reward": 0.0, "draw_reward": 30.0,
            "draw_health_scale": 0.0, "crash_reward": -250.0,
            "step_penalty": -0.001, "max_engage_time": 60.0,
        },
        randomization=_rand(1500.0, 180.0),
        advance_conditions={"crash_rate_max": 0.20},
        advance_window=10,
        # speed_mps 필수 (2026-08-03 실측): 파라미터 없이 두면 지령 400 이
        # 유지 불가능한 속도라 교사가 강하 비행으로 57초에 지면 추락 —
        # 24판 중 18판이 "target altitude below min"(전부 568스텝)으로 끝났다.
        env_overrides=_env("straight", {"speed_mps": FOE_SPEED}, 60.0),
    ))

    # ── 1~3: 등돌린 스폰 (2026-08-03 사용자 지시) ────────────────────────
    # 이전 설계는 유리한 각도(적 6시 새들)에서 시작했다. 이번 커리큘럼은
    # **전 전투 스테이지가 서로 등을 돌린 채**(양쪽 ATA 180도) 시작한다:
    #   내 위치 [0,0]  기수 225도  /  적 위치 [d/√2, d/√2]  기수 45도
    # 먼저 돌아서서 각도를 만드는 것부터가 과제다. 난이도는 스폰이 아니라
    # 분리거리(400 -> 700 -> 1200 m)와 적기 기동(직진 -> 선회)으로 올린다.
    #
    # 보상의 광각 유도항(w_aim_wide, 선형)이 이 스폰의 짝이다. 기존 곡선은
    # ATA 150~180도가 평평해서 "돌아서라"는 신호가 없었다(my_reward.py 1b 참조).
    def _btb(sep_m: float, own_spd: float = 280.0, tgt_spd: float = 250.0):
        off = sep_m / math.sqrt(2.0)
        return ([0.0, 0.0, -7000.0, 0.0, 0.0, 225.0, own_spd],
                [off, off, -7000.0, 0.0, 0.0, 45.0, tgt_spd])

    # ── 1: 등돌리기 400 m, 급선회 적기 — 반전을 배우는 스테이지 ──────────
    # **직진 적기는 안 된다 (2026-08-03 실측)**: 등돌린 스폰에서 직진 = 도주.
    # 반전(~15초, 속도 340 으로 하락)하면 적은 이미 1.5 km 앞에서 327 m/s 로
    # 도주 중이라 추월 여유 ~13 m/s 로는 못 따라잡는다 — 손 제어기 1/8,
    # 타임아웃 전부 WEZ 0. 선회 적기는 제자리를 돌므로 반전 후 원 안쪽을
    # 자르면 된다. 뱅크 40-60도 = 난이도 U자 곡선의 바닥(가장 쉬움, 실측).
    # 120초: 반전 15초 + 접근 + 사격. 게이트 win 0.5 -> 0.3 (반전 습득이
    # 목적이라 조준 체류를 주 조건으로 둔다).
    o1, t1 = _btb(400.0)
    S.append(CurriculumStage(
        index=1, name="btb_turnin",
        description="400 m apart, both facing away; foe circles at 40-60 bank. Learn the turn-in.",
        target_mode="fixed",
        episode_step_limit=1400, max_iterations=400, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "max_engage_time": 120.0},
        randomization=_rand(150.0, 20.0, 3.0),
        advance_conditions={"ep_wez_steps_min": 8.0, "win_rate_min": 0.30, "crash_rate_max": 0.15},
        advance_window=10,
        advance_episodes=120,
        env_overrides=_env("turn", {"bank_range": [40.0, 60.0], "speed_mps": FOE_SPEED}, 120.0,
                           own=o1, tgt=t1, wez_deg=12.0),
    ))

    # ── 2: 등돌리기 700 m, 선회 폭 확대 ──────────────────────────────────
    o2, t2 = _btb(700.0)
    S.append(CurriculumStage(
        index=2, name="btb_turn",
        description="700 m apart facing away; wider bank range - lead pursuit after the turn-in.",
        target_mode="fixed",
        episode_step_limit=1400, max_iterations=500, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "max_engage_time": 120.0},
        randomization=_rand(300.0, 30.0, 5.0),
        advance_conditions={"ep_wez_steps_min": 6.0, "win_rate_min": 0.40, "crash_rate_max": 0.15},
        advance_window=10,
        advance_episodes=120,
        env_overrides=_env("turn", {"bank_range": [30.0, 55.0], "speed_mps": FOE_SPEED}, 120.0,
                           own=o2, tgt=t2, wez_deg=8.0),
    ))

    # ── 3: 등돌리기 1.2 km — 반전 + 장거리 접근 + 얕은 선회(어려운 쪽) ───
    o3, t3 = _btb(1200.0)
    S.append(CurriculumStage(
        index=3, name="btb_far",
        description="1.2 km apart facing away; turn in, close the range, shallower banks.",
        target_mode="fixed",
        episode_step_limit=1700, max_iterations=500, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "max_engage_time": 150.0},
        randomization=_rand(400.0, 40.0, 5.0),
        advance_conditions={"ep_wez_steps_min": 6.0, "win_rate_min": 0.40, "crash_rate_max": 0.15},
        advance_window=10,
        advance_episodes=120,
        env_overrides=_env("turn", {"bank_range": [20.0, 45.0], "speed_mps": FOE_SPEED}, 150.0,
                           own=o3, tgt=t3, wez_deg=6.0),
    ))

    # ── 4: 서로 등진 상태에서 시작 ──────────────────────────────────────
    # 정면(760 m 앞, 마주봄)은 **양쪽 ATA 가 0.0** 이라 시작하자마자 서로 쏜다
    # (실측). 조준을 배우는 게 아니라 스폰이 이미 사격 자세인 것이다.
    #
    # 여기서는 앞뒤/옆으로 벌리고 **양쪽이 완전히 등을 돌린 채** 시작한다.
    #   적기 위치 앞 400 / 옆 400  -> 거리 566 m, 나에게서 적 방위 45도
    #   내 기수 225도 / 적 기수 45도 -> **양쪽 ATA 180도**
    # 둘 다 반대편을 보고 날아가므로, 먼저 돌아서 각도를 만드는 쪽이 이긴다.
    # 이게 이 커리큘럼에서 가장 어려운 시작 조건이다(다른 단계는 전부 유리한
    # 각도에서 시작한다).
    S.append(CurriculumStage(
        index=4, name="back_to_back",
        description="566 m offset, both facing 180 deg away: turn first to win.",
        target_mode="fixed",
        episode_step_limit=1700, max_iterations=600, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "max_engage_time": 150.0},
        randomization=_rand(150.0, 25.0, 5.0),
        advance_conditions={"ep_wez_steps_min": 6.0, "win_rate_min": 0.40, "crash_rate_max": 0.15},
        advance_window=10,
        advance_episodes=120,
        env_overrides=_env("turn", {"bank_range": [30.0, 55.0], "speed_mps": FOE_SPEED}, 150.0,
                           own=[0.0, 0.0, -7000.0, 0.0, 0.0, 225.0, 280.0],
                           tgt=[400.0, 400.0, -7000.0, 0.0, 0.0, 45.0, 200.0], wez_deg=5.0),
    ))

    # ── 5: 급선회 표적 사격 ─────────────────────────────────────────────
    # 난이도는 뱅크각에 U자형이다: 얕으면(15-30도) 도망가서 어렵고, 급하면
    # (60-75도) 각속도가 추적 한계를 넘어 어렵다. 45-65도가 가장 쉽다(실측).
    S.append(CurriculumStage(
        index=5, name="gunnery_easy",
        description="Track and shoot a hard-turning target that stays local.",
        target_mode="fixed",
        episode_step_limit=1700, max_iterations=500, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "max_engage_time": 150.0},
        randomization=_rand(1500.0, 150.0),
        advance_conditions={"win_rate_min": 0.35, "crash_rate_max": 0.20},
        advance_window=10,
        advance_episodes=120,
        env_overrides=_env("turn", {"bank_range": [45.0, 65.0], "speed_mps": FOE_SPEED}, 150.0, wez_deg=6.0),
    ))

    # ── 6: 난이도 곡선 양쪽 끝 (얕은 이탈 + 격한 브레이크) ───────────────
    S.append(CurriculumStage(
        index=6, name="gunnery_hard",
        description="Both arms of the difficulty curve: shallow escapes and violent breaks.",
        target_mode="fixed",
        episode_step_limit=1700, max_iterations=500, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "max_engage_time": 150.0},
        randomization=_rand(2000.0, 180.0),
        advance_conditions={"win_rate_min": 0.35, "crash_rate_max": 0.20},
        advance_window=10,
        advance_episodes=120,
        env_overrides=_env("turn", {"bank_range": [25.0, 75.0], "speed_mps": FOE_SPEED}, 150.0, wez_deg=4.0),
    ))

    # ── 7: 쫓기는 상황 (느린 순수추적) ──────────────────────────────────
    # 방어를 가르치는 게 아니라, 뒤를 잡힌 상태에서 **역전해 공격으로 전환**하는 것.
    S.append(CurriculumStage(
        index=7, name="chased_easy",
        description="A slow pure-pursuit chaser: survive, then turn the tables.",
        target_mode="fixed",
        episode_step_limit=2000, max_iterations=600, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "max_engage_time": 180.0,
                          # 원거리 스폰(평균 3.5 km)에서 교전 시작 기울기 확보 —
                          # 기본 게이트 2 km 밖은 조준 보상이 0 이라 stage 7 이
                          # 전판 타임아웃(wez 0, eval 0.0)으로 굶었다 (실측).
                          "aim_range_gate_m": 4500.0},
        # [2026-08-04 밤] 반경 2000->1200, 원뿔 3->5도. 92 iter 동안 WEZ 접촉
        # 0 이었다 — 리플레이 실측: 반전·접근은 되는데(7 km -> 1.1 km, ATA
        # 115->12도) 머지에서 스쳐 지나간다(ATA 38->122도). 3도 원뿔은 스치는
        # 통과에 아무 데미지도 주지 않아 "전환"에 기울기가 없었다. 가까운
        # 스폰 = 판당 머지 횟수 증가, 5도 = 스침도 약간은 점수가 나서 전환
        # 학습의 사다리가 생긴다. 원뿔은 stage 8(2도)에서 다시 조인다.
        randomization=_rand(1200.0, 180.0),
        advance_conditions={"win_rate_min": 0.45, "crash_rate_max": 0.20},
        advance_window=10,
        advance_episodes=120,
        # [2026-08-04 밤 3차] pursuit -> defensive. 추격 교사는 실측상
        # 반응 빠르면 무적 레이트파이터(시연자 0/8), 늦추면 도망자(따라잡기
        # 20 m/s) — 어느 쪽도 학습 사다리가 아니다. defensive 는 평시 추격
        # (쫓기는 경험) + 위협 시 브레이크 선회(잡을 수 있는 기하)로 취지를
        # 그대로 살리고, 시연자 5/8 (WEZ 36.5) 로 풀림을 실측했다.
        env_overrides=_env("defensive", {"break_bank_deg": 60.0, "speed_mps": FOE_SPEED,
                                         "reaction_delay_s": 0.5}, 180.0, wez_deg=5.0),
    ))

    # ── 8: 빠른 리드추적 추격자 — 여기서 원뿔이 대회 규격(2도)이 된다 ────
    S.append(CurriculumStage(
        index=8, name="chased_hard",
        description="Fast lead-pursuit chaser that cuts the corner.",
        target_mode="fixed",
        episode_step_limit=2000, max_iterations=600, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "loss_reward": -180.0, "max_engage_time": 180.0,
                          "aim_range_gate_m": 4500.0},
        randomization=_rand(2000.0, 180.0),
        # [2026-08-04 심야 2] 0.55 -> 0.45. 240 iter 실측: eval 최고 0.545,
        # 최근 평균 0.35 — 0.55 는 이 구성(defensive 65/0.3, 3.5도)에서 닿지
        # 않는 문턱이다. stage 9 가 같은 상대의 조임판이라 여기서 예산을
        # 태울 이유가 없다.
        advance_conditions={"win_rate_min": 0.45, "crash_rate_max": 0.15},
        advance_window=10,
        advance_episodes=120,
        # [2026-08-04 심야] 원뿔 5 -> 2도 점프가 과했다: 64 iter 동안 eval
        # 0.0~0.035, WEZ 1.4~9.5 진동만 하고 격추 전환 없음. 검증된 설계
        # (5->4->3->2 점진)대로 8=3.5도 / 9=2.5도 / 10+=2도(대회)로 완만하게.
        env_overrides=_env("defensive", {"break_bank_deg": 65.0, "speed_mps": FOE_SPEED,
                                         "reaction_delay_s": 0.3}, 180.0, wez_deg=3.5),
    ))

    # ── 9: 위협받으면 하드 브레이크하는 상대 — 진짜 BFM 시작 ────────────
    S.append(CurriculumStage(
        index=9, name="defensive_foe",
        description="Opponent breaks hard when threatened - real BFM starts here.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=800, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "max_engage_time": 200.0,
                          "aim_range_gate_m": 4500.0},
        randomization=_rand(2500.0, 180.0),
        advance_conditions={"win_rate_min": 0.60, "crash_rate_max": 0.15},
        advance_window=10,
        advance_episodes=120,
        env_overrides=_env("defensive", {"break_bank_deg": 70.0, "speed_mps": FOE_SPEED,
                                         "reaction_delay_s": 0.15}, 200.0, wez_deg=2.5),
    ))

    # ── 10: ace 상태기계, 반응 둔화 ─────────────────────────────────────
    S.append(CurriculumStage(
        index=10, name="ace_handicapped",
        description="Full BFM state machine with slowed reactions.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=1000, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "max_engage_time": 200.0,
                          "aim_range_gate_m": 4500.0},
        randomization=_rand(2500.0, 180.0),
        advance_conditions={"win_rate_min": 0.75, "crash_rate_max": 0.12},
        advance_window=10,
        advance_episodes=120,
        env_overrides=_env("ace", {"reaction_delay_s": 0.5, "break_bank_deg": 60.0,
                                   "lead_time_s": 0.6}, 200.0),
    ))

    # ── 11: 최강 ace, 대회 길이. 게이트 90% 격추 ────────────────────────
    S.append(CurriculumStage(
        index=11, name="ace_final",
        description="Full-strength ace at competition length. Gate: 90% kills.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=2000, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0, "max_engage_time": 200.0,
                          "aim_range_gate_m": 4500.0},
        randomization=_rand(2500.0, 180.0),
        advance_conditions={"win_rate_min": 0.90, "crash_rate_max": 0.05},
        advance_window=10,
        advance_episodes=120,
        env_overrides=_env("ace", {}, 200.0),
    ))

    # ── 12: 학습된 상대. 스크립트 교사가 아니라 실제 RL 정책과 싸운다 ────
    # 교사는 자동조종 지령(뱅크/방위/경로각)으로 움직여서 사람이 짠 규칙만큼만
    # 다양하다. 챔피언은 이 게임을 200 iteration 넘게 학습한 정책이라 회피
    # 패턴이 규칙으로 환원되지 않는다 — ace 를 이긴 뒤에도 여기서 진다면
    # 그 차이가 곧 남은 실력 격차다.
    S.append(CurriculumStage(
        index=12, name="rl_champion",
        description="Fight the previous workspace's champion (38-dim RL policy).",
        target_mode="fixed",            # provider 가 우선하므로 값은 무의미
        episode_step_limit=2200, max_iterations=2000, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          # 천장 강화 (2026-08-05 밤): w 4 로는 상승 나선 유지
                          # (ceil -1,450/판 고착). 10 이면 따라 올라가기가 명백한
                          # 손해 — 이탈 후 저고도 재교전을 배우게 한다. 12 한정.
                          "w_ceil": 10.0},
        randomization=_rand(2500.0, 180.0),
        # 도주-자멸 승 차단 (2026-08-05 리플레이 실측): 우리가 10 km 로 도주하면
        # 챔피언이 OOD 에서 자체 추락해 "승"이 쌓인다. 보상은 이를 안 사지만
        # (target_crash_reward 0) 승률 게이트는 통과시킨다 — 대회 규칙상 도주는
        # 실격이므로 WEZ 체류를 함께 요구해 실제 교전 없는 진급을 막는다.
        advance_conditions={"win_rate_min": 0.60, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        advance_episodes=120,
        # [2026-08-05 2차] 챔피언(잡음 포함)도 240 iter 동안 WEZ 부스러기(<=1)
        # — 상대가 너무 강해 접촉 신호 자체가 안 생긴다. 자가대전 사다리로 전환:
        # 상대 = 우리 자신의 stage 11 best (ace 0.90 통과 정책, 16차원).
        # rl_opponent 가 16차원 번들을 지원하도록 확장돼 있다(자기 빌더 사용).
        # 실력이 대칭이라 교전이 성립하고, 이것이 self-play 의 첫 단이다.
        # 챔피언/elo1667(38차원)은 stage 13 에 남는다.
        # [2026-08-05 4차: 풀 로테이션] 단일 동결 상대는 어떤 상대든 퇴화
        # 균형이 생겼다(챔피언=무접촉, 미러=교착, v2=나선상승/고저분리).
        # [MOD-OPPONENT] 풀 기계장치가 이미 이식돼 있고 policy 로더가 우리
        # rl_opponent(16/38차원 겸용)를 쓰므로, 매판 다른 상대를 뽑는 풀로
        # 전환한다 — 잡을 수 있는 클론(신호원) + 미러(도전) + 교사(기술
        # 망각 방지) + 구 챔피언(최상급, 저빈도). 다섯 상대를 동시에 속일
        # 수 있는 퇴화 전략은 없다.
        env_overrides={
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                {"weight": 3.0, "mode": "policy",
                 "bundle": str(ROOT / "artifacts" / "models" / "AeroFlyer" / "bc_btb_v2")},
                {"weight": 2.0, "mode": "policy",
                 "bundle": str(ROOT / "artifacts" / "models" / "AeroFlyer" / "bc_btb_v3")},
                {"weight": 2.0, "mode": "policy",
                 "bundle": str(ROOT / "artifacts" / "curriculum" / "AeroFlyer"
                               / "0804_btb9c" / "stage_11_ace_final" / "best_bundle")},
                {"weight": 2.0, "mode": "teacher",
                 "teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}}},
                {"weight": 1.0, "mode": "teacher",
                 "teacher": {"name": "defensive",
                             "params": {"break_bank_deg": 70.0, "speed_mps": FOE_SPEED,
                                        "reaction_delay_s": 0.15}}},
                {"weight": 1.0, "mode": "policy",
                 "bundle": RL_OPPONENTS["champion"]},
            ],
        },
    ))

    # ── 13: 리그 1위 정책. 마지막 관문 ─────────────────────────────────
    S.append(CurriculumStage(
        index=13, name="rl_elo1667",
        description="Fight the league's top-rated policy (authority Elo 1667.5).",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=2000, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0},
        randomization=_rand(2500.0, 180.0),
        # 도주-자멸 승 차단 (2026-08-05 리플레이 실측): 우리가 10 km 로 도주하면
        # 챔피언이 OOD 에서 자체 추락해 "승"이 쌓인다. 보상은 이를 안 사지만
        # (target_crash_reward 0) 승률 게이트는 통과시킨다 — 대회 규칙상 도주는
        # 실격이므로 WEZ 체류를 함께 요구해 실제 교전 없는 진급을 막는다.
        advance_conditions={"win_rate_min": 0.60, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        advance_episodes=120,
        # [2026-08-05] stage 12 의 교훈 그대로: 단일 동결 상대는 퇴화 균형.
        # 상급 배합 풀 — 엘리트(elo1667/챔피언) 중심 + 방금 풀에서 자란
        # stage 12 best 스냅샷(사다리) + 신호원(v3) + 교사(망각 방지).
        env_overrides={
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                {"weight": 2.0, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"]},
                {"weight": 2.0, "mode": "policy", "bundle": RL_OPPONENTS["champion"]},
                {"weight": 2.0, "mode": "policy",
                 "bundle": str(ROOT / "artifacts" / "curriculum" / "AeroFlyer"
                               / "0805_btb9e" / "stage_12_rl_champion" / "best_bundle")},
                {"weight": 1.5, "mode": "policy",
                 "bundle": str(ROOT / "artifacts" / "models" / "AeroFlyer" / "bc_btb_v3")},
                {"weight": 1.5, "mode": "teacher",
                 "teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}}},
            ],
        },
    ))

    # ── 14: 리그 세대 2 — 목표: 엘리트 RL 을 이긴다 (2026-08-05 사용자 지시) ──
    # gen-1(stage 12~13 풀)의 H2H 실측: elo1667/챔피언과 0승 0패 전무승부,
    # 데미지 교환 근소 열세. 이번 풀은 엘리트 비중 50% — 학습 압력의 절반이
    # 진짜 목표를 향한다. 게이트 win 0.5 는 비엘리트 전승(~0.45)으로도 못
    # 넘는 값이라, 엘리트전 승리가 나기 시작해야만 통과한다.
    S.append(CurriculumStage(
        index=14, name="league_gen2",
        description="League gen-2: beat the old-workspace RL elites head-to-head.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=3000, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0},
        randomization=_rand(2500.0, 180.0),
        # 게이트 0.99 = 의도적 도달불가 (2026-08-05 실측 수정): 결정론 게이트
        # 평가는 풀을 비우고 **교사(ace)** 를 상대로 재므로, 0.5 게이트가 ace
        # 0.9 실력으로 iter 9 에 즉시 통과해 버렸다 — 엘리트 실력과 무관한
        # 통과. 이 스테이지의 판정은 게이트가 아니라 **밖에서 도는 H2H
        # 프로브**(엘리트 6판 결정론)가 한다. 구 워크스페이스 stage 49 방식.
        advance_conditions={"win_rate_min": 0.99, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides={
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            # [2026-08-06] 대회 WEZ 페이즈: 100초 후 넓은 원뿔 x0.3, 150초 후
            # 더 넓게 x0.1 (매뉴얼 구조). 풀 HP 엘리트전이 완전 0:0(상호 무결
            # 회피 균형)이라 좁은 원뿔로는 기울기가 없다 — 넓은 페이즈 구간은
            # 명중이 물리적으로 쉬워 첫 타 기울기가 열리고, 대회 조건 그
            # 자체라 오버피팅도 아니다.
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                # 엘리트 핸디캡 드릴 [MOD-DEFICIT-T]: H2H 실측상 엘리트전은
                # 데미지 0:0 무승부라 기울기가 없다. HP 50~70% 를 깎아 격추를
                # 도달 가능하게 만들고(잔여 0.3~0.5 = 체류 1~1.6초) 세대마다
                # 핸디캡을 줄인다. 승리 조건(HP 0)은 그대로 — 꼼수 아님.
                # 두 갈래 드릴 (2026-08-05 밤): 핸디캡판 = "마무리" 연습,
                # 잡음판(explore, 풀 HP) = "온전한 상대에 첫 타" 연습.
                # 풀 HP 프로브 실측상 핸디캡만으론 첫 타 기술이 전이 안 됐다.
                {"weight": 1.5, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "target_hp_deficit": {"prob": 1.0, "min": 0.5, "max": 0.7}},
                {"weight": 1.5, "mode": "policy", "bundle": RL_OPPONENTS["champion"],
                 "target_hp_deficit": {"prob": 1.0, "min": 0.5, "max": 0.7}},
                {"weight": 1.5, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "explore": True},
                {"weight": 1.5, "mode": "policy", "bundle": RL_OPPONENTS["champion"],
                 "explore": True},
                {"weight": 1.0, "mode": "policy",
                 "bundle": str(ROOT / "artifacts" / "curriculum" / "AeroFlyer"
                               / "0805_btb9e" / "stage_13_rl_elo1667" / "best_bundle")},
                {"weight": 1.0, "mode": "policy",
                 "bundle": str(ROOT / "artifacts" / "curriculum" / "AeroFlyer"
                               / "0805_btb9e" / "stage_12_rl_champion" / "best_bundle")},
                {"weight": 1.0, "mode": "policy",
                 "bundle": str(ROOT / "artifacts" / "models" / "AeroFlyer" / "bc_btb_v3")},
                {"weight": 1.0, "mode": "teacher",
                 "teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}}},
            ],
        },
    ))

    # ── 15: elo1667 엑스플로이터 (2026-08-06 새벽) ───────────────────────
    # 풀 세대 4회 프로브: 풀 지배(0.9)가 깨끗한 엘리트 공격으로 전이 안 됨
    # (득점 항상 0, 판정 승패 무작위 진동). 페이즈 도입 후 엘리트가 먼저
    # 교전을 걸어오므로(우리가 소량 실점) 이제 접촉은 있는 게임 — 전 에피소드
    # 를 목표 상대로 채우는 엑스플로이터가 성립한다. 알파스타 리그의 exploiter
    # 역할. 게이트 도달불가(판정은 프로브).
    S.append(CurriculumStage(
        index=15, name="exploit_elo",
        description="Exploiter: every episode vs the clean elo1667 under phase rules.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=3000, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0},
        randomization=_rand(2500.0, 180.0),
        # 게이트 평가는 풀을 제거하고 target_teacher(ace)로 잰다. 0806_exploit 이
        # win 0.99 를 ace 상대로 넘겨 866 iter 에 조기 "졸업"해 버렸다 — 진짜
        # 상대(elo)의 실력과 무관한 종료. 1.01 로 막아 max_iterations 까지 돌리고,
        # 판정은 체크포인트를 밖에서(elo 결정론 프로브) 잰다.
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides={
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                {"weight": 1.0, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"]},
            ],
        },
    ))

    # ── 16: 퍼치 드릴 — 2026-08-06 대회 결승 프레임 분석에서 이식 ─────────
    # 결승 실측: 득점은 "0.7~1.8 km 후방에서 LOS 4~6°를 수 초 유지"에서 나온다
    # (FalconAI 조준유지 누적 14.1 s vs CtrlAltFly 2.5 s). exploit2 는 진짜 elo
    # 상대 200 iter 전판 타임아웃 — 관통 머지(최소 28~68 m, 600 m/s)만 시도.
    # 그래서 시작을 "적 6시 1.3 km 동일 기수"로 놓고(검증된 backward curriculum,
    # gun_saddle 의 RL 상대판) 유지 자세부터 배운다. w_perch 가 이 스폰의 짝.
    # 게이트는 ace 평가라 1.01 로 봉인 — 판정은 elo 결정론 프로브로만.
    own16 = [0.0, 0.0, -7000.0, 0.0, 0.0, 45.0, 280.0]
    off16 = 1300.0 / math.sqrt(2.0)
    tgt16 = [off16, off16, -7000.0, 0.0, 0.0, 45.0, 250.0]
    S.append(CurriculumStage(
        index=16, name="exploit_perch",
        description="Perch drill: spawn at elo1667's six at 1.3 km; learn to HOLD the aim.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=3000, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0,
                          # 0806_perch iter150 실측: 대역 체류 74%·사거리내
                          # 800~1,400스텝인데 ATA 중앙 29°, 3° 이하 0 —
                          # "옆에 붙어 돌기"가 국소최적. 작동점(29°)에 기울기를
                          # 만들기 위해 퍼치 원뿔 10→30°, w_aim 2배.
                          "w_perch": 0.06, "perch_ata_deg": 30.0,
                          "w_aim": 0.16,
                          "w_overspeed": 0.5, "overspeed_gate_m": 2500.0},
        randomization=_rand(300.0, 25.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                {"weight": 1.0, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"]},
            ],
        }, own16, tgt16, None),
    ))

    # ── 17: 격추 전용 — 추락 유인 봉인 (2026-08-07 사용자 지시) ───────────
    # perch3 후반에 "elo 를 지면에 박게 하는" 전략이 창발했다(결정론 8/16).
    # 원인은 보상 구멍: 무승부 -40 인데 적 추락은 0 이라, 유인이 무승부 회피
    # 수단으로 +40 가치를 가졌다. 사용자 지시 "추락유인 의미없어, 제대로
    # 격추해야" → 적 추락 = 무승부와 동일(-40)로 봉인. 이제 -40 를 벗어나는
    # 유일한 경로가 데미지·격추다. init 은 유일한 결정론 격추 정책(iter0860).
    S.append(CurriculumStage(
        index=17, name="exploit_kill",
        description="Gun kills only: target-crash reward sealed to draw level; init from the killer.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=3000, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0,
                          "w_perch": 0.06, "perch_ata_deg": 30.0,
                          "w_aim": 0.16,
                          "w_overspeed": 0.5, "overspeed_gate_m": 2500.0},
        randomization=_rand(300.0, 25.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                {"weight": 1.0, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"]},
            ],
        }, own16, tgt16, None),
    ))

    # ── 18: 대회 IC — 정면 3,048 m 머지 vs elo (2026-08-07 실측 후 신설) ──
    # iter0860 을 대회 초기조건으로 재보니: 본선 IC(정면 3,048 m) vs elo 에서
    # 0승·판정패 3·자멸 1 — elo 가 정면 머지 딜(피딜 0.02~0.30)로 이긴다.
    # 드릴 스폰(후방 1.3 km) 성적은 대회 조건을 대표하지 못했다. 그래서 훈련
    # 스폰을 본선 IC 로 옮기고, 즉시 피딜 벌점(w_damage_taken 50)으로 머지
    # 방어를 먼저 세운다. 추락 유인 봉인(-40)은 유지.
    own18 = [0.0, 0.0, -7000.0, 0.0, 0.0, 45.0, 280.0]
    off18 = 3048.0 / math.sqrt(2.0)
    tgt18 = [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]
    S.append(CurriculumStage(
        index=18, name="comp_ic",
        description="Competition head-on IC (3,048 m merge) vs elo1667; merge defence first.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=3000, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          "w_damage_taken": 50.0,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0,
                          "w_perch": 0.06, "perch_ata_deg": 30.0,
                          "w_aim": 0.16,
                          "w_overspeed": 0.5, "overspeed_gate_m": 2500.0},
        randomization=_rand(500.0, 30.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            # 본선(3,048 m)만 훈련하니 예선(760 m) 머지가 오히려 악화됐다
            # (comp iter300 실측: 본선 1승1패로 개선, 예선 0승3패로 후퇴).
            # 같은 elo 를 두 IC 엔트리로 — [MOD-ENTRY-SPAWN] 이 엔트리별
            # 표적 스폰을 고정한다. 예선 쪽을 6:4 로 약간 무겁게(약점 우선).
            "target_pool": [
                {"weight": 0.6, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [760.0 / math.sqrt(2.0), 760.0 / math.sqrt(2.0),
                                       -7000.0, 0.0, 0.0, 225.0, 250.0]}},
                {"weight": 0.4, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
        }, own18, tgt18, None),
    ))

    # ── 19: 근접 500 m 사격전 (2026-08-07 사용자 지시) ────────────────────
    # "우리 전투기를 적기와 500 m 정도로 근접하게. 보상의 거리 가중치가 너무
    #  낮다. 승리는 추락 유도가 아니라 조준 격추로만."
    # 실측 근거: w_range 0.04 는 aim 0.16·perch 0.06 보다 약해 정책이 사거리
    # 밖을 맴돌았다. 거리 항을 0.30 으로(7.5배) 올려 152~914 m 밴드 체류를
    # 주 수입으로 만들고, 퍼치 창도 300~900 m 로 옮겨 "500 m 부근에서 겨누는
    # 자세"가 최대 보상이 되게 한다. 추락 유도 봉인(-40)은 유지 — 딜·격추만이
    # -40 을 벗어나는 길이다.
    S.append(CurriculumStage(
        index=19, name="close500",
        description="Close gun fight: strong range weight pulls to ~500 m; kills by aiming only.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=3000, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          "w_damage_taken": 25.0,
                          "w_range": 0.30,
                          "w_perch": 0.08, "perch_ata_deg": 30.0,
                          "perch_near_m": 300.0, "perch_far_m": 900.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0,
                          "w_overspeed": 0.5, "overspeed_gate_m": 2500.0},
        randomization=_rand(500.0, 30.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                {"weight": 0.6, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [760.0 / math.sqrt(2.0), 760.0 / math.sqrt(2.0),
                                       -7000.0, 0.0, 0.0, 225.0, 250.0]}},
                {"weight": 0.4, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
        }, own18, tgt18, None),
    ))

    # ── 20: 예선 머지 보강 (2026-08-08 사용자 지시 "RL 이기게끔 이어서") ──
    # iter1940 실측: 본선(3,048 m) 조준딜 4승 0패 vs 예선(760 m) 0승 2패 —
    # 근접 정면 스타트의 첫 머지가 유일한 약점. elo 는 머지 딜 특화 정책이라
    # 2~3초 안에 선타를 낸다. 예선 8 : 본선 2 로 첫 머지를 집중 훈련하되
    # 본선 리허설을 남겨 4승 0패를 지킨다. init = champion_close_iter1940.
    S.append(CurriculumStage(
        index=20, name="quali760",
        description="Qualifier-merge drill: 80% at 760 m head-on vs elo; keep 본선 rehearsal.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=3000, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          "w_damage_taken": 25.0,
                          "w_range": 0.30,
                          "w_perch": 0.08, "perch_ata_deg": 30.0,
                          "perch_near_m": 300.0, "perch_far_m": 900.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0,
                          "w_overspeed": 0.5, "overspeed_gate_m": 2500.0},
        randomization=_rand(300.0, 20.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                {"weight": 0.8, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [760.0 / math.sqrt(2.0), 760.0 / math.sqrt(2.0),
                                       -7000.0, 0.0, 0.0, 225.0, 250.0]}},
                {"weight": 0.2, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
        }, own18, [760.0 / math.sqrt(2.0), 760.0 / math.sqrt(2.0),
                   -7000.0, 0.0, 0.0, 225.0, 250.0], None),
    ))

    # ── 21: 병합 마무리 — 50:50 IC (2026-08-09 사용자 지시 "계속 학습") ──
    # sil_merge_v1(유일한 양쪽 IC 딜승, 3승3패)을 기점으로 두 IC 균형 RL.
    # 보상은 검증된 stage 19/20 세팅 그대로. 판정은 프로브 사이클로 정점 동결.
    S.append(CurriculumStage(
        index=21, name="merge_polish",
        description="Polish the merged policy: 50/50 qualifier/final ICs vs elo.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=3000, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          "w_damage_taken": 25.0,
                          "w_range": 0.30,
                          "w_perch": 0.08, "perch_ata_deg": 30.0,
                          "perch_near_m": 300.0, "perch_far_m": 900.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0,
                          "w_overspeed": 0.5, "overspeed_gate_m": 2500.0},
        randomization=_rand(300.0, 20.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                {"weight": 0.5, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [760.0 / math.sqrt(2.0), 760.0 / math.sqrt(2.0),
                                       -7000.0, 0.0, 0.0, 225.0, 250.0]}},
                {"weight": 0.5, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
        }, own18, [760.0 / math.sqrt(2.0), 760.0 / math.sqrt(2.0),
                   -7000.0, 0.0, 0.0, 225.0, 250.0], None),
    ))

    # ── 22: 완전 근접 강제 (2026-08-10 사용자 지시) ───────────────────────
    # "전투기가 너무 멀리서 싸워, 보상으로 완전 근접 강제."
    # ① w_far 0.12: 1,200 m 밖 배회에 스텝당 최대 -0.12 (에피소드 만점 -240
    #    < crash -250 이라 자살 유인 없음, my_reward 3f)
    # ② 퍼치 창을 152~600 m 로 당기고 w 0.10 — 완전 근접에서 겨누는 자세가
    #    최대 수입: 500 m·정조준 = range 0.30 + perch ~0.09 + aim 0.16 = 0.55
    #    vs 2 km 배회 = -0.12 → 스텝당 0.67 수입 차.
    S.append(CurriculumStage(
        index=22, name="close_force",
        description="Force knife-fight: far-loiter penalty + perch pulled to 152-600 m.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=3000, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          "w_damage_taken": 25.0,
                          "w_range": 0.30,
                          "w_far": 0.12, "far_ramp_m": 400.0,
                          "w_perch": 0.10, "perch_ata_deg": 30.0,
                          "perch_near_m": 152.0, "perch_far_m": 600.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0,
                          "w_overspeed": 0.5, "overspeed_gate_m": 2500.0},
        randomization=_rand(300.0, 20.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                {"weight": 0.6, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [760.0 / math.sqrt(2.0), 760.0 / math.sqrt(2.0),
                                       -7000.0, 0.0, 0.0, 225.0, 250.0]}},
                {"weight": 0.4, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
        }, own18, [760.0 / math.sqrt(2.0), 760.0 / math.sqrt(2.0),
                   -7000.0, 0.0, 0.0, 225.0, 250.0], None),
    ))

    # ── 23: 콘-게이트 근접 (2026-08-10 사용자 지시) ──────────────────────
    # "적어도 적기가 조준콘 안에 있어야 하고, 데미지가 가장 좋은 최소지점에
    #  붙을수록 좋다." stage 22 는 w_range 0.30 이 조준과 무관하게 근접만으로
    # 지불해 "콘 밖 근접 선회"로 샜다(iter 108 실측: far 개선, win 0).
    # 근접 수입의 주력을 콘-게이트 항(w_wez, my_reward 3g)으로 교체:
    #   300 m 정조준  = wez 0.188 + aim 0.16 + range 0.10 ≈ +0.45/스텝
    #   300 m ATA 20° = range 0.10 뿐 (콘 밖 → wez 0)
    #   2 km 배회     = -0.12
    # perch 는 wez 와 창이 겹쳐 제거(0.0). 풀·IC·게이트는 stage 22 동일.
    S.append(CurriculumStage(
        index=23, name="cone_lock",
        description="Cone-gated closeness: pay proximity only while enemy is in the aim cone, peak at best-damage 260 m.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=3000, checkpoint_interval=20,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          "w_damage_taken": 25.0,
                          "w_range": 0.10,
                          "w_far": 0.12, "far_ramp_m": 400.0,
                          "w_perch": 0.0,
                          "w_wez": 0.20, "wez_cone_deg": 15.0,
                          "wez_best_m": 260.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0,
                          "w_overspeed": 0.5, "overspeed_gate_m": 2500.0},
        randomization=_rand(300.0, 20.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                {"weight": 0.6, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [760.0 / math.sqrt(2.0), 760.0 / math.sqrt(2.0),
                                       -7000.0, 0.0, 0.0, 225.0, 250.0]}},
                {"weight": 0.4, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
        }, own18, [760.0 / math.sqrt(2.0), 760.0 / math.sqrt(2.0),
                   -7000.0, 0.0, 0.0, 225.0, 250.0], None),
    ))

    # ── 24: 상호 근접 self-play (2026-08-10 사용자 지시) ─────────────────
    # "둘 다 너무 멀리서 싸운다. 상대방도 더 가까이 붙게, 그 상태에서 싸움을
    #  배우자." 고정 elo1667 은 원거리 성향이 동결돼 있어 우리만 붙어봐야
    # 편대비행이 된다. 풀의 67% 를 **자기 스냅샷**으로 채운다 — 스냅샷 상대는
    # 같은 콘-게이트 근접 보상으로 학습 중인 정책이라, 세대가 갈수록 양쪽이
    # 함께 붙는다(sidecar 가 20 iter 마다 스냅샷을 풀에 밀어넣음).
    # 스폰도 근접 시작(500~760 m 정면) 위주 — "그 상태에서" 싸움을 배운다.
    # elo1667 33% 는 진짜 목표 상대와의 접점 유지용.
    # 게이트 1.01 봉인 + 프로브는 번들만(eval 서브프로세스는 JSBSim 이중 초기화
    # 로 트레이너를 죽임, 07-30 실측) — 판정은 완주 후 out-of-process 프로브.
    _SNAP24 = ("artifacts/curriculum/AeroFlyer/0810_mutualclose/"
               "stage_24_mutual_close/snapshots")
    _QIC = [760.0 / math.sqrt(2.0), 760.0 / math.sqrt(2.0),
            -7000.0, 0.0, 0.0, 225.0, 250.0]
    _CIC500 = [500.0 / math.sqrt(2.0), 500.0 / math.sqrt(2.0),
               -7000.0, 0.0, 0.0, 225.0, 250.0]
    S.append(CurriculumStage(
        index=24, name="mutual_close",
        description="Mutual closeness self-play: 67% self snapshots (trained under the same cone-gated close reward) + 33% elo1667, close head-on spawns.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=3000, checkpoint_interval=20,
        eval_kill_probe_interval=20,   # 스냅샷 주기 (sidecar 가 풀로 승격)
        eval_kill_probe_eval=False,    # 번들만 — eval 서브프로세스 금지
        # 프로브는 eval_kill_floor > 0 일 때만 발화한다(train_curriculum 1101).
        # 0 으로 두면 스냅샷 번들이 영영 안 나와 sidecar 가 굶는다 (08-10 실측).
        # eval 이 꺼져 있어 프로브는 nan 을 돌려주고, nan 은 중단 판정에서
        # 제외되므로(isfinite 가드) 이 floor 로 학습이 멈출 일은 없다.
        eval_kill_floor=0.05,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          "w_damage_taken": 25.0,
                          "w_range": 0.10,
                          "w_far": 0.12, "far_start_m": 900.0,
                          "far_ramp_m": 400.0,
                          "w_perch": 0.0,
                          "w_wez": 0.20, "wez_cone_deg": 15.0,
                          "wez_best_m": 260.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0,
                          # 3d-2 (08-10): 감속-선회 이점 반영. iter_0120 실측
                          # 근접 280 m/s 관통 → ATA>30°(선회 필요)일 때만
                          # 190 m/s 초과에 벌점 만개(-0.8/step), 조준 추격은 면제.
                          "w_overspeed": 0.8, "overspeed_ref_mps": 190.0,
                          # 게이트 2000→1200 (08-10 iter_0880 실측): 2 km 게이트는
                          # 1.5~2.5 km 접근 속도까지 과세해 "멀찍이 저속 배회"
                          # (중앙 109~126 m/s @ 1.5~2.3 km, 딜 0)가 최적이 됐다.
                          # 감속 요구는 선회가 실익인 1.2 km 내로 한정.
                          "overspeed_gate_m": 1200.0,
                          "overspeed_turn_ata_deg": 30.0},
        randomization=_rand(300.0, 20.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                # self 스냅샷 67% — sidecar 가 snap_0000(부모)에서 최신으로 승격
                {"weight": 1.5, "mode": "policy", "bundle": f"{_SNAP24}/snap_0000",
                 "spawn": {"target": list(_QIC)}},
                {"weight": 0.5, "mode": "policy", "bundle": f"{_SNAP24}/snap_0000",
                 "spawn": {"target": list(_CIC500)}},
                {"weight": 0.5, "mode": "policy", "bundle": f"{_SNAP24}/snap_0000",
                 "spawn": {"target": list(_CIC500)}},
                {"weight": 0.5, "mode": "policy", "bundle": f"{_SNAP24}/snap_0000",
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
                # 진짜 목표 상대 33% — 예선/본선 IC 유지
                {"weight": 1.0, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_QIC)}},
                {"weight": 0.5, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
            "live_tune_file": (str(ROOT) + "/artifacts/curriculum/AeroFlyer/"
                               "0810_mutualclose/live_tune.json"),
        }, own18, list(_QIC), None),
    ))

    # ── 25: 스냅락 (2026-08-11) — mutualclose 정체의 다음 수 ─────────────
    # iter 1960 정점(본선 2승 2패) 후 2160·2420 연속 미달로 정체 확정.
    # 실측 갭: 콘 15° 체류 최대 47스텝인데 딜 0 — 15°→1° 정밀 조준의 수입
    # 기울기가 ~0.07/step 뿐. w_snap 0.5 (my_reward 3h): 밴드 내 ATA<3° 에
    # 가파른 보너스로 WEZ 문턱(±1°)까지 민다. 나머지는 stage 24 그대로.
    _SNAP25 = ("artifacts/curriculum/AeroFlyer/0811_snaplock/"
               "stage_25_snap_lock/snapshots")
    S.append(CurriculumStage(
        index=25, name="snap_lock",
        description="Snap-lock: steep in-band fine-aim bonus (ATA<3 deg) to bridge cone dwell into WEZ damage; mutual-close self-play pool.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=3000, checkpoint_interval=20,
        eval_kill_probe_interval=20,
        eval_kill_probe_eval=False,
        eval_kill_floor=0.05,   # 프로브 발화 조건 (stage 24 주석 참조)
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          "w_damage_taken": 25.0,
                          "w_range": 0.10,
                          "w_far": 0.12, "far_start_m": 900.0,
                          "far_ramp_m": 400.0,
                          "w_perch": 0.0,
                          "w_wez": 0.20, "wez_cone_deg": 15.0,
                          "wez_best_m": 260.0,
                          "w_snap": 0.5, "snap_ata_deg": 3.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0,
                          "w_overspeed": 0.8, "overspeed_ref_mps": 190.0,
                          "overspeed_gate_m": 1200.0,
                          "overspeed_turn_ata_deg": 30.0},
        randomization=_rand(300.0, 20.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                {"weight": 1.5, "mode": "policy", "bundle": f"{_SNAP25}/snap_0000",
                 "spawn": {"target": list(_QIC)}},
                {"weight": 0.5, "mode": "policy", "bundle": f"{_SNAP25}/snap_0000",
                 "spawn": {"target": list(_CIC500)}},
                {"weight": 0.5, "mode": "policy", "bundle": f"{_SNAP25}/snap_0000",
                 "spawn": {"target": list(_CIC500)}},
                {"weight": 0.5, "mode": "policy", "bundle": f"{_SNAP25}/snap_0000",
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
                {"weight": 1.0, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_QIC)}},
                {"weight": 0.5, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
            "live_tune_file": (str(ROOT) + "/artifacts/curriculum/AeroFlyer/"
                               "0811_snaplock/live_tune.json"),
        }, own18, list(_QIC), None),
    ))

    # ── 26: elo 주력 (2026-08-11) — snaplock 창 무딜의 다음 수 ───────────
    # snaplock(25)은 미러 딜은 컸지만(38.8) 정점 창(1700~1940) 전체에서 elo
    # 상대 딜 0 — self-play 67% 메타가 elo 전과 어긋나게 표류(미러 지표 함정).
    # 풀을 elo 62.5%(예선 1.5+본선 1.0)로 뒤집고 self 는 37.5%(1.5)로 축소:
    # 학습 분포를 진짜 목표 상대에 다시 정렬. 보상은 stage 25 그대로.
    _SNAP26 = ("artifacts/curriculum/AeroFlyer/0811_elomajor/"
               "stage_26_elo_major/snapshots")
    S.append(CurriculumStage(
        index=26, name="elo_major",
        description="Elo-majority pool (62.5%) to re-align the meta with the real target; snap-lock reward kept.",
        target_mode="fixed",
        # 3000 완주(08-11) 후 사용자 지시 "이어서 학습" — 한도 6000 으로 연장
        episode_step_limit=2200, max_iterations=6000, checkpoint_interval=20,
        eval_kill_probe_interval=20,
        eval_kill_probe_eval=False,
        eval_kill_floor=0.05,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          "w_damage_taken": 25.0,
                          "w_range": 0.10,
                          "w_far": 0.12, "far_start_m": 900.0,
                          "far_ramp_m": 400.0,
                          "w_perch": 0.0,
                          "w_wez": 0.20, "wez_cone_deg": 15.0,
                          "wez_best_m": 260.0,
                          "w_snap": 0.5, "snap_ata_deg": 3.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0,
                          "w_overspeed": 0.8, "overspeed_ref_mps": 190.0,
                          "overspeed_gate_m": 1200.0,
                          "overspeed_turn_ata_deg": 30.0},
        randomization=_rand(300.0, 20.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                # elo 62.5% — 예선/본선 IC
                {"weight": 1.5, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_QIC)}},
                {"weight": 1.0, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
                # self 37.5% — 다양성 유지용
                {"weight": 0.75, "mode": "policy", "bundle": f"{_SNAP26}/snap_0000",
                 "spawn": {"target": list(_QIC)}},
                {"weight": 0.5, "mode": "policy", "bundle": f"{_SNAP26}/snap_0000",
                 "spawn": {"target": list(_CIC500)}},
                {"weight": 0.25, "mode": "policy", "bundle": f"{_SNAP26}/snap_0000",
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
            "live_tune_file": (str(ROOT) + "/artifacts/curriculum/AeroFlyer/"
                               "0811_elomajor/live_tune.json"),
        }, own18, list(_QIC), None),
    ))

    # ── 27: 새들락 (2026-08-12 사용자 지적 "아직 근접전 안 하고 돌기만") ──
    # 프로브 실측: 머지 1회 스침(최소 10~80 m) 후 상호 이탈 → 2~4 km 재접근
    # 루프. WEZ 체류 0~3스텝 — 붙어 있는 상태를 경험할 기회가 판당 몇 초뿐이라
    # 유지 기술을 못 배운다. backward curriculum(초기 gun_saddle이 교사 상대
    # 조준을 뚫은 방법)을 elo 상대로 재적용: **적 후방 500~900 m 꼬리 스폰**
    # 위주로 시작해 "붙은 상태 유지 → 밴드 체류 → 딜"만 배우게 좁힌다.
    # 예선 정면 20%는 대회 IC 접점 유지용. 보상은 stage 26 그대로.
    _SNAP27 = ("artifacts/curriculum/AeroFlyer/0812_saddle/"
               "stage_27_saddle_lock/snapshots")
    def _tail(d):
        # own18 은 yaw 45°(북동) — 진행 방향 앞 d 미터, 같은 침로 = 우리가 적 6시
        return [d / math.sqrt(2.0), d / math.sqrt(2.0),
                -7000.0, 0.0, 0.0, 45.0, 250.0]
    S.append(CurriculumStage(
        index=27, name="saddle_lock",
        description="Saddle-lock: spawn at the enemy's six (500-900 m, same heading) vs elo+self; learn to HOLD the knife fight.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=6000, checkpoint_interval=20,
        eval_kill_probe_interval=20,
        eval_kill_probe_eval=False,
        eval_kill_floor=0.05,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          "w_damage_taken": 25.0,
                          "w_range": 0.10,
                          "w_far": 0.12, "far_start_m": 900.0,
                          "far_ramp_m": 400.0,
                          "w_perch": 0.0,
                          "w_wez": 0.20, "wez_cone_deg": 15.0,
                          "wez_best_m": 260.0,
                          "w_snap": 0.5, "snap_ata_deg": 3.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0,
                          "w_overspeed": 0.8, "overspeed_ref_mps": 190.0,
                          "overspeed_gate_m": 1200.0,
                          "overspeed_turn_ata_deg": 30.0},
        # 꼬리 스폰 기하를 지키도록 산포 축소 (300 m 산포는 500 m 새들을 뒤집는다)
        randomization=_rand(100.0, 10.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                # elo 새들 60% — 밴드 안/어깨의 꼬리 시작
                {"weight": 1.5, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": _tail(500.0)}},
                {"weight": 1.0, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": _tail(800.0)}},
                # 예선 정면 20% — 대회 IC 접점 유지
                {"weight": 0.8, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_QIC)}},
                # self 새들 20% — 상대도 근접 유지를 배우는 짝
                {"weight": 0.5, "mode": "policy", "bundle": f"{_SNAP27}/snap_0000",
                 "spawn": {"target": _tail(600.0)}},
                {"weight": 0.3, "mode": "policy", "bundle": f"{_SNAP27}/snap_0000",
                 "spawn": {"target": list(_CIC500)}},
            ],
            "live_tune_file": (str(ROOT) + "/artifacts/curriculum/AeroFlyer/"
                               "0812_saddle/live_tune.json"),
        }, own18, _tail(500.0), None),
    ))

    # ── 28: 정면전 + 접근 포텐셜 (2026-08-12 사용자 지시) ─────────────────
    # "접근할수록 보상. 꼬리 공격은 굳이 필요 없고, 원래 전면전을 배우기로 했다."
    # 새들(27) 노선 종료. 스폰은 전부 정면(예선 760 / 근접 500 / 본선 3048),
    # 보상에 접근 포텐셜 w_close_pot 15 신설(my_reward 3i): 1 km 좁힐 때마다
    # +15, 벌어지면 회수 — 머지 후 상호 이탈 루프에 직접 벌점. 정면샷 우대는
    # 기본값(w_headon_mult 1.0 = 정면 데미지 x2)이 이미 살아 있다.
    _SNAP28 = ("artifacts/curriculum/AeroFlyer/0812_headon/"
               "stage_28_headon_close/snapshots")
    S.append(CurriculumStage(
        index=28, name="headon_close",
        description="Head-on line + approach potential: every km closed pays, extension refunds; all-frontal spawns.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=6000, checkpoint_interval=20,
        eval_kill_probe_interval=20,
        eval_kill_probe_eval=False,
        eval_kill_floor=0.05,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          "w_damage_taken": 25.0,
                          "w_range": 0.10,
                          "w_far": 0.12, "far_start_m": 900.0,
                          "far_ramp_m": 400.0,
                          "w_perch": 0.0,
                          "w_wez": 0.20, "wez_cone_deg": 15.0,
                          "wez_best_m": 260.0,
                          "w_snap": 0.5, "snap_ata_deg": 3.0,
                          "w_close_pot": 15.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 10.0,
                          "w_overspeed": 0.8, "overspeed_ref_mps": 190.0,
                          "overspeed_gate_m": 1200.0,
                          "overspeed_turn_ata_deg": 30.0},
        randomization=_rand(100.0, 10.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                # elo 정면 62.5%
                {"weight": 1.2, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_QIC)}},
                {"weight": 0.6, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_CIC500)}},
                {"weight": 0.7, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
                # self 정면 37.5%
                {"weight": 0.9, "mode": "policy", "bundle": f"{_SNAP28}/snap_0000",
                 "spawn": {"target": list(_QIC)}},
                {"weight": 0.6, "mode": "policy", "bundle": f"{_SNAP28}/snap_0000",
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
            "live_tune_file": (str(ROOT) + "/artifacts/curriculum/AeroFlyer/"
                               "0812_headon/live_tune.json"),
        }, own18, list(_QIC), None),
    ))

    # ── 29: 신호 정화 (2026-08-14 실측 진단) ─────────────────────────────
    # headon(28) 6000 완주 후 학습곡선 분석: reward_mean 이 -1,950 에서 평평
    # (붕괴 아님, entropy·explained_var 안정). 그런데 **성분 분해에서 병이
    # 드러났다** — 배치 간 표준편차(PPO 가 실제로 배우는 양):
    #     ceil(고도천장)  652   <-- 지배
    #     overspeed        19
    #     damage           12   <-- 진짜 전투 신호
    # 즉 "이 배치가 우연히 높이 올라갔나"가 "더 잘 쐈나"보다 53배 크게 기울기를
    # 흔든다. 결정론 정책은 24~25k ft 로 정상 비행(실측)이라 실력 문제가
    # 아니라 **탐색 잡음 판이 무는 세금**이 배치 평균을 지배한 것.
    # 처방: 천장을 전투고도(19~26k ft)에서 사실상 0 으로 만들고, 고고도 퇴화
    # 차단 기능만 45k ft 위에 남긴다. w 10→2, 중심 40k→45k, 램프 3000→2000:
    #     26k ft  -0.0002/step (사실상 0, 기존 -0.09)
    #     40k ft  -0.15/step  (억제 유효)
    #     46k ft  -1.24/step  (강한 차단)
    # 나머지는 stage 28 그대로. init 은 headon 최고 번들(예선 딜 0.241).
    _SNAP29 = ("artifacts/curriculum/AeroFlyer/0814_signalclean/"
               "stage_29_signal_clean/snapshots")
    S.append(CurriculumStage(
        index=29, name="signal_clean",
        description="Signal cleanup: ceiling tax removed from combat altitudes so the damage gradient is no longer swamped (measured 53:1).",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=6000, checkpoint_interval=20,
        eval_kill_probe_interval=20,
        eval_kill_probe_eval=False,
        eval_kill_floor=0.05,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          "w_damage_taken": 25.0,
                          "w_range": 0.10,
                          "w_far": 0.12, "far_start_m": 900.0,
                          "far_ramp_m": 400.0,
                          "w_perch": 0.0,
                          "w_wez": 0.20, "wez_cone_deg": 15.0,
                          "wez_best_m": 260.0,
                          "w_snap": 0.5, "snap_ata_deg": 3.0,
                          "w_close_pot": 15.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          # 신호 정화의 핵심 (위 주석)
                          "w_ceil": 2.0, "ceil_ft": 45000.0,
                          "ceil_ramp_ft": 2000.0,
                          "w_overspeed": 0.8, "overspeed_ref_mps": 190.0,
                          "overspeed_gate_m": 1200.0,
                          "overspeed_turn_ata_deg": 30.0},
        randomization=_rand(100.0, 10.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                {"weight": 1.2, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_QIC)}},
                {"weight": 0.6, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_CIC500)}},
                {"weight": 0.7, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
                {"weight": 0.9, "mode": "policy", "bundle": f"{_SNAP29}/snap_0000",
                 "spawn": {"target": list(_QIC)}},
                {"weight": 0.6, "mode": "policy", "bundle": f"{_SNAP29}/snap_0000",
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
            "live_tune_file": (str(ROOT) + "/artifacts/curriculum/AeroFlyer/"
                               "0814_signalclean/live_tune.json"),
        }, own18, list(_QIC), None),
    ))

    # ── 30: 예선 집중 (2026-08-15) — 상보 약점을 RL 로 직접 때린다 ────────
    # 48판 다중시드 실측: signalclean_iter1420 은 본선 10승 2패(딜마진 +0.098)
    # 인데 예선(760 m 정면)은 2승 5패. 반대로 champion_close_iter1940 은
    # 예선 4승 1패·본선 7승 9패. 상보 관계다.
    # BC 병합(merge_expert_v3)은 실패 — 종합 11승 13패. 서로 다른 전술을
    # 평균내면 어느 쪽도 아닌 정책이 된다(모드 평균화, 이 프로젝트 4전 4패).
    # 그래서 **RL 로 약점만 직접** 훈련한다: 예선 IC 78%, 본선 22%(망각 방지).
    # self-play 스냅샷은 뺀다 — 미러 지표가 판정을 오도한 전례(미러 딜 65.9가
    # 48판에서 8승 14패로 드러남). 상대는 우리가 실제로 평가받는 elo 만.
    # 보상은 stage 29(신호 정화) 그대로. init = signalclean_iter1420.
    S.append(CurriculumStage(
        index=30, name="quali_focus",
        description="Qualifier-focused RL on the finals expert: 78% 760 m head-on vs elo, 22% finals to prevent forgetting, no mirror pool.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=6000, checkpoint_interval=20,
        eval_kill_probe_interval=20,
        eval_kill_probe_eval=False,
        eval_kill_floor=0.05,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          "w_damage_taken": 25.0,
                          "w_range": 0.10,
                          "w_far": 0.12, "far_start_m": 900.0,
                          "far_ramp_m": 400.0,
                          "w_perch": 0.0,
                          "w_wez": 0.20, "wez_cone_deg": 15.0,
                          "wez_best_m": 260.0,
                          "w_snap": 0.5, "snap_ata_deg": 3.0,
                          "w_close_pot": 15.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          "w_ceil": 2.0, "ceil_ft": 45000.0,
                          "ceil_ramp_ft": 2000.0,
                          "w_overspeed": 0.8, "overspeed_ref_mps": 190.0,
                          "overspeed_gate_m": 1200.0,
                          "overspeed_turn_ata_deg": 30.0},
        randomization=_rand(100.0, 10.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                # 예선 계열 78% — 약점 집중
                {"weight": 3.0, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_QIC)}},
                {"weight": 0.5, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_CIC500)}},
                # 본선 22% — 기존 강점 망각 방지
                {"weight": 1.0, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
        }, own18, list(_QIC), None),
    ))

    # ── 31: 사선(gunline) — 각도 대신 **미터**로 조준을 산다 (2026-08-15) ──
    # 왜 필요한가 (signalclean_iter1420, 본선 IC 8판 결정론 실측):
    #   판당 머지 4.9회 / 사거리 밴드 체류 103스텝(10.3초)  <- 기회는 있다
    #   밴드 안 미스거리(d x sin ATA) 중앙 235 m, p1 9.6 m  <- 사선에서 30배 밖
    #   패스당 딜 0.009 (클린 정면 패스 이론값 0.69)        <- 1.3%
    #   딜의 100%가 전반 100초. 후반 100초는 원뿔이 ±2°/±3°로 넓어지는데도 0
    # 즉 "못 붙어서"가 아니라 "붙어서도 사선에 못 올려서" 딜이 안 난다.
    # 각도 보상(w_wez 15° 원뿔)은 3 km 에서 1°=52 m 인 구간까지 값을 지불한다 —
    # 데미지가 물리적으로 불가능한 곳에 기울기가 몰려 있었다. 그래서 그 항을
    # 1/3 로 줄이고, 대신 거리와 무관하게 미터로 재는 w_nmd 를 주력으로 놓는다.
    # w_cpa 는 밴드 **밖** 담당: 머지는 밴드 통과가 1.2초뿐이라 들어간 뒤
    # 조준을 만들 시간이 없다. 들어가기 전에 충돌코스를 만들어 둬야 한다.
    #
    # 판정승 정렬 (같이 고친다): 종료식이
    #   terminal = draw_reward(-40) + draw_health_scale(100) x (own_hp - tgt_hp)
    # 라서, 대회 규칙상 **승리**인 딜마진 +0.098 이 -30.2점이었다. 교착(-40)과
    # 9.8점 차이뿐이라 shaping 잡음에 묻혀 "이겼다"가 정책에 보이지 않는다.
    # scale 을 600 으로 올리면 +0.098 -> +18.8, -0.098 -> -98.8 로 부호가 갈린다.
    #
    # 선회도 같이 고친다 (maxturn 실측, 180도 반전):
    #   BC 교사 설정(뱅크72·피치-0.85·풀스로틀)  22.6초 / 8.1°/s / 고도 +628 m
    #   뱅크85·풀당김·스로틀0.3                  16.9초 / 11.1°/s / 고도 -1144 m
    # 교사가 **선회하면서 상승한다** — 중력이 선회를 방해하는 방향이다. 정책이
    # 그걸 물려받았다. 물리 한계는 11.1°/s 고 우리는 8.1 을 쓰고 있으니 25%
    # 더 자주 머지할 수 있다. 천장 벌점을 더 낮춰(w_ceil 2.0 -> 1.0) 강하 선회를
    # 풀어주고, 과속 벌점의 선회 게이트는 유지한다(스로틀을 줄이는 쪽이 실제로
    # 더 빨리 돈다는 것이 실측으로 확인됐다 — 사용자 직관이 맞았다).
    #
    # 상대는 elo1667 만. self-play 미러는 넣지 않는다(미러 딜이 절대실력과
    # 역상관이었던 전례). IC 는 예선/본선 반반 — stage 30 이 예선 편중이라
    # 본선을 잃을 위험이 있어 여기서 균형으로 되돌린다.
    S.append(CurriculumStage(
        index=31, name="gunline",
        description="Metric-aimpoint stage: miss-distance and predicted-CPA shaping replace the wide-cone angle term, judgment-win margin aligned, descending turns unlocked.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=6000, checkpoint_interval=20,
        eval_kill_probe_interval=20,
        eval_kill_probe_eval=False,
        eval_kill_floor=0.05,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          # 판정승이 양수가 되도록 (위 주석)
                          "draw_health_scale": 600.0,
                          "w_damage_taken": 25.0,
                          "w_range": 0.10,
                          # far 램프를 정책이 실제로 사는 거리로 옮긴다.
                          # 실측: stage 30 은 1,028 iteration 내내 평균 교전거리가
                          # 2,710~2,754 m 로 고정(변동 1.6%)이었다. 원인은
                          # start 900 / ramp 400 이라 2,720 m 에서 시그모이드가
                          # 완전 포화 — 에피소드당 -148 점을 내면서 2,720->2,000 m
                          # 로 좁혀도 기울기가 0.0000022/m 뿐이다(900 m 의 1/34).
                          # "멀다"는 상수 세금이었을 뿐 "가까워져라"가 아니었다.
                          # 접근 포텐셜(w_close_pot)은 텔레스코프라 **끝 거리**만
                          # 값을 친다 — 머지로 붙었다가 이탈하면 순합 0(실측 -0.74).
                          # 그래서 "붙어 있는 시간"에 값을 치는 항이 비어 있었다.
                          "w_far": 0.12, "far_start_m": 1800.0,
                          "far_ramp_m": 1000.0,
                          "w_perch": 0.0,
                          # 넓은 원뿔 각도항은 1/3 로 — 데미지 불가 구간 지불을 줄인다
                          "w_wez": 0.06, "wez_cone_deg": 15.0,
                          "wez_best_m": 260.0,
                          "w_snap": 0.5, "snap_ata_deg": 3.0,
                          # 신설 주력 2항. 가중치는 **std 기준으로 실측해서**
                          # 잡았다(signal_scale.py, 챔피언 8판). 처음 잡은
                          # w_nmd 0.20 / w_cpa 0.10 은 에피소드 합이 0.68 / 2.11,
                          # std 가 0.24 / 0.82 로 **딜 std(32.3)의 0.7% / 3%** 라
                          # 사실상 보이지 않았다. 학습에 영향을 주는 것은 평균이
                          # 아니라 std 다 — 평균은 상수처럼 작용해 어드밴티지에서
                          # 상쇄된다(2026-08-14 신호 침몰 진단과 같은 계산).
                          # 40배/15배 올려 std 를 딜의 0.3 수준에 둔다. 딜을
                          # 밀어내지 않으면서 존재하는 크기.
                          # 파밍 안전: nmd 최대치는 NMD~0 을 밴드 안에서 유지할
                          # 때인데 그 상태가 곧 데미지라 유지하면 적이 1.6초에
                          # 죽는다 — 항 자체가 격추로 자동 종료된다.
                          "w_nmd": 8.0, "nmd_half_m": 10.0,
                          "w_cpa": 1.5, "cpa_half_m": 40.0,
                          "cpa_horizon_s": 8.0,
                          "w_close_pot": 15.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          # 강하 선회 해금 — 교사가 선회 중 628 m 상승했다
                          "w_ceil": 1.0, "ceil_ft": 45000.0,
                          "ceil_ramp_ft": 2000.0,
                          "w_overspeed": 0.8, "overspeed_ref_mps": 190.0,
                          "overspeed_gate_m": 1200.0,
                          "overspeed_turn_ata_deg": 30.0},
        randomization=_rand(100.0, 10.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                # 예선 50%
                {"weight": 1.8, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_QIC)}},
                {"weight": 0.2, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_CIC500)}},
                # 본선 50%
                {"weight": 2.0, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
        }, own18, list(_QIC), None),
    ))

    # ── 32: 사선+고도 규율 (gunline_low) — 2026-08-15 ────────────────────
    # stage 31 은 325 iteration 에 선행지표가 하나도 안 움직였다(평균 교전거리
    # 2,688~2,754 m 고정, nmd 43.9->45.0, 48판 8승 8패·예선 딜 0.000).
    # 원인을 두 층 더 파서 찾았다:
    #   1) 교전거리는 정책의 선택이 아니라 **선회 지름**이 정한다
    #   2) 선회 지름이 큰 이유는 정책이 **7,000 m 에서 8,167(중앙)~11,581(p90) m
    #      까지 올라가기 때문**이다 (alt_trace.py 8판: 7판이 9,000~13,300 m 종료)
    #   3) 올라가는 이유는 BC 교사의 기수-상승 선회(반전당 +628 m)를 물려받은 것
    # 실측 선회 지름: 7,000 m 2,907 m / 8,167 m 3,434 m / 11,500 m 5,225 m.
    # 사거리 밴드가 914 m 인데 선회 지름이 5 km 면 사격 기하에 들어갈 기회가 없다.
    # 그래서 조준 보상(31)만으로는 부족했다 — 틀린 게 아니라 **혼자서는** 부족.
    # w_high 로 상승에만 값을 매긴다(포텐셜이라 오르내림 차이만 지불, 파밍 불가,
    # 6,000 m 이하 무벌점이라 바닥으로 밀지 않는다).
    #
    # 아래는 stage 31 주석 원문 (조준 항의 근거):
    # ── 31: 사선(gunline) — 각도 대신 **미터**로 조준을 산다 (2026-08-15) ──
    # 왜 필요한가 (signalclean_iter1420, 본선 IC 8판 결정론 실측):
    #   판당 머지 4.9회 / 사거리 밴드 체류 103스텝(10.3초)  <- 기회는 있다
    #   밴드 안 미스거리(d x sin ATA) 중앙 235 m, p1 9.6 m  <- 사선에서 30배 밖
    #   패스당 딜 0.009 (클린 정면 패스 이론값 0.69)        <- 1.3%
    #   딜의 100%가 전반 100초. 후반 100초는 원뿔이 ±2°/±3°로 넓어지는데도 0
    # 즉 "못 붙어서"가 아니라 "붙어서도 사선에 못 올려서" 딜이 안 난다.
    # 각도 보상(w_wez 15° 원뿔)은 3 km 에서 1°=52 m 인 구간까지 값을 지불한다 —
    # 데미지가 물리적으로 불가능한 곳에 기울기가 몰려 있었다. 그래서 그 항을
    # 1/3 로 줄이고, 대신 거리와 무관하게 미터로 재는 w_nmd 를 주력으로 놓는다.
    # w_cpa 는 밴드 **밖** 담당: 머지는 밴드 통과가 1.2초뿐이라 들어간 뒤
    # 조준을 만들 시간이 없다. 들어가기 전에 충돌코스를 만들어 둬야 한다.
    #
    # 판정승 정렬 (같이 고친다): 종료식이
    #   terminal = draw_reward(-40) + draw_health_scale(100) x (own_hp - tgt_hp)
    # 라서, 대회 규칙상 **승리**인 딜마진 +0.098 이 -30.2점이었다. 교착(-40)과
    # 9.8점 차이뿐이라 shaping 잡음에 묻혀 "이겼다"가 정책에 보이지 않는다.
    # scale 을 600 으로 올리면 +0.098 -> +18.8, -0.098 -> -98.8 로 부호가 갈린다.
    #
    # 선회도 같이 고친다 (maxturn 실측, 180도 반전):
    #   BC 교사 설정(뱅크72·피치-0.85·풀스로틀)  22.6초 / 8.1°/s / 고도 +628 m
    #   뱅크85·풀당김·스로틀0.3                  16.9초 / 11.1°/s / 고도 -1144 m
    # 교사가 **선회하면서 상승한다** — 중력이 선회를 방해하는 방향이다. 정책이
    # 그걸 물려받았다. 물리 한계는 11.1°/s 고 우리는 8.1 을 쓰고 있으니 25%
    # 더 자주 머지할 수 있다. 천장 벌점을 더 낮춰(w_ceil 2.0 -> 1.0) 강하 선회를
    # 풀어주고, 과속 벌점의 선회 게이트는 유지한다(스로틀을 줄이는 쪽이 실제로
    # 더 빨리 돈다는 것이 실측으로 확인됐다 — 사용자 직관이 맞았다).
    #
    # 상대는 elo1667 만. self-play 미러는 넣지 않는다(미러 딜이 절대실력과
    # 역상관이었던 전례). IC 는 예선/본선 반반 — stage 30 이 예선 편중이라
    # 본선을 잃을 위험이 있어 여기서 균형으로 되돌린다.
    S.append(CurriculumStage(
        index=32, name="gunline_low",
        description="gunline + altitude discipline: a telescoping high-altitude potential stops the inherited nose-high climb that doubles the turn diameter.",
        target_mode="fixed",
        episode_step_limit=2200, max_iterations=6000, checkpoint_interval=20,
        eval_kill_probe_interval=20,
        eval_kill_probe_eval=False,
        eval_kill_floor=0.05,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          # 판정승이 양수가 되도록 (위 주석)
                          "draw_health_scale": 600.0,
                          # 딜 교환비를 승리 조건에 맞춘다 (2026-08-15 실측).
                          # 25 였을 때 w_damage 300 대비 **12:1** — "1 맞히면
                          # 12 맞아도 이득"이다. 대회 판정은 딜 **마진**이라
                          # 정반대다. 종료 보상(draw_health_scale 600)은 마진을
                          # 옳게 평가하지만 gamma 0.995 의 유효 지평이 200 스텝
                          # (20초)인데 에피소드는 1,900 스텝이라, 시작 시점
                          # 현재가치가 0.995^1900 = 0.00007 로 **보이지 않는다**.
                          # 실제로 정책을 움직이는 것은 조밀한 스텝 보상뿐이었다.
                          # 정책이 얼어 있는 동안엔 이 결함이 드러나지 않았다 —
                          # 옵티마이저를 푼 0815_unfreeze iter_0180 에서 피딜이
                          # 0.001 -> 0.067 (67배), 종합 8승8패 -> 5승16패.
                          "w_damage_taken": 0.0,   # [본선 2026-08-28] 300 -> 50 -> 0 (사용자 지시). 피격 페널티 제거 — 딜 보상만으로 선회전 학습
                          "w_range": 0.10,
                          # far 램프를 정책이 실제로 사는 거리로 옮긴다.
                          # 실측: stage 30 은 1,028 iteration 내내 평균 교전거리가
                          # 2,710~2,754 m 로 고정(변동 1.6%)이었다. 원인은
                          # start 900 / ramp 400 이라 2,720 m 에서 시그모이드가
                          # 완전 포화 — 에피소드당 -148 점을 내면서 2,720->2,000 m
                          # 로 좁혀도 기울기가 0.0000022/m 뿐이다(900 m 의 1/34).
                          # "멀다"는 상수 세금이었을 뿐 "가까워져라"가 아니었다.
                          # 접근 포텐셜(w_close_pot)은 텔레스코프라 **끝 거리**만
                          # 값을 친다 — 머지로 붙었다가 이탈하면 순합 0(실측 -0.74).
                          # 그래서 "붙어 있는 시간"에 값을 치는 항이 비어 있었다.
                          "w_far": 0.12, "far_start_m": 1800.0,
                          "far_ramp_m": 1000.0,
                          "w_perch": 0.0,
                          # 넓은 원뿔 각도항은 1/3 로 — 데미지 불가 구간 지불을 줄인다
                          "w_wez": 0.06, "wez_cone_deg": 15.0,
                          "wez_best_m": 260.0,
                          "w_snap": 0.5, "snap_ata_deg": 3.0,
                          # 신설 주력 2항. 가중치는 **std 기준으로 실측해서**
                          # 잡았다(signal_scale.py, 챔피언 8판). 처음 잡은
                          # w_nmd 0.20 / w_cpa 0.10 은 에피소드 합이 0.68 / 2.11,
                          # std 가 0.24 / 0.82 로 **딜 std(32.3)의 0.7% / 3%** 라
                          # 사실상 보이지 않았다. 학습에 영향을 주는 것은 평균이
                          # 아니라 std 다 — 평균은 상수처럼 작용해 어드밴티지에서
                          # 상쇄된다(2026-08-14 신호 침몰 진단과 같은 계산).
                          # 40배/15배 올려 std 를 딜의 0.3 수준에 둔다. 딜을
                          # 밀어내지 않으면서 존재하는 크기.
                          # 파밍 안전: nmd 최대치는 NMD~0 을 밴드 안에서 유지할
                          # 때인데 그 상태가 곧 데미지라 유지하면 적이 1.6초에
                          # 죽는다 — 항 자체가 격추로 자동 종료된다.
                          "w_nmd": 8.0, "nmd_half_m": 10.0,
                          "w_cpa": 1.5, "cpa_half_m": 40.0,
                          "cpa_horizon_s": 8.0,
                          "w_close_pot": 15.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          # 강하 선회 해금 — 교사가 선회 중 628 m 상승했다
                          "w_ceil": 1.0, "ceil_ft": 45000.0,
                          "ceil_ramp_ft": 2000.0,
                          # 고도 규율 — 가중치는 signal_scale.py 로 std 재고 확정
                          "w_high": 60.0, "high_floor_m": 6000.0,
                          "high_span_m": 8000.0,
                          "w_overspeed": 0.8, "overspeed_ref_mps": 190.0,
                          "overspeed_gate_m": 1200.0,
                          "overspeed_turn_ata_deg": 30.0},
        randomization=_rand(100.0, 10.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "live_tune_file": (str(ROOT) + "/artifacts/curriculum/AeroFlyer/"
                               "0815_symmetric/live_tune.json"),
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                # 예선 50%
                {"weight": 1.8, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_QIC)}},
                {"weight": 0.2, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_CIC500)}},
                # 본선 50%
                {"weight": 2.0, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
        }, own18, list(_QIC), None),
    ))

    # ── 33: 자가대전 사다리 (selfplay_ladder) — 2026-08-15 ───────────────
    # 왜: stage 32 가 정체했다. 96판 판별에서
    #     symmetric_iter1540  78승 9패 (승패차 +69)
    #     symmetric_iter1720  78승 7패 (승패차 +71)   <- 180 iter 차이, 동률
    # 승수가 78 로 **정확히 같다**. 그리고 96판 중 78판을 이긴다(81%) —
    # 상대(elo1667)를 압도해서 학습 신호가 남지 않은 것이다.
    # 그래서 보상은 **그대로 두고 상대만 우리 수준으로 올린다**: 풀의 절반을
    # 우리 챔피언으로 채운다. 살아있는 스냅샷 승격이 아니라 **고정 챔피언 번들**을
    # 쓰는 이유는 미러 지표가 절대 실력과 역상관인 함정 때문이다
    # (실측: 미러 딜 65.9 가 48판 8승 14패였다).
    # **판정은 계속 elo1667 고정 상대 96판으로만** 한다 — 미러 성적은 안 본다.
    S.append(CurriculumStage(
        index=33, name="selfplay_ladder",
        description="Same reward as stage 32; the opponent pool now mixes elo1667 with our own champion so the fight stays at our level once elo1667 is outclassed.",
        target_mode="fixed",
        # [2026-08-16] 6000 에서 상한에 걸려 멈췄다. 자가대전은 계속 오르는 중이라 올린다.
        episode_step_limit=2200, max_iterations=30000, checkpoint_interval=20,
        eval_kill_probe_interval=20,
        eval_kill_probe_eval=False,
        eval_kill_floor=0.05,
        reward_overrides={"w_deck": 4.0, "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          # 판정승이 양수가 되도록 (위 주석)
                          "draw_health_scale": 600.0,
                          # 딜 교환비를 승리 조건에 맞춘다 (2026-08-15 실측).
                          # 25 였을 때 w_damage 300 대비 **12:1** — "1 맞히면
                          # 12 맞아도 이득"이다. 대회 판정은 딜 **마진**이라
                          # 정반대다. 종료 보상(draw_health_scale 600)은 마진을
                          # 옳게 평가하지만 gamma 0.995 의 유효 지평이 200 스텝
                          # (20초)인데 에피소드는 1,900 스텝이라, 시작 시점
                          # 현재가치가 0.995^1900 = 0.00007 로 **보이지 않는다**.
                          # 실제로 정책을 움직이는 것은 조밀한 스텝 보상뿐이었다.
                          # 정책이 얼어 있는 동안엔 이 결함이 드러나지 않았다 —
                          # 옵티마이저를 푼 0815_unfreeze iter_0180 에서 피딜이
                          # 0.001 -> 0.067 (67배), 종합 8승8패 -> 5승16패.
                          "w_damage_taken": 0.0,   # [본선 2026-08-28] 300 -> 50 -> 0 (사용자 지시). 피격 페널티 제거 — 딜 보상만으로 선회전 학습
                          "w_range": 0.10,
                          # far 램프를 정책이 실제로 사는 거리로 옮긴다.
                          # 실측: stage 30 은 1,028 iteration 내내 평균 교전거리가
                          # 2,710~2,754 m 로 고정(변동 1.6%)이었다. 원인은
                          # start 900 / ramp 400 이라 2,720 m 에서 시그모이드가
                          # 완전 포화 — 에피소드당 -148 점을 내면서 2,720->2,000 m
                          # 로 좁혀도 기울기가 0.0000022/m 뿐이다(900 m 의 1/34).
                          # "멀다"는 상수 세금이었을 뿐 "가까워져라"가 아니었다.
                          # 접근 포텐셜(w_close_pot)은 텔레스코프라 **끝 거리**만
                          # 값을 친다 — 머지로 붙었다가 이탈하면 순합 0(실측 -0.74).
                          # 그래서 "붙어 있는 시간"에 값을 치는 항이 비어 있었다.
                          "w_far": 0.12, "far_start_m": 1800.0,
                          "far_ramp_m": 1000.0,
                          "w_perch": 0.0,
                          # 넓은 원뿔 각도항은 1/3 로 — 데미지 불가 구간 지불을 줄인다
                          "w_wez": 0.06, "wez_cone_deg": 15.0,
                          "wez_best_m": 260.0,
                          "w_snap": 0.5, "snap_ata_deg": 3.0,
                          # 신설 주력 2항. 가중치는 **std 기준으로 실측해서**
                          # 잡았다(signal_scale.py, 챔피언 8판). 처음 잡은
                          # w_nmd 0.20 / w_cpa 0.10 은 에피소드 합이 0.68 / 2.11,
                          # std 가 0.24 / 0.82 로 **딜 std(32.3)의 0.7% / 3%** 라
                          # 사실상 보이지 않았다. 학습에 영향을 주는 것은 평균이
                          # 아니라 std 다 — 평균은 상수처럼 작용해 어드밴티지에서
                          # 상쇄된다(2026-08-14 신호 침몰 진단과 같은 계산).
                          # 40배/15배 올려 std 를 딜의 0.3 수준에 둔다. 딜을
                          # 밀어내지 않으면서 존재하는 크기.
                          # 파밍 안전: nmd 최대치는 NMD~0 을 밴드 안에서 유지할
                          # 때인데 그 상태가 곧 데미지라 유지하면 적이 1.6초에
                          # 죽는다 — 항 자체가 격추로 자동 종료된다.
                          "w_nmd": 8.0, "nmd_half_m": 10.0,
                          "w_cpa": 1.5, "cpa_half_m": 40.0,
                          "cpa_horizon_s": 8.0,
                          "w_close_pot": 15.0,
                          "w_aim": 0.16,
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          # 강하 선회 해금 — 교사가 선회 중 628 m 상승했다
                          "w_ceil": 1.0, "ceil_ft": 45000.0,
                          "ceil_ramp_ft": 2000.0,
                          # 고도 규율 — 가중치는 signal_scale.py 로 std 재고 확정
                          "w_high": 60.0, "high_floor_m": 6000.0,
                          "high_span_m": 8000.0,
                          "w_overspeed": 0.8, "overspeed_ref_mps": 190.0,
                          "overspeed_gate_m": 1200.0,
                          "overspeed_turn_ata_deg": 30.0},
        randomization=_rand(100.0, 10.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "live_tune_file": (str(ROOT) + "/artifacts/curriculum/AeroFlyer/"
                               "0815_ladder/live_tune.json"),
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            "target_pool": [
                # elo1667 50% — 기존 기준선 유지(망각 방지)
                {"weight": 0.9, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": list(_QIC)}},
                {"weight": 1.1, "mode": "policy", "bundle": RL_OPPONENTS["elo1667"],
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
                # 우리 챔피언 50% — 동급 상대라야 기울기가 산다
                {"weight": 0.9, "mode": "policy",
                 "bundle": str(_MODELS / "symmetric_iter1720"),
                 "spawn": {"target": list(_QIC)}},
                {"weight": 1.1, "mode": "policy",
                 "bundle": str(_MODELS / "symmetric_iter1540"),
                 "spawn": {"target": [off18, off18, -7000.0, 0.0, 0.0, 225.0, 250.0]}},
            ],
        }, own18, list(_QIC), None),
    ))

    # ── 34: 선회 최적고도 사격술 (turnalt_gunnery) — 2026-08-16 ──────────
    # 사용자 아이디어: "선회가 잘 되는 고도에서 싸우면 사격 기회가 많아 타격을
    # 더 배운다. 추락 안 하는 고도는 확실히 막고, 선회 좋은 고도에서 가르치자."
    #
    # 실측 선회율: 1,500 m 17.5 / 3,000 m 15.9 / 5,000 m 13.4 / 7,000 m 11.1 /
    # 8,167 m 9.6 deg/s. 저고도가 1.6 배 빠르다.
    #
    # 왜 스폰이 아니라 보상인가 (실측): 어느 고도에 스폰해도 200 초 안에
    # 2,000~2,300 m 를 올라간다(1,500 -> 3,241 / 7,000 -> 9,262). 기존 보상은
    # w_deck(1,300 ft 아래)과 w_high(6,000 m 위) 사이가 **완전히 평평**해서
    # 3,000 m 와 6,000 m 가 정책에게 똑같기 때문이다. 선호 봉우리가 필요하다.
    #
    # 두 축을 같이 건다:
    #   w_turnalt 40  3,000 m 를 봉우리로 하는 포텐셜(위아래 양쪽에서 당김,
    #                 텔레스코프라 파밍 불가, 지면으로 파고드는 것도 벌점)
    #   w_deck 12 / deck_ft 2,000  바닥을 **확실히** 막는다. 추락 하한이 1,000 ft
    #                 인데 램프를 2,000 ft 로 올려 여유를 둔다. 저고도 유도와
    #                 추락률은 직접 맞바꾸는 관계라(오늘 4->8 로 겨우 잡음)
    #                 선호를 켜는 만큼 바닥을 더 세게 막아야 한다.
    #   w_high 0     선호 항과 이중 계산되므로 끈다.
    #
    # 상대 풀·나머지 보상은 stage 33 과 동일 — 바뀐 것은 고도 축뿐이라
    # 프로브 차이를 이 축에 귀속시킬 수 있다.
    # ── [스폰 고도 실험 2026-08-16] stage 34 전용 스폰 ────────────────────
    # 원래 값 (되돌릴 때 이 표를 쓴다 — 고도만 -7000 으로 되돌리면 된다):
    #   ownship      [0, 0, **-7000.0**, 0, 0, 45, 280]
    #   풀[0] w0.9   [537.40,  537.40,  **-7000.0**, 0, 0, 225, 250]  예선 760 m
    #   풀[1] w1.1   [2155.26, 2155.26, **-7000.0**, 0, 0, 225, 250]  본선 3,048 m
    #   풀[2] w0.9   = 풀[0] 과 동일 (상대만 우리 챔피언)
    #   풀[3] w1.1   = 풀[1] 과 동일
    # 분리거리(537.40 / 2155.26)·기수(45/225)·속도(280/250)는 그대로 두고
    # **고도만** 바꾼다. 공용 _QIC / off18 은 다른 스테이지도 쓰므로 건드리지 않고
    # 여기서 전용 리스트를 새로 만든다.
    #
    # 왜: w_turnalt 150 만으로는 고도가 8,549 m 에서 꿈쩍도 안 했다(340 iter,
    # 챔피언 8,601 m 와 동일). 그 항의 에피소드 총합이 약 -26 점인데 딜은
    # 370~415 점 — 6% 라 6.5 km 를 끌어내릴 크기가 아니었다. 목표 고도에서
    # **시작하면** 그 항은 자리를 지키기만 하면 된다(사용자 제안).
    # 계획: 저고도에서 사격을 배운 뒤 스폰을 -7000 으로 되돌려 전이를 확인한다.
    #
    # ── [2026-08-16 갱신] 스폰 고도 -2000 -> **-4572** (대회 서버 기본값) ──
    # 근거는 추측이 아니라 대회 교전서버를 뜯어서 나온 것이다:
    #   * docs 에 시작 고도는 **없다**. Slide 15 명문 "정확한 수치(시작거리,
    #     고도, 속력 등)는 차후 공개". 2000~3000ft / 10000ft 는 기체 간 **거리**다.
    #   * 서버 `Update LOG.xlsx` V0.1: "시나리오 설정에서 전투기들의 초기 속도와
    #     초기 고도값을 수정하는 기능을 추가" → 고도는 버튼과 별개인 Alt(ft) 입력.
    #   * 그 Alt(ft) 기본값 = **15,000 ft = 4,572 m** (뷰어 UI 기본값과
    #     aircraft/f16/f16_init.xml 의 <altitude unit="FT">15000</altitude> 일치).
    # 즉 7,000 m 는 아무 근거가 없었고, -2000 은 서버 기본보다도 낮았다.
    # 4,572 m 는 현재 우리가 가진 유일한 "대회 서버가 실제로 쓰는 숫자"다.
    # 고도가 미공개인 이상 최종적으로는 도메인 랜덤화(600~5,000 m)로 가야 하지만,
    # 먼저 이 한 점에서 저고도 사격술이 유지되는지부터 본다.
    # 되돌릴 값: -2000.0 (저고도 실험) / -7000.0 (원래)
    _S34_ALT = -4572.0
    # self-play 스냅샷 경로. 반드시 '/snapshots/' 를 포함해야 sidecar 가
    # 이 항목들을 자가 슬롯으로 인식한다(snapshot_sidecar.py self_idx 판정).
    _SNAP34 = ("artifacts/curriculum/AeroFlyer/0817_timefix/"
               "stage_34_turnalt_gunnery/snapshots")
    # [MOD-SRVSPAWN] 2026-08-21 — 스폰을 **대회 교전서버 실측값**으로 맞춘다.
    #
    # 왜: 정책이 학습한 적 없는 조건에서 싸우고 있었다. 오늘 교전서버 패킷을
    # 직접 뜯어 잰 초기조건은 아래와 같다(2000ft 시나리오, BattleServer_V1.1).
    #     거리 608 m (=2,000 ft)  고도 4,572 m (=15,000 ft)
    #     속도 200 m/s (Speed 입력칸 기본값)
    #     자세 roll 0 / pitch -0.002 / yaw 90도 — 두 기체가 **서로 옆구리**(ATA 90도)
    #
    # 종전 학습은 ATA 0도(서로 정면 조준선 위) · 250~280 m/s 였다. 그 차이가
    # 얼마나 큰지 오프라인에서 성분별로 쟀다(같은 두 정책, 10판씩):
    #     정면 ATA0 + 250 m/s     44.3초  격추 5
    #     abreast 90 + 250 m/s    76.3초  격추 0   <- 배치가 격추를 없앤다
    #     abreast 90 + 200 m/s   119.6초  격추 0   <- 속도가 시간을 늘린다
    # 실서버 실측 140~200초 / 격추 0 과 일치한다.
    #
    # 소프트웨어는 전부 결백으로 확인됐다(관측 15채널 2,000스텝 최대차 0.000e+00,
    # time_norm 양쪽 동일, 물리 23초 비행 최대차 35.2 m, 틱 60 Hz, 행동 0.000e+00).
    # 그러므로 남은 것은 이 스폰 하나뿐이다.
    #
    # 되돌릴 값: OWN yaw 45.0 spd 280.0 / QIC yaw 225.0 spd 250.0
    # [2026-08-21 기하 수정] 첫 시도는 적기를 East(=아군 기수 방향) 축에 놓아
    # 결과가 **정면 겨눔(ATA 5도)** 이 됐다. 실측으로 잡았다.
    # line abreast 는 적이 아군 기수의 **옆(90도)** 에 있어야 한다:
    #   아군 yaw 90도 = East 를 봄  ->  적기는 North 축에 놓는다.
    _S34_SPD = 200.0                  # 서버 Speed 입력칸 기본값
    _S34_SEP = 608.0                  # 서버 실측 거리 (2,000 ft)
    # [2026-08-21 실측 정합] 교전서버 첫 프레임을 그대로 옮긴다.
    #   아군  N=608.5  E=6.1   yaw  +90도
    #   적기  N=0.1    E=-7.3  yaw  -90도
    #   -> 두 기수 차이 180도, 양쪽 ATA 91.3도 (line abreast)
    # 앞선 시도는 N 좌표를 서로 뒤바꿔 놓아 **적이 반대편**에 있었다.
    # ATA 는 대칭이라 같아 보이지만 좌/우가 뒤집혀, 정책이 한쪽 선회만 익히면
    # 실전에서 반대로 돈다.
    _S34_OWN = [_S34_SEP, 0.0, _S34_ALT, 0.0, 0.0,  90.0, _S34_SPD]
    _S34_QIC = [0.0,      0.0, _S34_ALT, 0.0, 0.0, -90.0, _S34_SPD]
    # 본선 원거리 조건은 같은 배치로 3,048 m 만 벌린다(아군을 그만큼 북쪽에).
    _S34_MIC = [0.0,      0.0, _S34_ALT, 0.0, 0.0, -90.0, _S34_SPD]

    def _s34_at(alt_d):
        """[MOD-LOWENEMY] 적기 스폰을 고도만 바꿔 복제한다(NED 라 alt_d 는 음수)."""
        q = list(_S34_QIC)
        q[2] = float(alt_d)
        return q

    def _s34_own_at(alt_d):
        """[MOD-SAMEALT 2026-08-22] 아군도 같은 고도로. 양쪽을 세트로 내린다.

        왜 고쳤나: 앞선 [MOD-LOWENEMY] 는 **적기 고도만** 낮췄다. 리플레이
        12 판 실측 결과 10 판이 1,500~3,200 m 어긋난 채 시작했다.
        대회 서버의 `Alt(ft)` 는 `Speed(m/s)` 와 같이 **입력칸 하나** —
        양쪽이 반드시 같은 고도에서 뜬다. 즉 학습 표본의 83% 가
        **실전에 존재하지 않는 상태**였다.
        사용자 지시("4572 랑 저고도 랜덤화 50:50")도 스폰 고도 자체를
        반반 하라는 뜻이었다.
        """
        o = list(_S34_OWN)
        o[2] = float(alt_d)
        return o

    S.append(CurriculumStage(
        index=34, name="turnalt_gunnery",
        description="Stage 33 plus an altitude PREFERENCE at the turn-optimal band (3 km) and a hard deck floor: fight where the jet turns fast so gunnery gets more chances to learn.",
        target_mode="fixed",
        # [2026-08-16] 6000 에서 상한에 걸려 멈췄다. 자가대전은 계속 오르는 중이라 올린다.
        episode_step_limit=int(2200 * 6 / STEP_RATIO), max_iterations=30000, checkpoint_interval=20,
        eval_kill_probe_interval=20,
        eval_kill_probe_eval=False,
        eval_kill_floor=0.05,
        reward_overrides={
                          # [2026-08-18 자율조정 #2] deck_ft 2000 -> 4000,
                          #                          w_deck 20 -> 6.
                          # 앞선 #1(w_deck 12->20)은 **처방이 틀렸다**. 리플레이
                          # 156 판을 뜯어보니 추락은 바닥에 붙어 싸우다 난 것이
                          # 아니다: 914 m 아래 체류가 판당 2~8 초뿐이고, 피치
                          # -22~-84 도 / 롤 -103~-150 도 / 하강률 -45~-102 m/s —
                          # 뒤집힌 나선으로 고도를 다 쓰고 회복 못 하는 것이다.
                          # 정상 전투는 저고도에 아예 안 간다(비추락 67 판의
                          # 최저고도 중앙 2,846 m, 609 m 아래 체류 **0/67 판**).
                          # 즉 deck_ft=2000 항은 **한 번도 발동하지 않는 죽은 항**
                          # 이었고, 크기를 올린 #1 이 효과가 없던 게 당연하다.
                          # 왜 종단 -1500 으로는 안 배우나: 하강이 60~90 초라
                          # gamma 0.995^900 = 0.011, 하강 시작 시점엔 -16 으로
                          # 보인다. LSTM 기억창은 3.2 초라 "언제부터 떨어졌는지"
                          # 도 모른다. 그래서 **하강 도중에** 걸리는 신호가 필요.
                          # 4000 ft(1,219 m)로 올려 발동을 바닥 6 초 전 ->
                          # 18 초 전으로 당겼다. 크기는 20 -> 6 으로 낮췄다.
                          #
                          # ===== [2026-08-18 되돌림] 위 #2 는 실패했다 =====
                          # 311 iteration 만에 **퇴화**시켰다. judge10 실측:
                          #     snap_9000 (조치 전)   챔프마진 -0.075
                          #     snap_9300 (조치 직전) 챔프마진 **+0.017**  <- 최고
                          #     snap_9601 (조치 후)   챔프마진 **-0.297**
                          # 정책은 조치 직전까지 개선 중이었고 조치 후 무너졌다.
                          # 원인: deck_ft 4000 이 발동 스텝을 2.3 -> 15.1 (6.5 배)
                          # 로 늘려 판당 -84 = **총보상의 24%** 를 자기 고도
                          # 유지에 쓰게 만들었다. 이 프로젝트가 이미 기록해둔
                          # 함정 (1) 을 그대로 다시 밟은 것 —
                          # **"자기상태에만 걸린 항은 교전을 대체한다"**
                          # (w_turnalt 해킹: 각자 고도에서 빙글빙글).
                          # 교훈: 추락률 같은 **안전 지표만 보고 보상을 키우면
                          # 안 된다. 반드시 고정 상대 판정으로 교전 영향을 같이
                          # 잰다.** 미러 지표(승률·딜·궤적)로는 안 보였다.
                          # => 조치 #1 상태(w_deck 20 / deck_ft 2000)로 복귀.
                          #    추락률 0.06 은 남지만 그건 실력 -0.3 보다 싸다.
                          "w_deck": _perstep(20.0), "deck_ft": 2000.0,
                          "crash_reward": -1500.0,
                          # [2026-08-17 사용자 지시] 격추당하는 것도 추락과 같은 -1500.
                          # 대회 규칙상 둘 다 똑같이 지는 것인데 학습에서만 10배
                          # 차이가 났다(추락 -1500 vs 피격추 -150). 저고도 회피를
                          # 만든 울타리가 피격추에는 없어 비대칭이었다.
                          "loss_reward": -1500.0,
                          # [2026-08-17 A안] 승리도 -1500 에 맞춰 **대칭**으로.
                          # 배경: loss -1500 을 넣을 당시엔 36/36 격추승이라
                          # 이 항이 발동한 적이 없었다. 그런데 [MOD-OPPRATE] 로
                          # 적기 6배 핸디캡을 없애자 절반을 지게 됐고, 승 +500 대
                          # 패 -1500 의 비대칭이 즉시 지배적이 됐다:
                          #   50:50 싸움 기대값 = 0.5(+400)+0.5(-1500) = -550
                          #   시간종료 무승부  = -40 +- 딜마진
                          # => **안 싸우는 게 500점 이득**. 실제로 240 iter 동안
                          # 딜 90->71, WEZ 22.3->20.7, 거리 1802->1873, 보상
                          # -81->-237 로 교전 회피가 계속 강화됐다.
                          # 대회에서 승과 패는 대등한 사건이므로 승을 올려 맞춘다
                          # (문제는 "패널티가 크다"가 아니라 "승리가 그에 못 미친다").
                          # win_time_bonus 200 은 유지 — 빠른 결착 유인은 남긴다.
                          "win_reward": 1500.0,
                          "draw_reward": -40.0,
                          "target_crash_reward": -40.0,
                          # 판정승이 양수가 되도록 (위 주석)
                          "draw_health_scale": 600.0,
                          # 딜 교환비를 승리 조건에 맞춘다 (2026-08-15 실측).
                          # 25 였을 때 w_damage 300 대비 **12:1** — "1 맞히면
                          # 12 맞아도 이득"이다. 대회 판정은 딜 **마진**이라
                          # 정반대다. 종료 보상(draw_health_scale 600)은 마진을
                          # 옳게 평가하지만 gamma 0.995 의 유효 지평이 200 스텝
                          # (20초)인데 에피소드는 1,900 스텝이라, 시작 시점
                          # 현재가치가 0.995^1900 = 0.00007 로 **보이지 않는다**.
                          # 실제로 정책을 움직이는 것은 조밀한 스텝 보상뿐이었다.
                          # 정책이 얼어 있는 동안엔 이 결함이 드러나지 않았다 —
                          # 옵티마이저를 푼 0815_unfreeze iter_0180 에서 피딜이
                          # 0.001 -> 0.067 (67배), 종합 8승8패 -> 5승16패.
                          "w_damage_taken": 0.0,   # [본선 2026-08-28] 300 -> 50 -> 0 (사용자 지시). 피격 페널티 제거 — 딜 보상만으로 선회전 학습
                          "w_range": _perstep(0.10),
                          # far 램프를 정책이 실제로 사는 거리로 옮긴다.
                          # 실측: stage 30 은 1,028 iteration 내내 평균 교전거리가
                          # 2,710~2,754 m 로 고정(변동 1.6%)이었다. 원인은
                          # start 900 / ramp 400 이라 2,720 m 에서 시그모이드가
                          # 완전 포화 — 에피소드당 -148 점을 내면서 2,720->2,000 m
                          # 로 좁혀도 기울기가 0.0000022/m 뿐이다(900 m 의 1/34).
                          # "멀다"는 상수 세금이었을 뿐 "가까워져라"가 아니었다.
                          # 접근 포텐셜(w_close_pot)은 텔레스코프라 **끝 거리**만
                          # 값을 친다 — 머지로 붙었다가 이탈하면 순합 0(실측 -0.74).
                          # 그래서 "붙어 있는 시간"에 값을 치는 항이 비어 있었다.
                          # [무교전 억제 2026-08-16] w_idle 대체. 램프를 세워 사거리 안에서는
                          # 거의 0, 멀리 도망가면 강하게 문다 (200 초 기준 총합):
                          #   900 m -86 / 1,500 m -289 / 2,000 m -560 / 3,000 m -857
                          # 폐기한 idle 0.6 이 -1,020 이었으니 같은 자릿수인데
                          # **관측 가능한 양(거리)** 만 쓴다.
                          # [2026-08-17] far 항의 **크기가 아니라 위치**를 옮긴다.
                          # 실측 순딜(HP/1000스텝): 153-300 +17.9 / 300-500 +16.9
                          # / 500-700 +12.5 / 700-914 +3.5 / 914 m 밖 **0**.
                          # 그런데 옛 설정(중심 1800, 램프 400)은 기울기의 87%가
                          # 무수입 구간(914~2000 m)에 있었다: 300->914 m 로 붙어도
                          # 0.034/스텝뿐이라 근접 유인이 사실상 없었다. 정책이
                          # 1,990 m 에 수렴한 것은 그 설계의 정답이었다.
                          # 중심 700 / 램프 250 으로 옮기면 300->914 기울기가
                          # 0.240/스텝(7배)이 되고, 2000 m 에피소드 총량은
                          # 118 -> 188 점(딜 500 대비 38%, 기준 0.2~0.4 안쪽).
                          # 크기(w_far 0.45)는 그대로라 신호 침몰 위험이 없다.
                          # [2026-08-17 2차] 0.45 -> 0.7. 모양을 옮긴 뒤 350 iteration 을 봤는데
                          # 거리가 1,961 -> 1,974 m 로 안 내려왔다(기준 1,950 미달).
                          # 신호 크기 쪽 근거도 있다: 에피소드 far 총량이 -38.8 로
                          # 딜 503 의 7.7% 뿐 — 프로젝트 기준선 20~40% 보다 한참 낮다.
                          # 딜은 503(>480) 이라 되돌릴 조건은 아니다.
                          # [2026-08-17 3차] 0.7 -> **0.45 되돌림**. 올린 실험은 실패했다.
                          # 40 iter 단위 추이: 거리 1,917 -> 1,980 -> 2,006 ->
                          # 2,024 -> 2,044 로 **단조 증가**. 줄이려고 올린 항이
                          # 정확히 반대로 작동했다. 추락률도 0.015 -> 0.06 으로
                          # 올라 180 iter 중 80개가 스테이지 게이트(0.05)를 넘었고
                          # 보상은 1,009 -> 858 로 15% 내렸다.
                          # 결론: **far 항으로는 교전거리를 못 줄인다.** 모양 변경
                          # (1800->700)도 중립이었고 크기 상향은 해로웠다. 거리는
                          # 보상이 아니라 스폰/조건이 정한다는 기존 실측과 일치.
                          # 모양(700/250)은 유지 — 0.45 에서는 추락 0.0 으로 안정적이었다.
                          # [2026-08-18 되돌림] 중심 700 -> **1800 복귀**, 램프 250 -> 400.
                          # 700 으로 옮긴 근거였던 "153~300 m 교환비 23:1" 측정이
                          # **6배 느린 적기를 상대로 낸 것**이었다([MOD-OPPRATE] 이전).
                          # 느린 상대에겐 300 m 가 안전했지만 대등한 상대에게는
                          # 상호 위험 구간이다. 무효가 된 데이터로 정한 값이라 되돌린다.
                          # 되돌리는 근거(고정챔프 판정, 하네스 수정 후라 유효):
                          #   snap_7400 vs ladder_iter5220  마진 -0.200 / 격추 374
                          #   snap_8540 vs ladder_iter5220  마진 -0.203 / 격추 506
                          #   과거 자신(-300) 에게도 -0.080, -0.250 로 짐 = 퇴화 경보
                          # 그 사이 거리 -217/1000iter, 추락 0.01->0.04, 딜 -37/1000.
                          "w_far": _perstep(0.45), "far_start_m": 1800.0,
                          "far_ramp_m": 400.0,
                          # 시간 램프 (사용자 요구 "시간에 따라 붙게"). 경과 시간은
                          # 관측(time_norm)에 있으므로 MDP 유효 — 폐기한 w_idle 과
                          # 다른 점이 이것이다. 20 초까지 무료(3 km 접근 + 첫 반전),
                          # 80 초에 최대. 대회 데미지 계수가 100 초 뒤 0.3, 150 초 뒤
                          # 0.1 이라 **전반에 붙어야** 이기는 구조와도 맞는다.
                          "far_time_start_s": 20.0, "far_time_full_s": 80.0,
                          "w_perch": 0.0,
                          # 넓은 원뿔 각도항은 1/3 로 — 데미지 불가 구간 지불을 줄인다
                          "w_wez": _perstep(0.06), "wez_cone_deg": 15.0,
                          "wez_best_m": 260.0,
                          "w_snap": _perstep(0.5), "snap_ata_deg": 3.0,
                          # 신설 주력 2항. 가중치는 **std 기준으로 실측해서**
                          # 잡았다(signal_scale.py, 챔피언 8판). 처음 잡은
                          # w_nmd 0.20 / w_cpa 0.10 은 에피소드 합이 0.68 / 2.11,
                          # std 가 0.24 / 0.82 로 **딜 std(32.3)의 0.7% / 3%** 라
                          # 사실상 보이지 않았다. 학습에 영향을 주는 것은 평균이
                          # 아니라 std 다 — 평균은 상수처럼 작용해 어드밴티지에서
                          # 상쇄된다(2026-08-14 신호 침몰 진단과 같은 계산).
                          # 40배/15배 올려 std 를 딜의 0.3 수준에 둔다. 딜을
                          # 밀어내지 않으면서 존재하는 크기.
                          # 파밍 안전: nmd 최대치는 NMD~0 을 밴드 안에서 유지할
                          # 때인데 그 상태가 곧 데미지라 유지하면 적이 1.6초에
                          # 죽는다 — 항 자체가 격추로 자동 종료된다.
                          "w_nmd": _perstep(8.0), "nmd_half_m": 10.0,
                          "w_cpa": _perstep(1.5), "cpa_half_m": 40.0,
                          "cpa_horizon_s": 8.0,
                          "w_close_pot": 15.0,
                          "w_aim": _perstep(0.16),
                          "max_engage_time": 200.0, "aim_range_gate_m": 4500.0,
                          # 강하 선회 해금 — 교사가 선회 중 628 m 상승했다
                          "w_ceil": _perstep(1.0), "ceil_ft": 45000.0,
                          "ceil_ramp_ft": 2000.0,
                          # [stage 34] 고도 **선호** 로 교체. w_high 는 끈다 —
                          # 6,000 m 위에서 이중으로 물어 균형이 깨진다.
                          "w_high": 0.0,
                          # 가중치·span 은 signal_scale.py 로 실측해서 잡았다.
                          # 첫 시도 w40/span6000 은 std 비 0.1 로 너무 약했다 —
                          # 현 정책이 8,600 m 에 사는데 span 6,000 이면
                          # |8600-3000|/6000 = 0.93 으로 **거의 포화**라 기울기가
                          # 없다(옛 w_alt 가 6,300 m 클립으로 무용지물이던 것과
                          # 같은 실수). span 을 9,000 으로 넓혀 12,000 m 까지
                          # 포화를 없애고 가중치를 올린다.
                          # 봉우리 2,000 m (2026-08-16 사용자 지시). 선회 17.0 deg/s 로 3,000 m
                          # (15.9)보다 빠르면서, 반전당 고도손실이 221 m 라
                          # 추락 하한 305 m 까지 여유가 7.7 회 남는다
                          # (3,000 m 는 손실 314 m 로 8.6 회 — 큰 차이 없음).
                          # 더 낮추면 선회는 빨라지지만 여유 회수가 준다:
                          # 1,200 m 는 18.0 deg/s 인데 여유 5.4 회뿐이다.
                          # [보상해킹으로 비활성화 2026-08-16] 150 -> 0.
                          # 관측(사용자, 리플레이): 적기가 안 내려오고 두 기체가
                          # **각자 고도에서 빙글빙글** 돈다. 지표도 같은 얘기였다 —
                          # WEZ 체류 30 -> 20, 딜 400 -> 350 으로 **교전이 줄었다**.
                          # 원인: 이 항은 **적과 무관하게** 만족된다. 2,000 m 유지는
                          # 혼자서도 되는데 적기 추격은 어려우니 싼 쪽을 고른다.
                          # 교훈: 포텐셜을 상대와 무관한 자기 상태에 걸면 교전을
                          # 대체하는 값싼 목표가 된다. 되살리려면 상대와의 관계로
                          # 게이트해야 하고(예: 적이 일정 거리 안일 때만), 그 형태는
                          # 새 착취를 만들 수 있으므로 다시 실측 검증이 필요하다.
                          # 교전거리 -29% 는 **스폰**(-2,000 m)이 낸 것이고 이 항이
                          # 아니다 — 스폰은 유지한다.
                          "w_turnalt": 150.0, "turnalt_pref_m": 2000.0,
                          # [무교전 벌점 2026-08-16 사용자 지시] 고도 선호를
                          # 끄는 대신 **안 쫓는 것을 비싸게** 만들어 해킹을 막는다.
                          # 1,500 m 안에 들어가면 리셋, 15 초 유예 뒤 30 초에 걸쳐
                          # 최대까지. 크기: 스텝당 0.2 x 최대 1,550 스텝 = 약 -310
                          # (딜 370~415 와 같은 자릿수). 3.0 으로 잡으면 -4,650 이라
                          # 다른 신호를 전부 덮는다 — 실측으로 잡았다.
                          # [MDP 위반으로 폐기 2026-08-16] w_idle 은 "마지막 교전 이후
                          # 경과 시간"에 의존하는데 그 값은 **관측에 없다**.
                          # obs16 에는 time_norm(에피소드 경과)만 있고 idle 타이머는
                          # 없으며, LSTM 기억 창이 max_seq_len 32 @10Hz = **3.2 초**라
                          # 45 초짜리 타이머를 복원할 수 없다. 정책이 자기가 왜 벌받는지
                          # 알 수 없는 POMDP 가 된다.
                          # 같은 목적(안 쫓으면 손해)을 **현재 상태만으로** 하는 항이
                          # 이미 있다 -> w_far. 거리는 관측 1 번 값이라 MDP 안이다.
                          "w_idle": 0.0,
                          # [추락 벌점 강화] -250 -> -1500. 저고도 스폰 + 무교전
                          # 벌점은 둘 다 공격성을 올리는 쪽이라 지면 위험이 커진다.
                          # 승리가 +300~500 인데 추락이 -1500 이면 어떤 결과보다도
                          # 확실히 나쁘다(패배 -150 의 10 배).
                          "turnalt_span_m": 9000.0,
                          "w_overspeed": _perstep(0.8), "overspeed_ref_mps": 190.0,
                          "overspeed_gate_m": 1200.0,
                          "overspeed_turn_ata_deg": 30.0},
        randomization=_rand(100.0, 10.0, 5.0),
        advance_conditions={"win_rate_min": 1.01, "ep_wez_steps_min": 8.0,
                            "crash_rate_max": 0.05},
        advance_window=10,
        env_overrides=_spawn({
            "step_ratio": STEP_RATIO,
            "max_engage_time": 200.0,
            "wez_phases": {"enabled": True, "phases": [
                {"after_s": 0.0,   "angle_deg": 2.0, "max_range_m": 914.4,
                 "damage_scale": 1.0},
                {"after_s": 100.0, "angle_deg": 4.0, "max_range_m": 1066.8,
                 "damage_scale": 0.3},
                {"after_s": 150.0, "angle_deg": 6.0, "max_range_m": 1219.2,
                 "damage_scale": 0.1},
            ]},
            "live_tune_file": (str(ROOT) + "/artifacts/curriculum/AeroFlyer/"
                               "0817_timefix/live_tune.json"),
            "target_teacher": {"name": "ace", "params": {"speed_mps": FOE_SPEED}},
            # ── [2026-08-16 사용자 지시] 순수 self-play. 고정 상대 전면 제거 ──
            # "38차원 RL 은 우리가 안 쓰니까 버려라. 이제는 진짜 self play 로
            #  우리 현 정책이랑 싸우게, 고정 없이."
            #
            # 뺀 것: league250_elo1667 (2슬롯). 파일은 **지우지 않았다** —
            #   구 워크스페이스 artifacts\league\ 에 그대로 있고, 판정용으로
            #   계속 쓸 수 있다. 뺀 이유는 두 가지고 둘 다 실측이다:
            #     1) 관측 38차원이라 우리(16차원)와 보는 정보가 다르다.
            #        22개를 더 보는 상대라 "대등한 self-play" 가 아니다.
            #     2) 이미 천장이다 — 판정에서 32-0 으로 이겨서, 이 상대로는
            #        세대 간 향상을 더 이상 잴 수 없다(리그 기록).
            #   다른 스테이지(29/30/33)의 elo1667 참조는 건드리지 않았다.
            #   과거 실행을 재현 불가로 만들 이유가 없다.
            #
            # 넣은 것: 자가 스냅샷 4슬롯. sidecar 가 killfloor_probe(20 iter 마다
            #   갱신되는 현재 가중치)를 snapshots/snap_<iter>/ 로 복사하고
            #   live_tune.json 으로 이 풀을 통째로 갈아끼운다. 그래서 상대는
            #   **20 iteration 마다 현재 정책으로 갱신**된다. 동결이 아니다.
            #   슬롯 순서 = sidecar 의 picks 순서(최신 -> 이전 -> 이전2 -> 이전3).
            #   probe 간격 20 이므로 가장 오래된 슬롯도 60 iteration 전 자신이다.
            #
            # 가중치·초기조건은 직전과 **완전히 동일**하게 뒀다(0.9/1.1/0.9/1.1,
            # 예선 45% / 본선 55%). 상대 정체 하나만 바뀌게 해서 프로브 차이를
            # 여기에 귀속시킬 수 있게 한다.
            #
            # 알려진 위험 (반드시 대비할 것): 미러 지표는 절대 실력과 역상관인
            # 사례가 실측됐다(미러 딜 65.9 였던 정책이 48판에서 8승 14패).
            # 그래서 **판정은 학습 밖에서** 고정 상대(ladder_iter5220 등)로
            # 주기적으로 해야 한다. 학습 풀에 고정 상대가 없는 것과,
            # 판정에 고정 상대를 쓰는 것은 서로 모순되지 않는다.
            # [MOD-HPSCALE] 데미지 1/10 = HP 10배 효과. 장기전을 배우게 한다.
            # 실서버는 160~200초 딜 마진 판정인데 학습은 29초 동귀어진으로 끝나
            # 정책이 장기전을 겪은 적이 없다. 보상 w_damage/w_damage_taken 은
            # live_tune 에서 10배로 함께 올린다(기울기 크기 유지).
            #
            # 제출 시 되돌릴 필요 **없다**. 이 값은 학습 env 안에만 있고,
            # 대회 경로(my_submission.py -> 정책 -> CMD -> 대회 서버)는
            # single_agent_env.py 를 아예 실행하지 않는다. 데미지는 대회 서버가
            # 자기 규칙으로 계산한다.
            # 그리고 관측에 HP 가 없으므로 정책은 데미지 크기를 볼 수 없다.
            # 1/10 세계에서 배우는 것은 "조준을 오래 유지한다"이고, 대회(1배)에서는
            # 같은 행동이 10배 빨리 격추로 이어진다 -- 손해가 아니라 이득이다.
            # [2026-08-22] 사용자 지시로 1.0(대회 동일) 복귀. 0.1(HP 10배)에서
            # 실측된 것: 리플레이 30 판 격추 **0회**, 승부가 "누가 먼저 추락하나"로
            # 결정됨. 조준 한 번의 값이 1/10 이라 붙는 이득이 사라지고 정책이
            # 회피를 골랐다 -- 속도 148 m/s(적기 163), 고도 5,054 m(스폰보다 480 m
            # 위), 딜마진 -0.099. 1.0 이면 1.56 초 조준으로 격추라 붙는 값이 살아난다.
            "wez_damage_scale": 1.0,
            "target_pool": [
                # [MOD-LOWENEMY] 2026-08-22 — 4,572 m 와 저고도를 **50:50**,
                # 저고도 쪽은 1,400~3,000 m 로 흩뿌린다(사용자 지시).
                #
                # 왜: 사용자가 실서버에서 "상대를 잡으려고 빙글빙글 돌다가 같이
                # 추락하는" 것을 목격했다. 실측도 같다 — 추락 판의 마지막 8 초는
                # |롤|>90 & 기수 아래가 51.9%(비추락 14.8%), 뒤집힌 채 쫓아
                # 내려가는 나선이다. 그리고 그 나선은 **긴 판에서만** 나온다:
                #     38 초 2.8% / 58 초 4.3% / 166 초 32.3%  (초당 0.07 -> 0.20%)
                # HP 1 배로 되돌리자 판이 38 초가 되어 나선이 학습에서 사라졌다 —
                # 지면까지 4,000 m 가 남아 40 초 안에 닿지 못하기 때문이다.
                #
                # 해법을 보상에서 찾지 않는다. 오늘 비포텐셜 벌점 4 개(crash -5000,
                # w_deck 600, overspeed, sink)와 포텐셜 w_alt 까지 5 개가 전부
                # 실패했고, w_alt 는 오히려 고도 5,054 m(스폰보다 480 m 위)·
                # 속도 148 m/s(적기 163)로 **교전 자체를 대체**했다.
                # 기록된 실측: "상태 분포는 보상보다 **스폰**이 바꾼다"
                # (보상으로 340 iter 에 52 m, 스폰으로 즉시 -29%).
                #
                # 그래서 위험 상태에 **도달하기를 기다리는** 대신 **거기서 시작**한다.
                # 적기가 낮으면 첫 순간부터 "따라 내려갈 것인가"를 결정해야 하고,
                # 따라가면 지면이 곧 아래다 — 40 초 판에서도 나선이 나타난다.
                # 사용자가 말한 "적기가 내려갔을 때 안 따라가는 법"이 이 결정이다.
                #
                # 가중치: 고고도 1.4x2 = 2.8, 저고도 0.7x4 = 2.8 (정확히 50:50).
                # self(스냅샷) 2.8 = 고정 상대 2.8 로 계열도 반반.
                # 저고도를 4 개로 쪼갠 것은 한 고도에 과적합하지 않게 하기 위함이다.
                #
                # 경로에 '/snapshots/' 가 있는 항목만 sidecar 가 self 로 보고
                # 갱신한다. 고정 상대는 그대로 보존된다(snapshot_sidecar.py:114,162).
                {"weight": 1.4, "mode": "policy",
                 "bundle": f"{_SNAP34}/snap_0000",
                 # [MOD-SAMEALT] 반경 0 스캐터를 **6슬롯 전부** 켠다.
                 # env 는 randomization 이 켜진 판에서만
                 # add_random_init_position("ownship") 을 부르고(:362),
                 # spawn["ownship"] 을 읽는 곳은 그 함수 안뿐이다(:1766).
                 # 안 켜면 아군 고도가 이전 판 값 그대로 남아 샌다.
                 # 반경 0 이라 기하는 안 흔들린다 — 호출만 일어난다.
                 "randomization": {"enabled": True, "radius": 100.0,
                                   "r_roll": 10.0, "r_pitch": 5.0,
                                   "r_heading": 10.0},
                 "spawn": {"target": list(_S34_QIC)}},
                {"weight": 0.7, "mode": "policy",
                 "bundle": f"{_SNAP34}/snap_0000",
                 "randomization": {"enabled": True, "radius": 100.0,
                                   "r_roll": 10.0, "r_pitch": 5.0,
                                   "r_heading": 10.0},
                 "spawn": {"ownship": _s34_own_at(-1400.0),
                           "target": _s34_at(-1400.0)}},
                {"weight": 0.7, "mode": "policy",
                 "bundle": f"{_SNAP34}/snap_0000",
                 "randomization": {"enabled": True, "radius": 100.0,
                                   "r_roll": 10.0, "r_pitch": 5.0,
                                   "r_heading": 10.0},
                 "spawn": {"ownship": _s34_own_at(-2600.0),
                           "target": _s34_at(-2600.0)}},
                {"weight": 1.4, "mode": "policy",
                 "bundle": str(_MODELS / "sub_cand_peak3100"),
                 "randomization": {"enabled": True, "radius": 100.0,
                                   "r_roll": 10.0, "r_pitch": 5.0,
                                   "r_heading": 10.0},
                 "spawn": {"target": list(_S34_QIC)}},
                {"weight": 0.7, "mode": "policy",
                 "bundle": str(_MODELS / "sub_cand_snap13280"),
                 "randomization": {"enabled": True, "radius": 100.0,
                                   "r_roll": 10.0, "r_pitch": 5.0,
                                   "r_heading": 10.0},
                 "spawn": {"ownship": _s34_own_at(-2000.0),
                           "target": _s34_at(-2000.0)}},
                {"weight": 0.7, "mode": "policy",
                 "bundle": str(_MODELS / "sub_cand_snap13280"),
                 "randomization": {"enabled": True, "radius": 100.0,
                                   "r_roll": 10.0, "r_pitch": 5.0,
                                   "r_heading": 10.0},
                 "spawn": {"ownship": _s34_own_at(-3000.0),
                           "target": _s34_at(-3000.0)}},
            ],
        }, _S34_OWN, list(_S34_QIC), None),
    ))

    # ── [MOD-LADDER] 2026-08-22 고정 상대 사다리 (stage 35/36/37) ──────────
    #
    # 왜: self-play 미러 승률은 절대 실력과 역상관인 사례가 실측됐다. 그리고
    # 실서버에서 우리 정책의 나쁜 습관이 드러났다 — 계속 상승하며 스로틀을
    # 아이들(0.049)로 두어 146 m/s 까지 죽는다. 미러에서는 상대도 같이
    # 올라가니 상쇄되어 안 보이고, 이종 상대에게 붙이자 바로 나왔다.
    #
    # 그래서 상대를 **고정**한다. 고정 상대 승률은 절대 지표이고, 상승 습관은
    # 상승하지 않는 상대에게 지면 저절로 깎인다. 기록: "상태 분포는 보상보다
    # 상대·스폰이 바꾼다".
    #
    # 사다리: snap_12241 -> peak3100 -> ladder5220 (약한 순 -> 강한 순)
    # 각 단계 승률 80% 를 5 iteration(약 225 판) 평균으로 넘으면 다음 단계.
    #
    # 설계상 주의 세 가지:
    #  1) sidecar 를 띄우지 않는다. 상대가 고정이어야 승률이 지표가 된다.
    #  2) live_tune 은 **보상 전용 파일**을 따로 쓴다. stage 34 의 것을 그대로
    #     쓰면 그 안의 target_pool 이 우리 고정 상대를 덮어쓴다(실측된 사고).
    #  3) stage 34 의 보상 중 13 개가 live_tune 에만 있었다. 그대로 구워
    #     넣지 않으면 crash_reward 가 -1700 -> -1500 으로 조용히 되돌아간다.
    import dataclasses as _dc
    import json as _json

    _s34 = S[-1]
    assert _s34.index == 34, "사다리는 stage 34 뒤에 붙어야 한다"

    # stage 34 의 **실행 시점 보상**(스테이지 + live_tune 병합)을 그대로 굽는다
    _lt_src = _s34.env_overrides.get("live_tune_file")
    _reward_now = dict(_s34.reward_overrides or {})
    if _lt_src and Path(_lt_src).is_file():
        _reward_now.update(_json.load(open(_lt_src, encoding="utf-8")).get("reward", {}))

    # 보상만 담은 사다리 전용 live_tune (target_pool 없음 -> 풀이 덮일 수 없다)
    _LADDER_LT = ROOT / "artifacts" / "curriculum" / "AeroFlyer" / "ladder" / "live_tune.json"
    _LADDER_LT.parent.mkdir(parents=True, exist_ok=True)
    if not _LADDER_LT.is_file():
        _json.dump({"reward": _reward_now}, open(_LADDER_LT, "w", encoding="utf-8"),
                   ensure_ascii=False, indent=2)

    # [2026-08-22] 사다리를 **순환**시킨다(사용자 지시: "까먹지 않을 때까지").
    #
    # 왜: 1차 완주 직후 1단계로 되돌아가 보니 승률이 86.3% -> 71% 로 떨어져
    # 있었고, 그 상대와 다시 싸우는 중에도 0.71 -> 0.30 으로 계속 내려갔다.
    # 즉 3단계를 배우면서 1단계를 잊었다. 한 번에 상대 하나만 보는 순차
    # 사다리의 구조적 결과다.
    #
    # 순환시키면 잊은 상대가 곧 다시 표본에 들어오므로, 바퀴를 돌수록
    # 세 상대를 동시에 만족하는 지점으로 수렴한다. 이미 잘하는 바퀴는
    # 5 iteration 만에 통과하므로(min_iterations=0) 비용도 작다.
    #
    # 바퀴 수 5 = 15 스테이지(35~49). 다 통과하면 커리큘럼이 끝난다.
    _LADDER_CYCLES = 5
    _DRILL_ITERS = 300       # 추격 드릴 칸: 바퀴당 노출 iteration
    _FLEE_ITERS = 300        # 꼬리 추격 칸: 바퀴당 이만큼 돌고 통과
                             # 100 -> 300: 가장 못하는 기술이라 노출을 늘렸다
    # 4단 recv9980: 다른 기계에서 받은 별개 계열(iter 9980). 우리 후보와
    # 실서버에서 198초 100:100 무승부를 냈다 -- 난이도가 꼭대기에 맞고,
    # 우리 계보 밖이라 "계열 교착"을 실력으로 오독하는 것을 막아 준다.
    # [MOD-TAILCHASE 2026-08-23] 5단 = **도망가는 상대**(사용자 지시).
    #
    # 왜: 사다리 상대 넷은 전부 정면에서 맞붙는 정책이라, 꼬리를 물고 쫓는
    # 상황을 학습에서 겪은 적이 없다. 실서버 예선에서 상대가 이탈을 택하면
    # 우리는 그 상황을 처음 보게 된다.
    #
    # defensive 교사는 위협 원뿔(40도) 안에 들어오면 최대속도로 뱅크 70도
    # 브레이크를 건다(teachers.py:283) -- 쫓아야만 잡히는 상대다.
    # 스폰도 꼬리 추격으로 잡는다: 같은 방향, 적기가 900 m 앞.
    # [2026-08-23] 꼬리 추격을 **1단으로** 올린다(사용자 지시).
    # "뒤를 잡아도 안 쏜다" -- 위치는 잡는데 사격으로 못 바꾼다.
    # 가장 못하는 것을 맨 앞에 두고 노출도 늘린다.
    # [MOD-LADDER 2026-08-23] 카톡으로 받은 외부 계열 2개를 6·7단으로 추가.
    #   recv_aimcur_0823   stage aim_acquire_full      (조준 획득 커리큘럼)
    #   recv_scrim_exp025  stage quali_throttle_entry85 (예선 스로틀/진입)
    # 둘 다 우리와 동일 계약 확인: obs 16 / act 4 / lstm cell 128 / seq 32 /
    # observation_mode=student16 / step_ratio=6. 계약이 다르면 넣으면 안 된다.
    #
    # 왜 뒤에 붙이나: 우리 계보 밖 상대라 recv_snap9980 과 같은 역할이다.
    # 같은 계열만 상대하면 "계열 교착"을 실력으로 오독한다(80판 60승 0패 전례).
    # 상대 계열이 셋(우리/9980/이번 둘)이 되면 그 오독이 훨씬 어려워진다.
    # [MOD-TAILCHASE 제거 2026-08-23] 도망 칸을 사다리에서 뺀다(사용자 지시:
    # "안 배워지면 빼줘, 도망을 너무 잘 가면").
    #
    # 실측 근거 — 네 번 시도해서 네 번 다 승률 0.000 이었다:
    #   0823_chase / chase2 / chase3  (speed_cmd 320)  74 / 76 / 87 iteration
    #   0823_recv7b stage 42          (speed_cmd 240) 178 iteration
    # 속도를 320 -> 240 으로 낮춰도 결과가 같았다. 즉 원인이 속도가 아니다.
    #
    # 리플레이 3판 실측(stage_42_iter_000300):
    #   상대가 heading_cmd 90 / altitude_cmd -4572 를 **하나도 안 지킨다**.
    #   yaw 가 360도를 돌고 고도가 +2,400~2,600 m 올라간다. 직진 도망자가 아니라
    #   제멋대로 나선 상승하는 기체다. 우리는 그걸 따라 같이 올라간다.
    #   거리 2,237 m 로 시작해 최소가 2,237 m — 한 번도 안 가까워졌다.
    #   우리 속도 평균 289 / 최대 348 m/s (전속 471). 적 평균 319.
    #   200초 중 78%를 상대보다 느리게 날았다.
    # WEZ 체류가 평균 0.5 스텝(=0.05초)이라 조준을 배울 표본 자체가 없었다.
    #
    # 되살리려면 autopilot 이 명령을 따르게 만드는 것이 먼저다.
    # 그 전까지는 이 칸이 iteration 만 태운다(4,000 iter = 약 15시간).
    # [MOD-DRILL 2026-08-23] 추격 드릴을 **1단**으로 (사용자 지시).
    # 좌선회 / 우선회 / 직진 세 표적을 한 풀에 넣고 전부 최저 안정 속도로 난다.
    # [2026-08-23] 드릴을 스로틀 단계로 쌓는다(사용자 지시):
    # "30초 달성하면 상대 스로틀 0.4 로 올려서 다시".
    # 표적이 빨라질수록 우리가 더 밀어야 30초 안에 잡는다 -> 전속을 배운다.
    # [2026-08-23] 사이클 재구성(사용자 지시):
    #   "RL 6종 사이사이에 드릴 통과를 하나씩, 스로틀별로"
    # 즉 드릴과 RL 을 **하나씩 번갈아** 놓고, 드릴은 갈 때마다 스로틀이 오른다.
    #
    #   드릴 0.3 -> RL 12241 -> 드릴 0.4 -> RL 3100 -> 드릴 0.5 -> RL 5220
    #   -> 드릴 0.6 -> RL r9980 -> 드릴 0.7 -> RL aimcur -> 드릴 0.8 -> RL scrim
    #
    # 한 바퀴 = 12칸. 3바퀴 = 36칸 (index 35~70).
    # 왜 번갈아 놓나: 드릴만 연달아 태우면 50초 판·교사 상대에 과적합하고
    # time_norm 후반(200초 판)을 못 본다. 사이에 RL 을 끼우면 드릴에서 얻은
    # 추격·스로틀 습관을 곧바로 200초 실전 분포에서 검증한다.
    # [MOD-LADDER 2026-08-23] 사다리 상대 스폰 속도 200 -> 150 (사용자 지시).
    # 아군은 200 그대로 -- 초기 접근 우위 +50 m/s 를 준다.
    # **사다리 칸에만** 적용한다. _S34_QIC 를 직접 고치면 self-play 인 34단까지
    # 같이 바뀌므로 사본을 만들어 쓴다.
    # 주의: 실서버는 Speed 입력칸이 하나라 양쪽 200 이다. 이건 학습용 난이도
    # 조절이지 실전 조건이 아니다 -- 판정에는 절대 쓰지 말 것.
    # [2026-08-23] 150 -> 200 으로 되돌린다(사용자 지시).
    # 150 은 학습 난이도를 낮추려고 넣었던 값인데, 실서버는 Speed 입력칸이
    # **하나**라 양쪽이 항상 같은 속도(200)다. 아군만 +50 m/s 빠른 조건에서
    # 얻은 승률은 실전보다 후하게 나온다 -- stage 36 을 0.784 로 통과했지만
    # 그건 이 할인 포함이다. 판정뿐 아니라 학습도 실전 조건으로 맞춘다.
    _LADDER_TGT_SPD = 200.0
    _LADDER_TGT = list(_S34_QIC)
    _LADDER_TGT[6] = _LADDER_TGT_SPD

    # [2026-08-24] 0.7 / 0.8 제거(사용자 지시: "못 따라갈 듯").
    # 근거: t50(0.5) 에서 이미 사거리 도달에만 39~41초가 걸린다.
    #   평균 접근속도 23.9~37.4 m/s — 표적이 뱅크 45도로 도니 직선 속도차
    #   (우리 390 대 적 270)가 접근으로 거의 안 바뀐다.
    #   표적이 더 빨라지면 50초 판 안에 사거리에 닿지도 못한다.
    # [2026-08-24] 0.6 도 제거(사용자 지시). 게이트가 **판 상한과 같아 무의미**했다.
    #   0.6 게이트 50초 = 판 상한 50초 -> ep_len_mean 이 500 스텝을 못 넘으므로
    #   조건이 항상 참. 실측 3회 통과 승률 0.456 / 0.113 / 0.350 —
    #   53단은 9판 중 8판을 못 잡고도 통과했다. 거름망 역할이 0 이다.
    #   물리적으로도 무리다: 0.5 에서 이미 사거리 도달에 39~41초가 걸린다.
    _DRILL_TIERS = (30, 40, 50)
    _RL_RUNGS = [("ladder_12241",  "sub_cand_snap12241"),
                 ("ladder_3100",   "sub_cand_peak3100"),
                 ("ladder_5220",   "sub_cand_ladder5220"),
                 ("ladder_r9980",  "recv_snap9980"),
                 ("ladder_aimcur", "recv_aimcur_0823"),
                 ("ladder_scrim",  "recv_scrim_exp025")]
    _LADDER_CYCLES = 3
    _RUNGS = []
    _idx = 35
    for _c in range(_LADDER_CYCLES):
        # 드릴 4종 · RL 6종이라 zip 이면 RL 둘이 잘린다. 단계를 순환시켜 짝짓는다.
        for _j, (_n, _b) in enumerate(_RL_RUNGS):
            _t = _DRILL_TIERS[_j % len(_DRILL_TIERS)]
            _RUNGS.append((_idx, "ladder_drill%d_c%d" % (_t, _c + 1), "drill:%d" % _t))
            _idx += 1
            _RUNGS.append((_idx, "%s_c%d" % (_n, _c + 1), _b))
            _idx += 1

    # 꼬리 추격 스폰: 아군 뒤, 적기 900 m 앞, 같은 방향(yaw 동일)
    _TAIL_OWN = [_S34_SEP, 0.0, _S34_ALT, 0.0, 0.0, 90.0, _S34_SPD]
    # [2026-08-23] 2,300 m -- **사거리 밖**에서 시작한다(사용자 지시).
    #
    # 배워야 하는 것은 사격이 아니라 **좁히기**다. 실측으로 확정됐다:
    #   격추한 판  948/880/975 m -> 832/768/805  (우리가 +12~15 m/s 빠름)
    #   만료된 판  928/912 m     -> 1266/1321    (우리가 -15 m/s 느림)
    #   스로틀 평균 0.795 로 389 m/s. 전속이면 471 인데 적기는 404 로 달아난다.
    # 즉 조준(ATA 5도 이하)은 되는데 전속을 안 넣어 못 따라잡는다.
    #
    # 500 m 로 넣으면 사거리 안이라 그냥 쏘고 끝나 좁히기를 안 배운다.
    # 2,300 m(WEZ 상한 914.4 m 의 2.5배)에서 시작하면 **붙지 않으면
    # 아무 일도 일어나지 않으므로** 추력을 넣는 것 말고는 길이 없다.
    _TAIL_TGT = [_S34_SEP, 2300.0, _S34_ALT, 0.0, 0.0, 90.0, _S34_SPD]

    for _i, (_idx, _nm, _bundle) in enumerate(_RUNGS):
        _eo = dict(_s34.env_overrides)
        _eo["live_tune_file"] = str(_LADDER_LT)
        if isinstance(_bundle, str) and _bundle.startswith("drill:"):
            _tier = int(_bundle.split(":", 1)[1])
            # ── [MOD-DRILL 2026-08-23] 추격 드릴 ────────────────────────
            # 좌선회 / 우선회 / 직진 세 표적. 전부 SPD_MIN_MPS(320) 명령.
            #
            # 왜 320 이 "느린" 건가: 자동조종 속도 루프는 183~305 m/s 에서
            # **불안정**하다(teachers.py 상단 실측, 2026-07-20).
            #   명령 200/250/280 -> 달성 264/443/401/399  (발산, 초음속)
            #   명령 300/320/400/500 -> 달성 222/222/222/222  (완전 일정)
            # 즉 달성 속도는 고를 수 없고, 320 이 낼 수 있는 **가장 느린** 값이다.
            # 앞선 도망 칸이 speed_cmd 240 을 넣었다가 오히려 319 m/s 로
            # 달아난 것이 정확히 이 불안정 구간에 넣은 결과였다.
            # 222 m/s 면 우리 전속 471 대비 249 m/s 우위라 추격이 성립한다.
            #
            # 스폰은 꼬리 추격: 적기가 2,300 m 앞, 같은 방향.
            # 249 m/s 로 좁히면 사거리(914 m)까지 약 5.6초다.
            _eo.pop("target_autopilot", None)
            # [MOD-DRILL 2026-08-23] 임시 드릴 설정 (사용자 지시):
            #   1) 판을 **50초**로 끊는다. 200초를 주면 앞 20초에 못 붙어도
            #      나머지 180초를 배회하며 판이 끝난다 -- 실측 리플레이 3판 모두
            #      거리 2,366 -> 5,484 m 로 벌어졌는데 판은 200초를 다 썼다.
            #      50초면 "초반에 전속으로 붙는다"가 유일한 해법이 된다.
            #      time_norm 은 관측에서 0~200초로 하드코딩돼 있으므로
            #      (my_observation.py:305) 짧게 끊어도 관측 의미는 안 깨진다.
            #   2) 한 대도 못 맞히고 끝나면 **무딜 벌점**.
            #      지금 무딜 종료는 draw -40 + 600x(HP차) 인데 둘 다 온전하면
            #      HP차가 0 이라 -40 뿐이다. 아무것도 안 한 판과 잡은 판의
            #      차이가 너무 작았다. 종료 1회 부과라 추락 유도는 없다.
            _eo["max_engage_time"] = 50.0
            _drill_reward = dict(_reward_now)
            _drill_reward["w_nodmg"] = 400.0
            _drill_reward["nokill_hp_thresh"] = 0.0   # 30초 안에 **격추**해야 벌점 면제
            # [2026-08-23] 마감 30초(사용자 지시). 게이트(ep_len_mean <= 300스텝
            # = 30초)와 시점을 맞춘다 -- 30초 안에 딜이 없으면 그 자리에서 -400.
            # 종료 시점 판정이면 "50초 안에 언젠가"라 늦게 잡아도 값이 같았다.
            # [2026-08-23] far 벌점의 시간 램프를 판 길이에 맞춘다.
            # 기본값 20 -> 80초는 200초 판 기준(판의 10%~40% 지점)이라,
            # 50초 판에서는 처음 20초 동안 벌점이 아예 0 이고 판이 끝날 때도
            # 절반(tmul 0.50)까지밖에 안 켜졌다. 2,300 m 뒤에서 출발해 붙어야
            # 하는 그 초반 20초에 "멀면 손해"라는 신호가 꺼져 있었던 것이다.
            # 같은 비율로 5 -> 20초. 5초 뒤부터 켜지고 20초에 최대가 된다.
            _drill_reward["far_time_start_s"] = 5.0
            _drill_reward["far_time_full_s"] = 20.0
            # [2026-08-24] 시간초과 벌점 300 (사용자 지시). **드릴 칸에만.**
            # 39단 실측: 400판 중 진 판 0, 격추 51% / 만료 49% 였고
            # 만료 판의 47%가 총보상 양수였다. 만료를 손해로 못 박는다.
            _drill_reward["timeout_penalty"] = 300.0
            # [2026-08-24] 게이트 시간을 **스로틀 단계별로** 준다(사용자 지시:
            # "이번 드릴만 40초" — 0.5 단계만).
            # 근거(리플레이 실측, t50): 사거리 914 m 도달에만 39~41초가 걸린다.
            #   2,300 m 시작 · 평균 접근속도 23.9~37.4 m/s
            #   표적이 뱅크 45도로 도니 직선 속도차(우리 390 대 적 270)가
            #   접근으로 거의 안 바뀐다. 50초 판에서 사격 시간이 9~11초뿐이라
            #   35초 게이트는 물리적으로 도달 불가였다(시간초과 49%).
            # t30/t40 은 35초로 이미 통과했으므로 그대로 둔다.
            # 표적이 빨라질수록 접근에 쓰는 시간이 늘어나므로 게이트도 함께 연다.
            #   0.3 / 0.4 : 35초 (이미 통과)
            #   0.5       : 40초 (사거리 도달 39~41초 실측)
            #   0.6       : 45초
            # [2026-08-24] 0.5 를 40 -> 45초로 (사용자 지시). 0.6 은 50초.
            # 근거(경로 실측, t50 3판): 우리 경로 11.3~12.7 km · 적 9.6~11.0 km
            #   경로비 1.15~1.18 · **낭비 39~48 m (3% 미만)** — 헤매지 않는다.
            #   우리 평속 302 · 적 261 -> 속도차 41 m/s · 50초면 2,050 m.
            #   좁혀야 할 거리가 2,000 m 라 판을 다 써야 겨우 붙는 배치다.
            # 즉 정책이 더 잘할 여지가 거의 없다. 게이트를 물리에 맞춘다.
            _gate_s = {30: 35.0, 40: 35.0, 50: 45.0}.get(_tier, 35.0)
            _drill_reward["nodmg_deadline_s"] = _gate_s   # 게이트와 같은 시각
            # [2026-08-23] 빨리 잡을 이유를 실제로 만든다(사용자 진단).
            # 문제: 시간보너스가 200 x (1 - t/max_engage_time) 인데
            #       max_engage_time 이 200 이었다. 판은 50초로 끊었으면서
            #       보너스는 200초 자로 쟀으니, 우리가 쓰는 30~45초 구간은
            #       보너스 곡선의 앞쪽 8%만 지나갔다. 실측:
            #         20초 격추 1,680 · 40초 격추 1,660  -> 차이 겨우 10
            #         (무격추 벌점은 400 이라 40배 차이)
            #       즉 30초 경계만 절벽이고 그 밖은 평지라, 정책은
            #       "경계를 겨우 넘기지 말자"만 배우고 "빨리 잡자"는 못 배웠다.
            # 고침: 자를 판 길이(50초)에 맞추고 보너스를 키운다.
            #         20초 격추 +360 · 40초 격추 +120  -> 차이 240 (24배)
            _drill_reward["max_engage_time"] = 50.0
            _drill_reward["win_time_bonus"] = 600.0
            # [2026-08-23] 사거리 체류 보상 0.06 -> 2.0 (사용자 선택 ②).
            # 문제(실측, 거리 구간별 우리 속도):
            #   > 2,000 m  219 m/s   가속 +3.81      <- 추격 초반에 안 민다
            #   914~1,500  309 m/s   가속 +5.41
            #   < 914 m    325 m/s   가속 +2.99      <- 사거리에서 제일 빠르다
            # 모든 구간에서 계속 가속만 한다. 구간별 조절이 아니라
            # "판 내내 밀기"라는 단순해를 찾았고, 그래서 표적(213 m/s)을
            # 112 m/s 로 스쳐 지나간다 -- 사거리 안 표본이 전체의 5.6%뿐이다.
            # 원인: 체류에 보상이 없다. 300 m 에서 nmd 6.450 대 wez 0.056 (1/115).
            # 2.0 이면 근접 체류가 스텝당 최대 2.0 -> 20초 머물면 +400.
            # 파밍 걱정이 적은 항이다 -- 체류가 곧 사격 기회이고,
            # prox 가 거리에 비례해 914 m 언저리 체류는 거의 0 이다.
            # 2.0 은 판당 29 로 nmd(63)보다도 작았다 -> 12.0 으로 올린다(사용자 지시).
            #   실측 기준: wez 판당 0.86 · 사거리 체류 34.1 스텝 (w_wez 0.06)
            #   12.0 -> 판당 172   (체류가 3배로 늘면 516)
            # 상한 근거: 빨리 격추(terminal 1,740 + 시간보너스 240 = 1,980)를
            # 체류 파밍이 못 이겨야 한다. 체류를 3배로 늘려도 516 이라 안전하다.
            # 16.0 이면 687 로 damage(450)를 넘어 경합하기 시작해 위험하다.
            # [2026-08-23] 체류 보상 관련 오버라이드를 **전부 제거**한다(사용자 지시:
            # "가장 빨랐던 설정으로"). 즉 w_wez 0.06 / wez_cone_deg 15 기본값.
            #
            # 실측 기울기 비교 (stage 35 격추시간, 초/100 iteration):
            #   tier6  시간보너스만 수정 (w_wez 0.06)      -3.37   <- 가장 빠름
            #   tier8  + w_wez 12, 콘 15도                 +0.68
            #   tier9  + 콘 1도                            +4.65
            # 체류 이득과 시간보너스가 정면으로 싸운다. 체류가 이기면 근접해서
            # 오래 머물다 판이 길어진다(WEZ 34.1 -> 37.1, 시간 32.3 -> 35.9).
            #
            # 콘을 1도로 좁힌 파밍 차단도 같이 뺀다 -- w_wez 0.06 에서는
            # 50초 내내 파밍해도 2.7 이라 애초에 파밍할 값이 없다.
            # 체류를 다시 살릴 때는 콘 폭과 세트로 조정할 것.
            _drill_spawn = {"ownship": list(_TAIL_OWN), "target": list(_TAIL_TGT)}
            _drill_rand = {"enabled": True, "radius": 100.0,
                           "r_roll": 10.0, "r_pitch": 5.0, "r_heading": 10.0}
            # [2026-08-23] 교사(자동조종) -> **스틱 상대**로 교체(사용자 제안).
            # 자동조종 속도 루프가 speed_cmd 를 못 따라간다 -- 실측:
            #   명령 320 -> 달성 316 · 명령 180 -> 달성 288 m/s
            # 우리 최대가 298 m/s 라 물리적으로 못 잡는 배치였다.
            # DrillOpponent 는 FighterSim.step(action) 으로 스로틀을 0~1 로
            # 직접 준다(0.5 고정). 뱅크 45도라 실제로 돌고, 도는 만큼 느려진다.
            _eo["target_pool"] = [
                {"weight": 1.0, "mode": "aggressor", "level": "drill_left_t%d" % _tier,
                 "randomization": dict(_drill_rand),
                 "spawn": {k: list(v) for k, v in _drill_spawn.items()}},
                {"weight": 1.0, "mode": "aggressor", "level": "drill_right_t%d" % _tier,
                 "randomization": dict(_drill_rand),
                 "spawn": {k: list(v) for k, v in _drill_spawn.items()}},
                {"weight": 1.0, "mode": "aggressor", "level": "drill_straight_t%d" % _tier,
                 "randomization": dict(_drill_rand),
                 "spawn": {k: list(v) for k, v in _drill_spawn.items()}},
            ]
            # [2026-08-23] 게이트 = **30초 안에 결착** (사용자 지시).
            #   ep_len_mean_max 300 스텝. 10 Hz(step_ratio=6)라 300 스텝 = 30초.
            #   (200초 판이 2,000 스텝인 것으로 확인 -- console 의 num_steps=[2000])
            #
            # 왜 승률이 아니라 시간인가: 승률 100% 는 "언젠가 잡는다"까지 통과시킨다.
            # 지금 문제는 잡느냐가 아니라 **빨리 못 잡는 것**(스로틀을 안 민다)이다.
            #
            # crash_rate_max 를 같이 건 이유: 길이만 보면 **빨리 추락해도 통과**한다.
            # 실제로 그런 사고가 있었다 -- stage 1·2 가 win_rate 0.00 으로
            # max_iterations 를 소진했는데 런이 조용히 진행됐다([MOD-GATEFAIL]).
            # 드릴 표적은 공격 기동을 안 하므로 우리가 죽는 경로는 사실상 추락뿐이고,
            # 그것만 막으면 "짧은 판 = 격추"가 성립한다.
            # (이전 게이트) 승률 100%:
            # 앞선 도망 칸도 같은 게이트로 네 번 다 0.000 이었지만, 조건이
            # 달라졌다: 그때 표적은 speed_cmd 240 이 불안정 구간이라 오히려
            # 319 m/s 로 달아났다. 지금 표적은 약 222 m/s 로, 우리 전속 471
            # 대비 249 m/s 우위다 -- 2,300 m 를 5.6초에 좁힐 수 있으므로
            # 100% 가 원리상 도달 가능한 목표다.
            # ⚠ 못 넘으면 max_iterations 에서 gate_failed 로 런이 멈춘다.
            #    그건 "추격을 못 배웠다"는 신호이므로 조용히 넘어가는 것보다 낫다.
            S.append(_dc.replace(
                _s34, index=_idx, name=_nm,
                description="[MOD-DRILL] 추격 드릴 스로틀 %.1f: 좌/우선회+직진 " % (_tier/100.0)
                            + "평균 %.0f초 안에 결착할 때까지." % _gate_s,
                reward_overrides=_drill_reward, env_overrides=_eo,
                target_mode="aggressor",
                advance_conditions={"ep_len_mean_max": _gate_s * 10.0,
                                    "crash_rate_max": 0.02},
                advance_window=5, advance_episodes=0, min_iterations=0,
                # [2026-08-24] 드릴 노출 상한 4000 -> 150.
                # 드릴은 대회에서 흔한 꼬리 추격을 가르치므로 **유지**한다(사용자).
                # 다만 한 칸에 오래 붙으면 습관이 굳는다. 실측:
                #   std13(드릴 0.3/0.4, 짧게)      RL 칸 추락 0.007
                #   recv7b(드릴+도망칸, 중간)       추락 0.048
                #   g45(드릴 0.3~0.6, 37단 145 ·
                #       39단 500+ iteration)      추락 0.226
                # 한 칸에 수백 iteration 을 태운 실행에서만 추락이 터졌다.
                # 150 이면 통과에 충분하고(대부분 5~30 iteration 에 통과)
                # 못 넘으면 gate_failed 로 멈춰 원인을 보게 된다.
                max_iterations=150,
                gate_optional=True,   # [MOD-SOFTGATE] 못 넘어도 런을 안 세운다
                eval_kill_floor=0.0,
                eval_kill_abort=False, eval_kill_probe_eval=False))
            continue
        _bp = _MODELS / _bundle
        assert (_bp / "policy_weights.pkl.gz").is_file(), f"사다리 상대 없음: {_bp}"
        _eo["target_pool"] = [{
            "weight": 1.0, "mode": "policy", "bundle": str(_bp),
            # 반경 0 스캐터를 켠다 — env 는 randomization 이 켜진 판에서만
            # add_random_init_position("ownship") 을 부르고, spawn["ownship"]
            # 을 읽는 곳이 그 함수뿐이다. 안 켜면 아군 스폰이 이전 판 값으로
            # 샌다([MOD-SAMEALT] 에서 실측).
            "randomization": {"enabled": True, "radius": 100.0,
                              "r_roll": 10.0, "r_pitch": 5.0,
                              "r_heading": 10.0},
            "spawn": {"ownship": list(_S34_OWN), "target": list(_LADDER_TGT)},
        }]
        S.append(_dc.replace(
            _s34,
            index=_idx, name=_nm,
            description=f"[MOD-LADDER] 고정 상대 {_bundle} 상대 승률 80% 까지.",
            reward_overrides=_reward_now,
            env_overrides=_eo,
            # [2026-08-23] 게이트 0.80 -> 0.70 (사용자 지시). 실측 근거:
            # 완료된 13개 단계에서 0.70 도달에 1,328 iteration,
            # 0.70->0.80 에 **1,494 iteration** 이 더 들었다(전체의 53%).
            # 극단은 12241_c4 — 5 iteration 만에 0.70 을 찍고 0.80 을 만드는 데
            # 849 iteration 을 더 썼고, 그 사이 3100 상대 승률이 0.31 로 떨어졌다.
            # 마지막 10%p 를 짜내는 구간이 곧 과최적화 구간이고 다른 상대를
            # 잊는 구간이다. 낮추면 바퀴를 두 배 돌아 번갈아 보는 효과가 커진다.
            # [2026-08-24] 추락 조건 추가(사용자 지시: "추락 없을 때만").
            # 그전까지 RL 칸 게이트는 승률뿐이었고, 그래서 추락하는 정책이
            # 계속 승급하며 습관이 누적됐다. 실측(0824_g45):
            #   52단은 승률 0.7008 로 승급했는데 그 구간 추락률이 0.34~0.36 —
            #   3판에 1판 떨어지면서 10판에 7판 이기는 정책을 합격시켰다.
            #   상대별 평균 추락: ladder5220 0.455 · snap12241 0.197 ·
            #   recv9980 0.195 · peak3100 0.015 · aimcur 0.003 · 드릴 0.000
            # 승률은 추락한 판을 그냥 '진 판'으로만 세므로 나머지에서 이기면
            # 0.70 이 채워진다. 게이트가 그걸 못 걸렀다.
            # 0.02 = 50판에 1판. 드릴 칸과 같은 기준으로 맞춘다.
            advance_conditions={"win_rate_min": 0.70, "crash_rate_max": 0.02},
            advance_window=5,        # 약 225 판. 70% 에서 표준오차 3.1%
            advance_episodes=0,
            # [2026-08-22] min_iterations 제거(사용자 지적). 규칙은 '승률 80%%면
            # 통과'다. 이미 80%% 로 이기는 상대에게서는 배울 게 없으므로 최소
            # iteration 을 강제할 이유가 없다. 실제로 stage 35(86.3%%)·36(90.7%%)
            # 이 각각 30 iteration 을 채우느라 60 iteration 을 헛썼다.
            # advance_window=5 자체가 최소 5 iteration 을 요구하므로
            # 표본 없이 통과하는 일은 여전히 없다.
            min_iterations=0,
            max_iterations=4000,
            eval_kill_floor=0.0,     # 고정 상대라 ace 킬 바닥은 의미 없다
            eval_kill_abort=False,
            eval_kill_probe_eval=False,
        ))

    return S


__all__ = ["get_stages"]
