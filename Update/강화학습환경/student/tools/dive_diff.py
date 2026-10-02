# -*- coding: utf-8 -*-
"""[측정] 같은 강하(idle 75°)를 두 방식으로 회복시켜 스텝별로 비교.
  A) 캘리브 방식: 스크립트가 h_trig 에서 직접 회복 명령
  B) 가드 방식:  env deck_guard 가 발동해 회복
둘 다 같은 발동 고도에서 시작하게 맞추고, 고도·vz·피치·롤·V·실제 적용된 행동을 찍는다."""
import importlib
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, "src")
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

import train_curriculum as tc
from dogfight.sim.state_schema import StateIndex
import student.deck_guard as dg

START_ALT = 3500.0
GAMMA = 75.0
THR = -1.0
H_TRIG = 1130.0          # 검증에서 가드가 켜진 고도
_ROLL, _PITCH = 3, 4


def make_env(guard_on):
    st = [s for s in importlib.import_module("student.my_curriculum").get_stages() if s.index == 35][0]
    pre = {"step_ratio": 6, "observation_mode": "custom", "observation_module": "student.my_observation",
           "reward_module": "student.my_reward", "target_mode": "fixed", "ownship_control_mode": "rl"}
    e0 = tc.env_creator(pre)
    base = {**pre, "observation_mode": e0.config["observation_mode"], "reward": dict(e0.config["reward"]),
            "wez": dict(e0.config["wez"]), "observation_summary": dict(e0.config.get("observation_summary", {}))}
    e0.close()
    cfg = tc.build_stage_env_config(base, st)
    rnd = {"enabled": False, "radius": 0.0, "r_roll": 0.0, "r_pitch": 0.0, "r_heading": 0.0}
    far = {"ownship": [0.0, 0.0, -START_ALT, 0.0, 0.0, 0.0, 200.0],
           "target": [12000.0, 0.0, -START_ALT, 0.0, 0.0, 180.0, 200.0]}
    cfg["target_pool"] = [{"weight": 1.0, "mode": "policy", "bundle": "artifacts/models/AeroFlyer/cand_c13280_s45",
                           "randomization": rnd, "spawn": far, "pair": "diff", "side": "blue"}]
    cfg["pair_slots"] = False
    cfg["deck_guard"] = bool(guard_on)
    cfg["deck_guard_penalty"] = 0.0
    cfg["spawn_alt_m"] = [START_ALT, START_ALT]
    cfg["spawn_speed_mps"] = [200.0, 200.0]
    cfg.pop("live_tune_file", None)
    return tc.env_creator(cfg)


def sr(r):
    return ((float(r) + 180.0) % 360.0) - 180.0


def run(mode):
    env = make_env(guard_on=(mode == "B"))
    env.reset(seed=1234)
    for _ in range(5):
        env.step(np.asarray([0.0, 0.0, 0.0, 0.5], dtype=np.float32))
    prev = None
    rec = False
    rows = []
    for n in range(700):
        s = env._sim.get_state()
        alt, roll, pit = float(s[StateIndex.ALT]), float(s[_ROLL]), float(s[_PITCH])
        v = float(np.linalg.norm(np.asarray(s[6:9], dtype=np.float64)))
        vz = 0.0 if prev is None else (alt - prev) / 0.1
        prev = alt
        if mode == "A" and not rec and n >= 3 and vz < -5 and alt <= H_TRIG:
            rec = True
        if mode == "A" and rec:
            act = [float(np.clip(-sr(roll) / 25.0, -1, 1)), -1.0 if abs(sr(roll)) <= 100 else 0.0, 0.0,
                   -1.0 if pit < 0 else 1.0]
        else:
            act = [float(np.clip(-sr(roll) / 25.0, -1, 1)), float(np.clip((pit + GAMMA) / 20.0, -1, 1)), 0.0, THR]
        _, _, term, trunc, info = env.step(np.asarray(act, dtype=np.float32))
        fired = bool(getattr(env, "_deck_guard_fired", False))
        if mode == "B" and fired and not rec:
            rec = True
        if rec:
            rows.append((n / 10.0, alt, vz, pit, roll, v, fired))
        if term or trunc:
            rows.append(("END", info.get("end_condition"), None, None, None, None, None))
            break
        if rec and vz >= 0 and len(rows) > 5:
            break
    env.close()
    return rows


a = run("A")
b = run("B")
print("%-6s | %8s %7s %7s %6s %5s | %8s %7s %7s %6s %5s %4s"
      % ("t", "A_alt", "A_vz", "A_pit", "A_roll", "A_V", "B_alt", "B_vz", "B_pit", "B_roll", "B_V", "gd"))
print("-" * 100)
for i in range(max(len(a), len(b))):
    ra = a[i] if i < len(a) else None
    rb = b[i] if i < len(b) else None
    if ra and ra[0] == "END":
        print("A END:", ra[1]); ra = None
    if rb and rb[0] == "END":
        print("B END:", rb[1]); rb = None
    if not ra and not rb:
        continue
    fa = "%8.0f %7.0f %7.1f %6.1f %5.0f" % (ra[1], ra[2], ra[3], ra[4], ra[5]) if ra else "%36s" % ""
    fb = "%8.0f %7.0f %7.1f %6.1f %5.0f %4s" % (rb[1], rb[2], rb[3], rb[4], rb[5], "ON" if rb[6] else "-") if rb else ""
    t = ra[0] if ra else rb[0]
    if i % 3 == 0 or (ra and ra[1] < 420) or (rb and rb[1] < 420):
        print("%-6.1f | %s | %s" % (t, fa, fb))
