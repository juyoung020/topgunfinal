# -*- coding: utf-8 -*-
"""[측정 — 학습 아님] JSBSim 실측 회복 엔벨로프.

각 (V, 강하각 γ, roll) 에서 **가드가 살릴 수 있는 바닥 위 최소 고도 H_true** 를
이분탐색으로 찾는다. 이 표가 "완전 가드가 가능한 조건" 그 자체다:
  상태가 (고도−바닥) ≥ H_true 안에서 가드에 넘어오면 100% 회복.
  그 밖이면 어떤 제어로도 불가능 — 정책이 못 들어가게 막을 경계.

수식 H_needed 와 대조해 저속에서 수식이 얼마나 틀리는지도 같이 낸다.
--control 로 회복 제어를 바꿔가며 H_true 를 줄일(엔벨로프를 넓힐) 수 있는지 본다.
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


def make_env(start_alt, speed, roll, pitch):
    st = [s for s in importlib.import_module("student.my_curriculum").get_stages() if s.index == 35][0]
    pre = {"step_ratio": 6, "observation_mode": "custom", "observation_module": "student.my_observation",
           "reward_module": "student.my_reward", "target_mode": "fixed", "ownship_control_mode": "rl"}
    e0 = tc.env_creator(pre)
    base = {**pre, "observation_mode": e0.config["observation_mode"], "reward": dict(e0.config["reward"]),
            "wez": dict(e0.config["wez"]), "observation_summary": dict(e0.config.get("observation_summary", {}))}
    e0.close()
    cfg = tc.build_stage_env_config(base, st)
    rnd = {"enabled": False, "radius": 0.0, "r_roll": 0.0, "r_pitch": 0.0, "r_heading": 0.0}
    spawn = {"ownship": [0.0, 0.0, -start_alt, roll, pitch, 0.0, speed],
             "target": [9000.0, 0.0, -3000.0, 0.0, 0.0, 180.0, 200.0]}
    cfg["target_pool"] = [{"weight": 1.0, "mode": "policy", "bundle": "artifacts/models/AeroFlyer/cand_c13280_s45",
                           "randomization": rnd, "spawn": spawn, "pair": "env", "side": "blue"}]
    cfg["pair_slots"] = False
    cfg["deck_guard"] = True
    cfg["deck_guard_penalty"] = 0.0
    cfg["spawn_alt_m"] = [start_alt, start_alt]
    cfg["spawn_speed_mps"] = [speed, speed]
    cfg.pop("live_tune_file", None)
    return tc.env_creator(cfg)


def sr(r):
    return ((float(r) + 180.0) % 360.0) - 180.0


def recovers(start_h, speed, gamma, roll, max_steps=500):
    """바닥+start_h 에서 강하각 γ·롤 roll 로 스폰. 가드 켜고 '계속 숙임' 의도를 준다.
    가드가 살려서 바닥을 안 지나면 True."""
    env = make_env(FLOOR + start_h, speed, roll, -gamma)
    try:
        env.reset(seed=1234)
        min_alt = 1e9
        prev = None
        for n in range(max_steps):
            s = env._sim.get_state()
            alt, rl, pit = float(s[StateIndex.ALT]), float(s[_ROLL]), float(s[_PITCH])
            vz = 0.0 if prev is None else (alt - prev) / 0.1
            prev = alt
            if n >= 1:
                min_alt = min(min_alt, alt)
            # 의도: 롤 유지(가드가 풀도록 냅둔다) + 계속 강하각 유지
            p_cmd = float(np.clip((pit + gamma) / 20.0, -1.0, 1.0))
            _, _, term, trunc, info = env.step(np.asarray([0.0, p_cmd, 0.0, 0.5], dtype=np.float32))
            if term or trunc:
                return not ("ownship altitude" in str(info.get("end_condition", "")))
            if n > 12 and vz > 2 and alt > min_alt + 100:
                return True
        return min_alt > FLOOR
    finally:
        env.close()


def h_true(speed, gamma, roll, lo=10.0, hi=1700.0, tol=25.0):
    """가드가 회복하는 최소 바닥위 고도. 이분탐색."""
    if recovers(hi, speed, gamma, roll) is False:
        return None  # 최대 고도서도 실패
    if recovers(lo, speed, gamma, roll):
        return lo
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if recovers(mid, speed, gamma, roll):
            hi = mid
        else:
            lo = mid
    return hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speeds", default="100,130,160,200,250,300,350")
    ap.add_argument("--gammas", default="30,45,60,75")
    ap.add_argument("--rolls", default="0,90")
    ap.add_argument("--out", default="artifacts/eval_visual/envelope_map.txt")
    a = ap.parse_args()
    speeds = [float(x) for x in a.speeds.split(",")]
    gammas = [float(x) for x in a.gammas.split(",")]
    rolls = [float(x) for x in a.rolls.split(",")]
    lines = []

    def out(s=""):
        print(s, flush=True); lines.append(s)

    out("JSBSim 실측 회복 엔벨로프 — H_true = 가드가 살리는 바닥위 최소고도(m)")
    out("수식 H_needed×1.15+15 와 대조. None = 최대고도(1700m)서도 회복 실패")
    for roll in rolls:
        out("\n[roll %g°]" % roll)
        hdr = "%6s |" % "V\\γ" + "".join("%14.0f" % g for g in gammas)
        out(hdr)
        out("-" * len(hdr))
        for v in speeds:
            cells = []
            for g in gammas:
                ht = h_true(v, g, roll)
                hf = dg.h_needed_m(v, g) * (1.0 + dg.GUARD_MARGIN) + dg.GUARD_ABS_MARGIN_M
                cells.append("%5s/%-5.0f" % (("%.0f" % ht) if ht is not None else "X", hf))
            out("%6.0f |" % v + "".join("%14s" % c for c in cells))
    out("\n각 칸 = H_true실측 / H_수식.  실측 > 수식 이면 수식이 위험하게 낮게 잡은 것.")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    out("-> %s" % a.out)


if __name__ == "__main__":
    main()
