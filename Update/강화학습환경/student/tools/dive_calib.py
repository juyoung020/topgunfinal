# -*- coding: utf-8 -*-
"""[측정 — 학습 아님] 강하 회복 고도손실 표 만들기.

가드를 끈 채로 (스로틀, 목표 강하각) 조합마다:
  1) 3,500 m 에서 기수를 내려 목표 강하각으로 가속
  2) 고도 H_trig 에 닿으면 회복 시작 (롤 수평 → 풀당김, 기수 아래면 스로틀 0)
  3) 수직속도 >= 0 이 되면 생존, 304.8 m 아래면 추락
H_trig 을 이분탐색해 **살아남는 최소 회복 시작 고도**를 찾는다.
그 순간의 실제 속도 V·강하각 γ 와 함께 기록 → 물리식 계수 피팅용.

사용: python student/tools/dive_calib.py [--out artifacts/eval_visual/dive_calib.json]
"""
import argparse
import importlib
import json
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

FLOOR = 304.8
START_ALT = 3500.0
_ROLL = getattr(StateIndex, "ROLL", 3)
_PITCH = getattr(StateIndex, "PITCH", 4)


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
           "target": [12000.0, 0.0, -START_ALT, 0.0, 0.0, 180.0, 200.0]}   # 12 km 앞, 무관
    # 상대는 정책 번들 — 컷오프 BT 는 12 km 밖에서도 33초 만에 스스로 추락해 판을 끝냈다.
    cfg["target_pool"] = [{"weight": 1.0, "mode": "policy",
                           "bundle": "artifacts/models/AeroFlyer/cand_c13280_s45",
                           "randomization": rnd, "spawn": far,
                           "pair": "calib", "side": "blue"}]
    cfg["pair_slots"] = False
    cfg["deck_guard"] = False              # 가드 끄고 잰다
    cfg["spawn_alt_m"] = [START_ALT, START_ALT]
    cfg["spawn_speed_mps"] = [200.0, 200.0]
    cfg.pop("live_tune_file", None)
    return tc.env_creator(cfg)


def signed_roll(r):
    return ((float(r) + 180.0) % 360.0) - 180.0


def bank_hold(roll_deg, target=0.0, gain=1.0 / 25.0):
    return float(np.clip((target - signed_roll(roll_deg)) * gain, -1.0, 1.0))


def state_of(env):
    s = env._sim.get_state()
    v = float(np.linalg.norm(np.asarray(s[6:9], dtype=np.float64)))
    return float(s[StateIndex.ALT]), float(s[_ROLL]), float(s[_PITCH]), v


def run(env, thr_dive, gamma_deg, h_trig, max_steps=900):
    """한 판: 강하 → h_trig 에서 회복. (생존 여부, 회복시작 V, γ, 최저고도, 손실)"""
    env.reset(seed=1234)
    # 첫 스텝 전엔 상태가 0 으로 읽힌다(속도 0·고도 0) — 수평 행동으로 5스텝 예열한다.
    for _ in range(5):
        env.step(np.asarray([0.0, 0.0, 0.0, 0.5], dtype=np.float32))
    prev_alt = None
    recovering = False
    v_at = g_at = None
    min_alt = 1e9
    alt_at = None
    for n in range(max_steps):
        alt, roll, pit, v = state_of(env)
        vz = 0.0 if prev_alt is None else (alt - prev_alt) / 0.1
        prev_alt = alt
        if n >= 1:
            min_alt = min(min_alt, alt)
        if not recovering:
            # 실제로 강하 중(vz < -5)이고 고도가 정상값일 때만 회복 트리거를 본다
            if n >= 3 and vz < -5.0 and alt > FLOOR and alt <= h_trig:
                recovering = True
                v_at, alt_at = v, alt
                # 실제 비행경로각: sinγ = -vz/V
                g_at = math.degrees(math.asin(max(-1.0, min(1.0, -vz / max(v, 1.0)))))
            else:
                # 목표 강하각으로 기수 내리기 (P 제어), 날개 수평
                p_cmd = float(np.clip((pit + gamma_deg) / 20.0, -1.0, 1.0))   # pitch -> -γ
                act = [bank_hold(roll), p_cmd, 0.0, thr_dive]
        if recovering:
            # 가드와 같은 회복법: 롤 수평 우선, 풀당김, 기수 아래면 스로틀 0
            act = [bank_hold(roll), -1.0 if abs(signed_roll(roll)) <= 100.0 else 0.0,
                   0.0, -1.0 if pit < 0.0 else 1.0]
            if vz >= 0.0 and n > 2:
                return True, v_at, g_at, min_alt, alt_at - min_alt
        _, _, term, trunc, info = env.step(np.asarray(act, dtype=np.float32))
        if term or trunc:
            crashed = "ownship altitude" in str(info.get("end_condition", ""))
            return (not crashed), v_at, g_at, min_alt, (alt_at - min_alt) if alt_at else None
    return True, v_at, g_at, min_alt, (alt_at - min_alt) if alt_at else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/eval_visual/dive_calib.json")
    a = ap.parse_args()
    grid = [(thr, g) for thr in (-1.0, 0.0, 1.0) for g in (15.0, 30.0, 45.0, 60.0, 75.0)]
    rows = []
    print("%6s %6s | %8s %8s | %10s %8s"
          % ("스로틀", "목표γ", "V(㎧)", "실제γ", "최소회복고도", "손실(m)"))
    print("-" * 62)
    for thr, g in grid:
        lo, hi = FLOOR + 20.0, 2200.0
        best = None
        # 먼저 hi 에서 생존하는지
        env = make_env()
        try:
            ok, v, ga, mn, loss = run(env, thr, g, hi)
        finally:
            env.close()
        if not ok:
            print("%6.1f %6.0f | %8s %8s | %10s   (2,200 m 에서도 추락)" % (thr, g, "-", "-", "-"))
            rows.append({"thr": thr, "gamma_target": g, "h_min": None})
            continue
        best = (hi, v, ga, mn, loss)
        for _ in range(8):                      # 이분탐색 8회 → 약 8 m 해상도
            mid = 0.5 * (lo + hi)
            env = make_env()
            try:
                ok, v, ga, mn, loss = run(env, thr, g, mid)
            finally:
                env.close()
            if ok:
                hi = mid
                best = (mid, v, ga, mn, loss)
            else:
                lo = mid
        h, v, ga, mn, loss = best
        print("%6.1f %6.0f | %8.0f %8.1f | %10.0f %8.0f"
              % (thr, g, v or 0, ga or 0, h, loss or 0))
        sys.stdout.flush()
        rows.append({"thr": thr, "gamma_target": g, "h_min": h, "v": v,
                     "gamma": ga, "min_alt": mn, "loss": loss,
                     "needed": h - FLOOR})
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(rows, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n-> %s" % a.out)


if __name__ == "__main__":
    main()
