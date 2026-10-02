# -*- coding: utf-8 -*-
"""[측정] 강하 진단 한 판 — 지수·부호·상대 생존을 확인한다."""
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

START_ALT = 3500.0
_ROLL = getattr(StateIndex, "ROLL", 3)
_PITCH = getattr(StateIndex, "PITCH", 4)
print("StateIndex ALT=%s ROLL=%s PITCH=%s" % (StateIndex.ALT, _ROLL, _PITCH))


def make_env():
    st = [s for s in importlib.import_module("student.my_curriculum").get_stages()
          if s.index == 35][0]
    pre = {"step_ratio": 6, "observation_mode": "custom",
           "observation_module": "student.my_observation",
           "reward_module": "student.my_reward", "target_mode": "fixed",
           "ownship_control_mode": "rl"}
    e0 = tc.env_creator(pre)
    base = {**pre, "observation_mode": e0.config["observation_mode"],
            "reward": dict(e0.config["reward"]), "wez": dict(e0.config["wez"]),
            "observation_summary": dict(e0.config.get("observation_summary", {}))}
    e0.close()
    cfg = tc.build_stage_env_config(base, st)
    rnd = {"enabled": False, "radius": 0.0, "r_roll": 0.0, "r_pitch": 0.0, "r_heading": 0.0}
    far = {"ownship": [0.0, 0.0, -START_ALT, 0.0, 0.0, 0.0, 200.0],
           "target": [12000.0, 0.0, -START_ALT, 0.0, 0.0, 180.0, 200.0]}
    cfg["target_pool"] = [{"weight": 1.0, "mode": "policy",
                           "bundle": "artifacts/models/AeroFlyer/cand_c13280_s45",
                           "randomization": rnd, "spawn": far,
                           "pair": "diag", "side": "blue"}]
    cfg["pair_slots"] = False
    cfg["deck_guard"] = False
    cfg["spawn_alt_m"] = [START_ALT, START_ALT]
    cfg["spawn_speed_mps"] = [200.0, 200.0]
    cfg.pop("live_tune_file", None)
    return tc.env_creator(cfg)


env = make_env()
env.reset(seed=1)
gamma = 45.0
prev = None
print("%5s %8s %7s %7s %7s %7s %7s  %s" % ("t", "alt", "pitch", "roll", "V", "vz", "p_cmd", "end"))
for n in range(400):
    s = env._sim.get_state()
    alt = float(s[StateIndex.ALT]); pit = float(s[_PITCH]); roll = float(s[_ROLL])
    v = float(np.linalg.norm(np.asarray(s[6:9], dtype=np.float64)))
    vz = 0.0 if prev is None else (alt - prev) / 0.1
    prev = alt
    p_cmd = float(np.clip((pit + gamma) / 20.0, -1.0, 1.0)) if n >= 5 else 0.0
    sr = ((roll + 180.0) % 360.0) - 180.0
    r_cmd = float(np.clip(-sr / 25.0, -1.0, 1.0))
    if n % 10 == 0:
        print("%5.1f %8.0f %7.1f %7.1f %7.0f %7.0f %7.2f" % (n / 10.0, alt, pit, roll, v, vz, p_cmd))
    _, _, term, trunc, info = env.step(np.asarray([r_cmd, p_cmd, 0.0, 0.0], dtype=np.float32))
    if term or trunc:
        print("종료 @%.1fs  %s" % (n / 10.0, info.get("end_condition")))
        break
env.close()
