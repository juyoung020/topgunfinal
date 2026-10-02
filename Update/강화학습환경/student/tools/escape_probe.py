# -*- coding: utf-8 -*-
"""[측정 — 학습 아님] 컷오프 BT 에 물린 상태에서 어떤 기동이 벗어나는가.

우리가 앞(쫓기는 자리), 컷오프 BT 가 1,000 m 뒤 같은 기수로 시작한다.
우리 기체는 정책 대신 **스크립트 기동**을 넣고, 판마다 다음을 잰다.
  탈출     적ATA > 90도 (적이 나를 못 겨눔) 이 2초 이상 지속, 또는 거리 > 1,500 m 2초 이상
  탈출시각 처음 탈출한 시각
  피격     내 HP 감소량
  추락     내 추락 / 적 추락
Ray 없이 env 를 직접 연다. 학습과 동시에 돌려도 된다(CPU 1개).

사용: python student/tools/escape_probe.py [--episodes 10] [--out artifacts/eval_visual/escape_probe.txt]
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
from student.my_reward import _ata_deg

ALT_D = -4572.0                         # NED D (아래 양수) — 4,572 m
# 우리가 앞, 컷오프가 1,000 m 뒤 (측면 46.5 m), 같은 기수
SPAWN = {"ownship": [0.0, 0.0, ALT_D, 0.0, 0.0, 0.0, 200.0],
         "target": [-1000.0, -46.5, ALT_D, 0.0, 0.0, 0.0, 200.0]}

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
    cfg["target_pool"] = [{"weight": 1.0, "mode": "cutoffbt", "randomization": rnd,
                           "spawn": SPAWN, "pair": "cutoffbt|probe", "side": "red"}]
    cfg["pair_slots"] = False
    cfg.pop("live_tune_file", None)
    return tc.env_creator(cfg)


# ── 스크립트 기동 (10 Hz, 행동 = [roll, pitch, yaw, thr] 각 -1..1, pitch -1 = 당김) ──
def _bank_hold(roll_deg, target_deg, gain=1.0 / 25.0):
    """현재 롤을 target 으로 P 제어."""
    signed = ((roll_deg + 180.0) % 360.0) - 180.0
    return float(np.clip((target_deg - signed) * gain, -1.0, 1.0))


def m_baseline(t, s):
    return [_bank_hold(s[_ROLL], 0.0), 0.0, 0.0, 1.0]


def m_break_left(t, s):
    """수평 최대 선회 좌: 뱅크 -80도 유지 + 풀당김."""
    return [_bank_hold(s[_ROLL], -80.0), -1.0, 0.0, 1.0]


def m_break_right(t, s):
    return [_bank_hold(s[_ROLL], 80.0), -1.0, 0.0, 1.0]


def m_vertical(t, s):
    """날개 수평 + 풀당김 = 수직 상승(루프)."""
    return [_bank_hold(s[_ROLL], 0.0), -1.0, 0.0, 1.0]


def m_decel(t, s):
    """기수 40도 들고 스로틀 0: 속도 죽이기. 4초 뒤 수평 복귀."""
    if t < 4.0:
        return [_bank_hold(s[_ROLL], 0.0), -1.0 if s[_PITCH] < 40.0 else 0.0, 0.0, -1.0]
    return [_bank_hold(s[_ROLL], 0.0), 0.3 if s[_PITCH] > 5.0 else 0.0, 0.0, 1.0]


def m_scissors(t, s):
    """3초마다 좌우 뱅크 반전 + 풀당김."""
    tgt = -80.0 if int(t // 3.0) % 2 == 0 else 80.0
    return [_bank_hold(s[_ROLL], tgt), -1.0, 0.0, 0.3]


def m_split_s(t, s):
    """뒤집고(1.8초) 당김 = 강하 반전."""
    if t < 1.8:
        return [1.0, 0.0, 0.0, 0.3]
    return [_bank_hold(s[_ROLL], 180.0, gain=1.0 / 40.0), -1.0, 0.0, 0.3]


def m_break_then_vertical(t, s):
    """3초 수평 급선회 뒤 수직."""
    if t < 3.0:
        return [_bank_hold(s[_ROLL], -80.0), -1.0, 0.0, 1.0]
    return [_bank_hold(s[_ROLL], 0.0), -1.0, 0.0, 1.0]


MANEUVERS = [("직진(대조)", m_baseline), ("수평급선회", m_break_left),
             ("수직상승", m_vertical), ("급감속", m_decel),
             ("시저스", m_scissors), ("스플릿S", m_split_s),
             ("급선회→수직", m_break_then_vertical)]


def run_one(env, fn, seed, max_steps=1200):
    obs, _ = env.reset(seed=seed)
    hp0 = 1.0
    esc_t = sep_t = None                 # 탈출(각도) / 이탈(거리) — 따로 센다
    esc_run = far_run = 0
    min_fa = 180.0
    min_d = 1e9
    in_range = False
    hits = 0.0
    n = 0
    done = False
    info = {}
    while not done and n < max_steps:
        s = env._sim.get_state()
        ts = env._target_sim.get_state()
        t = n / 10.0
        act = np.asarray(fn(t, s), dtype=np.float32)
        obs, r, term, trunc, info = env.step(act)
        done = term or trunc
        n += 1
        fa = _ata_deg(ts, s)                # 적 기수 <-> 나
        d = float(env._geo_info._get_distance(s, ts))
        min_fa = min(min_fa, fa)
        min_d = min(min_d, d)
        if d < 914.4:
            in_range = True
        # 탈출 = 적이 나를 못 겨누는 상태(적ATA>90)가 근거리에서 2초 지속. 거리로 떼어놓는 건 제외.
        esc_run = esc_run + 1 if (fa > 90.0 and d < 1200.0) else 0
        far_run = far_run + 1 if d > 1500.0 else 0
        if esc_t is None and esc_run >= 20:
            esc_t = t
        if sep_t is None and far_run >= 20:
            sep_t = t
        hp = float(info.get("ownship_health", 1.0))
        hits = max(hits, hp0 - hp)
    return {"esc": esc_t, "sep": sep_t, "hits": hits, "min_fa": min_fa,
            "min_d": min_d, "in_range": in_range, "steps": n,
            "end": info.get("end_condition", ""), "outcome": info.get("outcome", ""),
            "own_hp": float(info.get("ownship_health", 1.0)),
            "tgt_hp": float(info.get("target_health", 1.0))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=10)
    ap.add_argument("--out", default="artifacts/eval_visual/escape_probe.txt")
    a = ap.parse_args()
    lines = []

    def out(s=""):
        print(s, flush=True)
        lines.append(s)

    out("컷오프 BT 탈출 실험 — 우리가 앞, 컷오프 1,000 m 뒤 · 판당 최대 120초 · %d판/기동"
        % a.episodes)
    out("  탈출 = 적ATA>90° 가 1,200 m 안에서 2초 지속 (각도로 벗어남) · 이탈 = 거리>1,500 m 2초 (떼어놓음)")
    out("%-12s %5s %7s %5s %7s %8s %8s %6s %6s   %s"
        % ("기동", "탈출", "시각", "이탈", "피격HP", "사거리진입", "최소거리", "내추락", "적추락", "결말"))
    out("-" * 96)
    for name, fn in MANEUVERS:
        res = []
        for i in range(a.episodes):
            env = make_env()
            try:
                res.append(run_one(env, fn, seed=7000 + i))
            finally:
                env.close()
        n = len(res)
        esc = [x for x in res if x["esc"] is not None]
        sep = [x for x in res if x["sep"] is not None]
        own_crash = sum(1 for x in res if "ownship altitude" in x["end"])
        tgt_crash = sum(1 for x in res if "target altitude" in x["end"])
        ends = {}
        for x in res:
            ends[x["outcome"]] = ends.get(x["outcome"], 0) + 1
        out("%-12s %4d/%-2d %6s %4d/%-2d %7.3f %7d/%-2d %7.0fm %6d %6d   %s"
            % (name, len(esc), n,
               ("%.1fs" % (sum(x["esc"] for x in esc) / len(esc))) if esc else "-",
               len(sep), n,
               sum(x["hits"] for x in res) / n,
               sum(1 for x in res if x["in_range"]), n,
               sum(x["min_d"] for x in res) / n,
               own_crash, tgt_crash,
               " ".join("%s%d" % (k, v) for k, v in sorted(ends.items(), key=lambda kv: -kv[1]))))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    out("\n-> %s" % a.out)


if __name__ == "__main__":
    main()
