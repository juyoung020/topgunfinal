# -*- coding: utf-8 -*-
"""Multi-episode win-rate evaluation for a trained PPO+LSTM bundle.

Win = enemy HP reaches 0 ("target destroyed"). This is the curriculum gate
metric: the final stage requires win_rate >= 0.90 vs the BT opponent.

Unlike run_local_dogfight.py (single episode, step_ratio 1 = 60 Hz), this
tool runs N episodes at the TRAINING timing (step_ratio 6 = 10 Hz decisions)
so evaluation matches how the policy was trained and how the submission
client acts (ACTION_REPEAT = 6).

Usage:
  python student/tools/eval_winrate.py --bundle-dir artifacts/models/team01/ppo_lstm_v1 \
      --opponent bt --episodes 20
  python student/tools/eval_winrate.py --bundle-dir ... --opponent pursuit --episodes 10 \
      --json-out eval.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]   # Release/ root
SRC = ROOT / "src"
for p in (ROOT, SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

from DogFightEnvWrapper import DogFightWrapper
from dogfight.ai.bt_action_provider import BTActionProvider
from dogfight.ai.rl_action_provider import RLActionProvider
from dogfight.ai.rllib_utils import build_algorithm_from_bundle
from dogfight.ai.student_hooks import load_observation_hook, load_reward_hook
from student.tools.obs_experiment import ActionRepeatProvider

# [MOD-EVALPOOL] competition spawn fixtures (league_eval.py imports these).
# main = finals opening (3,048 m head-on), quali = qualifier (760 m head-on);
# both turn on the time-phased WEZ from the rulebook (config.py defaults).
FIXTURES = {
    "main": {
        "ownship": [0.0, 0.0, -7000.0, 0.0, 0.0, 0.0, 250.0],
        "target": [3048.0, 0.0, -7000.0, 0.0, 0.0, 180.0, 250.0],
        "wez_phases": {"enabled": True},
    },
    "quali": {
        "ownship": [0.0, 0.0, -7000.0, 0.0, 0.0, 0.0, 250.0],
        "target": [760.0, 0.0, -7000.0, 0.0, 0.0, 180.0, 250.0],
        "wez_phases": {"enabled": True},
    },
}


def parse_args():
    p = argparse.ArgumentParser(description="Evaluate bundle win rate over N episodes.")
    p.add_argument("--bundle-dir", required=True)
    p.add_argument("--opponent", default="teacher",
                   choices=["teacher", "bt", "loiter", "autopilot", "pursuit",
                            "fixed", "policy"])
    p.add_argument("--teacher", default="ace",
                   help="scripted teacher name when --opponent teacher "
                        "(straight|turn|pursuit|defensive|ace)")
    p.add_argument("--teacher-params", default="",
                   help="JSON dict of teacher params, e.g. '{\"lead_time_s\":1.2}'")
    p.add_argument("--opponent-bundle", default="",
                   help="[MOD-EVALPOOL] frozen policy bundle for --opponent "
                        "policy (env holds it at 10 Hz, viewpoint flipped)")
    p.add_argument("--fixture", default="default",
                   choices=["default", "main", "quali"],
                   help="[MOD-EVALPOOL] spawn fixture: main=3048 m head-on, "
                        "quali=760 m head-on, both with phased WEZ")
    p.add_argument("--episodes", type=int, default=20)
    p.add_argument("--observation-module", default="student.my_observation")
    p.add_argument("--reward-module", default="student.my_reward")
    p.add_argument("--target-bt-dll", default="AIP_BASE_target.dll")
    p.add_argument("--max-engage-time", type=float, default=300.0)
    p.add_argument("--step-ratio", type=int, default=6)
    p.add_argument("--randomize-radius", type=float, default=2500.0,
                   help="Per-episode ownship spawn scatter (m); 0 disables.")
    p.add_argument("--json-out", default="", help="Optional summary JSON path.")
    p.add_argument("--save-log", action="store_true",
                   help="Save a Tacview CSV log of the LAST episode.")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    obs_hook = load_observation_hook(args.observation_module)
    reward_fn, reward_cfg = load_reward_hook(args.reward_module)

    # ActionRepeatProvider is REQUIRED: DogFightEnv queries the provider once
    # per physics substep (60 Hz) and rebuilds the observation each time, so an
    # unwrapped policy would run its LSTM 6x faster than during training and
    # than the Unreal client (ACTION_REPEAT=6). See obs_experiment.py.
    ownship_provider = ActionRepeatProvider(
        RLActionProvider(
            bundle_dir=args.bundle_dir,
            algorithm_factory=build_algorithm_from_bundle,
        ),
        args.step_ratio,
    )

    target_provider = None
    target_mode = args.opponent
    if args.opponent == "bt":
        target_provider = BTActionProvider(dll_name=args.target_bt_dll)
        target_mode = "rl"   # provider drives the target sim

    teacher_spec = {
        "name": args.teacher,
        "params": json.loads(args.teacher_params) if args.teacher_params else {},
    }

    env_config = {
        "step_ratio": args.step_ratio,
        "observation_mode": obs_hook["mode"],
        "observation_module": args.observation_module,
        "ownship_control_mode": "rl",
        "target_mode": target_mode,
        "target_teacher": teacher_spec,
        "max_engage_time": args.max_engage_time,
        "episode_step_limit": int(args.max_engage_time * 60 / args.step_ratio) + 200,
        "reward": reward_cfg,
        "target_loiter_bank_range": [20.0, 60.0],
        "ownship_randomization": {
            "enabled": args.randomize_radius > 0,
            "radius": args.randomize_radius,
            "r_roll": 10.0,
            "r_pitch": 8.0,
            "r_heading": 180.0,
        },
    }

    # [MOD-EVALPOOL] frozen-policy opponent + competition spawn fixtures.
    # The env's policy mode (single_agent_env [MOD-OPPONENT]) does the 10 Hz
    # hold and the viewpoint flip itself; only the bundle path travels here.
    if args.opponent == "policy":
        if not args.opponent_bundle:
            raise SystemExit("--opponent policy requires --opponent-bundle")
        env_config["target_policy_bundle"] = args.opponent_bundle
    env_config.update(FIXTURES.get(args.fixture, {}))

    env = DogFightWrapper(
        env_config,
        reward_fn=reward_fn,
        observation_fn=obs_hook["build_observation"],
        observation_size=obs_hook["size"],
        observation_low=obs_hook["low"],
        observation_high=obs_hook["high"],
        ownship_action_provider=ownship_provider,
        target_action_provider=target_provider,
    )

    outcomes: Counter = Counter()
    episode_rows = []
    zeros = np.zeros(4, dtype=np.float32)
    t_start = time.time()
    try:
        for ep in range(args.episodes):
            obs, info = env.reset()
            terminated = truncated = False
            total_reward = 0.0
            steps = 0
            # [MOD-TFIRST] step at which we FIRST put damage on the target.
            # "Quick kills at the merge" is the winning agent's signature in
            # the AlphaDogfight record, and 목표.md grades it, but the summary
            # carried only win_rate/jwin -- an agent that eventually grinds a
            # kill out and one that lands the first burst on the merge scored
            # identically.
            first_dmg_step = None
            while not (terminated or truncated):
                obs, reward, terminated, truncated, info = env.step(zeros)
                total_reward += float(reward)
                steps += 1
                if first_dmg_step is None:
                    try:
                        if float(info.get("target_health", 1.0)) < 1.0:
                            first_dmg_step = steps
                    except (TypeError, ValueError):
                        pass
            outcome = str(info.get("outcome", "unknown"))
            outcomes[outcome] += 1
            row = {
                "episode": ep,
                "outcome": outcome,
                "end_condition": info.get("end_condition", ""),
                "steps": steps,
                "reward": round(total_reward, 3),
                "ownship_health": round(float(info.get("ownship_health", -1)), 3),
                "target_health": round(float(info.get("target_health", -1)), 3),
                "t_first_damage_s": (round(first_dmg_step * args.step_ratio / 60.0, 2)
                                     if first_dmg_step else None),
            }
            episode_rows.append(row)
            print(
                f"[ep {ep + 1:3d}/{args.episodes}] {outcome:8s} "
                f"end={row['end_condition']:28s} steps={steps:5d} "
                f"R={total_reward:9.2f} own_hp={row['ownship_health']:.2f} "
                f"tgt_hp={row['target_health']:.2f}"
            )
            if args.save_log and ep == args.episodes - 1:
                env.make_tacviewLog()
                print("tacview log saved (last episode)")
    finally:
        env.close()

    n = max(1, len(episode_rows))
    win_rate = outcomes.get("win", 0) / n
    # [MOD-EVALPOOL] competition score: a full-time damage-advantage verdict
    # (judge_win) counts as a win under the rulebook, so gates on jwin.
    jwin = (outcomes.get("win", 0) + outcomes.get("judge_win", 0)) / n
    # Wilson 95% CI: 30 episodes cannot resolve a 90% gate (+-11%p), so the
    # interval is reported and the gate decision must use its LOWER bound.
    z = 1.96
    denom = 1.0 + z * z / n
    centre = (win_rate + z * z / (2 * n)) / denom
    half = (z * math.sqrt(win_rate * (1 - win_rate) / n + z * z / (4 * n * n))) / denom
    opponent_label = args.opponent
    if args.opponent == "teacher":
        opponent_label = f"teacher:{args.teacher}"
    elif args.opponent == "policy":
        opponent_label = f"policy:{args.opponent_bundle}"
    summary = {
        "bundle_dir": args.bundle_dir,
        "opponent": opponent_label,
        "fixture": args.fixture,
        "episodes": len(episode_rows),
        "win_rate": round(win_rate, 4),
        "jwin": round(jwin, 4),
        "win_rate_ci95": [round(max(0.0, centre - half), 4),
                          round(min(1.0, centre + half), 4)],
        "outcomes": dict(outcomes),
        "mean_reward": round(sum(r["reward"] for r in episode_rows) / n, 3),
        "mean_steps": round(sum(r["steps"] for r in episode_rows) / n, 1),
        # [MOD-TFIRST] how fast the first burst lands, and how often it lands
        # at all. Averaged over the episodes that HAD damage -- averaging a
        # miss as "slow" would confound aggression with accuracy.
        "damage_episode_rate": round(
            sum(1 for r in episode_rows if r["t_first_damage_s"] is not None) / n, 4),
        "mean_time_to_damage_s": (round(
            sum(r["t_first_damage_s"] for r in episode_rows
                if r["t_first_damage_s"] is not None)
            / max(1, sum(1 for r in episode_rows
                         if r["t_first_damage_s"] is not None)), 2)
            if any(r["t_first_damage_s"] is not None for r in episode_rows)
            else None),
        "elapsed_s": round(time.time() - t_start, 1),
    }
    lo, hi = summary["win_rate_ci95"]
    print("-" * 72)
    print(
        f"win_rate={summary['win_rate']:.3f} "
        f"jwin={summary['jwin']:.3f} "
        f"(95% CI {lo:.3f}-{hi:.3f}) vs {summary['opponent']} "
        f"({outcomes.get('win', 0)}/{len(episode_rows)} eps)"
    )
    print(f"outcomes={summary['outcomes']} mean_R={summary['mean_reward']}")
    if lo >= 0.90:
        print("GATE: PASS  (lower CI bound >= 0.90)")
    elif summary["win_rate"] >= 0.90:
        print(f"GATE: INCONCLUSIVE - point estimate >= 0.90 but CI reaches "
              f"{lo:.3f}; run more episodes")
    else:
        print("GATE: not met")
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.write_text(
            json.dumps({"summary": summary, "episodes": episode_rows}, indent=2),
            encoding="utf-8",
        )
        print(f"json saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
