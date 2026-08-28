# -*- coding: utf-8 -*-
"""Scripted Python opponents ("teachers") for curriculum training.

WHY THIS FILE EXISTS
--------------------
Measured 2026-07-19: the shipped BT opponent (`AIP_BASE_target.dll`) registers
only 9 nodes and the ONLY one that produces a steering point is `Task_Empty`,
whose body is `VP = position + forward * 10000` — i.e. it flies dead straight
at full throttle. Verified empirically: target heading changed 0.5 deg over
400 decision steps. The compiled BFM maneuver library (Pure/Lag/Turn/YoYo...)
exists only as stale 32-bit .obj files with no sources anywhere on disk, so it
cannot be rebuilt.

Training an agent only against a straight-flying target teaches gunnery, not
dogfighting. These Python teachers replace it: they command the JSBSim
autopilot directly (bank / heading / flight-path-angle / altitude / speed), so
no C++, no Rule XML file races, and every teacher is safe under parallel Ray
env runners because each runner owns its own instance.

Autopilot envelope: 3,048-8,534 m altitude. The documented speed range is
NOT usable -- see SPD_CMD_STABLE below for the measurement and why.

Difficulty is parameterised (reaction delay, max bank, lead time, threat cone,
energy discipline) so one class can serve several curriculum stages.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from dogfight.sim.state_schema import StateIndex

# Autopilot mode constants (see FighterSim.step_auto_cmd)
LAT_BANK = 2
LAT_HEADING = 3
LON_PITCH = 2
LON_GAMMA = 3
LON_ALT = 4
SPD_CMD = 3

ALT_MIN_M = 3200.0      # autopilot envelope, with margin
ALT_MAX_M = 8400.0

# Speed command. The autopilot's speed loop is UNSTABLE inside the range the
# wrapper documents as valid (183-305 m/s), and stable outside it. Measured
# 2026-07-20, 80 s of level turning at 7,000 m, commanded vs achieved:
#     cmd 200/250/280 -> 264, 443, 401, 399 m/s   (diverges, supersonic)
#     cmd 300/320/400/500 -> 222, 222, 222, 222   (dead steady)
# The cliff sits between 280 and 300, and every command above it converges to
# the same ~225 m/s, so the achieved speed is not selectable — only stable or
# not. The consequence of getting this wrong was severe and invisible: every
# teacher asked for 200-250 m/s, so every opponent in every stage quietly
# accelerated to ~460 m/s and left. The head-on merge stage was unwinnable by
# construction (agent tops out near 400 m/s), and a hand-flown pursuit
# demonstrator that kills 8/8 from the saddle scored 0/8 there, ending each
# episode 13 km behind a target it was aiming at within 1 degree.
# Any teacher speed request is therefore raised to the stable band.
SPD_CMD_STABLE = 400.0
SPD_MIN_MPS = 320.0
SPD_MAX_MPS = 500.0
SPD_ACHIEVED_MPS = 225.0   # what the airframe actually flies at, for planning

_D2R = math.pi / 180.0
_R2D = 180.0 / math.pi


# ── geometry helpers ──────────────────────────────────────────────────────

def _wrap360(deg: float) -> float:
    return deg % 360.0


def _angle_diff(a: float, b: float) -> float:
    """Signed smallest difference a-b in [-180, 180)."""
    return (a - b + 180.0) % 360.0 - 180.0


def _bearing_to(own, point_ne) -> float:
    return _wrap360(math.degrees(math.atan2(
        point_ne[1] - float(own[1]), point_ne[0] - float(own[0])
    )))


def _ned_velocity(state) -> np.ndarray:
    roll = float(state[StateIndex.ROLL]) * _D2R
    pitch = float(state[StateIndex.PITCH]) * _D2R
    yaw = float(state[StateIndex.YAW]) * _D2R
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    tx = np.array([[1.0, 0.0, 0.0], [0.0, cr, sr], [0.0, -sr, cr]])
    ty = np.array([[cp, 0.0, -sp], [0.0, 1.0, 0.0], [sp, 0.0, cp]])
    tz = np.array([[cy, sy, 0.0], [-sy, cy, 0.0], [0.0, 0.0, 1.0]])
    body = np.array([float(state[6]), float(state[7]), float(state[8])])
    return (tx @ ty @ tz).T @ body


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


@dataclass
class Geometry:
    """Everything a teacher needs about the engagement, computed once."""
    distance: float
    my_ata: float        # how far MY nose is off the foe (deg, 0 = on target)
    foe_ata: float       # how far the FOE's nose is off me (deg, small = threat)
    bearing: float       # heading from me to the foe (deg)
    my_alt: float
    foe_alt: float
    my_speed: float
    foe_speed: float
    closure: float       # >0 closing
    foe_pos: np.ndarray
    foe_vel_ned: np.ndarray


def compute_geometry(own, foe, geo_info) -> Geometry:
    distance = float(geo_info._get_distance(own, foe))
    my_ata = abs(float(geo_info._get_antenna_train_angle(own, foe, False)))
    foe_ata = abs(float(geo_info._get_antenna_train_angle(foe, own, False)))
    foe_pos = np.array([float(foe[0]), float(foe[1]), float(foe[2])])
    own_pos = np.array([float(own[0]), float(own[1]), float(own[2])])
    v_own = _ned_velocity(own)
    v_foe = _ned_velocity(foe)
    if distance > 1e-6:
        los = (foe_pos - own_pos) / distance
        closure = float((v_own - v_foe) @ los)
    else:
        closure = 0.0
    return Geometry(
        distance=distance,
        my_ata=my_ata,
        foe_ata=foe_ata,
        bearing=_bearing_to(own, foe_pos),
        my_alt=float(own[StateIndex.ALT]),
        foe_alt=float(foe[StateIndex.ALT]),
        my_speed=float(own[StateIndex.KCAS]),
        foe_speed=float(foe[StateIndex.KCAS]),
        closure=closure,
        foe_pos=foe_pos,
        foe_vel_ned=v_foe,
    )


# ── base ──────────────────────────────────────────────────────────────────

@dataclass
class Teacher:
    """Base scripted opponent. `command()` runs at the physics rate (60 Hz)."""

    speed_mps: float = SPD_CMD_STABLE
    altitude_m: float = 7000.0
    reaction_delay_s: float = 0.0
    name: str = "base"
    _held: dict[str, Any] | None = field(default=None, repr=False)
    _hold_left: float = field(default=0.0, repr=False)
    _mode: str = field(default="", repr=False)

    def reset(self, rng: np.random.Generator, own, foe) -> None:
        self._held = None
        self._hold_left = 0.0
        self._mode = ""

    # subclasses implement this
    def decide(self, own, foe, g: Geometry) -> dict[str, Any]:
        raise NotImplementedError

    def command(self, own, foe, geo_info, dt: float) -> dict[str, Any]:
        """Reaction delay: hold the previous command for reaction_delay_s."""
        if self._held is not None and self._hold_left > 0.0:
            self._hold_left -= dt
            return self._held
        g = compute_geometry(own, foe, geo_info)
        cmd = self.decide(own, foe, g)
        cmd.setdefault("lat_mode", LAT_HEADING)
        cmd.setdefault("lon_mode", LON_ALT)
        cmd.setdefault("spd_mode", SPD_CMD)
        cmd.setdefault("theta_deg", 0.0)
        cmd.setdefault("phi_deg", 0.0)
        cmd.setdefault("gamma_deg", 0.0)
        cmd.setdefault("psi_deg", 0.0)
        cmd["altitude_m"] = _clamp(cmd.get("altitude_m", self.altitude_m),
                                   ALT_MIN_M, ALT_MAX_M)
        cmd["speed_mps"] = _clamp(cmd.get("speed_mps", self.speed_mps),
                                  SPD_MIN_MPS, SPD_MAX_MPS)
        self._held = cmd
        self._hold_left = self.reaction_delay_s
        return cmd

    @property
    def mode(self) -> str:
        return self._mode


# ── ladder ────────────────────────────────────────────────────────────────

@dataclass
class StraightTeacher(Teacher):
    """Level flight on the spawn heading. Sanity baseline only."""
    name: str = "straight"
    _psi: float = field(default=0.0, repr=False)
    _psi_set: bool = field(default=False, repr=False)

    def reset(self, rng, own, foe) -> None:
        super().reset(rng, own, foe)
        # State rows are NOT populated yet at reset time: ALT reads 0 here,
        # which sent the "level" teacher into a -40 deg dive to the autopilot
        # floor (~3,200 m) every episode -- measured 07-24 (7000 -> 3717 m in
        # 25 s). Capture the hold altitude lazily on the first decide().
        self.altitude_m = 0.0
        # [2026-08-23] YAW 도 같은 이유로 지연 캡처한다. 고도만 고치고 yaw 는
        # 남겨 뒀던 탓에 _psi 가 0 으로 잡혀 **교사가 스폰 방향이 아니라 북쪽
        # (psi=0)으로 날아갔다.** 실측: 스폰 yaw +90 인데 판 끝에 +9.9 / +12.0
        # (두 판) -- 80도를 돌았다. 판마다 다른 건 상태가 채워지는 타이밍 차.
        # 꼬리 추격 드릴에서 "직진 도망자"가 사실은 선회하는 표적이었다.
        self._psi = 0.0
        self._psi_set = False

    def decide(self, own, foe, g: Geometry) -> dict[str, Any]:
        self._mode = "straight"
        if not self._psi_set:
            self._psi = float(own[StateIndex.YAW])
            self._psi_set = True
        if self.altitude_m <= 0.0:
            self.altitude_m = float(own[StateIndex.ALT])
        return {"lat_mode": LAT_HEADING, "psi_deg": self._psi,
                "altitude_m": self.altitude_m}


@dataclass
class TurnTeacher(Teacher):
    """Continuous banked turn — the classic 'circling target' gunnery drill."""
    name: str = "turn"
    bank_deg: float = 45.0
    bank_range: tuple = (25.0, 60.0)
    randomize: bool = True
    _sign: float = field(default=1.0, repr=False)

    def reset(self, rng, own, foe) -> None:
        super().reset(rng, own, foe)
        self._sign = 1.0 if rng.random() < 0.5 else -1.0
        if self.randomize:
            lo, hi = self.bank_range
            self.bank_deg = float(lo + (hi - lo) * rng.random())
        self.altitude_m = 0.0   # lazy capture -- ALT reads 0 at reset (see StraightTeacher)

    def decide(self, own, foe, g: Geometry) -> dict[str, Any]:
        self._mode = "turn"
        if self.altitude_m <= 0.0:
            self.altitude_m = float(own[StateIndex.ALT])
        return {"lat_mode": LAT_BANK, "phi_deg": self._sign * self.bank_deg,
                "altitude_m": self.altitude_m}


@dataclass
class PursuitTeacher(Teacher):
    """Lead pursuit: aims at where the agent WILL be.

    lead_time_s = 0 -> pure pursuit (chases the current position),
    0.5-2.0     -> lead pursuit (harder: cuts the corner).
    """
    name: str = "pursuit"
    lead_time_s: float = 0.8
    lead_range: tuple = (0.0, 1.5)
    randomize: bool = True

    def reset(self, rng, own, foe) -> None:
        super().reset(rng, own, foe)
        if self.randomize:
            lo, hi = self.lead_range
            self.lead_time_s = float(lo + (hi - lo) * rng.random())

    def decide(self, own, foe, g: Geometry) -> dict[str, Any]:
        self._mode = "pursuit"
        aim = g.foe_pos + g.foe_vel_ned * self.lead_time_s
        psi = _bearing_to(own, aim)
        # follow the agent vertically, but stay inside the autopilot envelope
        alt = float(foe[StateIndex.ALT]) - float(aim[2] - g.foe_pos[2])
        return {"lat_mode": LAT_HEADING, "psi_deg": psi, "altitude_m": alt}


@dataclass
class DefensiveTeacher(Teacher):
    """Turns hard away when the agent points at it, otherwise chases.

    This is the first teacher that punishes a naive tail-chase: the agent must
    fly BFM (lead/lag, vertical) instead of pointing and closing.
    """
    name: str = "defensive"
    threat_cone_deg: float = 40.0
    threat_range_m: float = 2500.0
    break_bank_deg: float = 70.0
    lead_time_s: float = 0.5

    def decide(self, own, foe, g: Geometry) -> dict[str, Any]:
        threatened = (g.foe_ata <= self.threat_cone_deg
                      and g.distance <= self.threat_range_m)
        if threatened:
            self._mode = "break"
            # break INTO the attacker's turn circle: bank away from its bearing
            side = 1.0 if _angle_diff(g.bearing, float(own[StateIndex.YAW])) < 0 else -1.0
            return {"lat_mode": LAT_BANK, "phi_deg": side * self.break_bank_deg,
                    "altitude_m": g.my_alt, "speed_mps": SPD_MAX_MPS}
        self._mode = "pursuit"
        aim = g.foe_pos + g.foe_vel_ned * self.lead_time_s
        return {"lat_mode": LAT_HEADING, "psi_deg": _bearing_to(own, aim),
                "altitude_m": float(foe[StateIndex.ALT])}


@dataclass
class AceTeacher(Teacher):
    """Full BFM state machine — the hardest teacher and the 90% win-rate gate.

    States:
      break   : agent is inside my rear threat cone -> max-bank defensive turn
      yoyo    : I am overshooting (fast + very close) -> climb to bleed closure
      attack  : I have the angles -> lead pursuit
      engage  : neutral -> turn toward the agent while holding energy
    """
    name: str = "ace"
    threat_cone_deg: float = 50.0
    threat_range_m: float = 3000.0
    break_bank_deg: float = 75.0
    attack_cone_deg: float = 45.0
    lead_time_s: float = 1.0
    overshoot_range_m: float = 500.0
    overshoot_closure_mps: float = 120.0
    yoyo_gamma_deg: float = 25.0
    engage_bank_deg: float = 55.0

    def decide(self, own, foe, g: Geometry) -> dict[str, Any]:
        my_yaw = float(own[StateIndex.YAW])
        bearing_err = _angle_diff(g.bearing, my_yaw)
        side = 1.0 if bearing_err >= 0 else -1.0

        # 1) defensive break
        if g.foe_ata <= self.threat_cone_deg and g.distance <= self.threat_range_m:
            self._mode = "break"
            return {"lat_mode": LAT_BANK, "phi_deg": -side * self.break_bank_deg,
                    "altitude_m": g.my_alt, "speed_mps": SPD_MAX_MPS}

        # 2) overshoot control (high yo-yo): too fast, too close
        if (g.distance <= self.overshoot_range_m
                and g.closure >= self.overshoot_closure_mps):
            self._mode = "yoyo"
            return {"lat_mode": LAT_BANK, "lon_mode": LON_GAMMA,
                    "phi_deg": side * 40.0, "gamma_deg": self.yoyo_gamma_deg,
                    "speed_mps": self.speed_mps}

        # 3) attack: I have the angles -> lead pursuit
        if g.my_ata <= self.attack_cone_deg:
            self._mode = "attack"
            aim = g.foe_pos + g.foe_vel_ned * self.lead_time_s
            return {"lat_mode": LAT_HEADING, "psi_deg": _bearing_to(own, aim),
                    "altitude_m": float(foe[StateIndex.ALT]),
                    "speed_mps": SPD_MAX_MPS}

        # 4) neutral: hard turn toward the agent, hold energy
        self._mode = "engage"
        return {"lat_mode": LAT_BANK, "phi_deg": side * self.engage_bank_deg,
                "altitude_m": g.my_alt, "speed_mps": self.speed_mps}


TEACHERS: dict[str, type[Teacher]] = {
    "straight": StraightTeacher,
    "turn": TurnTeacher,
    "pursuit": PursuitTeacher,
    "defensive": DefensiveTeacher,
    "ace": AceTeacher,
}


def make_teacher(spec: dict[str, Any] | str | None) -> Teacher:
    """Build a teacher from an env_config spec.

    spec = "ace"  or  {"name": "ace", "params": {"lead_time_s": 1.2, ...}}
    """
    if spec is None:
        spec = "straight"
    if isinstance(spec, str):
        spec = {"name": spec}
    name = str(spec.get("name", "straight")).lower()
    if name not in TEACHERS:
        raise ValueError(
            f"unknown teacher {name!r}; available: {sorted(TEACHERS)}"
        )
    params = dict(spec.get("params") or {})
    teacher = TEACHERS[name](**params)
    teacher.name = name
    return teacher


__all__ = ["Teacher", "TEACHERS", "make_teacher", "compute_geometry", "Geometry"]
