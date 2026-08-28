"""Curriculum stage definitions and advancement logic for dogfight RL training.

Stages (in order):
  0  flight_survival     — stay airborne, throttle control
  1  target_pursuit      — orient and close on fixed target
  2  wez_approach        — enter WEZ against loitering target
  3  autopilot_pursuit   — pursue a moving autopilot target
  4+ two_circle_headon   — alpha-based head-on curriculum stages
  N  full_dogfight       — full engagement vs. behavior-tree opponent
"""
from __future__ import annotations

import math

import copy
from dataclasses import dataclass, field
from typing import Any


# ── Stage definition ──────────────────────────────────────────────────────────

@dataclass
class CurriculumStage:
    index: int
    name: str
    description: str
    target_mode: str
    episode_step_limit: int     # steps per episode
    max_iterations: int         # hard cap; auto-advance may exit earlier
    checkpoint_interval: int    # save native checkpoint every N iterations
    reward_overrides: dict[str, Any]
    randomization: dict[str, Any]   # merged into env_config["ownship_randomization"]
    advance_conditions: dict[str, Any]  # metric key → threshold
    advance_window: int = 10    # rolling average window for advancement check
    env_overrides: dict[str, Any] = field(default_factory=dict)
    # [MOD-EPI] episode-based early graduation: when > 0, advancement is
    # evaluated over the most recent iterations covering at least this many
    # EPISODES (episode-weighted averages) instead of advance_window
    # iterations. The stage exits as soon as the conditions hold.
    advance_episodes: int = 0
    # [MOD-EVALFLOOR] hard stop: two consecutive finite gate evals below this
    # value abort the stage as failed. Added after the league's passivity
    # ratchet eroded the ace eval 0.93->0.67 while min_iterations FORCED the
    # erosion to continue (measured 07-23). 0 disables. Set the floor with
    # eval noise in mind: at 28-30 eps sigma~0.06, so 0.85 for a 0.95-true
    # policy false-triggers <1% while catching a real collapse in 2 evals.
    eval_hard_floor: float = 0.0
    # [MOD-MINITERS] floor before the gate opens. League stages gate on the
    # ace teacher (the pool is dropped in evaluation), which a warm-started
    # bundle can already ace on entry -- measured 07-23, stage 20's first
    # eval read 0.933 at iter 4, so the stage would have promoted at ~iter 20
    # having trained none of the thing it exists to train (judge-margin vs
    # policy diversity). The gate measures retention of the graded task; the
    # floor guarantees the stage actually spends its budget.
    min_iterations: int = 0
    # [MOD-KILLFLOOR] honest-kill dual floor (0 disables). eval_hard_floor
    # above reads eval_win_rate, which is a ~224-episode SLIDING WINDOW
    # (RLlib smoothing accumulates eval rounds) -- measured 07-25 it hid a
    # late-stage collapse (gate window 0.92-1.0 while the same weights scored
    # honest ace kill 0.458). This floor runs an OUT-OF-PROCESS deterministic
    # ace-kill probe (eval_winrate.py, fresh seeds) every
    # eval_kill_probe_interval iters and aborts on two consecutive probes
    # below eval_kill_floor (same recovery-grace as eval_hard_floor). The
    # self-play ignition checklist's only unimplemented blocker; also the
    # general vaccine against window-hidden erosion. Off by default (the
    # probe costs a subprocess); league/self-play stages set ~0.70.
    eval_kill_floor: float = 0.0
    eval_kill_probe_interval: int = 25
    eval_kill_probe_episodes: int = 48
    # [MOD-KILLPROBE] run the probe but do NOT abort on breaches. The probe
    # bundle is also what snapshot_sidecar turns into the self-play pool, so a
    # pure self-play stage needs the probe running while an ace-kill floor is
    # meaningless there -- it never fights the ace, so the tripwire measures a
    # skill the stage does not train. True keeps every existing stage as-is.
    eval_kill_abort: bool = True
    # [MOD-PROBEBUNDLE] run the probe for its BUNDLE only and skip the eval
    # subprocess. That subprocess initialises JSBSim a second time and the
    # DLL's BattleSpace is shared, which wipes the trainer's aircraft on the
    # next reset -- measured as repeated deaths at exactly the probe
    # iterations. Self-play stages need the bundle (snapshot_sidecar builds the
    # opponent pool from it) but not the ace-kill number.
    eval_kill_probe_eval: bool = True

    # [MOD-SOFTGATE 2026-08-24] max_iterations 에 닿아도 런을 세우지 않고
    # 다음 칸으로 넘긴다. 드릴(BT) 칸처럼 "못 넘어도 사다리는 돌아야" 하는
    # 칸에 쓴다. 기본값 False 라 기존 동작([MOD-GATEFAIL])은 그대로다.
    gate_optional: bool = False


# ── Stage catalogue ───────────────────────────────────────────────────────────

def get_stages() -> list[CurriculumStage]:
    """Return the ordered list of curriculum stages."""
    stages = [
        # ── Stage 0: Flight Survival ──────────────────────────────────────
        CurriculumStage(
            index=0,
            name="flight_survival",
            description="Stay airborne and develop throttle control. Target is stationary.",
            target_mode="fixed",
            episode_step_limit=3600,    # 60 s
            max_iterations=200,
            checkpoint_interval=10,
            reward_overrides={
                "survival_bonus": 0.05,         # +0.05 every step alive
                "pursuit_scale": 0.0,            # no pursuit required
                "damage_scale": 0.0,             # no damage reward
                "low_altitude_penalty": 1.0,     # 10× normal → hard boundary
                "win_reward": 0.0,
                "loss_reward": -50.0,            # crash penalty only
                "draw_reward": 0.0,
            },
            randomization={
                "enabled": True,
                "radius": 0.0,
                "r_roll": 5.0,
                "r_pitch": 5.0,
                "r_heading": 15.0,              # mild heading variation
            },
            advance_conditions={
                "crash_rate_max": 0.20,         # crash < 20 %
            },
        ),

        # ── Stage 1: Target Pursuit ───────────────────────────────────────
        CurriculumStage(
            index=1,
            name="target_pursuit",
            description="Orient nose toward and close on a fixed target.",
            target_mode="fixed",
            episode_step_limit=7200,    # 120 s
            max_iterations=300,
            checkpoint_interval=10,
            reward_overrides={
                "survival_bonus": 0.01,
                "pursuit_scale": 0.5,
                "pursuit_half_angle_deg": 60.0,  # wider gradient
                "pursuit_range_m": 8000.0,        # activates earlier
                "damage_scale": 0.0,
                "low_altitude_penalty": 0.3,
                "win_reward": 20.0,
                "loss_reward": -50.0,
                "draw_reward": 0.0,
            },
            randomization={
                "enabled": True,
                "radius": 500.0,
                "r_roll": 10.0,
                "r_pitch": 5.0,
                "r_heading": 60.0,
            },
            advance_conditions={
                "ep_min_distance_max": 2000.0,  # closes within 2 km
                "crash_rate_max": 0.15,
            },
        ),

        # ── Stage 2: WEZ Approach ─────────────────────────────────────────
        CurriculumStage(
            index=2,
            name="wez_approach",
            description="Enter WEZ against a loitering (non-threatening) target.",
            target_mode="loiter",
            episode_step_limit=10800,   # 180 s
            max_iterations=400,
            checkpoint_interval=10,
            reward_overrides={
                "survival_bonus": 0.0,
                "pursuit_scale": 0.3,
                "pursuit_half_angle_deg": 30.0,
                "pursuit_range_m": 3000.0,
                "damage_scale": 20.0,
                "low_altitude_penalty": 0.1,
                "win_reward": 100.0,
                "loss_reward": -100.0,
                "draw_reward": -30.0,
            },
            randomization={
                "enabled": True,
                "radius": 1000.0,
                "r_roll": 10.0,
                "r_pitch": 5.0,
                "r_heading": 120.0,
            },
            advance_conditions={
                # Either win rate meets threshold OR consistent WEZ contact
                "win_rate_min": 0.10,
                "ep_wez_steps_min": 10.0,      # OR-condition handled in check fn
            },
        ),

        # ── Stage 3: Autopilot Pursuit ────────────────────────────────────
        CurriculumStage(
            index=3,
            name="autopilot_pursuit",
            description="Pursue a moving target with fixed heading, altitude, and speed.",
            target_mode="autopilot",
            episode_step_limit=14400,   # 240 s
            max_iterations=500,
            checkpoint_interval=10,
            reward_overrides={
                "survival_bonus": 0.0,
                "pursuit_scale": 0.25,
                "pursuit_half_angle_deg": 25.0,
                "pursuit_range_m": 3500.0,
                "damage_scale": 20.0,
                "low_altitude_penalty": 0.1,
                "win_reward": 100.0,
                "loss_reward": -100.0,
                "draw_reward": -30.0,
            },
            randomization={
                "enabled": True,
                "radius": 1500.0,
                "r_roll": 12.0,
                "r_pitch": 8.0,
                "r_heading": 150.0,
            },
            advance_conditions={
                "ep_min_distance_max": 1500.0,
                "ep_wez_steps_min": 5.0,
                "crash_rate_max": 0.20,
            },
        ),

    ]
    two_circle_stages = _build_two_circle_headon_stages(start_index=len(stages))
    return stages + two_circle_stages + [
        CurriculumStage(
            index=len(stages) + len(two_circle_stages),
            name="full_dogfight",
            description="Full engagement against active behavior-tree opponent.",
            target_mode="behavior_tree",
            episode_step_limit=18000,   # 300 s
            max_iterations=1000,
            checkpoint_interval=10,
            reward_overrides={},        # use default reward (no overrides)
            randomization={
                "enabled": True,
                "radius": 2000.0,
                "r_roll": 15.0,
                "r_pitch": 10.0,
                "r_heading": 180.0,
            },
            advance_conditions={},      # no automatic advancement (final stage)
        ),
    ]


def _build_two_circle_headon_stages(start_index: int) -> list[CurriculumStage]:
    """Build alpha-based two-circle head-on curriculum stages."""
    stages = []
    for offset, alpha_deg in enumerate((0, 20, 40, 60, 80, 100, 120, 140, 160, 180)):
        stages.append(
            CurriculumStage(
                index=start_index + offset,
                name=f"two_circle_headon_a{alpha_deg:03d}",
                description=(
                    f"Two-circle head-on curriculum at alpha={alpha_deg} deg."
                ),
                target_mode="behavior_tree",
                episode_step_limit=18000,
                max_iterations=200,
                checkpoint_interval=10,
                reward_overrides={},
                randomization={"enabled": False},
                advance_conditions={
                    "win_rate_min": 0.70,
                    "crash_rate_max": 0.30,
                },
                advance_window=10,
                env_overrides={
                    "initial_scenario": {
                        "mode": "two_circle_headon",
                        "alpha_deg": float(alpha_deg),
                    },
                    "geometry_guard": {
                        "enabled": True,
                        "mode": "two_circle_headon",
                        "alpha_deg": float(alpha_deg),
                    },
                },
            )
        )
    return stages


# ── Config builder ────────────────────────────────────────────────────────────

def build_stage_env_config(base_config: dict, stage: CurriculumStage) -> dict:
    """Merge stage-specific overrides into a deep copy of base_config."""
    cfg = copy.deepcopy(base_config)
    cfg["target_mode"] = stage.target_mode
    cfg["episode_step_limit"] = stage.episode_step_limit
    # Reward overrides (only the keys listed; others keep base values)
    for k, v in stage.reward_overrides.items():
        cfg["reward"][k] = v
    # Position randomization
    if stage.randomization:
        cfg["ownship_randomization"] = {
            **cfg.get("ownship_randomization", {}),
            **stage.randomization,
        }
    if stage.env_overrides:
        _deep_update(cfg, stage.env_overrides)
    return cfg


def _deep_update(base: dict, updates: dict) -> dict:
    """Recursively merge stage env overrides in place."""
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


# ── Advancement logic ─────────────────────────────────────────────────────────

def check_advancement(stage: CurriculumStage, metric_window: list[dict]) -> tuple[bool, str]:
    """Evaluate whether the stage's advance_conditions are met.

    Args:
        stage: The current CurriculumStage.
        metric_window: List of per-iteration metric dicts (most recent last).
            Dicts may contain "n/a" strings for unavailable metrics.

    Returns:
        (should_advance, reason_string)
    """
    if not stage.advance_conditions or not metric_window:
        return False, ""

    # Compute rolling averages, skipping "n/a" entries
    averages: dict[str, float] = {}
    for key in stage.advance_conditions:
        metric_key = _condition_key_to_metric(key)
        values = [
            m[metric_key]
            for m in metric_window
            if isinstance(m.get(metric_key), (int, float))
        ]
        if values:
            averages[metric_key] = sum(values) / len(values)

    # WEZ approach special: win_rate_min OR ep_wez_steps_min (either condition)
    if stage.name == "wez_approach":
        win_avg   = averages.get("win_rate", None)
        wez_avg   = averages.get("ep_wez_steps", None)
        win_thr   = stage.advance_conditions.get("win_rate_min")
        wez_thr   = stage.advance_conditions.get("ep_wez_steps_min")
        if win_thr is not None and win_avg is not None and win_avg >= win_thr:
            return True, f"win_rate={win_avg:.3f} >= {win_thr}"
        if wez_thr is not None and wez_avg is not None and wez_avg >= wez_thr:
            return True, f"ep_wez_steps={wez_avg:.1f} >= {wez_thr}"
        return False, ""

    # General: ALL conditions must be met simultaneously
    reasons = []
    for cond_key, threshold in stage.advance_conditions.items():
        metric_key = _condition_key_to_metric(cond_key)
        avg = _finite(averages.get(metric_key))
        if avg is None:
            # NaN compares False against every threshold, so without this a
            # stage with no completed evaluation episodes passes BOTH the
            # "_min" and "_max" checks and advances silently. Measured
            # 2026-07-20: stage 4 advanced on "win_rate=nan" while its real
            # win rate was 0.000 with zero gun time.
            return False, f"{metric_key} is not a finite number yet"   # metric not yet available → wait

        if cond_key.endswith("_max") and avg > threshold:
            return False, f"{metric_key}={avg:.4f} still above {threshold}"
        if cond_key.endswith("_min") and avg < threshold:
            return False, f"{metric_key}={avg:.4f} still below {threshold}"
        reasons.append(f"{metric_key}={avg:.4f}")

    reason_str = ", ".join(reasons)
    return True, reason_str


def _condition_key_to_metric(cond_key: str) -> str:
    """Strip _max/_min suffix → metric key used in metric_history dicts."""
    for suffix in ("_max", "_min"):
        if cond_key.endswith(suffix):
            return cond_key[: -len(suffix)]
    return cond_key


# [MOD-EPI] episode-based advancement -----------------------------------------

def _finite(value):
    """Return value as a float if it is a real number, else None.

    isinstance(x, float) is True for NaN, and every comparison against NaN is
    False -- so a NaN metric satisfies "not below the minimum" AND "not above
    the maximum" at the same time and walks straight through a gate.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def check_advancement_episodes(
    stage: CurriculumStage,
    metric_history: list[dict],
) -> tuple[bool, str]:
    """Episode-weighted advancement check with early graduation.

    Walks metric_history backwards, accumulating "episodes_this_iter" until at
    least stage.advance_episodes episodes are covered; averages each condition
    metric weighted by episode count over that window. Returns (False, "") if
    not enough episodes were collected yet.
    """
    target_eps = int(stage.advance_episodes)
    if target_eps <= 0 or not stage.advance_conditions or not metric_history:
        return False, ""

    # Prefer DETERMINISTIC evaluation when the run produced any. Training
    # rollouts carry exploration noise, and on a task where a kill needs the
    # nose inside a few degrees that noise dominates: measured 2026-07-20,
    # stage 2 reported a training win rate of 0.05-0.13 while the very same
    # weights scored 12/12 evaluated deterministically. Gating on the noisy
    # number would hold a finished stage back indefinitely -- and the target
    # the curriculum exists to reach (90% kills) is a deterministic number.
    use_eval = any(_finite(m.get("eval_win_rate")) is not None
                   for m in metric_history)
    episode_key = "eval_episodes" if use_eval else "episodes_this_iter"
    prefix = "eval_" if use_eval else ""
    if use_eval:
        # advance_episodes is sized to average out exploration noise. Without
        # that noise the same confidence needs far fewer episodes, so demanding
        # the full count would stall a finished stage for tens of iterations.
        # A third, floored at 30, still puts the Wilson 95% lower bound within
        # about 0.1 of the estimate at the thresholds these gates use.
        target_eps = max(30, target_eps // 3)

    window: list[dict] = []
    cum_eps = 0
    for m in reversed(metric_history):
        eps = m.get(episode_key)
        if not isinstance(eps, (int, float)) or eps <= 0:
            continue
        if use_eval and _finite(m.get("eval_win_rate")) is None:
            continue
        window.append(m)
        cum_eps += int(eps)
        if cum_eps >= target_eps:
            break
    if cum_eps < target_eps:
        return False, ""

    averages: dict[str, float] = {}
    for cond_key in stage.advance_conditions:
        metric_key = _condition_key_to_metric(cond_key)
        total_w = 0.0
        total_v = 0.0
        for m in window:
            value = _finite(m.get(prefix + metric_key, m.get(metric_key)))
            if value is None:
                continue
            weight = float(m[episode_key])
            total_v += float(value) * weight
            total_w += weight
        if total_w > 0:
            averages[metric_key] = total_v / total_w

    suffix = (f" over {cum_eps} deterministic eval eps" if use_eval
              else f" over {cum_eps} eps")

    # WEZ approach special: win_rate_min OR ep_wez_steps_min
    if stage.name == "wez_approach":
        win_avg = averages.get("win_rate")
        wez_avg = averages.get("ep_wez_steps")
        win_thr = stage.advance_conditions.get("win_rate_min")
        wez_thr = stage.advance_conditions.get("ep_wez_steps_min")
        if win_thr is not None and win_avg is not None and win_avg >= win_thr:
            return True, f"win_rate={win_avg:.3f} >= {win_thr}{suffix}"
        if wez_thr is not None and wez_avg is not None and wez_avg >= wez_thr:
            return True, f"ep_wez_steps={wez_avg:.1f} >= {wez_thr}{suffix}"
        return False, ""

    reasons = []
    for cond_key, threshold in stage.advance_conditions.items():
        metric_key = _condition_key_to_metric(cond_key)
        avg = averages.get(metric_key)
        if avg is None:
            return False, ""
        if cond_key.endswith("_max") and avg > threshold:
            return False, f"{metric_key}={avg:.4f} still above {threshold}{suffix}"
        if cond_key.endswith("_min") and avg < threshold:
            return False, f"{metric_key}={avg:.4f} still below {threshold}{suffix}"
        reasons.append(f"{metric_key}={avg:.4f}")

    return True, ", ".join(reasons) + suffix
