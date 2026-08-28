# -*- coding: utf-8 -*-
"""[학생 파일] 옛 38차원 정책을 상대로 붙이는 어댑터.

문제
----
새 학습기는 관측이 16차원(`student.my_observation`)인데, 이전 워크스페이스에서
학습한 번들 52개는 전부 **38차원**이다(`metadata.observation_size == 38`).
env 는 `_build_observation_for()` 하나로 양쪽 관측을 만들기 때문에, 그냥 붙이면
38차원 정책에 16차원 벡터가 들어가 shape 오류로 죽는다.

해결 — 플랫폼 수정 0
--------------------
원본 SDK 의 `RLActionProvider` 가 이미 `obs_builder` 를 받는다:

    RLActionProvider(bundle_dir=..., obs_builder=Callable[[ActionContext], np.ndarray])

즉 **상대가 자기 관측을 스스로 만들도록** 설계돼 있다. 여기에 38차원 빌더를
꽂으면 16차원 학습기와 38차원 상대가 같은 env 에서 공존한다.
`FighterSim.py` / `single_agent_env.py` 를 건드릴 필요가 없다 —
교사(`teacher_provider.py`)를 붙인 것과 같은 훅이다.

주의
----
* 상대 provider 에게 오는 `context.ownship_state` 는 **상대 자신**이고
  `context.target_state` 가 우리다(env 가 시점을 뒤집어 넘긴다).
* 38차원 관측은 51칸 상태의 ALT/KCAS/HEALTH 등을 읽는다. 학습 env 는 그 칸을
  채우므로 문제없다 — 이 경로는 **학습에서만** 돌고 대회에 안 나간다.
* 10 Hz 유지: env 가 물리 substep 마다 provider 를 부르므로, 정책 추론은
  `step_ratio` 마다 하고 그 사이는 직전 행동을 반복한다. 이걸 안 하면 LSTM 이
  학습 때보다 6배 빠르게 은닉상태를 갱신한다(이 프로젝트가 하루 날린 버그).

2026-08-03 실측으로 고친 것 두 가지
-----------------------------------
1. **Ray 를 부르면 안 된다.** 처음엔 `RLActionProvider` +
   `build_algorithm_from_bundle` 을 썼는데, 그 함수는 추론 전용이라
   `ray.shutdown()` 후 `ray.init(local_mode=True)` 를 한다. 학습 러너 안에서
   실행되면 워커가 클러스터에서 떨어져 나간다 — stage 12 를 러너 2개로 돌려
   보니 지표가 전부 n/a 로 나오다가 raylet 이 "missed too many heartbeats" 로
   노드를 죽이고 프로세스가 access violation 으로 끝났다.
   상대는 forward 만 하면 되므로 Algorithm 이 필요 없다. RLModuleSpec 으로
   모듈만 세우고 번들 가중치를 넣는다(키 14개 완전 일치, Ray 미사용).
2. **스로틀 규약이 다르다.** 우리 기체는 env 가
   `_to_sim_action()` 으로 [-1,1] -> [0,1] 을 변환해 주지만, 적기 경로
   (`_step_target_aircraft`)는 provider 의 출력을 **그대로** 시뮬에 넣는다.
   그래서 정책의 스로틀 -1(아이들)~+1(최대) 이 0~1 로 해석되고, 게다가
   `clip_action` 의 하한이 0.0 이라 음수는 전부 아이들로 잘린다. 순항 출력
   0.1 이 0.55 가 아니라 0.1 로 들어가 적기가 추력 없이 난다. 여기서 직접
   변환한다. (교사 provider 는 애초에 0~1 로 내보내므로 무관하다.)
"""
from __future__ import annotations

import gzip
import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from dogfight.ai.action_provider import ActionContext, ActionProvider, ActionResult

from student.opponent.obs_features38 import make_observation_api

_OBS38_MODE, OBS38_SIZE, _build_obs38, _describe38 = make_observation_api("student38", None)

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
        # [2026-08-05] 16차원(우리 자신의 스냅샷) 지원 — 자가대전 사다리.
        # 38차원은 구 워크스페이스 번들, 16차원은 이 워크스페이스 번들이며
        # 어느 쪽이든 번들 metadata 의 크기를 신뢰하고 그에 맞는 빌더를 쓴다.
        self.obs_dim = obs_dim
        if obs_dim not in (OBS38_SIZE, 16):
            raise ValueError(
                f"opponent bundle is {obs_dim}-dim; supported: 38 (old ws), "
                f"16 (self): {bundle_dir}"
            )
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
    """38차원 번들을 상대로 조종한다. 10 Hz 유지 포함."""

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
    def _obs38(context: ActionContext) -> np.ndarray:
        """상대 시점의 38차원 관측. context.ownship_state 가 상대 자신이다."""
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
            _build_obs38(context.ownship_state, context.target_state, geo, wez),
            dtype=np.float32,
        )

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
            obs = (self._obs16(context) if getattr(inner, "obs_dim", 38) == 16
                   else self._obs38(context))
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
