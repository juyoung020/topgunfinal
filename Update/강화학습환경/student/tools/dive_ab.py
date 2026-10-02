# -*- coding: utf-8 -*-
"""[측정 — 학습 아님] 옛 가드 vs 새 가드 A/B.

같은 강하 시나리오(고속 200 · 저속 100 m/s × 각 5종 × 스로틀 3종)를 세 가드로 돌려
추락 수와 바닥 최저고도를 비교한다. "새 가드가 옛 가드보다 나쁘지 않은가"를 직접 답한다.

  old       : guard_pitch (2단 · 하드플로어 350 m · TF_GATE 4 s)  — 오늘 재작성 전
  phys      : guard_step  (물리식 · 피치율 선행 · 저속 풀추력)     — 현재 파일
  phys_noThr: 물리식이되 스로틀은 옛 규칙(기수 아래 idle)          — 스로틀 효과 격리
"""
import argparse
import importlib
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, "src"); sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

import train_curriculum as tc
from dogfight.sim.state_schema import StateIndex
import student.deck_guard as dg

FLOOR = 304.8
_ROLL, _PITCH = 3, 4


def make_env(start_alt, speed):
    st = [s for s in importlib.import_module("student.my_curriculum").get_stages() if s.index == 35][0]
    pre = {"step_ratio": 6, "observation_mode": "custom", "observation_module": "student.my_observation",
           "reward_module": "student.my_reward", "target_mode": "fixed", "ownship_control_mode": "rl"}
    e0 = tc.env_creator(pre)
    base = {**pre, "observation_mode": e0.config["observation_mode"], "reward": dict(e0.config["reward"]),
            "wez": dict(e0.config["wez"]), "observation_summary": dict(e0.config.get("observation_summary", {}))}
    e0.close()
    cfg = tc.build_stage_env_config(base, st)
    rnd = {"enabled": False, "radius": 0.0, "r_roll": 0.0, "r_pitch": 0.0, "r_heading": 0.0}
    far = {"ownship": [0.0, 0.0, -start_alt, 0.0, 0.0, 0.0, speed],
           "target": [12000.0, 0.0, -start_alt, 0.0, 0.0, 180.0, speed]}
    cfg["target_pool"] = [{"weight": 1.0, "mode": "policy", "bundle": "artifacts/models/AeroFlyer/cand_c13280_s45",
                           "randomization": rnd, "spawn": far, "pair": "ab", "side": "blue"}]
    cfg["pair_slots"] = False
    cfg["deck_guard"] = True
    cfg["deck_guard_penalty"] = 0.0
    cfg["spawn_alt_m"] = [start_alt, start_alt]
    cfg["spawn_speed_mps"] = [speed, speed]
    cfg.pop("live_tune_file", None)
    return tc.env_creator(cfg)


def sr(r):
    return ((float(r) + 180.0) % 360.0) - 180.0


# --- 세 가드를 guard_step 시그니처로 감싼다 (env 가 부르는 형태) ---
def guard_old(action, alt, vz, roll, pitch, dist, active, throttle_range=(0.0, 1.0),
              enemy_alt_m=None, speed_mps=None, pitch_rate_dps=None):
    out, fired = dg.guard_pitch(action, alt, vz, roll, pitch, throttle_range=throttle_range)
    return out, (1 if fired else 0)


_ORIG_STEP = dg.guard_step


def guard_phys_nothr(action, alt, vz, roll, pitch, dist, active, throttle_range=(0.0, 1.0),
                     enemy_alt_m=None, speed_mps=None, pitch_rate_dps=None):
    # 물리식이되 저속 풀추력을 끈다: LOW_ENERGY 를 0 으로 임시 낮춰 원래 규칙만 남긴다
    save = dg.LOW_ENERGY_MPS
    dg.LOW_ENERGY_MPS = 0.0
    try:
        return _ORIG_STEP(action, alt, vz, roll, pitch, dist, active, throttle_range=throttle_range,
                          enemy_alt_m=enemy_alt_m, speed_mps=speed_mps, pitch_rate_dps=pitch_rate_dps)
    finally:
        dg.LOW_ENERGY_MPS = save


VARIANTS = {"old": guard_old, "phys": None, "phys_noThr": guard_phys_nothr}  # None = 현재 guard_step


def run_case(env, thr, gamma, max_steps=1200):
    env.reset(seed=1234)
    for _ in range(5):
        env.step(np.asarray([0.0, 0.0, 0.0, 0.5], dtype=np.float32))
    min_alt = 1e9
    prev = None
    for n in range(max_steps):
        s = env._sim.get_state()
        alt, roll, pit = float(s[StateIndex.ALT]), float(s[_ROLL]), float(s[_PITCH])
        vz = 0.0 if prev is None else (alt - prev) / 0.1
        prev = alt
        if n >= 1:
            min_alt = min(min_alt, alt)
        act = [float(np.clip(-sr(roll) / 25.0, -1, 1)), float(np.clip((pit + gamma) / 20.0, -1, 1)), 0.0, thr]
        _, _, term, trunc, info = env.step(np.asarray(act, dtype=np.float32))
        if term or trunc:
            return "ownship altitude" in str(info.get("end_condition", "")), min_alt
        if n > 15 and vz > 0 and alt > min_alt + 100:
            return False, min_alt
    return False, min_alt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-alt", type=float, default=1400.0)
    ap.add_argument("--angles", default="15,30,45,60,75")
    ap.add_argument("--out", default="artifacts/eval_visual/dive_ab.txt")
    a = ap.parse_args()
    angles = [float(x) for x in a.angles.split(",")]
    lines = []

    def out(s=""):
        print(s, flush=True); lines.append(s)

    out("옛 가드 vs 새 가드 A/B — 시작 %.0f m · 각 %s · 스로틀 −1/0/1" % (a.start_alt, angles))
    for speed, tag in ((200.0, "고속 200 m/s"), (100.0, "저속 100 m/s")):
        out("\n[%s]" % tag)
        out("%-11s %8s %8s %10s" % ("가드", "추락수", "총판", "최저고도중앙"))
        out("-" * 42)
        for name, fn in VARIANTS.items():
            dg.guard_step = fn if fn is not None else _ORIG_STEP
            crashes = 0; mins = []; total = 0
            for thr in (-1.0, 0.0, 1.0):
                for g in angles:
                    env = make_env(a.start_alt, speed)
                    try:
                        c, mn = run_case(env, thr, g)
                    finally:
                        env.close()
                    crashes += int(c); mins.append(mn); total += 1
            dg.guard_step = _ORIG_STEP
            mmed = sorted(mins)[len(mins) // 2]
            out("%-11s %8d %8d %10.0f" % (name, crashes, total, mmed))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    out("\n-> %s" % a.out)


if __name__ == "__main__":
    main()
