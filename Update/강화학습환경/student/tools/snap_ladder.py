# -*- coding: utf-8 -*-
"""스냅샷 사다리 측정 (학습 아님): 기준 번들 A 를 여러 상대 B 와 양방향으로 붙여 격추/HP 마진을 센다.
사용: python student/tools/snap_ladder.py --a <번들> --b <번들1> <번들2> ... [--episodes 6]
양방향 = (A 가 ownship, B 가 target) + (B 가 ownship, A 가 target). 동시격추는 env 가 ownship 패배로 판정하므로
'A 먼저 격추' 와 'HP 마진(A HP - B HP)' 두 가지를 같이 본다.
"""
import argparse, importlib, os, sys, json
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT); sys.path.insert(0, "src"); sys.path.insert(0, ".")
import train_curriculum as tc
import student.rl_opponent as ro


def make_env(opp_bundle):
    st = [s for s in importlib.import_module("student.my_curriculum").get_stages() if s.index == 35][0]
    pre = {"step_ratio": 6, "observation_mode": "custom", "observation_module": "student.my_observation",
           "reward_module": "student.my_reward", "target_mode": "fixed", "ownship_control_mode": "rl"}
    e0 = tc.env_creator(pre)
    base = {**pre, "observation_mode": e0.config["observation_mode"], "reward": dict(e0.config["reward"]),
            "wez": dict(e0.config["wez"]), "observation_summary": dict(e0.config.get("observation_summary", {}))}
    e0.close()
    cfg = tc.build_stage_env_config(base, st)
    cfg["target_pool"] = [dict(cfg["target_pool"][0], weight=1.0, bundle=opp_bundle)]
    cfg.pop("live_tune_file", None)
    return tc.env_creator(cfg)


def play(env, pol, seed):
    obs, _ = env.reset(seed=seed); pol.reset(); done = False; n = 0
    while not done and n < 2200:
        a = pol.act(np.asarray(obs, dtype=np.float32))
        obs, r, t, tr, info = env.step(np.asarray(a, dtype=np.float32)); done = t or tr; n += 1
    return info.get("outcome"), float(info.get("ownship_health", 0)), float(info.get("target_health", 0)), n


def duel(own_bundle, tgt_bundle, episodes, seed0):
    env = make_env(tgt_bundle); pol = ro._BundleModule(own_bundle)
    out = [play(env, pol, seed0 + i) for i in range(episodes)]
    env.close(); return out


def classify(o, own_hp, tgt_hp, a_is_own):
    """A 시점 결과. 동시격추(양쪽 HP<=0)는 무승부로 따로 센다. 시간종료는 HP 우위로 판정(실서버 규칙)."""
    ah, bh = (own_hp, tgt_hp) if a_is_own else (tgt_hp, own_hp)
    if ah <= 0 and bh <= 0: return "tie"
    if bh <= 0 < ah: return "a_kill"
    if ah <= 0 < bh: return "b_kill"
    if abs(ah - bh) < 1e-6: return "tie"
    return "a_hp" if ah > bh else "b_hp"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--a", required=True); ap.add_argument("--b", nargs="+", required=True)
    ap.add_argument("--episodes", type=int, default=6); ap.add_argument("--seed", type=int, default=7000)
    args = ap.parse_args()
    print(f"A = {args.a}")
    print(f"{'B':28s} {'A격추승':>6s} {'B격추승':>6s} {'동시격추':>6s} {'종료A우위':>7s} {'종료B우위':>7s} {'HP마진(A-B)':>11s}  판수")
    for b in args.b:
        fwd = duel(args.a, b, args.episodes, args.seed)          # A ownship
        rev = duel(b, args.a, args.episodes, args.seed + 500)    # B ownship
        cats = [classify(o, oh, th, True) for o, oh, th, _ in fwd] + [classify(o, oh, th, False) for o, oh, th, _ in rev]
        margin = [oh - th for _, oh, th, _ in fwd] + [th - oh for _, oh, th, _ in rev]
        c = {k: cats.count(k) for k in ("a_kill", "b_kill", "tie", "a_hp", "b_hp")}
        print(f"{os.path.basename(b):28s} {c['a_kill']:6d} {c['b_kill']:6d} {c['tie']:6d} {c['a_hp']:7d} {c['b_hp']:7d} {np.mean(margin):+11.3f}  {len(cats)}")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
