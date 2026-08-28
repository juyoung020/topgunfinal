# -*- coding: utf-8 -*-
"""Force a lightweight bundle's exploration std to a chosen value.

WHY
---
RLlib's Gaussian policy head emits [mean, log_std]; at init log_std ~ 0, i.e.
std ~ 1.0 on a [-1, 1] stick. Measured 2026-07-20: a behaviour-cloned policy
scored 12/12 kills when evaluated deterministically but crashed in 100% of
TRAINING episodes, because training samples actions and std 1.0 shakes the
stick far beyond what a +-1 deg gun solution tolerates. The BC run's soft
penalty on log_std did not move it (verified: head bias still ~0).

This patches the head directly: zero the log_std rows of the final layer's
weight (making the noise state-independent) and set its bias to ln(std).
"""
from __future__ import annotations

import argparse
import gzip
import math
import pickle
from pathlib import Path

import numpy as np


def patch(bundle_dir: Path, std: float, action_dim: int = 4) -> None:
    weights_path = bundle_dir / "policy_weights.pkl.gz"
    with gzip.open(weights_path, "rb") as f:
        weights = pickle.load(f)

    # the policy head is the last linear layer emitting 2 * action_dim values
    target = None
    for key, value in weights.items():
        if not key.startswith("pi."):
            continue
        arr = np.asarray(value)
        if arr.ndim == 2 and arr.shape[0] == 2 * action_dim:
            target = key
    if target is None:
        raise SystemExit(f"could not find a policy head with {2*action_dim} outputs")

    bias_key = target.replace("weight", "bias")
    w = np.array(weights[target], dtype=np.float32)
    b = np.array(weights[bias_key], dtype=np.float32)

    before = np.exp(b[action_dim:])
    w[action_dim:, :] = 0.0
    b[action_dim:] = math.log(std)

    # keep the original container type (numpy array or torch tensor)
    def like(original, new):
        if hasattr(original, "detach"):          # torch tensor
            import torch
            return torch.as_tensor(new, dtype=original.dtype, device=original.device)
        return np.asarray(new, dtype=np.asarray(original).dtype)

    weights[target] = like(weights[target], w)
    weights[bias_key] = like(weights[bias_key], b)

    with gzip.open(weights_path, "wb") as f:
        pickle.dump(weights, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"[std] {target}")
    print(f"[std] std before (bias only): {np.round(before, 3)}")
    print(f"[std] std after             : {np.round(np.exp(b[action_dim:]), 3)}  "
          f"(state-independent)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Set a bundle's exploration std.")
    ap.add_argument("--bundle-dir", required=True)
    ap.add_argument("--std", type=float, default=0.15)
    ap.add_argument("--action-dim", type=int, default=4)
    args = ap.parse_args()
    patch(Path(args.bundle_dir), args.std, args.action_dim)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
