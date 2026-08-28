# -*- coding: utf-8 -*-
"""Elo self-play league math, ported faithfully from LAG / snu-larr CloseAirCombat
(algorithms/utils/selfplay.py :: PFSP, runner/selfplay_jsbsim_runner.py :: Update elo).

Reference (downloaded 2026-07-28):
  https://github.com/snu-larr/CloseAirCombat  (SNU fork of liuqh16/LAG)

We port ONLY the league ALGORITHM -- observation/env/reward/network are our own
frozen 38D PPO+LSTM and are NOT touched. This module is pure numpy so it can be
unit-tested and called from single_agent_env._prioritise / _note_opponent_result.

Two pieces:
  pfsp_weights(elos, ego_elo)  -- opponent sampling distribution (their PFSP.choose)
  update_elo(ego, opp, score)  -- Elo update after a match     (their runner)
"""
from __future__ import annotations

from typing import Dict, Sequence

import numpy as np

K_FACTOR = 32.0        # LAG runner: elo_gain = 32 * (actual - expected)
INIT_ELO = 1000.0      # LAG default init_elo; scale is arbitrary (relative only)


def expected_score(ego_elo: float, opp_elo: float) -> float:
    """Standard Elo expected score for EGO vs opponent (prob ego wins)."""
    return 1.0 / (1.0 + 10.0 ** ((opp_elo - ego_elo) / 400.0))


def update_elo(ego_elo: float, opp_elo: float, ego_score: float,
               k: float = K_FACTOR) -> tuple[float, float]:
    """One match update. ego_score = 1 win, 0.5 draw, 0 loss (win == kill OR
    judge_win in our env). Zero-sum like the LAG runner: winner up, loser down.
    Returns (new_ego_elo, new_opp_elo)."""
    exp = expected_score(ego_elo, opp_elo)
    gain = k * (ego_score - exp)
    return ego_elo + gain, opp_elo - gain


def outcome_to_score(outcome: str) -> float:
    """Our env outcomes -> Elo score. A judge win IS a win (competition rule,
    [MOD-JUDGE]); a draw/timeout is 0.5; loss/judge_loss/crash is 0."""
    if outcome in ("win", "judge_win"):
        return 1.0
    if outcome in ("loss", "judge_loss", "crash"):
        return 0.0
    return 0.5          # draw / timeout / other


def pfsp_weights(elos: Sequence[float], lam: float = 1.0, s: float = 100.0) -> np.ndarray:
    """PFSP opponent distribution, exactly LAG's PFSP.choose meta-solver:

        sample = 1/(1 + 10^(-(elo - median)/400)) * s
        p      = softmax( (lam/k) * sample ),  k = len+1

    Higher-Elo snapshots are sampled more -- you rehearse against the STRONG
    members of the growing pool, which is what makes the ladder climb.
    """
    e = np.asarray(list(elos), dtype=float)
    if e.size == 0:
        return e
    med = np.median(e)
    sample = 1.0 / (1.0 + 10.0 ** (-(e - med) / 400.0)) * s
    k = float(e.size + 1)
    z = np.exp(lam / k * sample)
    return z / z.sum()


def league_weights_from_history(names: Sequence[str], pool_elo: Dict[str, float],
                                ego_elo: float, floor: float = 0.05,
                                lam: float = 1.0, s: float = 100.0) -> np.ndarray:
    """PFSP weights for a list of opponent NAMES using the shared pool_elo, with a
    small floor so no live snapshot is starved (our pool is ~tens, not LAG's
    hundreds -- a zero-weight entry stops being measured)."""
    elos = [pool_elo.get(n, ego_elo) for n in names]
    w = pfsp_weights(elos, lam=lam, s=s)
    if w.size == 0:
        return w
    w = np.maximum(w, floor / w.size)
    return w / w.sum()
