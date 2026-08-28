# -*- coding: utf-8 -*-
"""[학생 파일] 우리 16차원 번들(스냅샷·챔피언)을 상대 기체에 붙이는 provider.

* 상대 provider 에게 오는 `context.ownship_state` 는 **상대 자신**이고
  `context.target_state` 가 우리다(env 가 시점을 뒤집어 넘긴다).
* 10 Hz 유지: env 가 물리 substep 마다 provider 를 부르므로, 정책 추론은
  `step_ratio` 마다 하고 그 사이는 직전 행동을 반복한다. 이걸 안 하면 LSTM 이
  학습 때보다 6배 빠르게 은닉상태를 갱신한다(이 프로젝트가 하루 날린 버그).
* Ray 를 부르지 않는다 — RLModuleSpec 으로 모듈만 세우고 번들 가중치를 넣는다.
  (`build_algorithm_from_bundle` 은 ray.init 을 다시 해 학습 러너를 클러스터에서 떼어낸다, 2026-08-03 실측)
* 스로틀 규약: 적기 경로(`_step_target_aircraft`)는 provider 출력을 그대로 시뮬에 넣으므로
  [-1,1] -> [0,1] 변환을 여기서 한다(`_to_sim_action`).
* [2026-08-28] 옛 워크스페이스 38차원 번들 어댑터(`student/opponent/obs_features38.py`) 제거 — 16차원 전용.
"""
from __future__ import annotations

import gzip
import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from dogfight.ai.action_provider import ActionContext, ActionProvider, ActionResult

_WEZ_FALLBACK = {"angle_deg": 2.0, "min_range_m": 152.4, "max_range_m": 914.4}

# 적기 경로는 provider 출력을 그대로 시뮬에 넣는다. 우리 기체에 붙는
# `DogFightEnv._to_sim_action` 과 같은 변환을 여기서 해야 한다.
_SIM_LOW = np.array([-1.0, -1.0, -1.0, 0.0], dtype=np.float32)
_SIM_HIGH = np.ones(4, dtype=np.float32)


def _to_sim_action(rl_action: np.ndarray) -> np.ndarray:
    a = np.clip(np.asarray(rl_action, dtype=np.float32), -1.0, 1.0)
    a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    a[3] = (a[3] + 1.0) / 2.0                      # [-1,1] -> [0,1]
    return np.clip(a, _SIM_LOW, _SIM_HIGH)


class _BundleModule:
    """번들 하나를 Ray 없이 torch 모듈로 굴린다.

    `build_algorithm_from_bundle` 은 ray.shutdown()+ray.init(local_mode=True)
    를 하므로 학습 러너 안에서 쓸 수 없다(실측: raylet 노드 사망). 상대는
    forward 만 필요하니 RLModuleSpec 으로 모듈만 세운다.
    """

    def __init__(self, bundle_dir: str):
        import torch
        from gymnasium.spaces import Box
        from ray.rllib.algorithms.ppo.torch.ppo_torch_rl_module import PPOTorchRLModule
        from ray.rllib.core.rl_module.rl_module import RLModuleSpec

        self._torch = torch
        b = Path(bundle_dir)
        meta = json.loads((b / "metadata.json").read_text(encoding="utf-8"))
        md = meta.get("metadata", {})
        with gzip.open(b / "policy_weights.pkl.gz", "rb") as f:
            weights = pickle.load(f)

        obs_dim = int(md["observation_size"])
        self.obs_dim = obs_dim
        if obs_dim != 16:
            raise ValueError(f"opponent bundle is {obs_dim}-dim; only 16 (student16) is supported: {bundle_dir}")
        # 번들이 저장한 model_config 를 그대로 쓴다. 손으로 다시 적으면
        # 활성함수 하나만 어긋나도 가중치가 조용히 안 맞는다.
        model_config = dict(md.get("model_config") or {})
        model_config.setdefault("fcnet_hiddens", [256, 256])
        model_config.setdefault("use_lstm", True)
        model_config.setdefault("lstm_cell_size", 128)

        self.module = RLModuleSpec(
            module_class=PPOTorchRLModule,
            observation_space=Box(-np.inf, np.inf, (obs_dim,), np.float32),
            action_space=Box(-1.0, 1.0, (4,), np.float32),
            inference_only=True,
            model_config=model_config,
        ).build()
        self.module.set_state(weights)
        self.module.eval()
        self._init_state = self.module.get_initial_state()
        self._state = None
        self.reset()

    def reset(self) -> None:
        t = self._torch
        # 분리 가치망(vf_share_layers=False) 번들은 초기 상태가 중첩 dict 다
        # ({"actor_encoder": {h,c}, ...}) — 재귀로 변환한다.
        def rep(v):
            if isinstance(v, dict):
                return {k: rep(x) for k, x in v.items()}
            return t.as_tensor(v).float().unsqueeze(0)
        self._state = rep(self._init_state)

    def act(self, obs: np.ndarray, explore: bool = False) -> np.ndarray:
        t = self._torch
        from ray.rllib.core.columns import Columns

        ob = t.as_tensor(np.asarray(obs, dtype=np.float32)).view(1, 1, -1)
        with t.no_grad():
            out = self.module.forward_inference(
                {Columns.OBS: ob, Columns.STATE_IN: self._state}
            )
        if Columns.STATE_OUT in out:
            self._state = out[Columns.STATE_OUT]
        logits = out[Columns.ACTION_DIST_INPUTS].reshape(-1)
        adim = logits.shape[0] // 2
        mean = logits[:adim]
        if explore:
            std = t.exp(logits[adim:].clamp(-20.0, 2.0))
            mean = mean + std * t.randn_like(std)
        return mean.numpy().astype(np.float32)


class RLOpponentProvider(ActionProvider):
    """16차원 번들을 상대로 조종한다. 10 Hz 유지 포함."""

    def __init__(self, bundle_dir: str, step_ratio: int = 6, explore: bool = False):
        self.bundle_dir = str(bundle_dir)
        self.step_ratio = max(1, int(step_ratio))
        self.explore = bool(explore)
        self._inner = None
        self._hold: np.ndarray | None = None
        self._count = 0

    # ── 지연 생성: torch 모듈은 Ray 액터 사이로 pickle 되지 않는다 ──
    def _ensure(self):
        if self._inner is None:
            self._inner = _BundleModule(self.bundle_dir)
        return self._inner

    @staticmethod
    def _obs16(context: ActionContext) -> np.ndarray:
        """상대 시점의 16차원 관측 (우리 자신의 빌더)."""
        import student.my_observation as _MO
        geo = getattr(context.sim, "_geo_info", None)
        if geo is None:
            from GeoMathUtil import GeometryInfo
            geo = GeometryInfo()
            try:
                context.sim._geo_info = geo
            except Exception:
                pass
        wez = (context.info or {}).get("wez") or _WEZ_FALLBACK
        return np.asarray(
            # observer="target": 경과시간 카운터를 아군과 분리한다.
            # 전에는 전역 하나를 공유해 서로 리셋시켰고, time_norm 이 self-play
            # 내내 0 에 고정됐다(2026-08-17 실측).
            _MO.build_observation(context.ownship_state, context.target_state,
                                  geo, wez, observer="target"),
            dtype=np.float32,
        )

    def reset(self, context: ActionContext | None = None) -> None:
        self._hold = None
        self._count = 0
        if self._inner is not None:
            self._inner.reset()

    def compute_action(self, context: ActionContext) -> ActionResult:
        # 10 Hz 유지. env 는 60 Hz 물리 substep 마다 여기를 부른다.
        if self._hold is None or self._count % self.step_ratio == 0:
            inner = self._ensure()
            dim = getattr(inner, "obs_dim", 16)
            # [MOD-OBSREUSE] 2026-08-21 — env 가 이미 observer="target" 으로
            # 만들어 넘겨준 관측을 **재사용**한다.
            #
            # 전에는 여기서 build_observation 을 다시 불렀다. my_observation 의
            # 경과시간 카운터(_slots["target"])는 호출될 때마다 오르므로,
            # 결정당 2회가 되어 **적기의 time_norm 이 2배속**으로 흘렀다.
            # 실측(4 env.step): build_observation ownship 4회 / target 8회,
            # 적기 obs[-1] 이 스텝당 0.002(=0.2초)씩 증가(아군은 0.001).
            # 대회 경로는 클라이언트당 1회라 1배속 -> **학습에만 있던 불일치**.
            ctx_obs = getattr(context, "observation", None)
            if ctx_obs is not None and int(np.asarray(ctx_obs).size) == int(dim):
                obs = np.asarray(ctx_obs, dtype=np.float32)
            else:
                obs = self._obs16(context)
            raw = inner.act(obs, explore=self.explore)
            self._hold = _to_sim_action(raw)
        self._count += 1
        return ActionResult(action=self._hold, source="rl_opponent",
                            info={"bundle": self.bundle_dir})


def make_rl_opponent(spec: Any, step_ratio: int = 6) -> RLOpponentProvider:
    """spec: 번들 경로 문자열 또는 {"bundle": 경로, "explore": bool}."""
    if isinstance(spec, dict):
        return RLOpponentProvider(spec["bundle"], step_ratio=step_ratio,
                                  explore=bool(spec.get("explore", False)))
    return RLOpponentProvider(str(spec), step_ratio=step_ratio)
