# -*- coding: utf-8 -*-
"""PPO learner with an annealed KL anchor to a frozen policy.

WHY
---
Rehearsal data alone does not stop forgetting in PPO. Measured 2026-07-21 on
the duel curriculum: with PFSP feeding the losing teachers extra episodes, the
policy still traded straight_600 from 1.000 down to 0.250 and ace to 0.000 as
its aggressor evaluation climbed 0.63 -> 0.70. The mechanism is structural --
PPO's clipping is relative to the CURRENT policy, so nothing in the objective
pins behaviour the old policy had. CLEAR (arXiv:1811.11682) adds an explicit
cloning loss toward past behaviour on top of replay data and ablates it at
about nine points; Kickstarting (arXiv:1803.03835) shows the same auxiliary
KL, ANNEALED, reaches teacher level ~10x faster and then surpasses it.

The anneal is the difference between this and EWC-style regularisation, which
buys zero forgetting by destroying plasticity (negative forward transfer in
every Continual World measurement). A decaying coefficient lets the policy
leave the anchor once it has consolidated something better.

MECHANICS
---------
KL(anchor || current) over the training batch, added to the PPO loss with a
coefficient that decays geometrically per update. The anchor module is a
frozen copy of the policy architecture loaded from a lightweight bundle,
evaluated on the same padded batch the learner already has (teacher-forward on
student trajectories, exactly as Kickstarting does). Warm-starting from the
same bundle the anchor uses means the penalty starts at ~zero and only grows
as the policy drifts.
"""
from __future__ import annotations

import copy

from ray.rllib.algorithms.ppo.torch.ppo_torch_learner import PPOTorchLearner
from ray.rllib.core.columns import Columns
from ray.rllib.utils.annotations import override


class AnchoredPPOTorchLearner(PPOTorchLearner):
    @override(PPOTorchLearner)
    def build(self) -> None:
        super().build()
        settings = dict(self.config.learner_config_dict or {})
        self._anchor_coef = float(settings.get("anchor_coef", 0.0))
        self._anchor_decay = float(settings.get("anchor_decay_per_update", 1.0))
        self._anchor_module = None

        bundle = settings.get("anchor_bundle")
        if not bundle or self._anchor_coef <= 0.0:
            return

        from dogfight.ai.checkpoint_io import load_lightweight_policy_bundle

        _meta, weights = load_lightweight_policy_bundle(bundle)
        anchor = copy.deepcopy(self.module["default_policy"].unwrapped())
        anchor.set_state(weights)
        for parameter in anchor.parameters():
            parameter.requires_grad_(False)
        anchor.eval()
        self._anchor_module = anchor
        print(f"[anchor] KL anchor active: bundle={bundle} "
              f"coef={self._anchor_coef} decay/update={self._anchor_decay:.8f}")

    @override(PPOTorchLearner)
    def compute_loss_for_module(self, *, module_id, config, batch, fwd_out):
        loss = super().compute_loss_for_module(
            module_id=module_id, config=config, batch=batch, fwd_out=fwd_out)

        if self._anchor_module is None or self._anchor_coef <= 1e-9:
            return loss

        import torch

        with torch.no_grad():
            anchor_out = self._anchor_module.forward_train(batch)

        module = self.module[module_id].unwrapped()
        dist_cls = module.get_train_action_dist_cls()
        current_dist = dist_cls.from_logits(fwd_out[Columns.ACTION_DIST_INPUTS])
        anchor_dist = dist_cls.from_logits(anchor_out[Columns.ACTION_DIST_INPUTS])

        kl = anchor_dist.kl(current_dist)
        mask = batch.get(Columns.LOSS_MASK)
        if mask is not None:
            # RNN batches are zero-padded; averaging over the padding would
            # dilute the term exactly where sequences are short
            kl = (kl * mask).sum() / mask.sum().clamp(min=1)
        else:
            kl = kl.mean()

        self._anchor_coef *= self._anchor_decay
        self.metrics.log_value((module_id, "anchor_kl"), float(kl.detach()),
                               window=1)
        self.metrics.log_value((module_id, "anchor_coef"), self._anchor_coef,
                               window=1)
        return loss + self._anchor_coef * kl
