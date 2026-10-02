# -*- coding: utf-8 -*-
"""[측정 — 학습 아님] 물리식 가드 검증.

A) 생존 검증: 가드 ON, 우리는 계속 기수를 숙인 채 스로틀만 다르게. 가드가 알아서 살려야 한다.
   조합마다 추락 여부 · 가드 첫 발동 고도 · 최저 고도 · 발동 스텝 수를 잰다.
   완만한 각(5°, 10°)도 넣어 하드플로어 없이 되는지 본다.
B) 비발동 검증: 45° 강하 후 **스스로** 안전 고도에서 회복하는 시나리오 —
   "아래 적을 잡는 강하"를 흉내낸 것. 가드가 한 번도 켜지면 안 된다.

사용: python student/tools/dive_validate.py [--out artifacts/eval_visual/dive_validate.txt]
"""
import argparse
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

FLOOR = 304.8
START_ALT = 3500.0
_ROLL = getattr(StateIndex, "ROLL", 3)
_PITCH = getattr(StateIndex, "PITCH", 4)


SPEED=200.0


def make_env(guard_on=True):
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
                           "pair": "validate", "side": "blue"}]
    cfg["pair_slots"] = False
    cfg["deck_guard"] = bool(guard_on)
    cfg["deck_guard_penalty"] = 0.0
    cfg["spawn_alt_m"] = [START_ALT, START_ALT]
    cfg["spawn_speed_mps"] = [SPEED, SPEED]
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


def dive_only(env, thr, gamma_deg, max_steps=900):
    """A) 계속 숙인다. 가드가 살리는지."""
    env.reset(seed=1234)
    for _ in range(5):
        env.step(np.asarray([0.0, 0.0, 0.0, 0.5], dtype=np.float32))
    prev = None
    fired_alt = None
    fired_v = fired_g = None
    fired_steps = 0
    min_alt = 1e9
    for n in range(max_steps):
        alt, roll, pit, v = state_of(env)
        vz = 0.0 if prev is None else (alt - prev) / 0.1
        prev = alt
        if n >= 1:
            min_alt = min(min_alt, alt)
        p_cmd = float(np.clip((pit + gamma_deg) / 20.0, -1.0, 1.0))
        act = [bank_hold(roll), p_cmd, 0.0, thr]
        _, _, term, trunc, info = env.step(np.asarray(act, dtype=np.float32))
        if getattr(env, "_deck_guard_fired", False):
            fired_steps += 1
            if fired_alt is None:
                fired_alt, fired_v = alt, v
                fired_g = math.degrees(math.asin(max(-1.0, min(1.0, -vz / max(v, 1.0)))))
        if term or trunc:
            crashed = "ownship altitude" in str(info.get("end_condition", ""))
            return crashed, fired_alt, fired_v, fired_g, min_alt, fired_steps
        # 가드가 살려서 다시 올라가면(발동 후 vz>0 이 2초) 종료
        if fired_alt is not None and vz > 0 and alt > fired_alt * 0.5 and n > 10:
            # 상승 전환 확인 후 2초 더 관찰
            ok = True
            for _ in range(20):
                a2, r2, p2, v2 = state_of(env)
                _, _, t2, tr2, i2 = env.step(np.asarray([bank_hold(r2), p_cmd, 0.0, thr], dtype=np.float32))
                min_alt = min(min_alt, a2)
                if getattr(env, "_deck_guard_fired", False):
                    fired_steps += 1
                if t2 or tr2:
                    return "ownship altitude" in str(i2.get("end_condition", "")), fired_alt, fired_v, fired_g, min_alt, fired_steps
            return False, fired_alt, fired_v, fired_g, min_alt, fired_steps
    return False, fired_alt, fired_v, fired_g, min_alt, fired_steps


def self_recover(env, thr, gamma_deg, recover_alt, max_steps=900):
    """B) 강하하다 recover_alt 에서 스스로 회복. 가드가 켜졌는지(켜지면 안 됨)."""
    env.reset(seed=1234)
    for _ in range(5):
        env.step(np.asarray([0.0, 0.0, 0.0, 0.5], dtype=np.float32))
    prev = None
    recovering = False
    fired = 0
    min_alt = 1e9
    rec_alt = None
    for n in range(max_steps):
        alt, roll, pit, v = state_of(env)
        vz = 0.0 if prev is None else (alt - prev) / 0.1
        prev = alt
        if n >= 1:
            min_alt = min(min_alt, alt)
        if not recovering and n >= 3 and vz < -5.0 and alt <= recover_alt:
            recovering = True
            rec_alt = alt
        if recovering:
            act = [bank_hold(roll), -1.0, 0.0, -1.0 if pit < 0.0 else 1.0]
        else:
            act = [bank_hold(roll), float(np.clip((pit + gamma_deg) / 20.0, -1.0, 1.0)), 0.0, thr]
        _, _, term, trunc, info = env.step(np.asarray(act, dtype=np.float32))
        if getattr(env, "_deck_guard_fired", False):
            fired += 1
        if term or trunc:
            return "ownship altitude" in str(info.get("end_condition", "")), fired, min_alt, rec_alt
        if recovering and vz >= 0.0 and n > 10:
            return False, fired, min_alt, rec_alt
    return False, fired, min_alt, rec_alt


def main():
    global START_ALT, SPEED
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/eval_visual/dive_validate.txt")
    ap.add_argument("--start-alt", type=float, default=START_ALT,
                    help="시작 고도 m. 완만한 각(5~10도)은 3,500 m 에서 90초 안에 바닥에 못 닿아 미발동으로 나온다 — 1,200 m 로 낮춰 다시 잰다")
    ap.add_argument("--angles", default="5,10,15,30,45,60,75")
    ap.add_argument("--skip-b", action="store_true")
    ap.add_argument("--speed", type=float, default=SPEED)
    a = ap.parse_args()
    START_ALT = float(a.start_alt)
    SPEED = float(a.speed)
    angles = [float(x) for x in a.angles.split(",") if x.strip()]
    lines = []

    def out(s=""):
        print(s, flush=True)
        lines.append(s)

    out("물리식 가드 검증 — margin %.2f · T_REACT %.2f · n=%.1f+%.3fV"
        % (dg.GUARD_MARGIN, dg.T_REACT_S, dg.N_A, dg.N_B))
    out("\n[A] 계속 숙임 — 가드가 살리는가")
    out("%6s %5s | %6s %6s | %8s %8s %8s %6s | %s"
        % ("스로틀", "γ", "V발동", "γ발동", "발동고도", "최저고도", "바닥여유", "ON스텝", "결과"))
    out("-" * 84)
    out("  시작 고도 %.0f m" % START_ALT)
    crashes = 0
    for thr in (-1.0, 0.0, 1.0):
        for g in angles:
            env = make_env(True)
            try:
                crashed, fa, fv, fg, mn, fs = dive_only(env, thr, g)
            finally:
                env.close()
            crashes += int(crashed)
            out("%6.1f %5.0f | %6s %6s | %8s %8.0f %8.0f %6d | %s"
                % (thr, g, ("%.0f" % fv) if fv else "-", ("%.1f" % fg) if fg is not None else "-",
                   ("%.0f" % fa) if fa else "미발동", mn, mn - FLOOR, fs,
                   "추락 X" if crashed else "생존"))
    out("\n추락 %d / %d" % (crashes, 3 * len(angles)))
    if a.skip_b:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        out("\n-> %s" % a.out)
        return

    out("\n[B] 비발동 — 45° 강하 후 스스로 회복 (아래 적 공격 흉내). 가드가 켜지면 안 된다")
    out("%6s %10s %10s %10s %8s | %s"
        % ("스로틀", "회복시작", "실제시작", "최저고도", "가드ON", "결과"))
    out("-" * 66)
    false_fire = 0
    for thr, rec in ((-1.0, 900.0), (-1.0, 750.0), (0.0, 1000.0), (0.0, 850.0), (1.0, 1100.0)):
        env = make_env(True)
        try:
            crashed, fired, mn, ra = self_recover(env, thr, 45.0, rec)
        finally:
            env.close()
        false_fire += int(fired > 0)
        out("%6.1f %9.0fm %9sm %9.0fm %8d | %s"
            % (thr, rec, ("%.0f" % ra) if ra else "-", mn, fired,
               ("추락" if crashed else ("가드 개입 X" if fired else "정책만으로 회복 · 가드 침묵"))))
    out("\n헛발동 %d / 5" % false_fire)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    out("\n-> %s" % a.out)


if __name__ == "__main__":
    main()
