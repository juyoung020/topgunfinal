from __future__ import annotations

import gzip
import json
import pickle
from pathlib import Path
from typing import Any


def _json_safe(value: Any):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _get_rl_module(algorithm, policy_id: str = "default_policy"):
    if not hasattr(algorithm, "get_module"):
        return None
    try:
        module = algorithm.get_module(policy_id)
        if module is not None:
            return module
    except Exception:
        pass
    try:
        return algorithm.get_module()
    except Exception:
        return None


def _extract_policy_weights(algorithm, policy_id: str = "default_policy"):
    module = _get_rl_module(algorithm, policy_id)
    if module is not None and hasattr(module, "get_state"):
        return module.get_state()

    try:
        policy = algorithm.get_policy(policy_id)
        if policy is not None:
            return policy.get_weights()
    except Exception:
        pass

    all_weights = algorithm.get_weights()
    if isinstance(all_weights, dict):
        return all_weights.get(policy_id) or next(iter(all_weights.values()), {})
    return all_weights


def _apply_policy_weights(
    algorithm,
    weights,
    policy_id: str = "default_policy",
) -> bool:
    """Load weights into the LEARNER and push them to every env runner.

    [MOD-WARMSTART] The original implementation set the state of the LOCAL
    env_runner and returned immediately. With `num_env_runners > 0` that local
    runner does not sample, the learner kept its random initial weights, and
    the first train() synced learner -> remote runners, silently discarding the
    restored policy. Measured 2026-08-02 on this workspace: a behaviour-cloned
    bundle whose own std is 0.2516 and whose action MSE against the
    demonstrator is 0.0058 produced rollouts with throttle mean -0.109 and
    action std 1.053 -- an untrained policy -- while the log still printed
    "Explicit bundle weights loaded successfully". Every warm start was a
    no-op. (The previous workspace measured the same two numbers, -0.10 and
    1.05, on 2026-07-20.)

    Order matters: the learner is authoritative because RLlib syncs from it.
    """
    applied = False

    # 1) learner group — this is what gets synced to the samplers
    learner_group = getattr(algorithm, "learner_group", None)
    if learner_group is not None and hasattr(learner_group, "foreach_learner"):
        def _set_on_learner(learner, *args, **kwargs):
            module = getattr(learner, "module", None)
            target = None
            if module is not None:
                try:
                    target = module[policy_id]
                except Exception:
                    target = module
            if target is not None and hasattr(target, "set_state"):
                target.set_state(weights)
                return True
            return False

        try:
            learner_group.foreach_learner(_set_on_learner)
            applied = True
        except Exception:
            pass

    # 2) algorithm-level fallback (old API stack)
    if not applied:
        for candidate in ({policy_id: weights}, weights):
            try:
                algorithm.set_weights(candidate)
                applied = True
                break
            except Exception:
                continue

    # 3) local module / policy fallback
    if not applied:
        module = _get_rl_module(algorithm, policy_id)
        if module is not None and hasattr(module, "set_state"):
            module.set_state(weights)
            applied = True
        else:
            try:
                policy = algorithm.get_policy(policy_id)
                if policy is not None:
                    policy.set_weights(weights)
                    applied = True
            except Exception:
                pass

    if not applied:
        return False

    # 4) push to the samplers: local runner first, then all remote runners
    env_runner = getattr(algorithm, "env_runner", None)
    if env_runner is not None:
        try:
            if hasattr(env_runner, "set_state"):
                env_runner.set_state({"rl_module": weights})
            elif hasattr(env_runner, "module"):
                env_runner.module.set_state(weights)
        except Exception:
            pass

    runner_group = getattr(algorithm, "env_runner_group", None)
    if runner_group is not None:
        pushed = False
        if hasattr(runner_group, "foreach_env_runner"):
            def _set_on_runner(runner, *args, **kwargs):
                try:
                    if hasattr(runner, "set_state"):
                        runner.set_state({"rl_module": weights})
                        return True
                    module = getattr(runner, "module", None)
                    if module is not None and hasattr(module, "set_state"):
                        module.set_state(weights)
                        return True
                except Exception:
                    return False
                return False

            try:
                runner_group.foreach_env_runner(_set_on_runner)
                pushed = True
            except Exception:
                pass
        if not pushed and hasattr(runner_group, "sync_weights"):
            try:
                runner_group.sync_weights()
            except Exception:
                pass

    return True


def save_lightweight_policy_bundle(
    algorithm,
    output_dir,
    policy_id: str = "default_policy",
    metadata: dict | None = None,
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    weights = _extract_policy_weights(algorithm, policy_id)
    config = algorithm.config.to_dict() if hasattr(algorithm.config, "to_dict") else dict(algorithm.config)
    metadata_payload = dict(metadata or {})
    model_config = getattr(algorithm.config, "model_config", None)
    if isinstance(model_config, dict) and model_config:
        metadata_payload.setdefault("model_config", _json_safe(model_config))

    payload = {
        "algorithm_class": algorithm.__class__.__name__,
        "policy_id": policy_id,
        "algorithm_config": _json_safe(config),
        "metadata": _json_safe(metadata_payload),
    }

    metadata_path = output_path / "metadata.json"
    metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    weights_path = output_path / "policy_weights.pkl.gz"
    with gzip.open(weights_path, "wb") as file:
        pickle.dump(weights, file, protocol=pickle.HIGHEST_PROTOCOL)

    return output_path


def load_lightweight_policy_bundle(bundle_dir):
    bundle_path = Path(bundle_dir)
    metadata_path = bundle_path / "metadata.json"
    weights_path = bundle_path / "policy_weights.pkl.gz"

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    with gzip.open(weights_path, "rb") as file:
        weights = pickle.load(file)

    return metadata, weights


def apply_lightweight_policy_bundle(
    algorithm,
    bundle_dir,
    policy_id: str = "default_policy",
) -> dict:
    """Load a lightweight bundle into an RLlib algorithm and verify it."""
    metadata, weights = load_lightweight_policy_bundle(bundle_dir)

    if not _apply_policy_weights(algorithm, weights, policy_id):
        raise RuntimeError(
            "Neither RLModule state loading nor old Policy weight loading worked."
        )

    # [MOD-WARMSTART] Verify against a SAMPLING env runner, not the local
    # module, and compare VALUES. The original check read back the object it
    # had just written and only asserted "not None" -- it passes even when the
    # weights never reached a runner that samples, which is how a no-op warm
    # start went unnoticed for a full day of training.
    _verify_weights_landed(algorithm, weights, policy_id)
    return metadata


def _first_tensor(state: dict):
    """Return (key, flat numpy array) of the first array-like entry."""
    import numpy as np

    for key in sorted(state):
        value = state[key]
        arr = value.detach().cpu().numpy() if hasattr(value, "detach") else value
        arr = np.asarray(arr)
        if arr.size >= 2 and arr.dtype.kind == "f":
            return key, arr.ravel()
    raise RuntimeError("no float tensor found in policy state")


def _verify_weights_landed(algorithm, weights, policy_id: str) -> None:
    import numpy as np

    key, expected = _first_tensor(weights)

    def _probe(runner, *args, **kwargs):
        module = getattr(runner, "module", None)
        if module is None:
            return None
        try:
            target = module[policy_id]
        except Exception:
            target = module
        state = target.get_state() if hasattr(target, "get_state") else None
        if not state or key not in state:
            return None
        value = state[key]
        arr = value.detach().cpu().numpy() if hasattr(value, "detach") else value
        return np.asarray(arr).ravel()

    runner_group = getattr(algorithm, "env_runner_group", None)
    samples = []
    if runner_group is not None and hasattr(runner_group, "foreach_env_runner"):
        try:
            samples = [s for s in runner_group.foreach_env_runner(_probe)
                       if s is not None]
        except Exception:
            samples = []

    if not samples:
        module = _get_rl_module(algorithm, policy_id)
        state = module.get_state() if module is not None else None
        if state and key in state:
            value = state[key]
            arr = value.detach().cpu().numpy() if hasattr(value, "detach") else value
            samples = [np.asarray(arr).ravel()]

    if not samples:
        raise RuntimeError("weight verification could not read any policy state back")

    for got in samples:
        if got.shape != expected.shape or not np.allclose(got, expected, atol=1e-5):
            diff = (float(np.max(np.abs(got - expected)))
                    if got.shape == expected.shape else "shape mismatch")
            raise RuntimeError(
                f"restored weights did not reach a sampling env runner "
                f"(tensor {key}: max abs diff {diff})"
            )
