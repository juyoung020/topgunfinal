from __future__ import annotations

import copy
import datetime
import json
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pymap3d as pm
try:
    import gymnasium as gym
except ImportError:  # pragma: no cover - compatibility fallback for local setups
    import gym as gym

import FighterSim
import JSBSimWrapper
from GeoMathUtil import GeometryInfo
from dogfight.ai.action_provider import ActionContext
from dogfight.ai.native_bt import AIPilot
from dogfight.config import FEET_TO_METER, METER_TO_FEET, merge_env_config
from dogfight.envs.observation import (
    build_observation,
    normalize,
    observation_size as builtin_observation_size,
)
from dogfight.envs.reward import compute_reward
from dogfight.envs.termination import evaluate_termination
from dogfight.sim.state_schema import StateIndex


REF_OLD_RANDOM_SCENARIOS = {
    0: (
        [1000.0, 0.0, -8100.0, 0.0, 0.0, 0.0, 250.0, 2],
        [3000.0, 0.0, -8000.0, 0.0, 0.0, 0.0, 250.0, 2],
    ),
    1: (
        [1500.0, 500.0, -8500.0, 0.0, 0.0, 0.0, 250.0, 2],
        [3000.0, 0.0, -8000.0, 0.0, 0.0, 0.0, 250.0, 2],
    ),
    2: (
        [3000.0, 1000.0, -8000.0, 0.0, 0.0, 270.0, 250.0, 2],
        [3000.0, 0.0, -8000.0, 0.0, 0.0, 0.0, 250.0, 2],
    ),
    3: (
        [3000.0, 0.0, -8000.0, 0.0, 0.0, 0.0, 250.0, 2],
        [2000.0, 1000.0, -8000.0, 0.0, 0.0, 315.0, 250.0, 2],
    ),
    4: (
        [3000.0, 0.0, -8000.0, 0.0, 0.0, 0.0, 250.0, 2],
        [2000.0, 0.0, -8000.0, 0.0, 0.0, 0.0, 250.0, 2],
    ),
    5: (
        [3000.0, 1000.0, -8000.0, 0.0, 0.0, 0.0, 250.0, 1],
        [4000.0, 0.0, -8000.0, 0.0, 0.0, 0.0, 250.0, 1],
    ),
    6: (
        [3000.0, 1000.0, -8000.0, 0.0, 0.0, 0.0, 250.0, 1],
        [4000.0, 0.0, -8000.0, 0.0, 0.0, 0.0, 250.0, 1],
    ),
    7: (
        [3000.0, 1000.0, -8000.0, 0.0, 0.0, 0.0, 250.0, 1],
        [4000.0, 0.0, -8000.0, 0.0, 0.0, 0.0, 250.0, 1],
    ),
}


def _opponent_name(entry: dict) -> str:
    """Stable short name for a pool entry, used as a metric suffix."""
    mode = str(entry.get("mode", "?"))
    if mode == "aggressor":
        return f"aggressor_{entry.get('level', '?')}"
    if mode == "policy":
        parts = Path(str(entry.get("bundle", ""))).parts
        # ...\<run-tag>\<stage-dir>est_bundle -> "frozen_<run-tag>"
        # Run-tag alone collapsed every league generation into one detector
        # row: the stage-20 pool carries four bundles from the SAME run
        # (stage_16/17/18/19 of 0721_anchor2) and all reported as
        # "frozen_0721_anchor2" (measured 2026-07-23), so a per-generation
        # regression would only ever show as a blend. Include the stage dir.
        # [MOD-ELO] FIX (2026-07-29): distinguish by LEAF, not parts[-3:-1].
        # The old rule DROPPED the leaf -> every artifacts/league/<name> champion
        # collapsed into one "frozen_artifacts_league" Elo bucket (fvs_v3 1654,
        # gen_r8 1500, v4 1572, champ38 1493 all merged) and every self-snapshot
        # into one bucket, so PFSP could not target the genuinely hard opponents.
        # Leaf is distinctive (fvs_v3_acekill13, snap_0150); when it is generic
        # (best_bundle/final_bundle) fall back to <parent>_<leaf>, which still
        # separates stage_16/17/18/19 of one run by their stage dir.
        _GENERIC = {"best_bundle", "final_bundle", "best", "final",
                    "policy", "bundle"}
        if not parts:
            tag = "policy"
        elif parts[-1] in _GENERIC and len(parts) >= 2:
            tag = "_".join(parts[-2:])
        else:
            tag = parts[-1]
        return f"frozen_{tag}"
    teacher = entry.get("teacher") or {}
    name = str(teacher.get("name", "?"))
    bank = (teacher.get("params") or {}).get("bank_range")
    if bank:
        return f"{name}{int(bank[0])}_{int(bank[1])}"
    return name


class DogFightEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        env_config: Optional[dict] = None,
        AIP_ownship=None,
        AIP_target=None,
        ownship_action_provider=None,
        target_action_provider=None,
        reward_fn=None,  # 학생 정의 보상 함수; None이면 reward.py 기본값 사용
        observation_fn=None,
        observation_size=None,
        observation_low=None,
        observation_high=None,
    ):
        super().__init__()
        self._closed = False
        self.battle_space_id: int | None = None
        self._sim = None
        self._target_sim = None
        self._ownship_ai = None
        self._target_ai = None
        self._ownship_action_provider = ownship_action_provider
        self._target_action_provider = target_action_provider

        self.config = merge_env_config(env_config)
        self._runner_index = self.config.get("_runner_index", "local")
        self._env_index = self.config.get("_env_index", 0)
        self._geo_info = GeometryInfo()
        self._sim_hz = int(self.config["sim_hz"])
        self._step_ratio = self._resolve_step_ratio(self.config)
        self._delta_t = 1.0 / self._sim_hz
        self._max_engage_time = float(self.config["max_engage_time"])
        self._min_altitude = float(self.config["min_altitude"])
        self._observation_mode = self.config["observation_mode"]
        self._episode_step_limit = self.config.get("episode_step_limit")
        self._geometry_guard = self.config.get("geometry_guard", {})
        self._wez = self.config["wez"]
        self._reward_config = self.config["reward"]
        self._artifacts_dir = self.config["artifacts_dir"]
        self._reward_fn = reward_fn  # None → compute_reward from reward.py
        self._observation_fn = observation_fn
        # [MOD-OBSROLE] 학생 observation_fn 이 observer 인자를 받는지 1회만 검사.
        # 옛 4인자 시그니처도 그대로 동작해야 하므로 넘기기 전에 확인한다.
        try:
            import inspect as _inspect
            self._obs_fn_takes_observer = bool(
                observation_fn is not None
                and "observer" in _inspect.signature(observation_fn).parameters)
        except (TypeError, ValueError):
            self._obs_fn_takes_observer = False

        self.battle_space_id = JSBSimWrapper.create_battleSpace()
        self._ownship_ai = (
            AIP_ownship if AIP_ownship is not None else self._build_ownship_ai()
        )
        self._target_ai = (
            AIP_target if AIP_target is not None else self._build_target_ai()
        )

        self.num_action = 4
        self.num_observation = (
            int(observation_size)
            if observation_fn is not None
            else builtin_observation_size(self._observation_mode)
        )
        if observation_fn is not None:
            low = -1.0 if observation_low is None else observation_low
            high = 1.0 if observation_high is None else observation_high
            self.observation_space = gym.spaces.Box(
                low=np.full(self.num_observation, low, dtype=np.float32)
                if np.isscalar(low) else np.asarray(low, dtype=np.float32),
                high=np.full(self.num_observation, high, dtype=np.float32)
                if np.isscalar(high) else np.asarray(high, dtype=np.float32),
                shape=(self.num_observation,),
                dtype=np.float32,
            )
        elif self._observation_mode == "tactical16":
            self.observation_space = gym.spaces.Box(
                low=-1.0, high=1.0, shape=(self.num_observation,), dtype=np.float32
            )
        else:
            self.observation_space = gym.spaces.Box(
                low=-np.inf, high=np.inf, shape=(self.num_observation,), dtype=np.float32
            )
        # All 4 action dims in [-1, 1] (throttle remapped to [0,1] internally).
        # Untrained networks output ≈0 → throttle = (0+1)/2 = 0.5 → no stall.
        self.action_space = gym.spaces.Box(
            low=-np.ones(self.num_action, dtype=np.float32),
            high=np.ones(self.num_action, dtype=np.float32),
            shape=(self.num_action,),
            dtype=np.float32,
        )

        self._sim = FighterSim.JSBSim(
            [
                1,
                1,
                self.config["ownship"][0],
                self.config["ownship"][1],
                self.config["ownship"][2],
                self.config["ownship"][3],
                self.config["ownship"][4],
                self.config["ownship"][5],
                self.config["ownship"][6],
            ],
            self._ownship_ai,
            self._sim_hz,
            self.battle_space_id,
        )
        self._target_sim = FighterSim.JSBSim(
            [
                1,
                2,
                self.config["target"][0],
                self.config["target"][1],
                self.config["target"][2],
                self.config["target"][3],
                self.config["target"][4],
                self.config["target"][5],
                self.config["target"][6],
            ],
            self._target_ai,
            self._sim_hz,
            self.battle_space_id,
        )

        self.ownship_log: List[List[float]] = []
        self.target_log: List[List[float]] = []
        self.info: Dict[str, object] = {"end_condition": ""}
        self.ownship_damage = 0.0
        self.target_damage = 0.0
        self.num_engage = 0
        self.current_timestep = 0
        self.pre_obs = np.zeros(self.num_observation, dtype=np.float32)
        # Episode-level accumulators (reset in reset())
        self._in_wez = False
        self._ep_wez_steps = 0
        self._ep_step_count = 0
        self._ep_distance_sum = 0.0
        self._ep_distance_min = float("inf")
        self._ep_altitude_penalty_steps = 0
        self._ep_total_reward = 0.0
        self._ep_reward_components: Dict[str, float] = {}
        self._ep_action_sum = np.zeros(self.num_action, dtype=np.float64)
        self._ep_action_sq_sum = np.zeros(self.num_action, dtype=np.float64)
        self._initial_scenario_metrics: Dict[str, float] = {}

    # Sim expects throttle in [0, 1]; RL policy outputs throttle in [-1, 1].
    _SIM_ACTION_LOW  = np.array([-1., -1., -1., 0.], dtype=np.float32)
    _SIM_ACTION_HIGH = np.ones(4, dtype=np.float32)

    def _to_sim_action(self, rl_action: np.ndarray) -> np.ndarray:
        """Convert RL action space [-1,1]^4 → simulator format (throttle [0,1])."""
        a = np.clip(rl_action, -1.0, 1.0).astype(np.float32)
        a[3] = (a[3] + 1.0) / 2.0                        # [-1,1] → [0,1]
        return np.clip(a, self._SIM_ACTION_LOW, self._SIM_ACTION_HIGH)

    def _build_ai(self, dll_name):
        if not dll_name:
            return None
        return AIPilot(dll_name)

    def _build_ownship_ai(self):
        if self._ownship_action_provider is not None:
            return None
        if self.config["ownship_control_mode"] != "behavior_tree":
            return None
        return self._build_ai(self.config["ownship_behavior_dll"])

    def _build_target_ai(self):
        if self._target_action_provider is not None:
            return None
        if self.config["target_mode"] != "behavior_tree":
            return None
        return self._build_ai(self.config["target_behavior_dll"])

    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None):
        super().reset(seed=seed)
        if options:
            self.config = merge_env_config({**self.config, **options})
            self._episode_step_limit = self.config.get("episode_step_limit")
            self._geometry_guard = self.config.get("geometry_guard", {})
            self._reward_config = self.config["reward"]

        scenario = self.config.get("initial_scenario", {})
        scenario_mode = scenario.get("mode", "default")
        if scenario_mode == "two_circle_headon":
            self._apply_two_circle_headon_initial_scenario(scenario)
        elif scenario_mode == "ref_old_random":
            self._apply_ref_old_random_initial_scenario(scenario)
        else:
            self._initial_scenario_metrics = {}

        # [MOD-LIVETUNE] hot-reload run overrides without a trainer restart:
        # every reset checks a sidecar JSON's mtime and, when it changed,
        # merges a WHITELISTED set of keys into the live config. Pool edits
        # land on the next opponent draw, reward edits on the next step.
        # Architecture/observation changes still need a restart.
        lt = self.config.get("live_tune_file")
        if lt:
            try:
                import os as _os, json as _json
                mt = _os.path.getmtime(lt)
                if mt != getattr(self, "_lt_mtime", None):
                    with open(lt, encoding="utf-8") as _f:
                        data = _json.load(_f)
                    for key in ("target_pool", "ownship_hp_deficit"):
                        if key in data:
                            self.config[key] = data[key]
                    if isinstance(data.get("reward"), dict):
                        self.config.setdefault("reward", {}).update(data["reward"])
                    # Cache the mtime only AFTER a successful load+merge.
                    # Caching it first meant a half-written JSON (editor
                    # mid-save) raised in json.load and was then skipped
                    # forever -- the mtime already matched, so the finished
                    # file never got re-read. Failing keeps mtime stale and
                    # the next reset retries.
                    self._lt_mtime = mt
            except FileNotFoundError:
                # NOT an error. The sidecar only writes live_tune.json after
                # the first snapshot (iteration 30 by default), so every reset
                # before that hit this path and printed a red WinError-2 line
                # per env runner -- 40 of them in the first two iterations,
                # which buried the real warnings. Announce ONCE per process,
                # quietly, then stay silent until the file appears.
                if not getattr(self, "_lt_absent_noted", False):
                    self._lt_absent_noted = True
                    print(f"[LIVETUNE] waiting for {lt} (sidecar writes it "
                          f"after the first snapshot)")
            except Exception as exc:
                print(f"[LIVETUNE] ignored ({exc})")
        # [MOD-OPPONENT] draw this episode's opponent FIRST: pool entries may
        # carry their own spawn geometry, and the scatter below reads it. The
        # draw uses only config and its own rng, so hoisting it is safe.
        self._sample_opponent()
        self._apply_entry_spawn()   # [MOD-OPPONENT] target-side geometry

        # Apply per-episode position randomization if configured
        rand = self.config.get("ownship_randomization", {})
        # [MOD-POOLRAND] a pool entry may pin its own ownship scatter. The
        # stage-wide scatter silently rewrote every rehearsal case: measured
        # 2026-07-23, straight_600 (guard benchmark 0.83) went 0/16 under the
        # duel stages' 400 m / +-120 deg opening scatter -- a runaway target
        # plus a nose pointed away turns a 600 m gun rehearsal into an
        # unwinnable tail chase, so the "keep old skills" episodes never
        # rehearsed the skill the guard grades. Entry randomization restores
        # each rehearsal case to the conditions it was designed and measured
        # under; entries without one keep the stage scatter.
        entry_rand = (getattr(self, "_episode_opponent", None) or {}).get(
            "randomization")
        if entry_rand is not None:
            rand = entry_rand
        if scenario_mode != "two_circle_headon" and rand.get("enabled", False):
            self.add_random_init_position(
                "ownship",
                radius=float(rand.get("radius", 0)),
                r_roll=float(rand.get("r_roll", 0)),
                r_pitch=float(rand.get("r_pitch", 0)),
                r_heading=float(rand.get("r_heading", 0)),
            )

        # [MOD-PURSUIT] per-episode teacher randomization
        if self.config.get("target_mode") == "pursuit":
            self._sample_pursuit_params()
        bank_range = self.config.get("target_loiter_bank_range")
        if bank_range and self.config.get("target_mode") == "loiter":
            lo, hi = float(bank_range[0]), float(bank_range[1])
            bank = lo + (hi - lo) * float(np.random.random())
            if float(np.random.random()) < 0.5:
                bank = -bank
            self.config["target_loiter"] = {
                **self.config.get("target_loiter", {}),
                "bank": bank,
            }
        # [/MOD-PURSUIT]

        JSBSimWrapper.Reset(self.battle_space_id)
        self._ownship_state = self._sim.reset()
        self._target_state = self._target_sim.reset()
        # [MOD-DEFICIT] league drill: start a fraction of episodes already
        # behind on points. Measured 07-23 (8 mirror games): when behind on
        # margin the policy held a 3.7 km standoff for the full 200 s and
        # never once came back to reverse it -- under competition judging
        # that is a guaranteed points loss, and the training data contained
        # ZERO episodes of "you are losing, go take the margin back".
        deficit = self.config.get("ownship_hp_deficit") or {}
        # [MOD-DEFICIT] remember what the drill deducted so the judge label
        # can add it back: the handicap is a training fiction, not damage the
        # opponent dealt, and without the correction a policy that WON the
        # actual fight on points was logged judge_loss whenever the deficit
        # exceeded the real margin. Labels only -- the reward terminal stays
        # uncorrected on purpose, so being behind still feels like losing.
        self._hp_deficit_applied = 0.0
        if float(deficit.get("prob", 0.0)) > 0.0 \
                and float(self.np_random.random()) < float(deficit["prob"]):
            lo = float(deficit.get("min", 0.05))
            hi = float(deficit.get("max", 0.15))
            amount = float(self.np_random.uniform(lo, hi))
            self._sim.deduct_health(amount)
            self._hp_deficit_applied = amount
            # the sim refreshes state[HEALTH] only on its next update tick,
            # so patch the already-copied state array for the first obs
            self._ownship_state[StateIndex.HEALTH] = self._sim._health

        # [MOD-DEFICIT-T 2026-08-05] TARGET-side handicap, per pool entry.
        # Purpose: make elite RL opponents killable so the damage gradient
        # flows at all. H2H measured 0W-0L with 0.00:0.00 exchanges vs
        # elo1667/champion -- elite episodes teach nothing because no reward
        # ever fires. Starting the elite at reduced HP turns "impossible kill"
        # into "finish a 1-2 s dwell", and the handicap is walked down across
        # league generations. Reads the sampled pool entry first so ONLY
        # marked entries (elites) are handicapped; teacher/clone entries and
        # every earlier stage are untouched.
        entry_t = getattr(self, "_episode_opponent", None) or {}
        tdef = entry_t.get("target_hp_deficit")             or self.config.get("target_hp_deficit") or {}
        self._target_hp_deficit_applied = 0.0
        if float(tdef.get("prob", 0.0)) > 0.0                 and float(self.np_random.random()) < float(tdef["prob"]):
            t_lo = float(tdef.get("min", 0.3))
            t_hi = float(tdef.get("max", 0.5))
            t_amt = float(self.np_random.uniform(t_lo, t_hi))
            self._target_sim.deduct_health(t_amt)
            self._target_hp_deficit_applied = t_amt
            self._target_state[StateIndex.HEALTH] = self._target_sim._health
        self._update_initial_geometry_metrics(scenario_mode)
        # [MOD-SPAWNVEL] 2026-08-21 — 리셋 직후 동체속도가 **0** 이라 첫 관측이 오염된다.
        #
        # 실측(교전서버 첫 프레임 vs env 첫 프레임, 같은 IC):
        #     speed        서버 -0.143010  /  env -1.000000   (env 는 하한에 박힘)
        #     los_rate_az  서버  1.000000  /  env  0.000000
        #     closure_rate 서버 -0.012583  /  env -0.000000
        #     나머지 13채널은 전부 0.000000 로 일치
        #     env 첫 속도 0.000  /  서버 199.973
        # 그 결과 **첫 행동이 1.89 만큼 달라지고**(범위 -1~1) 스텝 1 에 6.74 m,
        # 2.6초에 10 m 벌어진다. LSTM 이 오염된 첫 입력을 기억에 담고 출발한다.
        #
        # 서버는 첫 프레임부터 u=199.97 을 준다. 스폰은 수평·무횡활이므로
        # 동체속도는 (V, 0, 0) 이다. 그 값을 채워 서버와 같은 첫 관측을 만든다.
        # 물리에는 영향이 없다 — 캐시 상태는 다음 substep 에서 sim 값으로 덮인다.
        for _st, _fs in ((self._ownship_state, self._sim),
                         (self._target_state, self._target_sim)):
            if _st is None or _fs is None:
                continue
            try:
                if float(np.linalg.norm(_st[6:9])) < 1e-6:
                    _st[6] = float(getattr(_fs, "_init_speed", 0.0) or 0.0)
                    _st[7] = 0.0
                    _st[8] = 0.0
            except Exception:
                pass
        self.pre_obs = self.get_observation()
        self.info = {"end_condition": "", **self._initial_scenario_metrics}
        self.ownship_damage = 0.0
        self.target_damage = 0.0
        self.num_engage += 1
        self.current_timestep = 0
        self._reset_action_providers()
        self._reset_aggressor()  # [MOD-OPPONENT]
        self._reset_policy_opponent()  # [MOD-OPPONENT] fresh LSTM per episode
        self._reset_teacher()   # [MOD-TEACHER] per-episode teacher randomization
        # Reset episode accumulators
        self._in_wez = False
        self._ep_wez_steps = 0
        self._ep_step_count = 0
        self._ep_distance_sum = 0.0
        self._ep_distance_min = float("inf")
        self._ep_altitude_penalty_steps = 0
        self._ep_total_reward = 0.0
        self._ep_reward_components = {}
        self._ep_action_sum = np.zeros(self.num_action, dtype=np.float64)
        self._ep_action_sq_sum = np.zeros(self.num_action, dtype=np.float64)
        return np.array(self.pre_obs, dtype=np.float32), dict(self.info)

    def step(self, action) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        action = np.asarray(action, dtype=np.float32)
        failure = self._advance_simulation_step_ratio(action)
        if failure is not None:
            return failure
        cur_obs = self.get_observation()

        terminated, truncated, end_condition = evaluate_termination(
            self._ownship_state,
            self._target_state,
            self._sim,
            self._target_sim,
            self._max_engage_time,
            self._min_altitude,
            self.current_timestep,
            self._episode_step_limit,
            self._geo_info,
            self._geometry_guard,
        )

        ownship_health = float(self._ownship_state[StateIndex.HEALTH])
        target_health = float(self._target_state[StateIndex.HEALTH])
        outcome = self._classify_outcome(
            terminated,
            truncated,
            end_condition,
            ownship_health,
            target_health,
            hp_deficit=getattr(self, "_hp_deficit_applied", 0.0),
        )
        reward, components = self._compute_step_reward(
            terminated,
            truncated,
            end_condition,
        )

        ep_mean_dist, ep_min_dist = self._update_episode_metrics(
            action,
            reward,
            components,
        )

        self.info = {
            "end_condition": end_condition,
            "outcome": outcome,
            # [MOD-OPPONENT] which opponent this episode faced. An aggregate
            # win rate cannot see one opponent being forgotten while others
            # improve -- that is what a per-opponent table is for, and it is
            # the detector every published league system runs continuously.
            "opponent": (getattr(self, "_episode_opponent", None) or {}).get(
                "_name", str(self.config.get("target_mode", "?"))),
            "ownship_damage": self.ownship_damage,
            "target_damage": self.target_damage,
            "ownship_health": ownship_health,
            "target_health": target_health,
            # [MOD-DEFICIT] handicap this episode started with (0.0 = none),
            # so eval tables can split "real" margins from drill margins
            "hp_deficit": getattr(self, "_hp_deficit_applied", 0.0),
            "reward_components": components,
            "ep_reward_components": dict(self._ep_reward_components),
            "ep_wez_steps": self._ep_wez_steps,
            "ep_step_count": self._ep_step_count,
            "ep_mean_distance": ep_mean_dist,
            "ep_min_distance": ep_min_dist,
            "ep_altitude_penalty_steps": self._ep_altitude_penalty_steps,
            "final_ata_deg": abs(float(self._geo_info._get_antenna_train_angle(
                self._ownship_state, self._target_state, True
            ))),
            "final_aa_deg": abs(float(self._geo_info._get_aspect_angle(
                self._ownship_state, self._target_state, True
            ))),
            "headon_guard_fail": end_condition == "two circle headon guard fail",
            **self._initial_scenario_metrics,
        }

        if terminated or truncated:
            self._note_opponent_result(outcome)   # [MOD-OPPONENT] PFSP history
        self._append_logs()
        self.pre_obs = copy.deepcopy(cur_obs)
        self.current_timestep += 1
        if terminated or truncated:
            self._print_episode_termination(end_condition)
        return np.array(cur_obs, dtype=np.float32), reward, terminated, truncated, dict(self.info)

    def _advance_simulation_step_ratio(
        self,
        action: np.ndarray,
    ) -> tuple[np.ndarray, float, bool, bool, Dict] | None:
        ownship_damage_total = 0.0
        target_damage_total = 0.0
        in_wez_any = False
        # [MOD-LATENCY] 2026-08-22 — 대회 서버의 **조종 지연**을 학습에 넣는다.
        #
        # 실측(개루프, 롤 명령 계단 6구간): 서버는 CMD 를 보낸 뒤 **3프레임(50 ms)**
        # 뒤에 적용한다. A/B 클라이언트 둘 다 3프레임, 비대칭 0.
        # 학습 env 는 지연 0 이었다 -> 정책이 "지금 보이는 곳"을 겨누도록 배웠다.
        #
        # 그 대가가 조준이다(실측, 같은 조합·IC):
        #     지연 0f  WEZ 15스텝  밴드ATA  1.5도
        #     지연 3f  WEZ  1스텝  밴드ATA  6.5도
        #     지연 6f  WEZ  0스텝  밴드ATA 15.7도
        # 판 길이는 29초로 같은데 **조준만 무너진다**. 붙기는 붙는데 못 겨눈다.
        # 학습 대시보드에서 조준이 거의 다 성공하던 것이 이 때문이다.
        #
        # 지연을 넣으면 정책이 스스로 앞질러 꺾는 법(리드)을 배운다.
        # 프레임 단위 큐라 step_ratio 와 무관하게 정확히 N 프레임 늦춘다.
        _lat = int(self.config.get("action_latency_frames", 0) or 0)
        if _lat > 0:
            q = getattr(self, "_act_delay_q", None)
            if q is None or getattr(self, "_act_delay_n", -1) != _lat:
                from collections import deque
                q = deque([np.zeros(self.num_action, dtype=np.float32)] * _lat,
                          maxlen=_lat)
                self._act_delay_q = q
                self._act_delay_n = _lat
        for _ in range(int(self._step_ratio)):
            if _lat > 0:
                self._act_delay_q.append(np.asarray(action, dtype=np.float32))
                action_now = self._act_delay_q[0]
            else:
                action_now = action
            self._step_controlled_aircraft(action_now)
            if np.isnan(self._sim.get_state()).any():
                # [MOD-NANTERM] Pay the crash penalty. This path used to return
                # 0.0, which made blowing up the flight model the only free way
                # to end an episode: every other crash costs crash_reward and
                # even a draw costs draw_base, so a losing policy could escape
                # both by flying into a state the FDM cannot integrate. The
                # reward function is not called here because the state is NaN
                # and would poison every component, so the terminal is read
                # straight from the same config.
                # (Measured 2026-07-20: 0 occurrences across five runs, so this
                # is closing a hole, not fixing an observed exploit.)
                penalty = float(self._reward_config.get("crash_reward", -150.0))
                info = {"end_condition": "Ownship FDM output Fall", "outcome": "crash"}
                self._ep_step_count += 1
                self._print_episode_termination(info["end_condition"])
                return np.array(self.pre_obs, dtype=np.float32), penalty, True, False, info

            self._step_target_aircraft()
            if np.isnan(self._target_sim.get_state()).any():
                # Deliberately 0: the opponent's integrator failing is a
                # simulator artifact, not something the agent achieved, and
                # paying for it would reward driving the target into states
                # that break the FDM rather than shooting it down.
                info = {"end_condition": "Target FDM output Fall", "outcome": "other"}
                self._ep_step_count += 1
                self._print_episode_termination(info["end_condition"])
                return np.array(self.pre_obs, dtype=np.float32), 0.0, True, False, info

            self.update_damage()
            ownship_damage_total += float(self.ownship_damage)
            target_damage_total += float(self.target_damage)
            in_wez_any = in_wez_any or self._in_wez
            self._ownship_state = self._sim.get_state()
            self._target_state = self._target_sim.get_state()

        self.ownship_damage = ownship_damage_total
        self.target_damage = target_damage_total
        self._in_wez = in_wez_any
        return None

    @staticmethod
    def _classify_outcome(
        terminated: bool,
        truncated: bool,
        end_condition: str,
        ownship_health: float,
        target_health: float,
        hp_deficit: float = 0.0,
    ) -> str:
        if terminated:
            if target_health <= 0.0 < ownship_health:
                return "win"
            if ownship_health <= 0.0 < target_health:
                return "loss"
            # [MOD-JUDGE] a mutual kill previously fell through to "draw"
            # while the reward's terminal branch already charges it as a
            # death (-150) -- a dying policy could pass the loss_rate gate.
            # Label and reward now agree.
            if ownship_health <= 0.0 and target_health <= 0.0:
                return "draw"   # [MOD-TIE 2026-08-29] 동시격추는 지표상 무승부로 분리 (보상은 loss=draw=0 으로 동일)
            if end_condition in ("ownship altitude below min", "FDM Update Fail"):
                return "crash"
            # [MOD-JUDGE] rulebook (Top Gun Challenge deck, slide 11): below
            # 1,000 ft is death for EITHER side, and the round goes to the
            # surviving team. An opponent flown into the ground was labelled
            # "draw" -- 25% of decided policy-vs-policy games went unrecorded
            # (measured 07-23), so a legitimate winning tactic earned nothing
            # on the instruments.
            if end_condition == "target altitude below min":
                return "win"
            if end_condition == "two circle headon guard fail":
                return "loss"
            return "draw"
        if truncated:
            # [MOD-JUDGE] competition rules decide a full-time fight by
            # damage advantage, but every truncation was labelled "timeout"
            # regardless of margin -- the league's whole subject (the judge
            # game) was invisible to metrics and gates, and a policy losing
            # every fight on points still read as clean. Split by margin
            # with a small deadband; "timeout" now means a genuine draw.
            # Deadband trimmed 0.05 -> 0.01: measured mirror margins run
            # 0.006-0.20, and the competition rule has no deadband at all --
            # a real points loss (-0.006) was hiding inside "timeout".
            # [MOD-DEFICIT] add the drill's starting handicap back before
            # judging: the deficit is not damage the opponent dealt, and
            # counting it made "fought even from 0.1 behind" read judge_loss.
            # Death checks above stay on the RAW health -- a deficit episode
            # where hp actually hit 0 is still a loss.
            margin = (float(ownship_health) + float(hp_deficit)
                      - float(target_health))
            if margin > 0.01:
                return "judge_win"
            if margin < -0.01:
                return "judge_loss"
            return "timeout"
        return "ongoing"

    def _compute_step_reward(
        self,
        terminated: bool,
        truncated: bool,
        end_condition: str,
    ) -> tuple[float, dict]:
        _reward_fn = self._reward_fn if self._reward_fn is not None else compute_reward
        return _reward_fn(
            self._ownship_state,
            self._target_state,
            self.ownship_damage,
            self.target_damage,
            self._geo_info,
            self._wez,
            self._reward_config,
            terminated,
            truncated,
            end_condition,
        )

    def _update_episode_metrics(
        self,
        action: np.ndarray,
        reward: float,
        components: dict,
    ) -> tuple[float, float]:
        distance = self._geo_info._get_distance(self._ownship_state, self._target_state)
        self._ep_step_count += 1
        self._ep_total_reward += float(reward)
        self._ep_distance_sum += distance
        self._ep_distance_min = min(self._ep_distance_min, distance)
        if self._in_wez:
            self._ep_wez_steps += 1
        if components.get("safety", 0.0) < 0.0:
            self._ep_altitude_penalty_steps += 1
        for k, v in components.items():
            self._ep_reward_components[k] = self._ep_reward_components.get(k, 0.0) + v
        self._ep_action_sum += action.astype(np.float64)
        self._ep_action_sq_sum += action.astype(np.float64) ** 2

        ep_mean_dist = self._ep_distance_sum / self._ep_step_count
        ep_min_dist = self._ep_distance_min if self._ep_step_count > 0 else 0.0
        return ep_mean_dist, ep_min_dist

    @staticmethod
    def _resolve_step_ratio(config: dict) -> float:
        """Resolve RL-action hold ratio from explicit or legacy timing config."""
        ratio = config.get("step_ratio")
        if ratio is None:
            delta = config.get("delta")
            time_step = config.get("time_step")
            if delta is not None and time_step is not None:
                ratio = float(delta) / float(time_step)
            else:
                ratio = 1.0
        ratio = float(ratio)
        if int(ratio) <= 0:
            raise ValueError(f"step_ratio must resolve to at least 1, got {ratio}")
        return ratio

    def _step_controlled_aircraft(self, action: np.ndarray) -> None:
        if self._ownship_action_provider is not None:
            context = self._build_action_context(
                self._sim,
                self._target_sim,
                self._ownship_state,
                self._target_state,
                self.pre_obs,
            )
            result = self._ownship_action_provider.compute_action(context)
            self._sim.step(result.action)
            return

        control_mode = self.config["ownship_control_mode"]
        if control_mode == "behavior_tree":
            self._sim.step_behavior(self._target_sim.get_model())
        elif control_mode == "fixed":
            self._sim.step_fix()
        elif control_mode == "loiter":
            loiter = self.config["target_loiter"]
            self._sim.step_loiter(loiter["enabled"], loiter["bank"], loiter["pitch"])
        else:
            self._sim.step(self._to_sim_action(action))

    def _step_target_aircraft(self) -> None:
        # [MOD-OPPONENT] A sampled pool entry must override the attached
        # teacher provider. The provider early-return below used to win, so
        # every pool episode was silently flown by the teacher: measured
        # 2026-08-06, three different pool "opponents" produced trajectories
        # identical to 15 decimal places, and _policy_opponent was never
        # constructed. Only entry modes that need no provider are hijacked
        # here; teacher-mode entries still fall through to the provider.
        _entry_mode = (getattr(self, "_episode_opponent", None) or {}).get("mode")
        if _entry_mode == "policy":
            self._step_policy_opponent()
            return
        if _entry_mode == "aggressor":
            self._step_aggressor()
            return
        if self._target_action_provider is not None:
            context = self._build_action_context(
                self._target_sim,
                self._sim,
                self._target_state,
                self._ownship_state,
                self.pre_obs,
            )
            result = self._target_action_provider.compute_action(context)
            self._target_sim.step(result.action)
            return

        # [MOD-OPPONENT] a sampled pool entry overrides the configured mode
        target_mode = (getattr(self, "_episode_opponent", None) or {}).get(
            "mode", self.config["target_mode"])
        if target_mode == "behavior_tree":
            self._target_sim.step_behavior(self._sim.get_model())
        elif target_mode == "fixed":
            self._target_sim.step_fix()
        elif target_mode == "loiter":
            loiter = self.config["target_loiter"]
            self._target_sim.step_loiter(loiter["enabled"], loiter["bank"], loiter["pitch"])
        elif target_mode == "autopilot":
            autopilot = self.config["target_autopilot"]
            self._target_sim.step_autopilot(
                autopilot["heading_cmd"],
                autopilot["altitude_cmd"],
                autopilot["speed_cmd"],
            )
        elif target_mode == "pursuit":  # [MOD-PURSUIT] guided chaser teacher
            heading_cmd, altitude_cmd, speed_cmd = self._pursuit_autopilot_cmds()
            self._target_sim.step_autopilot(heading_cmd, altitude_cmd, speed_cmd)
        elif target_mode == "aggressor":  # [MOD-OPPONENT] stick-flying attacker
            self._step_aggressor()
        elif target_mode == "policy":     # [MOD-OPPONENT] frozen self-play
            self._step_policy_opponent()
        elif target_mode == "teacher":  # [MOD-TEACHER] scripted Python opponent
            teacher = self._ensure_teacher()
            cmd = teacher.command(
                self._target_state,
                self._ownship_state,
                self._geo_info,
                1.0 / float(self.config.get("sim_hz", 60)),
            )
            self._target_sim.step_auto_cmd(
                cmd["lat_mode"], cmd["lon_mode"], cmd["spd_mode"],
                cmd["theta_deg"], cmd["phi_deg"], cmd["gamma_deg"],
                cmd["psi_deg"], cmd["altitude_m"], cmd["beta_deg"]
                if "beta_deg" in cmd else 0.0, cmd["speed_mps"],
            )
        else:
            self._target_sim.step_fix()

    # [MOD-TEACHER] ------------------------------------------------------
    def _ensure_teacher(self):
        """Lazily build the scripted teacher for this env (per worker)."""
        teacher = getattr(self, "_teacher", None)
        if teacher is None:
            from student.scripted_opponents import make_teacher  # [MOD-RENAME 2026-08-28] teachers.py -> scripted_opponents.py
            teacher = make_teacher(self.config.get("target_teacher"))
            self._teacher = teacher
            self._teacher_rng = np.random.default_rng()
            teacher.reset(self._teacher_rng, self._target_state, self._ownship_state)
        return teacher

    def _reset_teacher(self) -> None:
        teacher = getattr(self, "_teacher", None)
        if teacher is not None:
            teacher.reset(
                getattr(self, "_teacher_rng", np.random.default_rng()),
                self._target_state,
                self._ownship_state,
            )
    # [/MOD-TEACHER] -----------------------------------------------------

    # [MOD-OPPONENT] -----------------------------------------------------
    def _step_aggressor(self) -> None:
        """Drive the target with a stick-flying attacker.

        Separate from the teacher path because the two speak different
        languages: teachers issue autopilot commands, this issues stick
        deflections. That distinction is the whole reason it exists -- the
        autopilot caps bank near 32 deg in heading mode, so no teacher built on
        it can point at a maneuvering target (measured: 0.00% of steps inside
        its own firing envelope over 8,167 steps).
        """
        provider = self._ensure_aggressor()
        context = self._build_action_context(
            self._target_sim, self._sim,
            self._target_state, self._ownship_state, self.pre_obs,
        )
        result = provider.compute_action(context)
        self._target_sim.step(result.action)

    def _ensure_aggressor(self):
        entry = getattr(self, "_episode_opponent", None) or {}
        level = entry.get("level", self.config.get("target_aggressor", "cadet"))
        if isinstance(level, dict):
            level = level.get("level", "cadet")
        provider = getattr(self, "_aggressor", None)
        if provider is None or getattr(self, "_aggressor_level", None) != level:
            from student.opponents import make_aggressor
            seed = int(self._opponent_rng().integers(0, 2 ** 31 - 1))
            provider = make_aggressor(level, seed=seed)
            provider.reset()
            self._aggressor = provider
            self._aggressor_level = level
        return provider

    def _opponent_rng(self):
        rng = getattr(self, "_opponent_rng_state", None)
        if rng is None:
            rng = np.random.default_rng()
            self._opponent_rng_state = rng
        return rng

    def _sample_opponent(self) -> None:
        """Draw this episode's opponent from the pool.

        Sampling from a POOL rather than always facing the newest opponent is
        the standard guard against catastrophic forgetting and against the
        cycling that non-transitive games produce (A beats B beats C beats A).
        Keeping the old scripted teachers in the pool permanently is what stops
        the agent from trading its gunnery for dogfighting.
        """
        pool = self.config.get("target_pool")
        if not pool:
            self._episode_opponent = None
            # [MOD-OPPMODE] no pool -> scripted opposition; stamp the mode so
            # an opponent-conditional reward sees "teacher" here and in eval
            # (eval prunes the pool to []).
            self._reward_config = {**self.config["reward"],
                                   "_opponent_mode": "teacher"}
            return
        weights = np.array([float(e.get("weight", 1.0)) for e in pool], dtype=float)
        weights = self._prioritise(pool, weights)
        weights = weights / weights.sum()
        entry = dict(pool[int(self._opponent_rng().choice(len(pool), p=weights))])
        entry["_name"] = _opponent_name(entry)
        self._episode_opponent = entry
        # [MOD-OPPMODE] margin play is the right lesson against a mirror
        # policy (no kill key exists between competent policies) and the
        # wrong lesson against a teacher (league training took ace kill
        # 0.96 -> 0.27 while the partial gate metric held 0.93+). Stamp the
        # opponent's mode so the reward module can gate margin terms per
        # episode. Fresh dict each reset -- LIVETUNE reward edits flow in.
        self._reward_config = {**self.config["reward"],
                               # [MOD-ICREWARD] per-pool-entry reward overrides: an
                               # entry may carry its own "reward" dict so ONE run can
                               # teach aggression on the merge (kill nudge) and
                               # patience on the ace (judge margin) at once -- the
                               # aggression<->patience tension cannot be broken by a
                               # single global reward + anchor (measured, S9-32).
                               # Absent -> {} -> every existing stage is unchanged.
                               **(entry.get("reward") or {}),
                               "_opponent_mode": str(entry.get("mode", "teacher"))}
        if entry.get("mode") == "teacher" and entry.get("teacher"):
            # rebuild only when the spec actually changes
            if getattr(self, "_teacher_spec", None) != entry["teacher"]:
                from student.scripted_opponents import make_teacher  # [MOD-RENAME 2026-08-28] teachers.py -> scripted_opponents.py
                self._teacher = make_teacher(entry["teacher"])
                self._teacher_spec = entry["teacher"]
                self._teacher_rng = np.random.default_rng()

    def _note_opponent_result(self, outcome: str) -> None:
        entry = getattr(self, "_episode_opponent", None)
        if not entry:
            return
        history = getattr(self, "_opponent_history", None)
        if history is None:
            history = {}
            self._opponent_history = history
        from collections import deque
        name = entry.get("_name", "?")
        window = history.setdefault(name, deque(maxlen=40))
        # [MOD-JUDGE] competition scoring: a judge win IS a win. Counting it
        # as a loss here would make PFSP treat a points-winning matchup as a
        # losing one the moment policy entries join the prioritised set.
        window.append(1.0 if outcome in ("win", "judge_win") else 0.0)
        # [MOD-ELO] Elo self-play league (LAG / snu-larr CloseAirCombat port,
        # student/opponent_elo.py). Only for policy/snapshot opponents and only
        # when the stage opts in (use_elo_pfsp) -- teacher stages are untouched.
        # Observation/reward/network are NOT changed; this only rates opponents
        # and (in _prioritise) samples them. New opponent seeded at ego Elo.
        if self.config.get("use_elo_pfsp") and entry.get("mode") == "policy":
            from student.opponent_elo import update_elo, outcome_to_score, INIT_ELO
            if not hasattr(self, "_ego_elo"):
                # ego starts at init_elo (default 1500, the calibrated scale's
                # anchor); frozen champions are pre-seeded at their calibrated
                # Elo from elo_seed_file so the ego climbs relative to a known
                # ladder. Live snapshots (not in the seed) start at ego Elo.
                self._ego_elo = float(self.config.get("init_elo", 1500.0))
                self._pool_elo = {}
                self._elo_matches = 0
                seed = self.config.get("elo_seed_file")
                if seed:
                    try:
                        import json
                        from pathlib import Path
                        raw = json.loads(Path(seed).read_text(encoding="utf-8"))
                        self._pool_elo.update({k: float(v) for k, v in
                                               raw.get("ratings", raw).items()})
                    except Exception:
                        pass
            opp = float(self._pool_elo.get(name, self._ego_elo))
            self._ego_elo, self._pool_elo[name] = update_elo(
                self._ego_elo, opp, outcome_to_score(outcome))
            self._elo_matches += 1
            self._persist_elo()

    def _persist_elo(self) -> None:
        """[MOD-ELO] write ego+pool Elo so the sidecar/eval can read the ladder and
        the ego's climbing trajectory. Every 5 matches early (confirm it works),
        then every 20. Path is resolved to the PROJECT ROOT -- a relative path was
        the bug: RLlib env runners run in a different cwd, so the write silently
        failed and no file ever appeared."""
        if self._elo_matches % (5 if self._elo_matches <= 40 else 20) != 0:
            return
        out = self.config.get("elo_out_file") or self.config.get("live_tune_file")
        if not out:
            return
        try:
            import json
            from pathlib import Path
            p = Path(out)
            if not p.is_absolute():
                # ROOT = src/dogfight/envs/single_agent_env.py -> parents[3]
                p = Path(__file__).resolve().parents[3] / p
            if p.suffix != ".json":
                p = p.with_name("pool_elo.json")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({
                "ego_elo": round(self._ego_elo, 1),
                "matches": self._elo_matches,
                "pool": {k: round(v, 1) for k, v in self._pool_elo.items()},
            }, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _prioritise(self, pool: list, weights: np.ndarray) -> np.ndarray:
        """Spend the rehearsal budget on the opponents we are losing to.

        Uniform rehearsal is the documented failure mode: with a fixed share
        each, most games go to opponents already beaten ~100% of the time while
        the one being forgotten gets the same thin slice. Measured here, a
        uniform pool still let defensive_foe fall 1.000 -> 0.125 while three
        turning opponents rose to 1.000.

        This is PFSP's f_hard(x) = (1 - x)^p, which sends zero games to an
        opponent you always beat. Applied only to the REHEARSAL entries -- the
        new opponent keeps its configured share, because the published systems
        that work are a mixture (prioritisation alone measured worse than plain
        self-play), not pure prioritisation.

        A floor keeps every opponent sampled occasionally: with seven of them
        rather than a league of hundreds, an entry dropped to zero stops being
        measured and we would lose the signal that it recovered.
        """
        history = getattr(self, "_opponent_history", None)
        if not history:
            return weights
        exponent = float(self.config.get("pfsp_exponent", 2.0))
        floor = float(self.config.get("pfsp_floor", 0.25))
        out = weights.copy()
        # [MOD-ELO] Elo PFSP over the POLICY opponents (LAG PFSP.choose): sample
        # the growing snapshot pool by Elo so rehearsal favours the STRONG
        # snapshots and the ego climbs the ladder. Gated by use_elo_pfsp; teacher
        # retention below is untouched. (Falls back to fixed policy weights off.)
        if self.config.get("use_elo_pfsp") and getattr(self, "_pool_elo", None):
            from student.opponent_elo import pfsp_weights
            pol = [i for i, e in enumerate(pool) if e.get("mode") == "policy"]
            if len(pol) >= 2:
                ego = getattr(self, "_ego_elo", 1000.0)
                elos = [self._pool_elo.get(_opponent_name(pool[i]), ego) for i in pol]
                pw = pfsp_weights(elos)
                pol_total = float(weights[pol].sum())      # preserve policy budget
                fl = 0.05 / len(pol)
                pw = np.maximum(pw, fl); pw = pw / pw.sum()
                # [MOD-PFSPCAP] the softmax has a FLOOR but no CEILING: measured
                # 2026-07-29, an 80-Elo spread already sends 67.6% of games to
                # one opponent and 300 Elo sends 96.4%, which is rehearsal
                # against a single policy wearing a pool's clothing. The paper
                # this port follows clipped its sampling probability to
                # [0.2%, 11.7%] over ~31 opponents, i.e. ~3.5x uniform; we keep
                # the same ratio against our own pool size. Iterated because
                # renormalising after a clip can push another entry over.
                cap_mult = float(self.config.get("pfsp_cap_mult", 0.0) or 0.0)
                if cap_mult > 0.0:
                    cap = min(1.0, cap_mult / len(pol))
                    for _ in range(8):
                        over = pw > cap
                        if not over.any():
                            break
                        excess = float((pw[over] - cap).sum())
                        pw[over] = cap
                        room = ~over
                        if not room.any() or excess <= 0.0:
                            break
                        pw[room] += excess * (pw[room] / pw[room].sum())
                for j, i in enumerate(pol):
                    out[i] = pol_total * pw[j]
        for index, entry in enumerate(pool):
            if entry.get("mode") in ("aggressor", "policy"):
                # threats keep their configured share; PFSP redistributes the
                # RETENTION set only. A frozen sparring partner we lose to
                # would otherwise swallow the rehearsal budget and starve the
                # very teachers the pool exists to preserve.
                continue
            window = history.get(_opponent_name(entry))
            if not window or len(window) < 4:
                continue                      # not enough evidence yet
            win_rate = float(sum(window) / len(window))
            out[index] = weights[index] * (floor + (1.0 - floor)
                                           * (1.0 - win_rate) ** exponent)
        # keep the rehearsal bucket the same size overall, only redistributed
        mask = np.array([e.get("mode") not in ("aggressor", "policy")
                         for e in pool])
        if mask.any() and out[mask].sum() > 0:
            out[mask] *= weights[mask].sum() / out[mask].sum()
        return out

    # [MOD-OPPONENT] frozen self-play ------------------------------------
    def _step_policy_opponent(self) -> None:
        """Drive the target with a FROZEN policy bundle.

        The safe half of self-play: the opponent's weights never change, so
        training stays stationary, but it is as strong as we ever were -- the
        only opponent that can realistically shoot us down, and therefore the
        only way loss_rate stops being identically zero.

        The hold logic is not optional. The env polls the target provider once
        per physics substep (60 Hz), while every policy here is trained and
        deployed at one decision per step_ratio substeps (10 Hz). Running the
        LSTM at 60 Hz advances its state six times faster than the dynamics it
        learned -- the exact evaluation bug that cost a day earlier in this
        project -- so the action is computed once and held for step_ratio
        substeps, mirroring ActionRepeatProvider.
        """
        provider = self._ensure_policy_opponent()
        # [되돌림 2026-08-20] 20 Hz 시도를 접으면서 [MOD-OPPHZ] 를 원복했다.
        # (양측 결정 주기를 분리하던 것 — 10 Hz 전용이 된 지금은 필요 없다.)
        ratio = max(1, int(self._step_ratio))
        count = getattr(self, "_policy_hold_count", 0)
        if count % ratio == 0 or getattr(self, "_policy_hold", None) is None:
            context = self._build_action_context(
                self._target_sim, self._sim,
                self._target_state, self._ownship_state, self.pre_obs,
            )
            self._policy_hold = provider.compute_action(context).action
        self._policy_hold_count = count + 1
        self._target_sim.step(self._policy_hold)

    def _ensure_policy_opponent(self):
        entry = getattr(self, "_episode_opponent", None) or {}
        bundle = str(entry.get("bundle")
                     or self.config.get("target_policy_bundle") or "")
        provider = getattr(self, "_policy_opponent", None)
        want_explore = bool((entry or {}).get("explore",
                            self.config.get("target_rl_explore", False)))
        cache_key = (bundle, want_explore)
        if provider is None or getattr(self, "_policy_opponent_bundle", None) != cache_key:
            # Built lazily inside the env worker: an RLlib Algorithm cannot be
            # pickled across Ray, so only the bundle PATH travels in config.
            # [MOD-OPPOBS] student/rl_opponent.RLOpponentProvider, not the
            # SDK's RLActionProvider. Two reasons:
            #   * every pool bundle is observation_size 38 while this workspace
            #     trains on 16, so the opponent must build its OWN observation;
            #     RLOpponentProvider carries a 38-dim builder and ignores ours.
            #   * the SDK provider here would need `module=`, which only the
            #     previous workspace's copy has -- and rl_action_provider.py is
            #     on the submission path and is kept byte-identical to the SDK.
            # It loads the bundle as a bare RLModule (no Algorithm, no Ray:
            # building an Algorithm inside a Ray env-runner actor spawns nested
            # actors and killed a run outright), holds the action for
            # step_ratio substeps, and applies the [-1,1] -> [0,1] throttle
            # conversion the target path does not do for us.
            from student.rl_opponent import RLOpponentProvider
            # [MOD-DEFICIT-T] 풀 엔트리가 explore(탐색잡음)를 지정할 수 있게 —
            # 잡음 엘리트 = 온전한 HP 로 "부상 입히기"를 연습할 수 있는 상대.
            # [MOD-OPPRATE] 2026-08-17: step_ratio=1 이다. **감쇠가 이중이었다.**
            # _step_policy_opponent 는 이미 `_policy_hold_count % step_ratio` 로
            # 물리 substep(60Hz)을 10Hz 로 낮춰서 provider 를 부른다. 그런데
            # provider 안에서도 자기 `_count % step_ratio` 로 또 나눴다.
            # 실측(2026-08-17, env.step 60회):
            #     _step_policy_opponent  360회 (6.00/스텝, substep)
            #     provider.compute_action 60회 (1.00/스텝) <- 이미 10Hz
            #     적기 신규 추론          10회 (0.17/스텝) <- 또 6으로 나뉨
            # => 아군은 0.1초마다, 적기는 **0.6초마다** 조종했다. 6배 핸디캡.
            #
            # 이것이 오래 못 풀던 것들의 공통 원인이다:
            #   * 같은 정책끼리 붙여도 아군 슬롯이 5승 0패(하네스 편향 +0.937)
            #   * self-play 인데 우리만 일방적으로 잘 싸움(36/36 격추, 피딜 0.047)
            #   * w_far 를 어떻게 조정해도 교전거리가 안 줄어듦 — 느린 상대는
            #     멀리서 요리하는 것이 **실제로 최적**이었다
            # 다른 호출 경로(_target_action_provider, 737행)는 substep 마다
            # 부르므로 거기서는 provider 자체 감쇠가 옳다. 그래서 provider 를
            # 고치지 않고 **이 생성 지점에서만** 끈다.
            provider = RLOpponentProvider(
                bundle_dir=bundle, step_ratio=1,
                explore=want_explore)
            provider.reset()
            self._policy_opponent = provider
            self._policy_opponent_bundle = cache_key
        return provider

    def _apply_entry_spawn(self) -> None:
        """Set the TARGET's spawn for this episode.

        The per-episode randomization path only ever touches the ownship
        (reset calls add_random_init_position("ownship", ...)), so a pool
        entry's geometry -- which lives almost entirely in the target's
        position -- never landed through the scatter hook alone. Measured:
        every teacher entry started at the stage's ~900 m instead of its own
        600-3,000 m benchmark geometry.

        The stage's own target spawn is snapshotted once; every reset then
        pins the target to the entry geometry when one was drawn, or back to
        the stage base when not, so an override cannot leak into the next
        episode.
        """
        target = self._target_sim
        base = getattr(target, "_dogfight_stage_spawn", None)
        if base is None:
            base = [target._init_pos_n, target._init_pos_e, target._init_pos_d,
                    target._init_roll, target._init_pitch, target._init_heading,
                    target._init_speed]
            target._dogfight_stage_spawn = base
        entry = getattr(self, "_episode_opponent", None) or {}
        arr = (entry.get("spawn") or {}).get("target") or base
        self.change_init_position(
            "target",
            init_n=float(arr[0]), init_e=float(arr[1]), init_d=float(arr[2]),
            init_roll=float(arr[3]), init_pitch=float(arr[4]),
            init_heading=float(arr[5]),
            init_speed=float(arr[6]) if len(arr) > 6 else float(base[6]),
            target_type=getattr(self, "_target_type", 2),
        )

    def _reset_policy_opponent(self) -> None:
        provider = getattr(self, "_policy_opponent", None)
        if provider is not None:
            provider.reset()          # fresh LSTM state each episode
        self._policy_hold = None
        self._policy_hold_count = 0
    # [/MOD-OPPONENT frozen self-play] -----------------------------------

    def _reset_aggressor(self) -> None:
        provider = getattr(self, "_aggressor", None)
        if provider is not None:
            provider.reset()
    # [/MOD-OPPONENT] ----------------------------------------------------

    # [MOD-PURSUIT] ------------------------------------------------------
    def _sample_pursuit_params(self) -> None:
        """Sample per-episode chaser parameters so the teacher varies."""
        cfg = self.config.get("target_pursuit", {}) or {}

        def _sample(key, default_lo, default_hi):
            rng = cfg.get(key) or [default_lo, default_hi]
            lo, hi = float(rng[0]), float(rng[1])
            return lo + (hi - lo) * float(np.random.random())

        self._pursuit_params = {
            "speed_mps": _sample("speed_mps_range", 200.0, 280.0),
            "lead_time_s": _sample("lead_time_s_range", 0.0, 1.5),
            "altitude_bias_m": _sample("altitude_bias_m_range", -300.0, 300.0),
        }

    def _pursuit_autopilot_cmds(self) -> tuple:
        """Lead-pursuit autopilot commands toward the ownship.

        lead_time 0 = pure pursuit; >0 aims at the ownship's predicted
        position (harder teacher). Returns (heading_deg, altitude_D_m,
        speed_mps) for FighterSim.step_autopilot.
        """
        params = getattr(self, "_pursuit_params", None) or {
            "speed_mps": 250.0,
            "lead_time_s": 0.0,
            "altitude_bias_m": 0.0,
        }
        own = self._ownship_state
        tgt = self._target_state

        # ownship NED velocity from body velocity + Euler angles
        d2r = math.pi / 180.0
        roll, pitch, yaw = (
            float(own[StateIndex.ROLL]) * d2r,
            float(own[StateIndex.PITCH]) * d2r,
            float(own[StateIndex.YAW]) * d2r,
        )
        cr, sr = math.cos(roll), math.sin(roll)
        cp, sp = math.cos(pitch), math.sin(pitch)
        cy, sy = math.cos(yaw), math.sin(yaw)
        tx = np.array([[1, 0, 0], [0, cr, sr], [0, -sr, cr]])
        ty = np.array([[cp, 0, -sp], [0, 1, 0], [sp, 0, cp]])
        tz = np.array([[cy, sy, 0], [-sy, cy, 0], [0, 0, 1]])
        v_own_ned = (tx @ ty @ tz).T @ np.array(
            [float(own[6]), float(own[7]), float(own[8])]
        )

        lead = float(params["lead_time_s"])
        aim_n = float(own[0]) + v_own_ned[0] * lead
        aim_e = float(own[1]) + v_own_ned[1] * lead
        aim_d = float(own[2]) + v_own_ned[2] * lead

        heading_cmd = math.degrees(
            math.atan2(aim_e - float(tgt[1]), aim_n - float(tgt[0]))
        ) % 360.0
        # keep the chaser off the deck: never command below 1000 m altitude
        altitude_cmd = min(aim_d + float(params["altitude_bias_m"]), -1000.0)
        return heading_cmd, altitude_cmd, float(params["speed_mps"])
    # [/MOD-PURSUIT] -----------------------------------------------------

    def get_observation(self):
        return self._build_observation_for(self._ownship_state, self._target_state)

    # [MOD-OBSROLE] 2026-08-17: 관측을 만드는 주체를 학생 모듈에 알린다.
    # my_observation 은 경과시간을 호출 횟수로 센다(9/9 패킷에 시간이 없다).
    # 그 카운터가 전역 하나였는데, 아래 _build_action_context 가 **적기 시점**
    # 으로도 이 헬퍼를 불러 같은 슬롯을 덮어썼다. 두 기체는 760~3,048 m
    # 떨어져 있어 매 호출이 "리셋"으로 오인됐고, self-play 내내 time_norm 이
    # 0 에 고정됐다(실측 2026-08-17). observer 를 넘겨 슬롯을 분리한다.
    def _build_observation_for(self, ownship_state, target_state,
                               observer: str = "ownship") -> np.ndarray:
        if self._observation_fn is not None:
            observation = self._observation_fn(
                np.array(ownship_state, copy=True),
                np.array(target_state, copy=True),
                self._geo_info,
                self._wez,
                **({"observer": observer} if self._obs_fn_takes_observer else {}),
            )
            observation = np.asarray(observation, dtype=np.float32)
            if observation.shape != (self.num_observation,):
                raise ValueError(
                    "custom observation_fn returned shape "
                    f"{observation.shape}, expected {(self.num_observation,)}"
                )
            return observation

        wez_cfg = self._wez if self._observation_mode == "tactical16" else None
        return build_observation(
            self._observation_mode,
            ownship_state,
            target_state,
            self._geo_info,
            wez_cfg,
        )

    def get_reward(self):
        terminated, truncated, end_condition = evaluate_termination(
            self._ownship_state,
            self._target_state,
            self._sim,
            self._target_sim,
            self._max_engage_time,
            self._min_altitude,
            self.current_timestep,
            self._episode_step_limit,
            self._geo_info,
            self._geometry_guard,
        )
        _reward_fn = self._reward_fn if self._reward_fn is not None else compute_reward
        result = _reward_fn(
            self._ownship_state,
            self._target_state,
            self.ownship_damage,
            self.target_damage,
            self._geo_info,
            self._wez,
            self._reward_config,
            terminated,
            truncated,
            end_condition,
        )
        return result[0] if isinstance(result, tuple) else result

    def get_done(self):
        return evaluate_termination(
            self._ownship_state,
            self._target_state,
            self._sim,
            self._target_sim,
            self._max_engage_time,
            self._min_altitude,
            self.current_timestep,
            self._episode_step_limit,
            self._geo_info,
            self._geometry_guard,
        )[:2]

    def _print_episode_termination(self, end_condition: str) -> None:
        print(
            f"runner:{self._runner_index}/env:{self._env_index}\t"
            f"num_steps=[{self._ep_step_count}] | "
            f"total rewards=[{self._ep_total_reward:.4f}] | "
            f"termination= [{end_condition}]",
            flush=True,
        )

    # [MOD-WEZPHASE] Competition WEZ widens with engagement time (manual:
    # 0-100 s LOS<1 deg / 500-3000 ft / x1.0, 100-150 s LOS<2 deg / 500-3500 ft
    # / x0.3, 150-200 s LOS<3 deg / 500-4000 ft / x0.1, lower phase wins when
    # both apply). Training uses the fixed +-1 deg cone unless a stage opts in
    # via env_config["wez_phases"]["enabled"], so default behaviour is
    # unchanged.
    def _active_wez_envelopes(self, sim_time: float) -> list[dict]:
        cfg = self.config.get("wez_phases") or {}
        if not cfg.get("enabled", False):
            return [{
                "angle_deg": self._wez["angle_deg"],
                "min_range_m": self._wez["min_range_m"],
                "max_range_m": self._wez["max_range_m"],
                "damage_scale": 1.0,
            }]
        envs = []
        for phase in cfg.get("phases", []):
            if float(sim_time) >= float(phase.get("after_s", 0.0)):
                envs.append({
                    "angle_deg": float(phase["angle_deg"]),
                    "min_range_m": float(phase.get("min_range_m", self._wez["min_range_m"])),
                    "max_range_m": float(phase["max_range_m"]),
                    "damage_scale": float(phase.get("damage_scale", 1.0)),
                })
        return envs or [{
            "angle_deg": self._wez["angle_deg"],
            "min_range_m": self._wez["min_range_m"],
            "max_range_m": self._wez["max_range_m"],
            "damage_scale": 1.0,
        }]

    @staticmethod
    def _wez_damage(env: dict, dis_m: float, ata_deg: float, delta_t: float,
                    global_scale: float = 1.0) -> float:
        span = env["max_range_m"] - env["min_range_m"]
        if span <= 0 or not (env["min_range_m"] <= dis_m <= env["max_range_m"]):
            return 0.0
        if abs(ata_deg) > env["angle_deg"] / 2.0:
            return 0.0
        return (((env["max_range_m"] - dis_m) / span) * delta_t
                * env["damage_scale"] * float(global_scale))

    def update_damage(self):
        sim_state = self._sim.get_state()
        target_sim_state = self._target_sim.get_state()
        dis_m = self._geo_info._get_distance(sim_state, target_sim_state)
        ownship_ata_deg = self._geo_info._get_antenna_train_angle(sim_state, target_sim_state, False)
        target_ata_deg = self._geo_info._get_antenna_train_angle(target_sim_state, sim_state, False)

        envelopes = self._active_wez_envelopes(
            float(sim_state[StateIndex.SIM_TIME])
        )
        # [MOD-HPSCALE] 2026-08-21 — 데미지 전역 배율.
        #
        # 왜: 실서버 교전은 160~200초로 딜 마진 판정까지 가는데, 학습은 29초에
        # 동귀어진으로 끝난다(오프라인 25판 전부 29.2~29.5초). 정책이 **장기전을
        # 겪어본 적이 없다**. HP 를 10배로 늘리는 것과 같은 효과를 내려면 데미지를
        # 1/10 로 주면 된다. FighterSim.py 는 제출 원본이라 손대지 않는다.
        #
        # 보상 쪽 `w_damage`/`w_damage_taken` 은 스텝당 데미지에 곱해지므로,
        # 같은 기울기 크기를 유지하려면 **함께 10배**로 올려야 한다.
        # 제출 시 되돌릴 필요 없다 -- 이 파일은 대회 경로에서 실행되지 않는다.
        # 데미지는 대회 서버가 계산하고, 관측에 HP 가 없어 정책은 크기를 못 본다.
        dscale = float(self.config.get("wez_damage_scale", 1.0) or 1.0)
        target_damage = 0.0
        ownship_damage = 0.0
        for env in envelopes:   # ordered: earliest (strongest) phase wins
            if target_damage == 0.0:
                target_damage = self._wez_damage(
                    env, dis_m, ownship_ata_deg, self._delta_t, dscale)
            if ownship_damage == 0.0:
                ownship_damage = self._wez_damage(
                    env, dis_m, target_ata_deg, self._delta_t, dscale)
            if target_damage and ownship_damage:
                break

        self.ownship_damage = ownship_damage
        self.target_damage = target_damage
        self._in_wez = target_damage > 0.0  # True when ownship is inside WEZ toward target
        self._sim.deduct_health(ownship_damage)
        self._target_sim.deduct_health(target_damage)

    def change_init_position(
        self,
        flight="ownship",
        init_n=0,
        init_e=0,
        init_d=-8000,
        init_roll=0,
        init_pitch=0,
        init_heading=0,
        init_speed=250,
        target_type=2,
    ):
        fighter = self._sim if flight == "ownship" else self._target_sim
        self._target_type = target_type
        fighter._init_pos_n = init_n
        fighter._init_pos_e = init_e
        fighter._init_pos_d = init_d
        fighter._init_roll = init_roll
        fighter._init_pitch = init_pitch
        fighter._init_heading = init_heading
        fighter._init_speed = init_speed
        lla = pm.ned2geodetic(
            fighter._init_pos_n,
            fighter._init_pos_e,
            fighter._init_pos_d,
            fighter._origin_lat,
            fighter._origin_lon,
            fighter._origin_alt,
        )
        fighter._init_pos_lat = lla[0]
        fighter._init_pos_lon = lla[1]
        fighter._init_pos_alt = lla[2]

    def _apply_two_circle_headon_initial_scenario(self, scenario: dict) -> None:
        """Place both aircraft on the paper's two-circle head-on curriculum."""
        alpha_deg = float(scenario.get("alpha_deg", 0.0))
        alpha_rad = math.radians(alpha_deg)
        turn_diameter_ft = float(scenario.get("turn_diameter_ft", 6000.0))
        jitter_min_ft, jitter_max_ft = self._range_values(
            scenario.get("separation_jitter_ft", [3000.0, 6000.0])
        )
        jitter_ft = float(self.np_random.uniform(jitter_min_ft, jitter_max_ft))
        separation_m = (
            2.0 * turn_diameter_ft * math.sin(alpha_rad) + jitter_ft
        ) * FEET_TO_METER

        center_n = float(scenario.get("center_n_m", 3500.0))
        center_e = float(scenario.get("center_e_m", 0.0))
        altitude_m = float(scenario.get("altitude_m", 7000.0))
        half_sep = separation_m / 2.0

        speed_min, speed_max = self._range_values(
            scenario.get("speed_mps_range", [250.0, 300.0])
        )
        roll_min, roll_max = self._range_values(
            scenario.get("roll_range_deg", [0.0, 180.0])
        )
        side = float(self.np_random.choice(scenario.get("side_choices", [-1.0, 1.0])))
        pitch = float(self.np_random.choice(
            scenario.get("vertical_pitch_choices_deg", [0.0, 10.0, -10.0])
        ))

        own_heading = self._wrap_heading(side * alpha_deg)
        target_heading = self._wrap_heading(180.0 + side * alpha_deg)
        own_roll = float(self.np_random.uniform(roll_min, roll_max))
        target_roll = float(self.np_random.uniform(roll_min, roll_max))
        own_speed = float(self.np_random.uniform(speed_min, speed_max))
        target_speed = float(self.np_random.uniform(speed_min, speed_max))

        self.change_init_position(
            "ownship",
            init_n=center_n - half_sep,
            init_e=center_e,
            init_d=-altitude_m,
            init_roll=own_roll,
            init_pitch=pitch,
            init_heading=own_heading,
            init_speed=own_speed,
        )
        self.change_init_position(
            "target",
            init_n=center_n + half_sep,
            init_e=center_e,
            init_d=-altitude_m,
            init_roll=target_roll,
            init_pitch=-pitch,
            init_heading=target_heading,
            init_speed=target_speed,
        )

        self._initial_scenario_metrics = {
            "initial_alpha_deg": alpha_deg,
            "initial_distance_m": separation_m,
        }

    def _apply_ref_old_random_initial_scenario(self, scenario: dict) -> None:
        """Apply ref_oldDogFightEnv 1vs1 mixed BT/loiter initial scenarios."""
        indices = list(scenario.get("legacy_scenario_indices", [0]))
        if scenario.get("legacy_use_first_scenario_only", False):
            scenario_index = int(indices[0])
        elif scenario.get("legacy_use_random_scenario", True):
            scenario_index = int(self.np_random.choice(indices))
        else:
            scenario_index = int(scenario.get("legacy_scenario_index", indices[0]))
        ownship, target = REF_OLD_RANDOM_SCENARIOS[scenario_index]

        self.change_init_position(
            "ownship",
            init_n=ownship[0],
            init_e=ownship[1],
            init_d=ownship[2],
            init_roll=ownship[3],
            init_pitch=ownship[4],
            init_heading=ownship[5],
            init_speed=ownship[6],
            target_type=ownship[7],
        )
        self.change_init_position(
            "target",
            init_n=target[0],
            init_e=target[1],
            init_d=target[2],
            init_roll=target[3],
            init_pitch=target[4],
            init_heading=target[5],
            init_speed=target[6],
            target_type=target[7],
        )

        randomization = scenario.get("legacy_randomization", {})
        self.add_random_init_position(
            "ownship",
            radius=float(randomization.get("aircraft_radius_m", 100.0)),
            r_roll=float(randomization.get("roll_deg", 5.0)),
            r_pitch=float(randomization.get("pitch_deg", 5.0)),
            r_heading=float(randomization.get("heading_deg", 5.0)),
        )
        self.add_random_init_position(
            "target",
            radius=float(randomization.get("aircraft_radius_m", 100.0)),
            r_roll=float(randomization.get("roll_deg", 5.0)),
            r_pitch=float(randomization.get("pitch_deg", 5.0)),
            r_heading=float(randomization.get("heading_deg", 5.0)),
        )
        self._add_ref_old_shared_random_starting_position(randomization)

        if int(target[7]) == 1:
            bank_min, bank_max = self._range_values(
                randomization.get("loiter_bank_deg_range", [40.0, 70.0])
            )
            bank = float(
                self.np_random.choice([-1.0, 1.0])
                * self.np_random.uniform(bank_min, bank_max)
            )
            self.config["target_mode"] = "loiter"
            self.config["target_loiter"] = {
                "enabled": True,
                "bank": bank,
                "pitch": 0.0,
            }
        else:
            self.config["target_mode"] = "behavior_tree"

        self._initial_scenario_metrics = {
            "legacy_scenario_index": float(scenario_index),
        }

    def _add_ref_old_shared_random_starting_position(self, randomization: dict) -> None:
        sign = np.array([-1.0, 1.0])
        rand_n = float(
            self.np_random.choice(sign)
            * self.np_random.uniform(
                0.0, float(randomization.get("shared_n_m", 4000.0))
            )
        )
        rand_e = float(
            self.np_random.choice(sign)
            * self.np_random.uniform(
                0.0, float(randomization.get("shared_e_m", 4000.0))
            )
        )
        rand_d = float(
            self.np_random.choice(sign)
            * self.np_random.uniform(
                0.0, float(randomization.get("shared_d_m", 4000.0))
            )
        )
        rand_distance_n = float(
            self.np_random.choice(sign)
            * self.np_random.uniform(
                0.0, float(randomization.get("target_distance_n_m", 300.0))
            )
        )
        rand_speed = float(
            self.np_random.choice(sign)
            * self.np_random.uniform(
                0.0, float(randomization.get("speed_mps", 50.0))
            )
        )

        self._sim._init_pos_n += rand_n
        self._sim._init_pos_e += rand_e
        self._sim._init_pos_d += rand_d
        self._sim._init_speed += rand_speed
        self._target_sim._init_pos_n += rand_n + rand_distance_n
        self._target_sim._init_pos_e += rand_e
        self._target_sim._init_pos_d += rand_d
        self._target_sim._init_speed += rand_speed

        for fighter in (self._sim, self._target_sim):
            lla = pm.ned2geodetic(
                fighter._init_pos_n,
                fighter._init_pos_e,
                fighter._init_pos_d,
                fighter._origin_lat,
                fighter._origin_lon,
                fighter._origin_alt,
            )
            fighter._init_pos_lat = lla[0]
            fighter._init_pos_lon = lla[1]
            fighter._init_pos_alt = lla[2]

    def _update_initial_geometry_metrics(self, scenario_mode: str) -> None:
        if scenario_mode not in ("two_circle_headon", "ref_old_random"):
            return
        ata = abs(float(self._geo_info._get_antenna_train_angle(
            self._ownship_state, self._target_state, True
        )))
        aa = abs(float(self._geo_info._get_aspect_angle(
            self._ownship_state, self._target_state, True
        )))
        distance = float(self._geo_info._get_distance(
            self._ownship_state, self._target_state
        ))
        self._initial_scenario_metrics.update({
            "initial_ata_deg": ata,
            "initial_aa_deg": aa,
            "initial_distance_m": distance,
        })

    @staticmethod
    def _range_values(values) -> tuple[float, float]:
        if isinstance(values, (int, float)):
            value = float(values)
            return value, value
        if len(values) != 2:
            raise ValueError(f"Expected two range values, got {values!r}")
        return float(values[0]), float(values[1])

    @staticmethod
    def _wrap_heading(value: float) -> float:
        return float(value % 360.0)

    def add_random_init_position(self, flight="ownship", radius=500.0, r_roll=5, r_pitch=5, r_heading=5):
        fighter = self._sim if flight == "ownship" else self._target_sim
        sign = np.array([-1.0, 1.0])

        # [MOD-RESETDRIFT] Scatter around the BASE spawn, do not accumulate.
        # The original code used `+=`, so every reset random-walked the spawn:
        # measured over 40 resets the initial altitude wandered 5797 -> 8085 ->
        # 1446 m and initial pitch/roll drifted to -43/-49 deg. In training
        # (thousands of resets per worker) the spawn eventually left the valid
        # envelope and ~90% of episodes died with a NaN state on step 1 —
        # 751 of 843 terminations, all at step 1. Snapshot the base once and
        # always set = base + offset.
        base = getattr(fighter, "_dogfight_base_spawn", None)
        if base is None:
            base = {
                "n": fighter._init_pos_n,
                "e": fighter._init_pos_e,
                "d": fighter._init_pos_d,
                "roll": fighter._init_roll,
                "pitch": fighter._init_pitch,
                "heading": fighter._init_heading,
            }
            fighter._dogfight_base_spawn = base

        # [MOD-OPPONENT] a pool entry may pin this episode's geometry so the
        # retention set trains on the geometry it is graded on. Measured
        # 2026-07-21: head_on_merge regressed to 0.125 in BOTH the PFSP and
        # the anchored runs because no training episode ever visited a 760 m
        # merge -- rehearsal data and a KL anchor are both powerless on states
        # that never occur. Overrides the episode's BASE only; the permanent
        # snapshot stays untouched.
        entry_spawn = (getattr(self, "_episode_opponent", None) or {}).get("spawn")
        if entry_spawn:
            key = "ownship" if fighter is self._sim else "target"
            arr = entry_spawn.get(key)
            if arr:
                base = {"n": float(arr[0]), "e": float(arr[1]), "d": float(arr[2]),
                        "roll": float(arr[3]), "pitch": float(arr[4]),
                        "heading": float(arr[5])}
                if len(arr) > 6:
                    fighter._init_speed = float(arr[6])

        def scatter(span):
            span = float(span)
            if span <= 0:
                return 0.0
            return float(self.np_random.choice(sign) * self.np_random.integers(0, span))

        fighter._init_pos_n = base["n"] + scatter(radius)
        fighter._init_pos_e = base["e"] + scatter(radius)
        fighter._init_pos_d = base["d"] + scatter(radius)
        fighter._init_roll = base["roll"] + scatter(r_roll)
        fighter._init_pitch = base["pitch"] + scatter(r_pitch)
        fighter._init_heading = base["heading"] + scatter(r_heading)

        if fighter._init_roll > 180:
            fighter._init_roll -= 360
        if fighter._init_roll < -180:
            fighter._init_roll += 360
        if fighter._init_pitch > 180:
            fighter._init_pitch -= 360
        if fighter._init_pitch < -180:
            fighter._init_pitch += 360
        if fighter._init_heading > 360:
            fighter._init_heading -= 360
        if fighter._init_heading < 0:
            fighter._init_heading += 360

        lla = pm.ned2geodetic(
            fighter._init_pos_n,
            fighter._init_pos_e,
            fighter._init_pos_d,
            fighter._origin_lat,
            fighter._origin_lon,
            fighter._origin_alt,
        )
        fighter._init_pos_lat = lla[0]
        fighter._init_pos_lon = lla[1]
        fighter._init_pos_alt = lla[2]

    def _append_logs(self):
        self.ownship_log.append(
            [
                self._ownship_state[StateIndex.LAT],
                self._ownship_state[StateIndex.LON],
                self._ownship_state[StateIndex.ALT],
                self._ownship_state[StateIndex.ROLL],
                self._ownship_state[StateIndex.PITCH],
                self._ownship_state[StateIndex.YAW],
                self._ownship_state[StateIndex.HEALTH],
            ]
        )
        self.target_log.append(
            [
                self._target_state[StateIndex.LAT],
                self._target_state[StateIndex.LON],
                self._target_state[StateIndex.ALT],
                self._target_state[StateIndex.ROLL],
                self._target_state[StateIndex.PITCH],
                self._target_state[StateIndex.YAW],
                self._target_state[StateIndex.HEALTH],
            ]
        )

    def _build_action_context(self, sim, opponent_sim, ownship_state, target_state, observation) -> ActionContext:
        if ownship_state is not None and target_state is not None:
            # [MOD-OBSROLE] 이 헬퍼는 ownship_state 시점으로 관측을 만든다.
            # 적기 provider 가 부를 때는 ownship_state 가 **적기** 다.
            observation = self._build_observation_for(
                np.array(ownship_state, copy=True),
                np.array(target_state, copy=True),
                observer=("ownship" if ownship_state is self._ownship_state
                          else "target"),
            )
        return ActionContext(
            sim=sim,
            opponent_sim=opponent_sim,
            ownship_state=np.array(ownship_state, copy=True) if ownship_state is not None else None,
            target_state=np.array(target_state, copy=True) if target_state is not None else None,
            observation=np.array(observation, copy=True) if observation is not None else None,
            info={"timestep": self.current_timestep},
        )

    def _reset_action_providers(self) -> None:
        for provider, sim, opponent, ownship_state, target_state in (
            (self._ownship_action_provider, self._sim, self._target_sim, self._ownship_state, self._target_state),
            (self._target_action_provider, self._target_sim, self._sim, self._target_state, self._ownship_state),
        ):
            if provider is None:
                continue
            provider.reset(self._build_action_context(sim, opponent, ownship_state, target_state, self.pre_obs))

    def get_ownship_sim(self):
        return self._sim

    def get_target_sim(self):
        return self._target_sim

    def get_ownship_action(self):
        return np.array(self._sim.action, dtype=np.float32)

    def get_target_action(self):
        return np.array(self._target_sim.action, dtype=np.float32)

    def get_ownship_VP(self):
        return np.array(self._sim.VP, dtype=np.float32)

    def get_target_VP(self):
        return np.array(self._target_sim.VP, dtype=np.float32)

    def get_ownship_state(self) -> np.ndarray:
        return self._ownship_state

    def get_target_state(self) -> np.ndarray:
        return self._target_state

    def get_damage(self):
        return self.ownship_damage, self.target_damage

    def get_ownship_state_for_udp(self) -> List:
        return [
            self._ownship_state[StateIndex.N],
            self._ownship_state[StateIndex.E],
            -self._ownship_state[StateIndex.D],
            self._ownship_state[StateIndex.ROLL],
            self._ownship_state[StateIndex.PITCH],
            self._ownship_state[StateIndex.YAW],
            self._ownship_state[StateIndex.HEALTH],
        ]

    def get_target_state_for_udp(self) -> List:
        return [
            self._target_state[StateIndex.N],
            self._target_state[StateIndex.E],
            -self._target_state[StateIndex.D],
            self._target_state[StateIndex.ROLL],
            self._target_state[StateIndex.PITCH],
            self._target_state[StateIndex.YAW],
            self._target_state[StateIndex.HEALTH],
        ]

    def make_tacviewLog(self):
        os.makedirs(self._artifacts_dir, exist_ok=True)
        timestamp = datetime.datetime.today()
        ownship_filename = (
            f"{timestamp.year}_{timestamp.month}_{timestamp.day}_{timestamp.hour}_{timestamp.minute}_{timestamp.second}_ownship_(F-16)[Blue].csv"
        )
        target_filename = (
            f"{timestamp.year}_{timestamp.month}_{timestamp.day}_{timestamp.hour}_{timestamp.minute}_{timestamp.second}_target_(F-16)[Red].csv"
        )
        summary_filename = (
            f"{timestamp.year}_{timestamp.month}_{timestamp.day}_{timestamp.hour}_{timestamp.minute}_{timestamp.second}_summary.json"
        )
        self._write_log(os.path.join(self._artifacts_dir, ownship_filename), self.ownship_log)
        self._write_log(os.path.join(self._artifacts_dir, target_filename), self.target_log)
        self._write_log_summary(os.path.join(self._artifacts_dir, summary_filename))

    def _write_log(self, path: str, entries: List[List[float]]) -> None:
        with open(path, "w", encoding="utf-8") as file:
            file.write(
                "Time,Longitude,Latitude,Altitude,Roll (deg),Pitch (deg),"
                "Yaw (deg),Health\n"
            )
            # [MOD-REPLAYTIME] One row is appended per DECISION step, not per
            # physics substep, so consecutive rows are step_ratio/sim_hz apart.
            # Stamping them at 1/sim_hz made every replay run step_ratio times
            # too fast: a measured 114 s engagement was written as a 19 s one,
            # and anything reading these timestamps -- Tacview, the dashboard
            # replay tab, the competition viewer -- played it back at 6x.
            row_interval = self._delta_t * max(1, int(self._step_ratio))
            for step, item in enumerate(entries):
                time_value = np.floor(row_interval * step * 10000) / 10000
                health = item[6] if len(item) > 6 else ""
                file.write(
                    f"{time_value},{item[1]},{item[0]},{item[2]},"
                    f"{item[3]},{item[4]},{item[5]},{health}\n"
                )

    def _write_log_summary(self, path: str) -> None:
        summary = {
            "end_condition": self.info.get("end_condition", ""),
            "outcome": self.info.get("outcome", ""),
            # Which opponent this episode faced. Without it a replay of the
            # straight teacher (a legitimate 10% of pooled episodes) is
            # indistinguishable from a broken aggressor -- and was reported as
            # exactly that confusion while watching the dashboard.
            "opponent": self.info.get("opponent", ""),
            "ownship_health": self.info.get("ownship_health", None),
            "target_health": self.info.get("target_health", None),
        }
        with open(path, "w", encoding="utf-8") as file:
            json.dump(summary, file, indent=2, ensure_ascii=False)

    def render(self):
        return None

    def close(self):
        if getattr(self, "_closed", True):
            return
        self._closed = True
        providers = (
            getattr(self, "_ownship_action_provider", None),
            getattr(self, "_target_action_provider", None),
        )
        for provider in providers:
            if provider is not None:
                try:
                    provider.close()
                except Exception:
                    pass
        sim_ai_pairs = (
            (getattr(self, "_sim", None), getattr(self, "_ownship_ai", None)),
            (getattr(self, "_target_sim", None), getattr(self, "_target_ai", None)),
        )
        for sim, ai in sim_ai_pairs:
            if (
                ai is not None
                and sim is not None
                and getattr(sim, "_model", None) is not None
            ):
                try:
                    ai.RemoveBT(sim.get_model().fighterID)
                except Exception:
                    pass
        battle_space_id = getattr(self, "battle_space_id", None)
        if battle_space_id is not None:
            try:
                JSBSimWrapper.RemoveSpace(battle_space_id)
            except Exception:
                pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


__all__ = ["DogFightEnv", "normalize", "FEET_TO_METER", "METER_TO_FEET"]
