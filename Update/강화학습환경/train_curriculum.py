"""Curriculum training for dogfight RL — Sequential Phase with strong fault recovery.

Recovery guarantees
-------------------
1. Atomic state file  — every iteration updates curriculum_state.json via
   write-to-temp + atomic rename; never leaves a partial write.
2. Native checkpoint  — saved every `checkpoint_interval` iterations
   (full algorithm state: weights + optimizer + replay buffer).
3. Lightweight bundle — saved at stage end AND on emergency exit.
4. Emergency save     — on ANY unhandled exception: bundle + native checkpoint
   + traceback written to stage_N/emergency/{timestamp}/.
5. Multi-path restore — on stage start, tries in order:
     (a) within-stage native checkpoint  (most recent progress)
     (b) previous-stage final bundle     (inter-stage weight transfer)
     (c) fresh start                     (no prior weights)
   Each path has its own try/except; next path tried on failure.
6. Resume mode        — `--resume` reads curriculum_state.json and
   continues from the exact iteration that was interrupted.

Usage
-----
  # Fresh start
  python train_curriculum.py --algorithm ppo --use-lstm --output-name f16_v1

  # Resume after crash
  python train_curriculum.py --algorithm ppo --use-lstm --output-name f16_v1 --resume

  # Resume from a specific native RLlib checkpoint
  python train_curriculum.py --algorithm ppo --restore-checkpoint artifacts/.../checkpoint

  # Restart from a lightweight policy bundle (weights only)
  python train_curriculum.py --algorithm ppo --init-bundle artifacts/.../final_bundle

  # Force a specific starting stage (skips prior stages, no weight transfer)
  python train_curriculum.py --algorithm ppo --output-name f16_v1 --start-stage 2
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import zlib
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent   # Release/ 루트
SRC  = ROOT / "src"
for p in (ROOT, SRC):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)
_pythonpath_entries = [str(ROOT), str(SRC)]
_existing_pythonpath = os.environ.get("PYTHONPATH", "")
if _existing_pythonpath:
    _pythonpath_entries.append(_existing_pythonpath)
os.environ["PYTHONPATH"] = os.pathsep.join(_pythonpath_entries)
_RAY_RAYLET_START_WAIT_TIME_S = "60"

# Keep console output stable on cp949 Windows terminals (no UnicodeEncodeError
# when stdout is piped/redirected).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

from ray.tune.registry import register_env

from DogFightEnvWrapper import DogFightWrapper
from dogfight.ai.checkpoint_io import (
    apply_lightweight_policy_bundle,
    save_lightweight_policy_bundle,
)
from dogfight.ai.engagement_replay_logger import EngagementReplayLogger
from dogfight.ai.policy_probe_logger import PolicyProbeLogger
from dogfight.ai.dashboard_logger import DashboardJsonlLogger
from dogfight.ai.curriculum import (
    CurriculumStage,
    build_stage_env_config,
    check_advancement,
    check_advancement_episodes,
    get_stages,
)
from dogfight.ai.rllib_utils import (
    build_algorithm_config,
    normalize_algorithm_name,
)
from dogfight.ai.student_hooks import (
    load_curriculum_stages,
    load_observation_hook,
    load_reward_hook,
)
from dogfight.ai.training_record import save_training_record
from dogfight.envs.observation import (
    observation_size as builtin_observation_size,
)


def _ensure_ray_runtime_env() -> None:
    """Restart Ray with local project paths available to worker actors."""
    import ray

    # 2026-05-29: Give slower PCs more time for raylet/GCS startup after shutdown.
    os.environ.setdefault("RAY_raylet_start_wait_time_s", _RAY_RAYLET_START_WAIT_TIME_S)
    ray.shutdown()
    ray.init(
        ignore_reinit_error=True,
        include_dashboard=False,
        runtime_env={
            "env_vars": {
                "PYTHONPATH": os.environ["PYTHONPATH"],
                "RAY_raylet_start_wait_time_s": os.environ[
                    "RAY_raylet_start_wait_time_s"
                ],
            }
        },
    )


def env_creator(env_config):
    cfg = dict(env_config)
    cfg["_runner_index"] = getattr(
        env_config,
        "worker_index",
        cfg.get("_runner_index", "local"),
    )
    cfg["_env_index"] = getattr(
        env_config,
        "vector_index",
        cfg.get("_env_index", 0),
    )
    reward_fn = None
    observation_hook = None
    reward_module = str(cfg.get("reward_module", "")).strip()
    if reward_module:
        reward_fn, reward_config = load_reward_hook(reward_module)
        cfg.setdefault("reward", reward_config)
    observation_module = str(cfg.get("observation_module", "")).strip()
    if observation_module:
        observation_hook = load_observation_hook(observation_module)
        cfg["observation_mode"] = observation_hook["mode"]
        cfg["observation_module"] = observation_module
        cfg["observation_summary"] = observation_hook["description"]
    # [MOD-TEACHERHOOK] Drive the scripted teacher through the stock
    # `target_action_provider` hook instead of the old `target_mode == "teacher"`
    # branch. That branch calls FighterSim.step_auto_cmd(), which this workspace
    # does not have -- FighterSim.py is kept byte-identical to the SDK. The hook
    # is already in single_agent_env._step_target_aircraft and takes precedence
    # over target_mode, so no platform file needs the 24-line addition.
    target_provider = None
    teacher_spec = cfg.get("target_teacher")
    if teacher_spec:
        from student.teacher_provider import TeacherActionProvider
        # `_runner_index` is a STRING by platform convention ("local", and
        # "engagement_replay" from the replay logger). int() on it raised
        # ValueError while EngagementReplayLogger.maybe_log swallows exceptions,
        # so every replay silently produced an empty directory (measured
        # 2026-08-02: 0 replay CSVs anywhere in the workspace). crc32 keeps the
        # seed deterministic across processes; hash() does not.
        def _index_seed(value) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return zlib.crc32(str(value).encode("utf-8")) % 100000
        seed = _index_seed(cfg.get("_runner_index", 0)) * 1000 +             _index_seed(cfg.get("_env_index", 0))
        target_provider = TeacherActionProvider(teacher_spec, seed=seed)

    # [MOD-RLOPPONENT] a stage may fly a trained 38-dim policy as the enemy.
    # The old workspace's bundles are all observation_size 38 while this one
    # trains on 16, so RLOpponentProvider gives the opponent its OWN builder.
    # Takes precedence over target_teacher.
    rl_bundle = cfg.get("target_rl_bundle")
    if rl_bundle:
        from student.rl_opponent import RLOpponentProvider
        target_provider = RLOpponentProvider(
            bundle_dir=str(rl_bundle),
            step_ratio=int(cfg.get("step_ratio") or 6),
            explore=bool(cfg.get("target_rl_explore", False)),
        )

    env = DogFightWrapper(
        cfg,
        reward_fn=reward_fn,
        observation_fn=observation_hook["build_observation"] if observation_hook else None,
        observation_size=observation_hook["size"] if observation_hook else None,
        observation_low=observation_hook["low"] if observation_hook else None,
        observation_high=observation_hook["high"] if observation_hook else None,
        target_action_provider=target_provider,
    )
    if reward_module and "reward" in cfg:
        env.config["reward"] = dict(cfg["reward"])
    return env


def _build_observation_bundle_metadata(
    env_config: dict,
    fallback_mode: str,
) -> dict[str, Any]:
    """Return serializable observation metadata for lightweight bundles."""
    mode = str(env_config.get("observation_mode", fallback_mode))
    summary = env_config.get("observation_summary")
    if isinstance(summary, dict):
        observation_summary = dict(summary)
    else:
        observation_summary = None

    observation_size = None
    if observation_summary is not None:
        observation_size = _to_positive_int(observation_summary.get("size"))
    if observation_size is None:
        observation_size = _to_positive_int(env_config.get("observation_size"))
    if observation_size is None:
        observation_size = _to_positive_int(builtin_observation_size(mode))

    return {
        "obs_mode": mode,
        "observation_mode": mode,
        "observation_module": env_config.get("observation_module", ""),
        "observation_size": observation_size,
        "observation_summary": observation_summary,
    }


def _build_curriculum_bundle_metadata(
    args,
    algorithm_name: str,
    env_config: dict,
    *,
    stage: CurriculumStage | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build metadata for curriculum lightweight bundles."""
    metadata = {
        "algorithm": algorithm_name,
        **_build_observation_bundle_metadata(env_config, args.observation_mode),
        "action_dim": 4,
        "env_class": "DogFightWrapper",
        "target_mode": env_config.get("target_mode", ""),
        "use_lstm": args.use_lstm,
        "lstm_cell_size": args.lstm_cell_size if args.use_lstm else None,
        "max_seq_len": args.max_seq_len if args.use_lstm else None,
        "network_spec": (
            json.loads(args.network_spec_json) if args.network_spec_json else None
        ),
    }
    if stage is not None:
        metadata.update({"stage_index": stage.index, "stage_name": stage.name})
    if extra:
        metadata.update(extra)
    return metadata


def _to_positive_int(value: Any) -> int | None:
    """Return a positive integer value or None if unavailable."""
    if value is None or isinstance(value, bool):
        return None
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


# -- CLI -----------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Curriculum training for dogfight RL.")
    p.add_argument("--algorithm",         choices=["ppo"], default="ppo")
    p.add_argument("--framework",         default="torch", choices=["torch"])
    p.add_argument("--num-env-runners",   type=int, default=1)
    p.add_argument("--observation-mode",  default="tactical16",
                   choices=["classic12", "relative14", "tactical16", "custom"])
    p.add_argument("--observation-module", default="",
                   help="Optional module with custom observation size and build_observation(...).")
    p.add_argument("--target-behavior-dll", default="AIP_BASE_target.dll")
    p.add_argument("--lr",                type=float, default=3e-4)
    p.add_argument("--gamma",             type=float, default=0.99)
    p.add_argument("--train-batch-size",  type=int,   default=4096)
    p.add_argument("--minibatch-size",    type=int,   default=256)
    # RLlib's default is 30. With a 24,576 batch and 512 minibatches that is
    # 1,440 gradient steps per iteration -- enough for PPO to undo the std
    # clamp within a single iteration (entropy settled at -1.5 instead of the
    # -5.6 the clamp sets) and enough to walk a good policy a long way on one
    # batch of advantages.
    # [MOD-UPDATESIZE] 30 은 RLlib 기본. batch 16384 / minibatch 1024 이면
    # iteration 당 480 경사하강이라 첫 갱신 KL 이 0.326 까지 튀었다(실측).
    p.add_argument("--num-epochs",        type=int,   default=10)
    # [MOD-UPDATESIZE] RLlib 기본 0.2 는 이 과제에 너무 약하다. BC 로 심은
    # std 0.10 정책은 확률비가 민감해 첫 갱신 KL 이 3.334 까지 튀었고(건강한
    # 값은 0.01), 적응형 kl_coeff 가 KL 을 잡는 9 iteration 사이에 승률이
    # 1.000 -> 0.044 로 파괴됐다(실측 0803_bcaim).
    p.add_argument("--kl-coeff",          type=float, default=1.0,
                   help="PPO KL penalty coefficient (RLlib default 0.2).")
    p.add_argument("--grad-clip",         type=float, default=1.0,
                   help="Global-norm gradient clip. RLlib default is None.")
    p.add_argument("--vf-loss-coeff",     type=float, default=0.5,
                   help="Value loss weight. vf_share_layers is True, so this "
                        "gradient also flows through the policy encoder.")
    # Deterministic gate evaluation (see rllib_utils.build_algorithm_config).
    p.add_argument("--gate-eval-episodes",  type=int, default=30,
                   help="episodes per deterministic evaluation (0 disables)")
    p.add_argument("--gate-eval-interval",  type=int, default=5,
                   help="run a deterministic evaluation every N iterations")
    p.add_argument("--gate-eval-runners",   type=int, default=4)
    p.add_argument("--anchor-bundle", default="",
                   help="frozen policy bundle for the KL anchor (empty = off)")
    p.add_argument("--anchor-coef", type=float, default=0.0,
                   help="initial KL-anchor coefficient")
    p.add_argument("--anchor-half-life-iters", type=float, default=80.0,
                   help="iterations for the anchor coefficient to halve")
    p.add_argument("--regression-baseline", default="",
                   help="frozen benchmark scorecard to guard against")
    p.add_argument("--regression-tolerance", type=float, default=0.20)
    p.add_argument("--regression-episodes", type=int, default=8)
    p.add_argument("--regression-exempt", action="append", default=[],
                   metavar="STAGE:CASE",
                   help="benchmark case whose regression is REPORTED but does "
                        "not block promotion, scoped to one stage, e.g. "
                        "15:turn_shallow_2000. Repeatable. A bare CASE applies "
                        "to every stage (discouraged -- it hides a real "
                        "collapse from the verdict for the rest of the run).")
    p.add_argument("--policy-std-cap", type=float, default=0.0,
                   help="hold the Gaussian exploration std at this value after "
                        "every iteration (0 = let PPO move it freely)")
    p.add_argument("--gae-lambda",        type=float, default=0.95)
    p.add_argument("--kl-target",         type=float, default=None,
                   help="[MOD-KLTARGET] adaptive-KL target (RLlib default 0.01); the step size cap per iteration")
    p.add_argument("--clip-param",        type=float, default=0.2)
    p.add_argument("--entropy-coeff",     type=float, default=None,
                   help="PPO entropy bonus coefficient (default: RLlib default).")
    p.add_argument("--model-fcnet-hiddens", default=None,
                   help="Comma-separated RLlib model hidden sizes, e.g. 512,256,128.")
    p.add_argument("--model-fcnet-activation", default=None,
                   help="RLlib model encoder activation, e.g. relu or tanh.")
    p.add_argument("--model-head-fcnet-hiddens", default=None,
                   help="Comma-separated RLlib model head hidden sizes, or empty for none.")
    p.add_argument("--model-head-fcnet-activation", default=None,
                   help="RLlib model head activation, e.g. relu or tanh.")
    p.add_argument("--model-vf-share-layers", default=None,
                   help="Whether PPO value function shares layers: true or false.")
    p.add_argument("--network-spec-json", default="",
                   help=("JSON object for DogFight sequence_v1 network layout. "
                         "Usually supplied by scripts/run_experiment.py from algo.network."))
    p.add_argument("--use-lstm", action="store_true",
                   help="Enable RLlib DefaultModelConfig LSTM for PPO.")
    p.add_argument("--lstm-cell-size", type=int, default=64,
                   help="LSTM hidden state size for --use-lstm.")
    p.add_argument("--max-seq-len", type=int, default=8,
                   help="Train sequence length for --use-lstm.")
    p.add_argument("--debug-io", dest="debug_io", action="store_true",
                   help="Print recurrent RLlib debug I/O shape checks.")
    p.add_argument("--debug-lstm-io", dest="debug_io", action="store_true",
                   help=argparse.SUPPRESS)
    p.add_argument("--policy-probe-interval", type=int, default=0,
                   help=("Log fixed policy probe actions every N total iterations. "
                         "0 disables policy_probe.csv/jsonl."))
    p.add_argument("--policy-probe-steps", type=int, default=4,
                   help="Number of recurrent inference steps per policy probe.")
    p.add_argument("--no-policy-probe-print", action="store_true",
                   help="Write policy probe files without console summaries.")
    p.add_argument("--engagement-log-interval", type=int, default=0,
                   help=("Run a short policy-vs-target replay every N total "
                         "iterations and save Tacview CSV logs. 0 disables it."))
    p.add_argument("--engagement-log-steps", type=int, default=600,
                   help="Maximum environment steps per engagement replay episode.")
    p.add_argument("--engagement-log-episodes", type=int, default=1,
                   help="Number of replay episodes to save at each interval.")
    p.add_argument("--no-engagement-log-print", action="store_true",
                   help="Write engagement replay files without console summaries.")
    # [MOD-STDCLIP] exp(-1.2) = 0.301. From the kill sweep, not taste.
    # [MOD-VFCLIP] RLlib PPO 기본값은 10. 우리 수익은 수백 단위라
    # 크리틱이 절대 따라잡지 못한다(실측 explained_var -0.98~0.04).
    # 1000 이면 사실상 클리핑 없음 - 최대 |수익| ~800 보다 크다.
    p.add_argument("--vf-clip-param", type=float, default=1000.0,
                   help="PPO value-function clip. RLlib default 10 is far "
                        "below this project's return scale.")
    p.add_argument("--log-std-clip", type=float, default=-1.2,
                   help="Upper bound on the policy log_std (std <= exp(x)). "
                        "RLlib default is 20, i.e. std up to 4.8e8.")
    p.add_argument("--output-name",       default="f16_curriculum")
    p.add_argument("--output-tag",        default="v1")
    p.add_argument("--resume",            action="store_true",
                   help="Resume from curriculum_state.json of a previous run.")
    p.add_argument("--start-stage",       type=int, default=None,
                   help="Force-start at this stage index (ignores state file).")
    p.add_argument("--notes",             default="")
    p.add_argument("--reward-module",     default="",
                   help="Optional module with MY_REWARD_CONFIG and compute_reward(...).")
    p.add_argument("--stages-module",     default="",
                   help="Optional module with get_stages() returning CurriculumStage list.")
    p.add_argument("--restore-checkpoint", default="",
                   help="Restore a full RLlib native checkpoint for the first active stage.")
    p.add_argument("--init-bundle", "--restart-from-bundle", dest="init_bundle",
                   default="",
                   help="Load lightweight policy bundle weights for the first active stage.")
    p.add_argument("--experiment-yaml",   default="",
                   help="Optional source experiment YAML path for records.")
    args = p.parse_args()
    if args.restore_checkpoint and args.init_bundle:
        p.error("--restore-checkpoint and --init-bundle are mutually exclusive.")
    return args


def _build_model_config_args(args: argparse.Namespace) -> dict[str, Any]:
    model_config = {
        "fcnet_hiddens": args.model_fcnet_hiddens,
        "fcnet_activation": args.model_fcnet_activation,
        "head_fcnet_hiddens": args.model_head_fcnet_hiddens,
        "head_fcnet_activation": args.model_head_fcnet_activation,
        "vf_share_layers": args.model_vf_share_layers,
    }
    if args.network_spec_json:
        model_config["network_spec"] = json.loads(args.network_spec_json)
    # [MOD-STDCLIP] Bound the Gaussian policy's log_std.
    # RLlib's default log_std_clip_param is 20, i.e. std may reach
    # exp(20) = 4.8e8, and with no usable reward gradient it goes there:
    # measured 2026-08-03, action std went 0.150 -> 0.71 -> 5.3 -> 434 ->
    # 5.7e7 over 1,900 iterations while win_rate stayed 0.00. A std past
    # ~0.2 already stops this task scoring (12-episode sweep: 3/12 kills
    # deterministic, 2/12 at 0.15, 1/12 at 0.25, 0/12 at 0.32).
    model_config.setdefault("log_std_clip_param", float(args.log_std_clip))
    model_config["enabled"] = any(value is not None for value in model_config.values())
    return model_config


def _sync_lstm_args_from_init_bundle(args) -> None:
    """Align LSTM architecture args with a lightweight bundle before build."""

    if not args.init_bundle:
        return

    bundle_path = Path(args.init_bundle)
    metadata_path = bundle_path / "metadata.json"
    if not metadata_path.exists():
        return

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    bundle_meta = payload.get("metadata", {})
    saved_model_config = bundle_meta.get("model_config") or {}
    if not saved_model_config.get("use_lstm"):
        return

    lstm_cell_size = int(
        saved_model_config.get("lstm_cell_size")
        or bundle_meta.get("lstm_cell_size")
        or args.lstm_cell_size
    )
    max_seq_len = int(
        saved_model_config.get("max_seq_len")
        or bundle_meta.get("max_seq_len")
        or args.max_seq_len
    )
    network_spec = (
        saved_model_config.get("dogfight_network_spec")
        or bundle_meta.get("network_spec")
    )

    changed = (
        not args.use_lstm
        or args.lstm_cell_size != lstm_cell_size
        or args.max_seq_len != max_seq_len
        or (
            network_spec is not None
            and args.network_spec_json
            != json.dumps(network_spec, ensure_ascii=False, separators=(",", ":"))
        )
    )
    args.use_lstm = True
    args.lstm_cell_size = lstm_cell_size
    args.max_seq_len = max_seq_len
    if network_spec is not None:
        args.network_spec_json = json.dumps(
            network_spec, ensure_ascii=False, separators=(",", ":")
        )
    if changed:
        print(
            "[DogFightEnv][LSTM_RESUME] "
            f"init_bundle={bundle_path} use_lstm=True "
            f"lstm_cell_size={lstm_cell_size} max_seq_len={max_seq_len} "
            f"network_type={(network_spec or {}).get('type')}"
        )


# -- Metric helpers ------------------------------------------------------------

def _extract_learner_stats(result: dict) -> dict:
    keys = (
        "policy_loss", "vf_loss", "entropy", "kl", "clip_frac", "explained_var",
        "anchor_kl", "anchor_coef",
        "actor_loss", "critic_loss", "alpha_loss", "alpha", "target_entropy",
        "replay_buffer_size", "replay_buffer_memory_mb", "env_steps_per_sec",
        "learner_steps_per_sec", "iteration_time_s",
    )
    stats = {k: "n/a" for k in keys}
    learners = result.get("learners", {})
    if learners:
        ps = learners.get("default_policy") or next(
            (v for k, v in learners.items() if k != "__all_modules__"),
            {},
        )
        stats.update({
            "policy_loss":   ps.get("policy_loss",   "n/a"),
            "vf_loss":       ps.get("vf_loss",        "n/a"),
            "entropy":       ps.get("entropy",         "n/a"),
            "kl":            ps.get("mean_kl_loss",   ps.get("kl", "n/a")),
            "clip_frac":     ps.get("clip_frac",       "n/a"),
            "explained_var": ps.get("vf_explained_var","n/a"),
            # the declaration tuple above only sets "n/a" defaults; a key that
            # is not ALSO read here never leaves the learner. Done that twice.
            "anchor_kl":     ps.get("anchor_kl",       "n/a"),
            "anchor_coef":   ps.get("anchor_coef",     "n/a"),
        })
        _fill_optional_learner_stats(stats, ps, result)
        return stats
    ps = next(iter(result.get("info", {}).get("learner", {}).values()), {})
    if ps:
        stats.update({
            "policy_loss":   ps.get("policy_loss",    "n/a"),
            "vf_loss":       ps.get("vf_loss",         "n/a"),
            "entropy":       ps.get("entropy",          "n/a"),
            "kl":            ps.get("kl",               "n/a"),
            "clip_frac":     ps.get("clip_frac",        "n/a"),
            "explained_var": ps.get("vf_explained_var", "n/a"),
        })
        _fill_optional_learner_stats(stats, ps, result)
    return stats


def _fill_optional_learner_stats(stats: dict, policy_stats: dict, result: dict) -> None:
    def first_present(*names: str):
        for source in (policy_stats, result):
            for name in names:
                if name in source and source[name] is not None:
                    return source[name]
        return "n/a"

    stats["actor_loss"] = first_present("actor_loss", "policy_loss")
    stats["critic_loss"] = first_present("critic_loss", "qf_loss", "q_loss")
    stats["alpha_loss"] = first_present("alpha_loss")
    stats["alpha"] = first_present("alpha", "alpha_value")
    if stats["alpha"] == "n/a":
        log_alpha = first_present("log_alpha_value", "curr_log_alpha")
        if isinstance(log_alpha, (int, float)):
            stats["alpha"] = math.exp(float(log_alpha))
    stats["target_entropy"] = first_present("target_entropy")
    stats["replay_buffer_size"] = first_present(
        "replay_buffer_size", "num_steps_trained_this_iter"
    )
    stats["env_steps_per_sec"] = first_present(
        "env_steps_per_sec", "num_env_steps_sampled_throughput_per_sec"
    )
    stats["learner_steps_per_sec"] = first_present(
        "learner_steps_per_sec", "num_env_steps_trained_throughput_per_sec"
    )
    stats["iteration_time_s"] = first_present("time_this_iter_s")


def _fill_algorithm_runtime_stats(stats: dict, algorithm: Any) -> None:
    """Fill direct-loop stats that RLlib does not always place in result."""
    replay_buffer = getattr(algorithm, "local_replay_buffer", None)
    if replay_buffer is None:
        return

    if stats.get("replay_buffer_memory_mb") == "n/a":
        stats["replay_buffer_memory_mb"] = _estimate_object_memory_mb(replay_buffer)

    if stats.get("replay_buffer_size") != "n/a":
        return

    for getter_name in ("get_num_timesteps", "get_num_episodes"):
        getter = getattr(replay_buffer, getter_name, None)
        if getter is None:
            continue
        try:
            stats["replay_buffer_size"] = getter()
            return
        except Exception:
            pass

    try:
        stats["replay_buffer_size"] = len(replay_buffer)
    except Exception:
        pass


def _estimate_object_memory_mb(obj: Any) -> Any:
    """Estimate Python object memory recursively, returned in MiB."""
    if obj is None:
        return "n/a"

    seen: set[int] = set()

    def sizeof(value: Any, depth: int = 0) -> int:
        obj_id = id(value)
        if obj_id in seen:
            return 0
        seen.add(obj_id)

        size = sys.getsizeof(value, 0)
        nbytes = getattr(value, "nbytes", None)
        if isinstance(nbytes, int):
            size += nbytes
            return size
        if hasattr(value, "numel") and hasattr(value, "element_size"):
            try:
                size += int(value.numel()) * int(value.element_size())
                return size
            except Exception:
                return size
        if depth >= 8:
            return size

        if isinstance(value, dict):
            for key, item in value.items():
                size += sizeof(key, depth + 1)
                size += sizeof(item, depth + 1)
        elif isinstance(value, (list, tuple, set, frozenset)):
            for item in value:
                size += sizeof(item, depth + 1)
        elif hasattr(value, "__dict__"):
            size += sizeof(vars(value), depth + 1)
        return size

    try:
        return sizeof(obj) / (1024.0 * 1024.0)
    except Exception:
        return "n/a"


def _extract_custom_metrics(result: dict) -> dict:
    cm = result.get("env_runners", {}).get("custom_metrics", {})

    def metric(name: str):
        # New API logs plain keys ("win"); old API aggregates to "win_mean".
        for key in (f"{name}_mean", name):
            if key in cm and cm[key] is not None:
                return cm[key]
        return "n/a"

    extracted = {
        "win_rate":          metric("win"),
        "loss_rate":         metric("loss"),
        "draw_rate":         metric("draw"),   # [MOD-TIE 2026-08-29] 동시격추
        "timeout_rate":      metric("timeout"),
        "crash_rate":        metric("crash"),
        # [MOD-JUDGE] full-time fights decided on damage advantage
        "judge_win_rate":    metric("judge_win"),
        "judge_loss_rate":   metric("judge_loss"),
        "ep_wez_steps":      metric("ep_wez_steps"),
        "ep_mean_distance":  metric("ep_mean_distance"),
        "ep_min_distance":   metric("ep_min_distance"),
        "ep_reward_survival":metric("ep_reward_survival"),
        "ep_reward_pursuit": metric("ep_reward_pursuit"),
        "ep_reward_damage":  metric("ep_reward_damage"),
        "ep_altitude_penalty_steps": metric("ep_altitude_penalty_steps"),
        "action_sat_rate":   metric("action_saturation_rate"),
        "action_roll_mean":  metric("action_roll_mean"),
        "action_pitch_mean": metric("action_pitch_mean"),
        "action_rudder_mean":metric("action_rudder_mean"),
        "action_throttle_mean": metric("action_throttle_mean"),
        "action_roll_std":   metric("action_roll_std"),
        "action_pitch_std":  metric("action_pitch_std"),
        "action_rudder_std": metric("action_rudder_std"),
        "action_throttle_std": metric("action_throttle_std"),
        "initial_alpha_deg": metric("initial_alpha_deg"),
        "initial_ata_deg":   metric("initial_ata_deg"),
        "initial_aa_deg":    metric("initial_aa_deg"),
        "initial_distance_m":metric("initial_distance_m"),
        "final_ata_deg":     metric("final_ata_deg"),
        "final_aa_deg":      metric("final_aa_deg"),
        "headon_guard_fail": metric("headon_guard_fail"),
    }
    # Per-opponent breakdown. These keys are DYNAMIC (one pair per opponent in
    # the pool), so a fixed extraction list silently drops them -- the detector
    # would record faithfully and show nothing. Passed through by prefix.
    for key, value in cm.items():
        if not key.startswith("vs_") or value is None:
            continue
        extracted[key[:-5] if key.endswith("_mean") else key] = value
    # [MOD-REWARDCOMPS] Reward components are DYNAMIC too -- one per term in
    # my_reward.py -- and the three listed above (survival, pursuit, damage) are
    # names the reward stopped emitting long ago. Everything the reward actually
    # computes was therefore dropped here, which is why metrics.jsonl carried a
    # single reward series and a newly added term could not be checked while a
    # run was in progress. Same prefix pass-through as the per-opponent keys.
    for key, value in cm.items():
        if not key.startswith("ep_reward_") or value is None:
            continue
        name = key[:-5] if key.endswith("_mean") else key
        extracted.setdefault(name, value)
    return extracted


def _fmt(val, fmt=".4f"):
    return f"{val:{fmt}}" if isinstance(val, (int, float)) else str(val)


def _console_header(algorithm_name: str) -> str:
    base = (
        f"{'St':>2} {'Iter':>5} | {'Reward':>10} | "
        f"{'Win%':>6} | {'Crash%':>7} | {'WEZ':>6} | "
    )
    return base + f"{'Entropy':>8} | {'VF_loss':>8} |"


_CSV_FIELDS = [
    "stage", "iter_in_stage", "total_iter",
    "reward_mean", "ep_len_mean", "episodes_this_iter",
    "win_rate", "loss_rate", "draw_rate", "timeout_rate", "crash_rate",
    "judge_win_rate", "judge_loss_rate",
    "ep_wez_steps", "ep_mean_distance", "ep_min_distance",
    "ep_reward_survival", "ep_reward_pursuit", "ep_reward_damage",
    # [MOD-REWARDCOMPS] my_reward.py 가 내는 성분: aim / range /
    # damage / deck / terminal / step. DictWriter 는 fieldnames 에 없는
    # 키를 만나면 ValueError 로 죽는다 - 성분 이름 하나 바꿨다고 학습이
    # 첫 iteration 에서 멈춘 적이 있다(실측).
    "ep_reward_aim", "ep_reward_aim_wide",
    "ep_reward_range", "ep_reward_deck", "ep_reward_ceil", "ep_reward_alt",
    "ep_reward_underrun",
    "ep_reward_terminal", "ep_reward_step",
    "ep_reward_track", "ep_reward_gunsnap_blue", "ep_reward_gunsnap_red",
    "ep_altitude_penalty_steps",
    "action_sat_rate",
    "action_roll_mean", "action_pitch_mean", "action_rudder_mean",
    "action_throttle_mean", "action_roll_std", "action_pitch_std",
    "action_rudder_std", "action_throttle_std",
    "initial_alpha_deg", "initial_ata_deg", "initial_aa_deg",
    "initial_distance_m", "final_ata_deg", "final_aa_deg",
    "headon_guard_fail",
    # Deterministic gate evaluation (present only on evaluation iterations).
    "eval_win_rate", "eval_crash_rate", "eval_loss_rate", "eval_wez_steps",
    "eval_episodes",
    "anchor_kl", "anchor_coef",
    "policy_loss", "vf_loss", "entropy", "kl", "clip_frac", "explained_var",
    "actor_loss", "critic_loss", "alpha_loss", "alpha", "target_entropy",
    "replay_buffer_size", "replay_buffer_memory_mb", "env_steps_per_sec",
    "learner_steps_per_sec", "iteration_time_s",
    # 열 어긋남 방지: 새 필드는 반드시 끝에 추가 (2026-08-05 교훈)
    "ep_reward_overspeed",
    "ep_reward_perch",
    "ep_reward_far",
    "ep_reward_wez",
    "ep_reward_snap",
    "ep_reward_close",
    "ep_reward_nmd",
    "ep_reward_cpa",
    # ep_reward_high 하나로 순상승을 읽을 수 있다:
    #   순상승(m) = -ep_reward_high / w_high * high_span_m
    # 포텐셜이라 총합이 (끝-시작)뿐이기 때문. 별도 고도 지표를 안 만든 이유.
    "ep_reward_high",
    # [2026-08-16] stage 34 선회고도 선호. 이 열이 없으면 항이 작동하는지
    # 학습 중에 볼 수 없다 — 순상승은 -ep_reward_high/w*span 로 역산했지만
    # turnalt 는 봉우리형이라 부호만으로는 고도를 못 읽으므로 열이 필요하다.
    "ep_reward_turnalt",
]

# -- CurriculumTrainer ---------------------------------------------------------

class CurriculumTrainer:

    STAGES: list[CurriculumStage] = get_stages()

    def __init__(self, args):
        self.args = args
        self.algorithm_name = normalize_algorithm_name(args.algorithm)
        self.stages = (
            load_curriculum_stages(args.stages_module)
            if args.stages_module
            else self.STAGES
        )
        self.curriculum_dir = (
            ROOT / "artifacts" / "curriculum" / args.output_name / args.output_tag
        )
        self.curriculum_dir.mkdir(parents=True, exist_ok=True)
        self.state_path   = self.curriculum_dir / "curriculum_state.json"
        self.csv_path     = self.curriculum_dir / "training_log.csv"
        # ONE place for every replay this run produces -- the periodic ones,
        # the best-policy ones and their paired failures. The dashboard watches
        # this directory and picks up new captures live. It used to be pointed
        # at a folder of copied CSVs, which went stale the moment training wrote
        # the next one and made it look like replays had stopped being saved.
        self.replay_dir = (ROOT / "artifacts" / "replays"
                           / f"{args.output_name}_{args.output_tag}")
        self.replay_dir.mkdir(parents=True, exist_ok=True)
        # The dashboard reads metrics.jsonl. Only train_rllib.py wrote one, so
        # curriculum runs -- the main training path -- produced no dashboard
        # data at all and the board sat empty while a run was going.
        self.dashboard_logger = DashboardJsonlLogger(
            ROOT / "artifacts" / "dashboard",
            f"{args.output_name}_{args.output_tag}",
            config=vars(args),
            append=True,
        )
        self._total_iter  = 0
        self._explicit_checkpoint_restored = False
        self._explicit_bundle_loaded = False
        # [MOD-GUARDCACHE] the promotion path records _guard_cache["detail"]
        # unconditionally; the skipped/BROKEN guard returns used to leave the
        # attribute unset and the run died WITH ITS GATE MET (6d 07-24 16:08,
        # 6f 17:05 -- 'CurriculumTrainer' object has no attribute '_guard_cache').
        self._guard_cache = {}

        env_preview_config = {
            "observation_mode":    args.observation_mode,
            "target_mode":         "fixed",
            "target_behavior_dll": args.target_behavior_dll,
            "ownship_control_mode":"rl",
        }
        if args.reward_module:
            env_preview_config["reward_module"] = args.reward_module
        if args.observation_module:
            env_preview_config["observation_module"] = args.observation_module
        env_preview = env_creator(env_preview_config)
        self.base_env_config = {
            **env_preview_config,
            "observation_mode": env_preview.config["observation_mode"],
            "reward": dict(env_preview.config["reward"]),
            "wez":    dict(env_preview.config["wez"]),
        }
        if args.observation_module:
            self.base_env_config["observation_module"] = args.observation_module
            self.base_env_config["observation_summary"] = dict(
                env_preview.config["observation_summary"]
            )
        obs_shape = getattr(env_preview.observation_space, "shape", (0,))
        action_shape = getattr(env_preview.action_space, "shape", (4,))
        self._probe_obs_dim = int(obs_shape[0]) if obs_shape else 0
        self._probe_action_dim = int(action_shape[0]) if action_shape else 4
        env_preview.close()
        self.policy_probe_logger = PolicyProbeLogger(
            self.curriculum_dir,
            obs_dim=self._probe_obs_dim,
            action_dim=self._probe_action_dim,
            interval=args.policy_probe_interval,
            sequence_steps=args.policy_probe_steps,
            print_to_console=not args.no_policy_probe_print,
            append=args.resume,
        )
        self.engagement_replay_logger = EngagementReplayLogger(
            self.replay_dir,
            env_factory=env_creator,
            env_config=self.base_env_config,
            interval=args.engagement_log_interval,
            max_steps=args.engagement_log_steps,
            episodes=args.engagement_log_episodes,
            print_to_console=not args.no_engagement_log_print,
            append=args.resume,
        )

    def run(self):
        _ensure_ray_runtime_env()
        state = self._init_or_load_state()

        if state["status"] == "completed":
            print("Curriculum already completed. Use a different --output-tag to restart.")
            return

        csv_exists = self.csv_path.exists()
        with open(self.csv_path, "a", newline="", encoding="utf-8") as csv_file:
            # extrasaction="ignore": a metric appearing only on some
            # iterations must not abort a run mid-stage.
            writer = csv.DictWriter(csv_file, fieldnames=_CSV_FIELDS,
                                    extrasaction="ignore")
            if not csv_exists:
                writer.writeheader()
            self._csv_writer = writer
            self._csv_file   = csv_file
            self.policy_probe_logger.__enter__()
            self.engagement_replay_logger.__enter__()

            try:
                for stage in self.stages:
                    # [MOD-STAGEAPPEND] a stage added to the module AFTER the
                    # run began has no ledger entry, and resume crashed with
                    # KeyError on it (hit 2026-07-23 when the league stage 20
                    # was appended to a completed run). Backfill the same
                    # pending template _initial_state writes; existing entries
                    # are never touched, so history is preserved.
                    stage_state = state["stages"].setdefault(str(stage.index), {
                        "status":              "pending",
                        "iterations_trained":  0,
                        "advance_reason":      None,
                        "final_bundle_dir":    None,
                        "last_bundle_dir":     None,
                        "last_checkpoint_dir": None,
                        "emergency_dirs":      [],
                        "metric_history":      [],
                    })
                    if stage_state["status"] == "completed":
                        self._total_iter += stage_state.get("iterations_trained", 0)
                        print(f"[Stage {stage.index}] Already completed - skipping.")
                        continue
                    if self.args.start_stage is not None and stage.index < self.args.start_stage:
                        self._total_iter += stage_state.get("iterations_trained", 0)
                        print(f"[Stage {stage.index}] Skipped by --start-stage.")
                        continue

                    self._run_stage(stage, state)

                    if state.get("status") == "failed":
                        print(f"\n[Stage {stage.index}] Failed. Run with --resume to continue.")
                        break
                else:
                    state["status"] = "completed"
                    self._save_state(state)
                    print("=== Curriculum training completed ===")
            finally:
                self.policy_probe_logger.__exit__(None, None, None)
                self.engagement_replay_logger.__exit__(None, None, None)
                if self.policy_probe_logger.enabled:
                    print(f"policy probe CSV saved to {self.policy_probe_logger.csv_path}")
                    print(f"policy probe JSONL saved to {self.policy_probe_logger.jsonl_path}")
                if self.engagement_replay_logger.enabled:
                    print(
                        "engagement replay index saved to "
                        f"{self.engagement_replay_logger.csv_path}"
                    )
                    print(
                        "engagement replay JSONL saved to "
                        f"{self.engagement_replay_logger.jsonl_path}"
                    )

    def _run_stage(self, stage: CurriculumStage, state: dict):
        stage_state = state["stages"][str(stage.index)]
        start_iter  = stage_state.get("iterations_trained", 0)
        metric_window: list[dict] = list(stage_state.get("metric_history", []))

        print(f"\n{'='*60}")
        print(f"  Stage {stage.index}: {stage.name}")
        print(f"  {stage.description}")
        print(f"  target_mode={stage.target_mode}  "
              f"max_iter={stage.max_iterations}  resume_from={start_iter}")
        print(f"{'='*60}")

        stage_env_config = build_stage_env_config(self.base_env_config, stage)
        env_name = f"dogfight-curriculum-stage{stage.index}"
        register_env(env_name, env_creator)

        algorithm = self._build_algorithm(stage, stage_env_config, env_name)
        self._prev_eps_lifetime = 0   # [MOD-EPI] lifetime counter restarts per stage
        # [MOD-EVALFLOOR] breach counter is PER STAGE: without the reset, one
        # breach left over from a previous stage silently halved the next
        # stage's two-strike allowance. And the floor only ARMS after the
        # first eval at/above it -- a warm-started bundle's transient dip on
        # entry (offline-to-online, measured stage 11: 0.902 -> 0.737) must
        # not count as a collapse before the stage ever reached its floor.
        self._floor_breaches = 0
        self._floor_armed = False
        self._floor_last_eval = None
        self._kill_breaches = 0            # [MOD-KILLFLOOR] per-stage reset
        self._kill_armed = False
        self._kill_last = None
        self._guard_cooldown_until = -1   # [MOD-GUARDCOOL] per-stage reset
        state["current_stage"] = stage.index
        stage_state["status"]  = "in_progress"
        # A resumed run must not keep wearing the previous crash's "failed"
        # label while it is actively training -- the watchdog reads this field
        # and walked away from a live run because of the stale verdict (07-22).
        state["status"]     = "running"
        state["last_error"] = None
        self._save_state(state)

        self._restore_weights(algorithm, stage, stage_state, state)

        interrupted_iter = start_iter
        try:
            for it in range(start_iter, stage.max_iterations):
                interrupted_iter = it
                try:
                    result = algorithm.train()
                except Exception as train_exc:
                    print(f"\n[Stage {stage.index}] algorithm.train() failed at iter {it}: {train_exc}")
                    self._emergency_save(algorithm, stage, it, state, train_exc)
                    raise

                if self.args.policy_std_cap > 0.0:
                    _clamp_policy_std(algorithm, self.args.policy_std_cap)

                metrics = self._collect_metrics(result, stage.index, it, algorithm)

                # Keep the best weights this stage ever reached. Fine-tuning a
                # cloned policy degrades before it recovers (a documented
                # offline-to-online effect, and measured here: stage 11 peaked
                # at 0.902 on iteration 4 and was at 0.737 by iteration 24), so
                # saving only the final bundle throws away the best policy the
                # run produced.
                current_eval = metrics.get("eval_win_rate")
                if isinstance(current_eval, (int, float)) and current_eval == current_eval:
                    best_so_far = stage_state.get("best_eval_win_rate")
                    # [MOD-BESTTIE] ties REFRESH the bundle (>=, was >): at an
                    # eval ceiling the strict test froze best_bundle forever
                    # (stage 26 iter 34; stage 28 iter 128) and the guard kept
                    # judging stale weights -- the 07-24/25 deadlocks. A tie
                    # now re-saves the CURRENT weights; the replay capture
                    # stays strict-improvement-only so ceiling refreshes cost
                    # seconds, not a 2-episode recording per eval.
                    improved = best_so_far is None or current_eval > best_so_far
                    if improved or current_eval >= best_so_far:
                        try:
                            best_dir = self._stage_dir(stage) / "best_bundle"
                            save_lightweight_policy_bundle(
                                algorithm, best_dir,
                                metadata=_build_curriculum_bundle_metadata(
                                    self.args, self.algorithm_name,
                                    stage_env_config, stage=stage),
                            )
                            stage_state["best_eval_win_rate"] = float(current_eval)
                            stage_state["best_bundle_dir"] = str(best_dir)
                            stage_state["best_bundle_iter"] = int(it)
                            self._save_state(state)
                            if improved:
                                self._capture_best_replay(stage, best_dir, it)
                                print(f"  -> new best for stage {stage.index}: "
                                      f"eval_win_rate={current_eval:.3f} (iter {it}) "
                                      f"saved to {best_dir}")
                        except Exception as bexc:
                            print(f"  [WARNING] best bundle save failed: {bexc}")
                metric_window.append(metrics)

                self._csv_writer.writerow({
                    "stage": stage.index, "iter_in_stage": it,
                    "total_iter": self._total_iter, **metrics,
                })
                self._csv_file.flush()
                self.dashboard_logger.write_row(
                    {"stage": stage.index, "iter_in_stage": it,
                     "total_iter": self._total_iter, **metrics},
                    step_key="total_iter",
                )
                self.policy_probe_logger.maybe_log(
                    algorithm,
                    iteration=self._total_iter,
                    sampled_steps=self._total_iter,
                    stage=stage.index,
                )
                self.engagement_replay_logger.env_config = stage_env_config
                self.engagement_replay_logger.maybe_log(
                    algorithm,
                    iteration=self._total_iter,
                    sampled_steps=self._total_iter,
                    stage=stage.index,
                )

                stage_state["iterations_trained"]    = it + 1
                # [MOD-EPI] keep more history in episode mode
                keep = max(stage.advance_window * 2, 200) if int(
                    getattr(stage, "advance_episodes", 0)
                ) > 0 else stage.advance_window * 2
                stage_state["metric_history"]        = metric_window[-keep:]
                state["total_iterations_elapsed"]    = self._total_iter
                state["updated_at"]                  = _now()
                self._save_state(state)
                self._total_iter += 1

                if (it + 1) % stage.checkpoint_interval == 0:
                    self._save_checkpoint(algorithm, stage, it + 1, stage_state, state)

                self._print_row(stage.index, it, metrics)

                # [MOD-EVALFLOOR] hard stop on eval collapse: the league's
                # passivity ratchet took the ace eval 0.93 -> 0.67 while the
                # iteration floor forced training to continue. Two consecutive
                # finite evals below the stage's floor end the stage as
                # failed -- rollback beats grinding in the wrong direction.
                floor = float(getattr(stage, "eval_hard_floor", 0.0) or 0.0)
                if floor > 0.0:
                    ev = metrics.get("eval_win_rate")
                    if isinstance(ev, (int, float)) and math.isfinite(float(ev)):
                        prev_ev = getattr(self, "_floor_last_eval", None)
                        if float(ev) >= floor:
                            # first eval at/above the floor ARMS the trip
                            # wire; until then sub-floor evals are the
                            # warm-start transient, not a collapse
                            self._floor_armed = True
                            self._floor_breaches = 0
                        elif getattr(self, "_floor_armed", False):
                            if (prev_ev is not None
                                    and float(ev) >= float(prev_ev) + 0.05):
                                # sub-floor but climbing: the recovery leg of
                                # a V-shaped dip, not a collapse. A collapse
                                # keeps falling or sits flat; hold the counter
                                # instead of tripping on the way back up
                                # (0.897->0.576->0.826 aborted a stage 0.024
                                # short of its floor while WEZ time rose).
                                pass
                            else:
                                self._floor_breaches = getattr(
                                    self, "_floor_breaches", 0) + 1
                        self._floor_last_eval = float(ev)
                        if self._floor_breaches >= 2:
                            msg = (f"eval hard floor: two consecutive gate "
                                   f"evals below {floor} (last {ev:.3f})")
                            print(f"\n  !! Stage {stage.index} ABORTED: {msg}")
                            stage_state["status"] = "gate_failed"
                            stage_state["last_error"] = msg
                            state["status"] = "failed"
                            self._save_state(state)
                            return
                # [MOD-KILLFLOOR] honest-kill dual floor: eval_win_rate above
                # is a ~224-ep sliding window that HID a collapse (07-25: gate
                # 0.92-1.0 while honest ace kill was 0.458). An out-of-process
                # deterministic ace-kill probe every eval_kill_probe_interval
                # iters catches what the window smooths over. Same two-strike +
                # recovery-grace logic as eval_hard_floor. Only runs after
                # min_iterations (skip the warm-start transient) and never
                # aborts on a probe that failed to run (nan = broken tool, not
                # a collapse). This is the self-play ignition blocker.
                kfloor = float(getattr(stage, "eval_kill_floor", 0.0) or 0.0)
                kint = int(getattr(stage, "eval_kill_probe_interval", 25) or 25)
                if (kfloor > 0.0 and (it + 1) >= int(getattr(stage, "min_iterations", 0) or 0)
                        and (it + 1) % kint == 0):
                    kr = self._honest_kill_probe(algorithm, stage)
                    if math.isfinite(kr):
                        kprev = getattr(self, "_kill_last", None)
                        stage_state["last_kill_probe"] = kr
                        if kr >= kfloor:
                            self._kill_armed = True
                            self._kill_breaches = 0
                            print(f"  + kill-floor probe: ace kill {kr:.3f} "
                                  f">= {kfloor} (clear)")
                        elif getattr(self, "_kill_armed", False):
                            if kprev is not None and kr >= float(kprev) + 0.05:
                                print(f"  ~ kill-floor probe: {kr:.3f} below "
                                      f"{kfloor} but climbing (grace held)")
                            else:
                                self._kill_breaches = getattr(
                                    self, "_kill_breaches", 0) + 1
                                print(f"  ! kill-floor probe: ace kill {kr:.3f} "
                                      f"< {kfloor} (breach "
                                      f"{self._kill_breaches}/2)")
                        else:
                            print(f"  ~ kill-floor probe: {kr:.3f} < {kfloor} "
                                  f"but floor not yet armed (warm-start)")
                        self._kill_last = kr
                        # [MOD-KILLPROBE] a stage can keep the PROBE (its
                        # bundle is what snapshot_sidecar turns into the
                        # self-play pool) while disarming the ABORT. Required
                        # for pure self-play stages: they never fight the ace,
                        # so an ace-kill floor is a tripwire on a skill the
                        # stage does not train, and it fires around iter 45.
                        # Default True => every existing stage is unchanged.
                        if not bool(getattr(stage, "eval_kill_abort", True)):
                            if getattr(self, "_kill_breaches", 0) >= 2:
                                print("  ~ kill-floor breaches ignored "
                                      "(eval_kill_abort=False, probe only)")
                                self._kill_breaches = 0
                        elif getattr(self, "_kill_breaches", 0) >= 2:
                            msg = (f"honest kill floor: two consecutive ace "
                                   f"probes below {kfloor} (last {kr:.3f})")
                            print(f"\n  !! Stage {stage.index} ABORTED: {msg}")
                            stage_state["status"] = "gate_failed"
                            stage_state["last_error"] = msg
                            state["status"] = "failed"
                            self._save_state(state)
                            return
                # [MOD-MINITERS] the gate stays shut below the stage's floor:
                # a warm-started bundle can ace a teacher-based gate on entry
                # (stage 20 read 0.933 at iter 4) and graduate a league stage
                # that trained nothing. The floor spends the budget first.
                min_iters = int(getattr(stage, "min_iterations", 0) or 0)
                if min_iters > 0 and (it + 1) < min_iters:
                    continue
                # [MOD-EPI] episode-based early graduation when configured
                if int(getattr(stage, "advance_episodes", 0)) > 0:
                    ok, reason = check_advancement_episodes(stage, metric_window)
                    # [MOD-GUARDCOOL] a held verdict suppresses the guard for
                    # 25 iterations. Without the cooldown a stage whose gate
                    # stays met but whose guard keeps holding thrashes:
                    # measured 07-24, stage 25 progressed ~30 iters in 5 hours
                    # (4 min of training per 20-min guard run) and the
                    # 25-iter replay cadence never fired.
                    cool_until = getattr(self, "_guard_cooldown_until", -1)
                    if ok and self.args.regression_baseline and it < cool_until:
                        ok = False
                        print(f"    gate met; guard on cooldown until iter "
                              f"{cool_until} (last verdict: held)")
                    elif ok and self.args.regression_baseline:
                        held, detail = self._regression_guard(algorithm, stage)
                        if held:
                            ok = False
                            self._guard_cooldown_until = it + 25
                            print(f"  ! Stage {stage.index} met its gate but "
                                  f"REGRESSED on the frozen benchmark: {detail}")
                            print("    training continues; the gate is "
                                  "re-checked as it recovers")
                        elif detail.startswith("BROKEN") or "skipped" in detail:
                            # [MOD-GUARDCACHE] a guard that could not run must
                            # not be mistaken for one that passed: hold the
                            # gate and retry after the cooldown, exactly like a
                            # held verdict. (Before 07-25 this branch advanced
                            # UNPROTECTED -- a broken guard flipped the design
                            # into its opposite.)
                            ok = False
                            self._guard_cooldown_until = it + 25
                            print(f"  !! regression guard did NOT run: {detail}")
                            print("    holding the gate; retry after cooldown")
                        else:
                            print(f"  + regression guard clear: {detail}")
                    if ok:
                        if self.args.regression_baseline:
                            # permanent record of what the guard measured (and
                            # possibly tolerated) at the moment of promotion
                            stage_state["regression_note"] = \
                                self._guard_cache.get("detail")
                        print(f"\n  + Stage {stage.index} advancement: {reason}")
                        break
                else:
                    window = metric_window[-stage.advance_window:]
                    if len(window) >= stage.advance_window:
                        ok, reason = check_advancement(stage, window)
                        if ok:
                            print(f"\n  + Stage {stage.index} advancement: {reason}")
                            break

            stage_state["status"] = "completed"
            passed = bool(locals().get("ok", False))
            stage_state["advance_reason"] = reason if passed else "max_iterations_reached"
            # [MOD-GATEFAIL] Do NOT carry a policy that failed its gate into
            # harder stages. Measured 2026-07-20: stages 1 and 2 both exhausted
            # max_iterations with win_rate 0.00 and the run silently advanced,
            # so stage 3 was training a policy that had never scored a kill.
            # Failing loudly here forces a fix (reward/teacher/gate) instead of
            # burning hours on a broken curriculum.
            # [MOD-SOFTGATE 2026-08-24] gate_optional 인 칸은 조건 미달이어도
            # 런을 세우지 않고 다음 칸으로 넘긴다(사용자 지시: "드릴만 넘기는거").
            if not passed and stage.advance_conditions and getattr(stage, "gate_optional", False):
                msg = (
                    chr(10) + '  ~ Stage %d (%s) hit max_iterations '
                    'WITHOUT meeting %s -- gate_optional, 그냥 다음 칸으로 넘어간다.'
                    % (stage.index, stage.name, stage.advance_conditions)
                )
                print(msg)
            elif not passed and stage.advance_conditions:
                stage_state["status"] = "gate_failed"
                state["status"] = "failed"
                self._save_state(state)
                print(
                    f"\n  ! Stage {stage.index} ({stage.name}) hit max_iterations "
                    f"WITHOUT meeting {stage.advance_conditions}.\n"
                    f"    Stopping instead of advancing a policy that cannot do "
                    f"this stage. Fix the stage, then --resume."
                )
                return

        except KeyboardInterrupt:
            print(f"\n[Stage {stage.index}] Interrupted at iter {interrupted_iter}.")
            self._emergency_save(algorithm, stage, interrupted_iter, state,
                                 RuntimeError("KeyboardInterrupt"))
            stage_state["status"] = "interrupted"
            state["status"]       = "failed"
            self._save_state(state)
            algorithm.stop()
            raise

        except Exception as exc:
            stage_state["status"] = "failed"
            state["status"]       = "failed"
            state["last_error"]   = str(exc)
            self._save_state(state)
            algorithm.stop()
            raise

        finally:
            try:
                bundle_dir = self._stage_dir(stage) / "final_bundle"
                save_lightweight_policy_bundle(
                    algorithm,
                    bundle_dir,
                    metadata=_build_curriculum_bundle_metadata(
                        self.args,
                        self.algorithm_name,
                        stage_env_config,
                        stage=stage,
                    ),
                )
                stage_state["final_bundle_dir"] = str(bundle_dir)
                self._save_state(state)
                print(f"  -> Final bundle saved: {bundle_dir}")
            except Exception as bexc:
                print(f"  [WARNING] Final bundle save failed: {bexc}")

            try:
                algorithm.stop()
            except Exception:
                pass

        try:
            record_dir = (ROOT / "artifacts" / "records" /
                          self.args.output_name / self.args.output_tag /
                          f"stage_{stage.index}")
            save_training_record(
                output_dir=record_dir,
                algorithm_name=self.algorithm_name,
                cli_args=vars(self.args),
                env_config=stage_env_config,
                algorithm_config={},
                result_history=metric_window,
                workspace_root=ROOT,
            )
        except Exception as rexc:
            print(f"  [WARNING] Training record save failed: {rexc}")

    def _build_algorithm(self, stage: CurriculumStage, env_config: dict, env_name: str):
        args = self.args
        config = build_algorithm_config(
            algorithm_name=self.algorithm_name,
            env_name=env_name,
            env_config=env_config,
            args={
                "framework":        args.framework,
                "num_env_runners":  args.num_env_runners,
                "lr":               args.lr,
                "gamma":            args.gamma,
                "train_batch_size": args.train_batch_size,
                "minibatch_size":   args.minibatch_size,
                "gae_lambda":       args.gae_lambda,
                "clip_param":       args.clip_param,
                "vf_clip_param":    args.vf_clip_param,
                "entropy_coeff":    args.entropy_coeff,
                "num_epochs":       args.num_epochs,
                "grad_clip":        args.grad_clip,
                "kl_coeff":         args.kl_coeff,
                "kl_target":        args.kl_target,   # [MOD-KLTARGET]
                "vf_loss_coeff":    args.vf_loss_coeff,
                "model_config": _build_model_config_args(args),
                "network_spec": args.network_spec_json,
                "use_lstm": args.use_lstm,
                "lstm_cell_size": args.lstm_cell_size,
                "max_seq_len": args.max_seq_len,
                "debug_io": args.debug_io,
                "anchor": ({
                    "bundle": args.anchor_bundle,
                    "coef": args.anchor_coef,
                    # geometric decay per gradient update, calibrated so the
                    # coefficient halves every anchor_half_life_iters
                    "decay_per_update": 0.5 ** (
                        1.0 / max(args.anchor_half_life_iters, 0.1)
                        / max((args.train_batch_size // max(args.minibatch_size, 1))
                              * max(args.num_epochs, 1), 1)),
                } if args.anchor_bundle and args.anchor_coef > 0 else None),
                "evaluation": ({
                    "episodes": args.gate_eval_episodes,
                    "interval": args.gate_eval_interval,
                    "runners":  args.gate_eval_runners,
                } if args.gate_eval_episodes > 0 else None),
            },
        )
        return config.build_algo()

    def _restore_weights(self, algorithm, stage: CurriculumStage,
                         stage_state: dict, state: dict):
        if self.args.restore_checkpoint and not self._explicit_checkpoint_restored:
            ckpt_path = Path(self.args.restore_checkpoint)
            if not ckpt_path.exists():
                raise FileNotFoundError(f"restore checkpoint not found: {ckpt_path}")
            print(f"  [Restore] Explicit native checkpoint -> {ckpt_path}")
            algorithm.restore(str(ckpt_path))
            self._explicit_checkpoint_restored = True
            stage_state["last_checkpoint_dir"] = str(ckpt_path)
            self._save_state(state)
            print("  [Restore] [OK] Explicit checkpoint restored successfully.")
            return

        if self.args.init_bundle and not self._explicit_bundle_loaded:
            bundle_path = Path(self.args.init_bundle)
            if not bundle_path.exists():
                raise FileNotFoundError(f"lightweight bundle not found: {bundle_path}")
            print(f"  [Restore] Explicit lightweight bundle -> {bundle_path}")
            self._apply_bundle_weights(algorithm, str(bundle_path))
            self._explicit_bundle_loaded = True
            stage_state["restart_bundle_dir"] = str(bundle_path)
            self._save_state(state)
            print("  [Restore] [OK] Explicit bundle weights loaded successfully.")
            return

        ckpt = stage_state.get("last_checkpoint_dir")
        if ckpt:
            ckpt = str(Path(ckpt).resolve())   # [MOD-RELPATH] 상태 파일엔 상대경로가 올 수 있다; pyarrow 는 절대경로만 받는다
        if ckpt and Path(ckpt).exists():
            print(f"  [Restore] Path 1: native checkpoint -> {ckpt}")
            try:
                algorithm.restore(ckpt)
                print(f"  [Restore] [OK] Checkpoint restored successfully.")
                return
            except Exception as exc:
                print(f"  [Restore] [X] Checkpoint restore failed: {exc}")

        if stage.index > 0:
            previous = state["stages"].get(str(stage.index - 1), {})
            prev_bundle = (previous.get("best_bundle_dir")
                           or previous.get("final_bundle_dir"))
            if prev_bundle and Path(prev_bundle).exists():
                print(f"  [Restore] Path 2: previous-stage bundle -> {prev_bundle}")
                try:
                    self._apply_bundle_weights(algorithm, prev_bundle)
                    print(f"  [Restore] [OK] Weight transfer from stage {stage.index - 1} succeeded.")
                    return
                except Exception as exc:
                    print(f"  [Restore] [X] Weight transfer failed: {exc}")

            for prev_idx in range(stage.index - 2, -1, -1):
                fallback_bundle = state["stages"].get(str(prev_idx), {}).get("final_bundle_dir")
                if fallback_bundle and Path(fallback_bundle).exists():
                    print(f"  [Restore] Path 2b: fallback bundle stage {prev_idx} -> {fallback_bundle}")
                    try:
                        self._apply_bundle_weights(algorithm, fallback_bundle)
                        print(f"  [Restore] [OK] Fallback transfer from stage {prev_idx} succeeded.")
                        return
                    except Exception as exc:
                        print(f"  [Restore] [X] Fallback failed: {exc}")

            for prev_idx in range(stage.index - 1, -1, -1):
                emg_dirs = state["stages"].get(str(prev_idx), {}).get("emergency_dirs", [])
                for emg in reversed(emg_dirs):
                    emg_bundle = Path(emg) / "bundle"
                    if emg_bundle.exists():
                        print(f"  [Restore] Path 2c: emergency bundle -> {emg_bundle}")
                        try:
                            self._apply_bundle_weights(algorithm, str(emg_bundle))
                            print(f"  [Restore] [OK] Emergency bundle transfer succeeded.")
                            return
                        except Exception as exc:
                            print(f"  [Restore] [X] Emergency bundle failed: {exc}")

        print(f"  [Restore] Path 3: fresh start (no prior weights loaded).")

        # Nothing above restored anything: no explicit checkpoint, no explicit
        # bundle, no previous-stage bundle, no stage checkpoint. The run will
        # proceed from RANDOM weights while --resume keeps appending to the
        # same metric history, which looks like the run continuing. Measured
        # 2026-07-21: a resumed stage went win 0.58 -> 0.00 and anchor_kl
        # 0.02 -> 5.26 before anyone noticed. Say it loudly.
        print("  !! [Restore] RESTORED NOTHING - training starts from RANDOM "
              "weights. If this stage was warm-started before, pass "
              "--init-bundle again; --resume alone cannot restore weights "
              "until the first checkpoint exists.")


    def _apply_bundle_weights(self, algorithm, bundle_dir: str):
        apply_lightweight_policy_bundle(algorithm, bundle_dir)

    def _save_checkpoint(self, algorithm, stage: CurriculumStage, iteration: int,
                         stage_state: dict, state: dict):
        ckpt_dir = self._stage_dir(stage) / "checkpoints" / f"iter_{iteration:04d}"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        try:
            algorithm.save(str(ckpt_dir))
            stage_state["last_checkpoint_dir"] = str(ckpt_dir)
            self._save_state(state)
            print(f"  [Checkpoint] Saved iter {iteration} -> {ckpt_dir}")
        except Exception as exc:
            print(f"  [WARNING] Checkpoint save failed at iter {iteration}: {exc}")

    def _emergency_save(self, algorithm, stage: CurriculumStage,
                        iteration: int, state: dict, exc: Exception):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        emg_root = self._stage_dir(stage) / "emergency" / timestamp
        emg_root.mkdir(parents=True, exist_ok=True)
        print(f"\n  [EMERGENCY] Saving to {emg_root}")
        try:
            tb = traceback.format_exc()
            (emg_root / "exception.txt").write_text(
                f"{type(exc).__name__}: {exc}\n\n{tb}", encoding="utf-8"
            )
        except Exception:
            pass
        bundle_ok = False
        try:
            stage_env_config = build_stage_env_config(self.base_env_config, stage)
            save_lightweight_policy_bundle(
                algorithm,
                emg_root / "bundle",
                metadata=_build_curriculum_bundle_metadata(
                    self.args,
                    self.algorithm_name,
                    stage_env_config,
                    stage=stage,
                    extra={"iteration": iteration, "emergency": True},
                ),
            )
            bundle_ok = True
            print(f"  [EMERGENCY] [OK] Bundle saved.")
        except Exception as e2:
            print(f"  [EMERGENCY] [X] Bundle failed: {e2}")
        ckpt_ok = False
        try:
            algorithm.save(str(emg_root / "checkpoint"))
            ckpt_ok = True
            print(f"  [EMERGENCY] [OK] Native checkpoint saved.")
        except Exception as e2:
            print(f"  [EMERGENCY] [X] Native checkpoint failed: {e2}")
        try:
            ss = state["stages"][str(stage.index)]
            emg_entry = {
                "timestamp": timestamp, "iteration": iteration,
                "bundle_ok": bundle_ok, "ckpt_ok": ckpt_ok,
                "path": str(emg_root),
            }
            ss.setdefault("emergency_dirs", []).append(str(emg_root))
            ss["last_emergency"] = emg_entry
            if ckpt_ok:
                ss["last_checkpoint_dir"] = str(emg_root / "checkpoint")
            if bundle_ok:
                ss["last_bundle_dir"] = str(emg_root / "bundle")
            state["last_error"] = f"{type(exc).__name__}: {exc}"
            self._save_state(state)
        except Exception as e3:
            print(f"  [EMERGENCY] State update failed: {e3}")

    def _init_or_load_state(self) -> dict:
        if self.args.resume and self.state_path.exists():
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
            print(f"[Resume] Loaded state from {self.state_path}")
            print(f"  Current stage: {state['current_stage']}  "
                  f"Total iters: {state['total_iterations_elapsed']}")
            self._total_iter = state.get("total_iterations_elapsed", 0)
            return state

        if self.state_path.exists() and not self.args.resume:
            raise RuntimeError(
                f"State file exists at {self.state_path}.\n"
                "  Use --resume to continue, or choose a different --output-tag."
            )

        state = {
            "output_name":               self.args.output_name,
            "output_tag":                self.args.output_tag,
            "algorithm":                 self.algorithm_name,
            "obs_mode":                  self.base_env_config.get(
                "observation_mode",
                self.args.observation_mode,
            ),
            "status":                    "in_progress",
            "current_stage":             self.stages[0].index,
            "current_iteration":         0,
            "total_iterations_elapsed":  0,
            "created_at":                _now(),
            "updated_at":                _now(),
            "notes":                     self.args.notes,
            "stages": {
                str(s.index): {
                    "status":              "pending",
                    "iterations_trained":  0,
                    "advance_reason":      None,
                    "final_bundle_dir":    None,
                    "last_bundle_dir":      None,
                    "last_checkpoint_dir": None,
                    "emergency_dirs":      [],
                    "metric_history":      [],
                }
                for s in self.stages
            },
        }
        if self.args.start_stage is not None:
            state["current_stage"] = self.args.start_stage
        self._save_state(state)
        return state

    def _save_state(self, state: dict):
        state["updated_at"] = _now()
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.state_path)

    def _stage_dir(self, stage: CurriculumStage) -> Path:
        d = self.curriculum_dir / f"stage_{stage.index}_{stage.name}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _collect_metrics(
        self,
        result: dict,
        stage_idx: int,
        it: int,
        algorithm: Any,
    ) -> dict:
        env_m   = result.get("env_runners", {})
        custom  = _extract_custom_metrics(result)
        learner = _extract_learner_stats(result)
        _fill_algorithm_runtime_stats(learner, algorithm)
        # [MOD-EPI] per-iteration episode count for episode-based advancement
        eps_this_iter = env_m.get("num_episodes")
        if not isinstance(eps_this_iter, (int, float)):
            eps_lifetime = env_m.get("num_episodes_lifetime")
            if isinstance(eps_lifetime, (int, float)):
                prev = getattr(self, "_prev_eps_lifetime", 0) or 0
                eps_this_iter = max(0, int(eps_lifetime) - int(prev))
                self._prev_eps_lifetime = int(eps_lifetime)
            else:
                eps_this_iter = "n/a"
        # Deterministic evaluation, when this iteration ran one. Kept under
        # separate keys so the gate can prefer it without the noisy training
        # win rate being averaged into it.
        evaluation = result.get("evaluation") or {}
        eval_env = evaluation.get("env_runners", evaluation) or {}
        eval_custom = _extract_custom_metrics({"env_runners": eval_env})
        eval_metrics = {}
        # RLlib carries the last evaluation result forward on the iterations
        # between evaluations, so recording it every time would let the gate
        # count one 30-episode evaluation as 60 and pass on half the evidence
        # it thinks it has. Record each evaluation exactly once.
        # [MOD-EVALFLOOR] episode_return_mean joins the fingerprint: it is
        # continuous-valued, so two GENUINE consecutive evaluations that both
        # read 0.0 win rate (exactly the collapse the hard floor exists to
        # catch) no longer collide with the carry-forward ghost and vanish.
        fingerprint = (eval_custom.get("win_rate"), eval_env.get("num_episodes"),
                       eval_custom.get("ep_wez_steps"),
                       eval_env.get("episode_return_mean"))
        repeated = fingerprint == getattr(self, "_last_eval_fingerprint", None)
        self._last_eval_fingerprint = fingerprint
        # [MOD-JUDGE] NaN is a float: RLlib's metric carry-forward emits one
        # ghost row exactly two iters after every real evaluation (743 real :
        # 743 nan measured over the whole log), and the isinstance check let
        # it through. Gates and best were already _finite-guarded downstream;
        # this stops the ghost at the source.
        _wr = eval_custom.get("win_rate")
        if not repeated and isinstance(_wr, (int, float)) \
                and math.isfinite(float(_wr)):
            eval_metrics = {
                "eval_win_rate":   eval_custom.get("win_rate"),
                "eval_crash_rate": eval_custom.get("crash_rate"),
                # being shot down only became a possible outcome once the
                # opponent could shoot; without this key a loss_rate_max gate
                # would find nothing to read and pass silently
                "eval_loss_rate":  eval_custom.get("loss_rate"),
                "eval_wez_steps":  eval_custom.get("ep_wez_steps"),
                # the count that actually completed, not the count requested:
                # a partial evaluation must not be weighted as a full one
                "eval_episodes":   (eval_env.get("num_episodes")
                                    if isinstance(eval_env.get("num_episodes"),
                                                  (int, float))
                                    else self.args.gate_eval_episodes),
            }

        return {
            "stage":             stage_idx,
            "iter_in_stage":     it,
            "total_iter":        self._total_iter,
            "reward_mean":       env_m.get("episode_return_mean", "n/a"),
            "ep_len_mean":       env_m.get("episode_len_mean",    "n/a"),
            "episodes_this_iter": eps_this_iter,
            **custom,
            **learner,
            **eval_metrics,
        }

    def _capture_best_replay(self, stage, bundle_dir, iteration: int) -> None:
        """Record a kill replay for each new best policy, in the background.

        The periodic engagement log samples whatever the policy happens to be
        every N iterations, which is rarely the one worth watching: of the
        three duel5 captured, two were timeouts. What anyone actually wants to
        see is the best policy so far, winning.

        Fire-and-forget subprocess, for two reasons. It must not add its
        episodes to the training loop's wall clock, and it must not build an
        RLlib Algorithm inside this process -- doing that in the regression
        guard killed the trainer's Ray actors. At most one runs at a time; if
        the previous capture is still going, this best is skipped rather than
        queued, because the next one will be better anyway.
        """
        import subprocess
        import sys as _sys

        previous = getattr(self, "_replay_proc", None)
        if previous is not None and previous.poll() is None:
            return
        out_dir = (self.replay_dir / "best"
                   / f"stage{stage.index:02d}_iter{iteration:04d}")
        try:
            self._replay_proc = subprocess.Popen(
                [_sys.executable, "-m", "student.tools.save_kill_replay",
                 "--bundle-dir", str(bundle_dir),
                 "--stage", str(stage.index),
                 "--max-episodes", "8",
                 "--out-dir", str(out_dir)],
                cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            print(f"  -> capturing a replay of this best in the background "
                  f"-> {out_dir}")
        except Exception as exc:
            print(f"  [WARNING] best-replay capture could not start: {exc}")

    def _isolated_ray_env(self) -> dict:
        """Environment for a scorer subprocess so its Ray does not fight ours.

        build_algorithm_from_bundle calls ray.shutdown() + ray.init(). Run in a
        child that inherited the trainer's Ray session vars, that shutdown/init
        collides with the live cluster and the child blocks forever waiting on
        raylet -- measured 2026-07-25, every kill-floor probe and regression
        guard hung the whole trainer at iter 60 of self-play. Clearing the
        inherited session vars and forcing a fresh local instance isolates it.
        """
        import os as _os
        env = dict(_os.environ)
        for key in ("RAY_ADDRESS", "RAY_SESSION_DIR", "RAY_NODE_IP_ADDRESS",
                    "RAY_RAYLET_PID", "RAY_JOB_ID", "RAY_GCS_ADDRESS"):
            env.pop(key, None)
        env["RAY_ADDRESS"] = "local"          # never attach to the trainer cluster
        return env

    def _honest_kill_probe(self, algorithm, stage) -> float:
        """Deterministic ace-kill rate of the LIVE weights, out-of-process.

        Same isolation reasoning as _regression_guard: scoring in-process
        would build a second RLlib Algorithm and kill the trainer's Ray
        actors. Returns the kill rate, or nan if the probe could not run --
        a broken measurement must never be read as a collapse ([MOD-KILLFLOOR]).
        """
        import json as _json
        import subprocess
        import sys as _sys

        probe_dir = self._stage_dir(stage) / "killfloor_probe"
        try:
            save_lightweight_policy_bundle(
                algorithm, probe_dir,
                metadata=_build_curriculum_bundle_metadata(
                    self.args, self.algorithm_name, self.base_env_config,
                    stage=stage))
            out = self._stage_dir(stage) / "killfloor_probe.json"
            eps = int(getattr(stage, "eval_kill_probe_episodes", 48) or 48)
            # [MOD-PROBEBUNDLE] bundle-only mode. The bundle above is the only
            # thing a self-play stage needs from this probe -- snapshot_sidecar
            # turns it into the opponent pool -- while the eval subprocess below
            # is what makes the trainer die. Measured 2026-07-30: the trainer
            # was killed at exactly the probe iterations (90 on the 30 s run, 30
            # on the qualifier run, both probe points), with the probe's own
            # result file written but last_kill_probe never recorded, and the
            # log ending in "[JSB][Reset] fighter_count_after=0" then "training
            # exited with code -1". The subprocess initialises JSBSim a second
            # time and the DLL's BattleSpace is shared, so the trainer's
            # aircraft disappear on the next reset. Skipping the eval keeps the
            # snapshots and removes the crash; the ace kill rate is simply not
            # measured, which costs nothing on a stage that never fights the ace.
            if not bool(getattr(stage, "eval_kill_probe_eval", True)):
                print("  -> probe bundle written (eval skipped: "
                      "eval_kill_probe_eval=False)")
                out.write_text(_json.dumps(
                    {"summary": {"win_rate": float("nan"), "episodes": 0,
                                 "note": "bundle-only probe, eval skipped"}}),
                    encoding="utf-8")
                return float("nan")
            # DEVNULL, not a pipe: eval_winrate floods JSBSim init logs, and a
            # captured pipe deadlocks once the 64 KB buffer fills (child blocks
            # on write, parent blocks on wait without reading) -- measured
            # 2026-07-25, the trainer hung 16 min on a probe whose result file
            # was already written. The result comes from --json-out, so nothing
            # of value is lost. timeout cut to 900 s as a backstop.
            completed = subprocess.run(
                [_sys.executable, "student/tools/eval_winrate.py",
                 "--bundle-dir", str(probe_dir),
                 "--opponent", "teacher", "--teacher", "ace",
                 "--episodes", str(eps),
                 "--json-out", str(out)],
                cwd=str(ROOT), stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=900,
                env=self._isolated_ray_env())
            if completed.returncode != 0 or not out.exists():
                raise RuntimeError(
                    f"probe subprocess rc={completed.returncode}, "
                    f"out_exists={out.exists()}")
            data = _json.loads(out.read_text(encoding="utf-8"))
            return float(data["summary"]["win_rate"])
        except Exception as exc:
            print(f"  !! kill-floor probe did not run: "
                  f"{type(exc).__name__}: {str(exc)[:200]}")
            return float("nan")

    def _regression_guard(self, algorithm, stage) -> tuple[bool, str]:
        """Refuse to advance a stage that traded away an old skill.

        Detection without enforcement is not prevention: the frozen benchmark
        measured defensive_foe 1.000 -> 0.583 after the cadet duel stage and
        the curriculum advanced anyway, because nothing joined them.

        Runs in a SUBPROCESS. The first version built a second RLlib Algorithm
        inside the training process to score the probe, and tearing it down
        killed the trainer's own actors:

            Failed to submit task to actor ... It might be dead

        A stub test passed because it ran with no training in flight, which is
        exactly the condition the bug needs. Scoring out-of-process cannot
        touch the trainer's Ray state, and it reuses benchmark.py unchanged.
        """
        import json as _json
        import subprocess
        import sys as _sys
        from pathlib import Path as _Path

        baseline_path = _Path(self.args.regression_baseline)
        if not baseline_path.exists():
            detail = f"baseline {baseline_path} missing, guard skipped"
            # [MOD-GUARDCACHE] every exit records a verdict for the promotion note
            self._guard_cache = {"stamp": None, "held": False, "detail": detail}
            return False, detail
        try:
            baseline = {r["case"]: r for r in _json.loads(
                baseline_path.read_text(encoding="utf-8"))["results"]}
            # Judge the artifact that advancement actually promotes. The next
            # stage warm-starts from the stage's BEST bundle, but this used to
            # probe the current weights -- measured 2026-07-21, the best bundle
            # (iter 24) scored ace 0.500 and would pass while the live weights
            # scored ace 0.000 and held the stage. With an unconsolidated skill
            # oscillating between evaluations, judging the live weights makes
            # promotion a matter of timing luck, in both directions.
            best_dir = self._stage_dir(stage) / "best_bundle"
            if best_dir.exists():
                probe_dir = best_dir
                # The gate can re-open every advancement window while the best
                # bundle stays the same, and each guard run blocks the training
                # loop for the length of a benchmark subprocess (measured
                # 5-8 minutes). Same bundle -> same verdict: reuse it.
                weights = probe_dir / "policy_weights.pkl.gz"
                stamp = weights.stat().st_mtime if weights.exists() else None
                cached = getattr(self, "_guard_cache", None)
                # [MOD-GUARDCACHE] only CLEAR verdicts are reusable. "Same
                # bundle -> same verdict" holds for a pass, but a HOLD is a
                # recoverable state measured with 24-episode noise (measured
                # 07-23: violent read 0.583 on one 24-ep draw and 0.729 at 48
                # episodes) -- caching it while the best bundle sits at an
                # eval ceiling (mtime never changes) froze promotion with no
                # path to re-judge. A held verdict now re-measures every time
                # the gate re-opens.
                if cached and cached.get("stamp") == stamp \
                        and not cached.get("held"):
                    held, detail = cached["held"], cached["detail"]
                    print(f"  + regression guard (cached, bundle unchanged): "
                          f"clear {detail}")
                    return held, detail
            else:
                probe_dir = self._stage_dir(stage) / "regression_probe"
                save_lightweight_policy_bundle(
                    algorithm, probe_dir,
                    metadata=_build_curriculum_bundle_metadata(
                        self.args, self.algorithm_name, self.base_env_config,
                        stage=stage))

            tag = f"guard_stage{stage.index}"
            out_dir = ROOT / "artifacts" / "benchmark"
            completed = subprocess.run(
                [_sys.executable, "-m", "student.tools.benchmark",
                 "--bundle-dir", str(probe_dir), "--tag", tag,
                 "--episodes", str(self.args.regression_episodes),
                 "--out-dir", str(out_dir)],
                # DEVNULL, not a captured pipe: benchmark floods JSBSim init
                # logs (192 episodes across 8 fixtures), and a captured pipe
                # deadlocks once its 64 KB buffer fills -- the same hang the
                # kill-floor probe hit on 2026-07-25. Result comes from the
                # --out-dir scorecard, so captured stdout was only an error tail.
                cwd=str(ROOT), stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=1800,
                env=self._isolated_ray_env(),
            )
            score_path = out_dir / f"{tag}.json"
            if completed.returncode != 0 or not score_path.exists():
                raise RuntimeError(
                    f"benchmark subprocess rc={completed.returncode}, "
                    f"scorecard_exists={score_path.exists()}")

            scored = _json.loads(score_path.read_text(encoding="utf-8"))
            # A stage-scoped exemption ("15:turn_shallow_2000") makes that
            # case reported-but-non-blocking: the delta still prints on every
            # guard run (so erosion or recovery stays visible), the baseline
            # bar is untouched, and the scope expires at promotion -- from the
            # next stage on the case blocks again.
            exempt = set()
            for spec in (self.args.regression_exempt or []):
                stage_str, _, case = spec.rpartition(":")
                if not stage_str or int(stage_str) == stage.index:
                    exempt.add(case)
            unknown = exempt - set(baseline)
            if unknown:
                print(f"  !! regression exemption names unknown cases: "
                      f"{sorted(unknown)}")

            worst_case, worst_delta, tolerated = None, 0.0, []
            for row in scored["results"]:
                if row["case"] not in baseline:
                    continue
                delta = row["kill_rate"] - baseline[row["case"]]["kill_rate"]
                if row["case"] in exempt:
                    tolerated.append(f"{row['case']} {delta:+.3f} EXEMPT")
                    continue
                if delta < worst_delta:
                    worst_case, worst_delta = row["case"], delta

            held = bool(worst_case
                        and worst_delta < -abs(self.args.regression_tolerance))
            detail = (f"{worst_case} {worst_delta:+.3f}" if held else
                      (f"worst {worst_case} {worst_delta:+.3f}"
                       if worst_case else "nothing below baseline"))
            if tolerated:
                detail += " | tolerated: " + ", ".join(tolerated)
            weights = probe_dir / "policy_weights.pkl.gz"
            self._guard_cache = {
                "stamp": weights.stat().st_mtime if weights.exists() else None,
                "held": held, "detail": detail,
            }
            return held, detail
        except Exception as exc:
            # A guard that fails must not be mistaken for one that passed. It
            # still does not halt training, but it says so unmistakably.
            import traceback
            print("  !! REGRESSION GUARD BROKEN - advancing UNPROTECTED")
            print(f"     {type(exc).__name__}: {exc}")
            traceback.print_exc()
            detail = f"BROKEN ({type(exc).__name__}: {str(exc)[:300]})"
            # [MOD-GUARDCACHE] record the failure where the promotion note (and
            # the post-mortem) can see it; the console line dies with the window
            self._guard_cache = {"stamp": None, "held": False, "detail": detail}
            return False, detail

    def _print_row(self, stage_idx: int, it: int, m: dict):
        """One line per iteration, using the CANONICAL metric names.

        The console used to print Reward/WinRate/Crash/WEZ/VF_loss while the
        CSV, the state file and the dashboard called the same quantities
        reward_mean/win_rate/crash_rate/ep_wez_steps/vf_loss. Reading a number
        off the screen and then finding it in a file meant translating names by
        hand every time. One name per quantity, everywhere.
        """
        parts = [
            f"stage={stage_idx}",
            f"iter_in_stage={it}",
            f"total_iter={m['total_iter']}",
            f"reward_mean={_fmt(m['reward_mean'], '.2f')}",
            f"win_rate={_fmt(m['win_rate'], '.3f')}",
            f"draw_rate={_fmt(m.get('draw_rate'), '.3f')}",
            f"crash_rate={_fmt(m['crash_rate'], '.3f')}",
            f"ep_wez_steps={_fmt(m['ep_wez_steps'], '.1f')}",
            f"episodes_this_iter={_fmt(m.get('episodes_this_iter'), '')}",
            f"entropy={_fmt(m['entropy'], '.3f')}",
            f"vf_loss={_fmt(m['vf_loss'], '.3f')}",
        ]
        # only on evaluation iterations, and it is the number that gates
        if isinstance(m.get("eval_win_rate"), (int, float)):
            parts.append(f"eval_win_rate={_fmt(m['eval_win_rate'], '.3f')}")
        print(" | ".join(parts))

        # Per-opponent line, only when there is something to say. An aggregate
        # win rate cannot show one opponent being forgotten while others
        # improve, which is the whole reason these keys exist.
        breakdown = []
        for key in sorted(m):
            if not key.startswith("vs_") or not key.endswith("_win"):
                continue
            name = key[3:-4]
            wins = m.get(key)
            count = m.get(f"vs_{name}_n")
            if not isinstance(wins, (int, float)) or wins != wins:
                continue
            breakdown.append(f"{name} {wins:.2f}"
                             + (f"({count:.0f})" if isinstance(count, (int, float))
                                and count == count else ""))
        if breakdown:
            print("      vs " + "  ".join(breakdown))


# -- Utilities -----------------------------------------------------------------


def _clamp_policy_std(algorithm, std: float, action_dim: int = 4) -> float | None:
    """Pin the Gaussian head's exploration std after a PPO update.

    Sampling noise is not a free parameter here. Measured 2026-07-20, injecting
    Gaussian noise of size sigma into a policy that wins 10/10 deterministically:

        sigma  stage 2   stage 4
        0.00    10/10      5/10
        0.05    10/10      1/10
        0.10     9/10      0/10
        0.20     1/10      0/10

    A gun kill needs the nose inside a couple of degrees, so the task collapses
    somewhere between sigma 0.1 and 0.2 -- far below what a typical continuous
    control task tolerates. PPO does not know that, and with a stale critic it
    drifts the std upward: on stage 11 the entropy climbed from -2.7 to -1.3
    (sigma ~0.12 -> ~0.17) while the deterministic win rate fell 0.790 -> 0.571
    over the same iterations. Clamping keeps exploration inside the band where
    the task still works.
    """
    import numpy as np

    def _set(learner, *args, **kwargs):
        module = getattr(learner, "module", None)
        target = None
        if module is not None:
            try:
                target = module["default_policy"]
            except Exception:
                target = module
        if target is None or not hasattr(target, "get_state"):
            return None
        state = target.get_state()
        head = None
        for key, value in state.items():
            if not key.startswith("pi."):
                continue
            array = value.detach().cpu().numpy() if hasattr(value, "detach") else value
            array = np.asarray(array)
            if array.ndim == 2 and array.shape[0] == 2 * action_dim:
                head = key
        if head is None:
            return None
        bias_key = head.replace("weight", "bias")
        import torch
        with torch.no_grad():
            weight = state[head]
            bias = state[bias_key]
            weight[action_dim:, :] = 0.0            # state-independent noise
            bias[action_dim:] = float(np.log(std))
        target.set_state(state)
        return std

    learner_group = getattr(algorithm, "learner_group", None)
    if learner_group is None or not hasattr(learner_group, "foreach_learner"):
        return None
    try:
        learner_group.foreach_learner(_set)
    except Exception:
        return None

    # the samplers must see it too, or the clamp only affects the next sync
    runner_group = getattr(algorithm, "env_runner_group", None)
    if runner_group is not None and hasattr(runner_group, "sync_weights"):
        try:
            runner_group.sync_weights()
        except Exception:
            pass
    return std


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# -- Entry point ---------------------------------------------------------------

def main():
    args = parse_args()
    _sync_lstm_args_from_init_bundle(args)
    trainer = CurriculumTrainer(args)
    trainer.run()


if __name__ == "__main__":
    main()



