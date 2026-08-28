# -*- coding: utf-8 -*-
"""Opponents that actually attack, and the pool they are drawn from.

WHY THE SCRIPTED TEACHERS ARE NOT ENOUGH
----------------------------------------
Measured 2026-07-20 over 8,167 steps of our best policy against the `ace`
teacher, the hardest one we have:

    our aim error      median   3.8 deg    we were inside its firing envelope  1.62% of steps
    their aim error    median 155.1 deg    they were inside theirs             0.00% of steps
    their aim within 30 deg: 2.6% of steps.  Within 5 deg: 0.00%.

Across every stage of every run, loss_rate is exactly 0.0000. The agent has
never once been shot at, so the damage-taken term in the reward and the threat
features in the observation have never carried a signal.

The cause is not the teachers' logic, it is their hands. They steer through the
JSBSim autopilot, and the one state in AceTeacher that aims at us -- `attack`
-- uses LAT_HEADING, which caps bank near 32 deg: an 8.2 km turn radius at
225 m/s, against an agent pulling 75 deg of bank in a 2.4 km circle. Worse, the
attack state only triggers once its aim is already inside 45 deg, an angle it
has no way to generate. The gate and the key to it are locked in the same box.

Anything that is going to threaten us has to fly the stick directly, which is
what the pursuit demonstrator and our own policy already do.

DIFFICULTY IS A HANDICAP, NOT A DIFFERENT BRAIN
-----------------------------------------------
`AggressorOpponent` wraps the same proportional-pursuit controller that flies
the behaviour-cloning demonstrations (0.3 deg tracking, 8/8 kills from the
saddle), and weakens it in ways that map to a real pilot's limits: reaction
delay, a cap on how hard it may pull, a throttle ceiling, aim noise, and a
delay before it engages at all. One controller, a continuum of difficulty, and
we know exactly how strong the top of the ladder is because we measured it.
"""
from __future__ import annotations

import math

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from GeoMathUtil import GeometryInfo
from dogfight.ai.action_provider import ActionContext, ActionProvider, ActionResult
from dogfight.sim.state_schema import StateIndex


# ── the attacking opponent ────────────────────────────────────────────────

@dataclass
class AggressorOpponent(ActionProvider):
    """Proportional pursuit on the stick, handicapped to a chosen difficulty.

    Handicaps, and what each one costs the opponent:

    reaction_delay_s  it holds its previous stick for this long, so it lags a
                      reversal -- the single most human-like weakness
    max_pull          scales the pitch command; below 1.0 it cannot sustain a
                      hard enough turn to hold the nose on a maneuvering target
    throttle_cap      limits energy, so it loses the vertical and falls behind
    aim_noise_deg     perturbs the bearing it flies to, widening its tracking
    engage_delay_s    it flies straight for this long at the start, handing us
                      the first move
    """

    reaction_delay_s: float = 0.0
    max_pull: float = 1.0
    throttle_cap: float = 1.0
    aim_noise_deg: float = 0.0
    engage_delay_s: float = 0.0
    seed: int = 0
    name: str = "aggressor"

    _held: np.ndarray | None = field(default=None, repr=False)
    _hold_left: float = field(default=0.0, repr=False)
    _elapsed: float = field(default=0.0, repr=False)
    _rng: Any = field(default=None, repr=False)
    _geo: Any = field(default=None, repr=False)
    _episode: int = field(default=0, repr=False)

    def reset(self, context: ActionContext | None = None) -> None:
        self._held = None
        self._hold_left = 0.0
        self._elapsed = 0.0
        # A fresh stream per episode, still reproducible from the base seed.
        # It used to re-seed with `self.seed` every reset, so every episode on
        # a runner replayed the identical aim-noise sequence -- measured, three
        # consecutive resets drew the same five numbers. With one seed per
        # level per runner that is 12 distinct opponents for a whole run, and a
        # policy can fit the pattern instead of the behaviour.
        self._rng = np.random.default_rng((self.seed, self._episode))
        self._episode += 1
        self._ou_az = 0.0
        self._ou_el = 0.0
        if self._geo is None:
            self._geo = GeometryInfo()

    def close(self) -> None:
        return None

    def compute_action(self, context: ActionContext) -> ActionResult:
        # The env builds the context from the point of view of whichever jet
        # this provider drives: installed as the target provider, its
        # `ownship_state` IS the target and `target_state` is the agent. No
        # perspective flip is needed here, and adding one would silently make
        # the opponent chase itself.
        if self._rng is None:
            self.reset()
        own = context.ownship_state
        foe = context.target_state
        geo = self._geo
        # the provider is polled once per physics substep
        dt = 1.0 / 60.0

        if own is None or foe is None:
            return ActionResult(action=self._to_sim(np.zeros(4, dtype=np.float32)),
                                source=self.name, confidence=0.0,
                                info={"mode": "no-state"})
        self._elapsed += dt

        if self._elapsed < self.engage_delay_s:
            action = np.array([0.0, 0.0, 0.0, 0.4], dtype=np.float32)
            return ActionResult(action=self._to_sim(action), source=self.name,
                                confidence=1.0, info={"mode": "wait"})

        if self._held is not None and self._hold_left > 0.0:
            self._hold_left -= dt
            return ActionResult(action=self._to_sim(self._held), source=self.name,
                                confidence=1.0, info={"mode": "hold"})

        action = self._pursue(own, foe, geo)
        self._held = action
        self._hold_left = self.reaction_delay_s
        return ActionResult(action=self._to_sim(action), source=self.name,
                            confidence=1.0, info={"mode": "pursue"})

    def _pursue(self, own, foe, geo) -> np.ndarray:
        import math

        az, el = geo._get_los_angle(own, foe)
        distance = float(geo._get_distance(own, foe))

        if self.aim_noise_deg > 0.0:
            # Ornstein-Uhlenbeck rather than white noise. Independent samples
            # at 10-60 Hz average out within a couple of decisions, so white
            # aim error barely moves the flown path. Real aim error wanders:
            # it leans one way and is corrected slowly. OU has exactly that
            # structure -- mean-reverting with ~2 s correlation -- and keeps
            # aim_noise_deg as the stationary standard deviation, so the
            # difficulty knob keeps its meaning.
            theta, dt = 0.5, 1.0 / 60.0
            sigma = self.aim_noise_deg * math.sqrt(2.0 * theta)
            for attr in ("_ou_az", "_ou_el"):
                value = getattr(self, attr, 0.0)
                value += (-theta * value * dt
                          + sigma * math.sqrt(dt) * float(self._rng.normal()))
                setattr(self, attr, value)
            az += self._ou_az
            el += self._ou_el

        # Behind the wing line the lift-vector law is singular: with the target
        # dead astern the roll error is +-90 deg, so the jet rolls past vertical
        # and the body-frame bearing flips sign as it goes, which makes the
        # command oscillate. Use the roll-invariant 2-D bearing to pick a side
        # and fly a hard level turn instead.
        # How hard it may pull, from the measured sustained-turn envelope.
        # Bank 70 deg, full throttle, constant pitch, 40 s (2026-07-21):
        #
        #   pitch   speed 0s -> 20s -> 40s      turn rate   altitude
        #   -1.00     182 -> 102 ->  27 m/s      14.8 deg/s   +3,180 m
        #   -0.80     182 -> 124 ->  43          14.3         +3,522
        #   -0.60     182 -> 180 -> 103           8.6         +3,257
        #   -0.40     182 -> 231 -> 252           5.0           +518
        #   -0.25     182 -> 259 -> 313           3.9         -1,023
        #
        # Anything past -0.4 is a one-shot maneuver: the jet converts its speed
        # into altitude and is down to a third of its energy inside 40 s. Only
        # -0.4 sustains -- it holds 250 m/s and level flight at 5 deg/s. The
        # first version of this controller held -0.85 whenever it was off the
        # nose, and measured, it bled 250 -> 144 m/s and finished aiming
        # perfectly at a target 11 km away. Guessing a limit made it worse
        # still (it stopped turning at all and drifted 25 km out), which is why
        # these numbers come from the table above rather than from intuition.
        speed = float(own[StateIndex.KCAS])
        surplus = float(np.clip((speed - 240.0) / 40.0, 0.0, 1.0))
        pitch_limit = (0.40 + 0.45 * surplus) * self.max_pull
        low_energy = speed < 190.0

        if abs(az) > 100.0:
            ata_2d = float(geo._get_antenna_train_angle(own, foe, True))
            side = 1.0 if ata_2d >= 0.0 else -1.0
            roll_now = float(own[StateIndex.ROLL])
            roll_cmd = float(np.clip((70.0 * side - roll_now) / 40.0, -1.0, 1.0))
            return np.array([roll_cmd, -pitch_limit, 0.0, 1.0], dtype=np.float32)

        phi_err = math.degrees(math.atan2(az, max(el, -89.0) + 1e-6))
        roll_cmd = float(np.clip(phi_err / 45.0, -1.0, 1.0))
        angle_err = math.hypot(az, el)
        align = max(0.0, 1.0 - abs(phi_err) / 90.0)
        pitch_cmd = float(np.clip(
            -np.clip(angle_err / 25.0, 0.0, 1.0) * align * pitch_limit,
            -pitch_limit, 0.3))

        if low_energy:
            # trade angles back for speed: unload and run. Losing the nose for
            # a few seconds beats arriving slow, which is unrecoverable.
            pitch_cmd = float(np.clip(pitch_cmd, -0.25, 0.3))
            throttle = 1.0
        else:
            throttle = float(np.clip((distance - 550.0) / 400.0, -1.0, 1.0))
        return np.array([roll_cmd, pitch_cmd, 0.0, throttle], dtype=np.float32)

    def _to_sim(self, action: np.ndarray) -> np.ndarray:
        """Policy space [-1,1]^4 -> simulator space, throttle capped.

        The ActionProvider contract is SIMULATOR space; the env feeds a
        provider's action straight to sim.step() with no conversion. Getting
        this wrong once already cost a day (see policy_to_sim_action).
        """
        out = np.clip(np.asarray(action, dtype=np.float32), -1.0, 1.0).copy()
        out[3] = min((out[3] + 1.0) / 2.0, self.throttle_cap)
        return np.clip(out, np.array([-1.0, -1.0, -1.0, 0.0], dtype=np.float32),
                       np.ones(4, dtype=np.float32))


@dataclass
class DrillOpponent(ActionProvider):
    """[MOD-DRILL 2026-08-23] 추격 드릴용 표적 — **스로틀 고정 · 고정 뱅크**.

    왜 스틱 경로인가 (사용자 제안):
      자동조종(step_autopilot / AutoRun)의 속도 루프는 speed_cmd 를 못 따라간다.
      실측 2026-08-23:  명령 320 -> 달성 316 · 명령 180 -> 달성 288 m/s.
      즉 명령을 낮춰도 표적이 안 느려지고, 우리 최대 298 m/s 로는 못 잡는다.
      FighterSim.step(action) 은 스로틀을 0~1 로 **직접** 받으므로
      (action[3], FighterSim.py:107) 그 루프를 통째로 건너뛴다.

    조종은 비례 제어 두 축뿐이다:
      roll  : 목표 뱅크로 (x_stick -1 좌 / +1 우)
      pitch : 목표 피치로 (y_stick -1 당김 / +1 밈)  -> 부호가 반대라 -k 를 쓴다
      rudder: 0
    """

    bank_deg: float = 0.0        # +우선회, -좌선회, 0 직진
    pitch_deg: float = 0.0       # 목표 피치. +면 상승
    throttle: float = 0.5        # **시뮬레이터 공간 0~1 그대로** (변환 없음)
    k_roll: float = 0.04
    k_pitch: float = 0.06
    seed: int = 0
    name: str = "drill"

    _geo: Any = field(default=None, repr=False)

    def reset(self, context: ActionContext | None = None) -> None:
        return None

    def close(self) -> None:
        return None

    def compute_action(self, context: ActionContext) -> ActionResult:
        own = context.ownship_state
        if own is None:
            return ActionResult(
                action=np.array([0.0, 0.0, 0.0, self.throttle], dtype=np.float32),
                source=self.name, confidence=0.0, info={"mode": "no-state"})

        roll = float(own[StateIndex.ROLL])
        pitch = float(own[StateIndex.PITCH])

        x = float(np.clip(self.k_roll * (self.bank_deg - roll), -1.0, 1.0))
        # y_stick 은 -1 이 당김(기수 상승)이라 오차에 마이너스를 건다
        y = float(np.clip(-self.k_pitch * (self.pitch_deg - pitch), -1.0, 1.0))

        action = np.array([x, y, 0.0, float(np.clip(self.throttle, 0.0, 1.0))],
                          dtype=np.float32)
        return ActionResult(action=action, source=self.name, confidence=1.0,
                            info={"mode": "drill", "bank": self.bank_deg})


# ── difficulty ladder ─────────────────────────────────────────────────────
# Tuned so the ladder spans "hands us the first move and cannot hold a turn"
# through "the demonstrator at full strength". The numbers are starting points
# to be MEASURED against the learnability band (keep the agent's win rate
# roughly 0.3-0.7); outside that band there is no gradient either way.
AGGRESSOR_LEVELS = {
    "rookie":   dict(reaction_delay_s=0.80, max_pull=0.35, throttle_cap=0.70,
                     aim_noise_deg=10.0, engage_delay_s=15.0),
    "novice":   dict(reaction_delay_s=0.60, max_pull=0.45, throttle_cap=0.75,
                     aim_noise_deg=6.0, engage_delay_s=8.0),
    # Inserted after measuring the ladder against the finished curriculum
    # policy: novice 3/8, cadet 0/8. A step that goes straight from winnable to
    # hopeless gives no gradient, so this fills the gap.
    #
    # Softened 07-22 by the same rule that created it. The stage-15 policy
    # (which beats novice 11/16 even at the wide 1500 m / 75 deg spawn) went
    # 0/16 against the old values (0.50/0.55/0.80/5.0/6.0) at BOTH geometries
    # -- 271 rollout games at 1% wins, outside the learnability band, no
    # gradient. Now the novice<->old-trainee midpoint; max_pull is the axis
    # that mattered (+22% sustained turn was what broke the tracking).
    # Second notch 07-22 05:30: after 300 iterations at the first softening
    # the deterministic eval still oscillated around 0.25 (rollout 0.18-0.21
    # vs trainee) -- below the band, frontier not moving toward the 0.45 gate
    # while other skills (pursuit, straight) kept improving.
    "trainee":  dict(reaction_delay_s=0.575, max_pull=0.475, throttle_cap=0.7625,
                     aim_noise_deg=5.75, engage_delay_s=7.5),
    # Re-interpolated 07-22 19:45: after trainee was softened twice, the
    # trainee->cadet step had silently doubled (pull 0.475 -> 0.65), and the
    # stage-15 graduate went 0/16 against the old cadet at BOTH geometries
    # while beating trainee 8/16 at the wide stage-16 spawn -- the same
    # level-not-geometry cliff signature as trainee's. Midpoint between the
    # current trainee and the old cadet (old values: 0.40/0.65/0.85/4.0/4.0).
    # The midpoint (pull 0.56) was STILL 0/16 -- the difficulty is not linear
    # in max_pull; somewhere between 0.475 and 0.56 the opponent's sustained
    # turn crosses what the policy can track and win rate falls off a cliff.
    # Quarter-step from the current trainee instead.
    # pull 0.52 probed 3/16 -- threshold found but just under the band.
    # One more notch: these are the FIRST-softening trainee values, so the
    # ladder now reads twice-softened (stage 15) -> once-softened (stage 16);
    # the names have drifted from their original numbers, but the measured
    # 0.3-0.7 band is what governs, not the label.
    "cadet":    dict(reaction_delay_s=0.55, max_pull=0.50, throttle_cap=0.775,
                     aim_noise_deg=5.5, engage_delay_s=7.0),
    # cadet -> veteran moves every handicap at once, and the policy stalled
    # there: 145 iterations oscillating 0.13-0.44 against a 0.40 gate, with the
    # ladder reading novice 0.625, trainee 0.603, cadet 0.460, veteran ~0.15.
    # Same shape as the novice -> cadet cliff that `trainee` fixed.
    #
    # Re-aimed 07-22 23:00: the stage-16 graduate went 0/59 against the old
    # values (0.30/0.75/0.90/3.0/2.5) -- the third cliff of the run. The
    # measured lesson from cadet's binary search is that difficulty is a
    # sharp THRESHOLD in max_pull (0.50 -> 0.625, 0.52 -> 0.19, 0.56 -> 0.0
    # for the stage-15 policy), so each rung should sit just outside the
    # current wall, not at a fixed schedule. Senior now aims one notch past
    # the cadet the policy just beat.
    # The pull threshold is razor sharp for the stage-16 graduate at the true
    # stage-17 spawn (3000 m / 120 deg): pull 0.50 -> 8/16, 0.51 -> 3/16,
    # 0.53 -> 1/16. Beating stage 16 did NOT move the wall -- pool pressure
    # alone doesn't buy sustained-tracking skill. So stage 17 keeps pull at
    # the wall's edge and sharpens the other axes instead; its new material
    # is the geometry (long range, full heading scatter), one axis per stage.
    # Softened 07-23 04:30 after a single-axis decomposition probe. The first
    # senior (0.53/0.50/0.78/5.2/6.5) sat at 0.19 for 385 iterations -- below
    # the band -- and the probe split the damage: reaction 0.55->0.53 alone
    # cost -0.19 (4/16), throttle 0.775->0.78 alone -0.06 (6/16), engage
    # 7.0->6.5 alone was free (7/16), and the all-axes midpoint fully
    # recovered cadet's 7/16. Reaction delay has the same razor threshold as
    # max_pull: half a step is free, a full step halves the win rate. So the
    # rung keeps the axes that measured free at full sharpness and takes the
    # measured-free half-step on the two that bite.
    "senior":   dict(reaction_delay_s=0.54, max_pull=0.50, throttle_cap=0.7775,
                     aim_noise_deg=5.2, engage_delay_s=6.5),
    "veteran":  dict(reaction_delay_s=0.20, max_pull=0.85, throttle_cap=0.95,
                     aim_noise_deg=2.0, engage_delay_s=1.5),
    "expert":   dict(reaction_delay_s=0.05, max_pull=1.00, throttle_cap=1.00,
                     aim_noise_deg=0.5, engage_delay_s=0.0),
}


# [MOD-DRILL 2026-08-23] 스로틀 고정 드릴 표적.
# 뱅크 45도 = 실제로 도는 표적. 자동조종 헤딩 모드가 32도에서 뱅크를 막던
# 제약이 스틱 경로에는 없다(AggressorOpponent 독스트링 참조).
#
# 스로틀 단계별로 레벨을 만든다 -- 30초 안에 잡으면 다음 단계로 올린다(사용자 지시).
# 실측 대응표(2026-08-23, 50초 판):
#   throttle 0.3 -> 표적 213 m/s   우리 255~264   -> 격추 3/3, 최소거리 406~427 m
#   throttle 0.5 -> 표적 270 m/s   우리 265~281   -> 직진 표적 못 잡음(2,208 m 그대로)
DRILL_LEVELS = {}
for _t in (30, 40, 50, 60, 70, 80):
    for _nm, _bank in (("left", -45.0), ("right", +45.0), ("straight", 0.0)):
        DRILL_LEVELS[f"drill_{_nm}_t{_t}"] = dict(
            bank_deg=_bank, pitch_deg=2.0, throttle=_t / 100.0)
# 하위호환: 접미사 없는 이름은 0.3 단계
for _nm in ("left", "right", "straight"):
    DRILL_LEVELS[f"drill_{_nm}"] = DRILL_LEVELS[f"drill_{_nm}_t30"]


def make_aggressor(level: str = "cadet", seed: int = 0):
    if level in DRILL_LEVELS:
        return DrillOpponent(seed=seed, **DRILL_LEVELS[level])
    if level not in AGGRESSOR_LEVELS:
        raise ValueError(f"unknown aggressor level {level!r}; "
                         f"have {sorted(AGGRESSOR_LEVELS)}")
    return AggressorOpponent(seed=seed, name=f"aggressor:{level}",
                             **AGGRESSOR_LEVELS[level])


__all__ = ["AggressorOpponent", "AGGRESSOR_LEVELS", "make_aggressor",
           "DrillOpponent", "DRILL_LEVELS"]
