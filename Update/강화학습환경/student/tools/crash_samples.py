# -*- coding: utf-8 -*-
"""추락 표본 수집 (학습 아님): 번들 A 를 지정 스폰(기본: 914 m 옆구리 + 914 m 래트레이스)에서 B 와 N판 돌려
추락한 판의 고도·거리 시계열을 그림으로 저장한다.
사용: python student/tools/crash_samples.py --a <번들> --b <번들> [--episodes 20] [--out artifacts/eval_visual/crash_samples.png]
"""
import argparse, importlib, os, sys
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT); sys.path.insert(0, "src"); sys.path.insert(0, ".")
import train_curriculum as tc
import student.rl_opponent as ro
from dogfight.sim.state_schema import StateIndex

LOW = -914.4
SPAWNS = {
    "abreast_914": {"ownship": [608.0, 0.0, LOW, 0.0, 0.0, 90.0, 200.0], "target": [0.0, 0.0, LOW, 0.0, 0.0, -90.0, 200.0]},
    "abreast_914_swap": {"ownship": [0.0, 0.0, LOW, 0.0, 0.0, -90.0, 200.0], "target": [608.0, 0.0, LOW, 0.0, 0.0, 90.0, 200.0]},
    "ratrace_914": {"ownship": [600.0, 0.0, LOW, 60.0, 0.0, 90.0, 200.0], "target": [-600.0, 0.0, LOW, 60.0, 0.0, 270.0, 200.0]},
    "ratrace_914_swap": {"ownship": [-600.0, 0.0, LOW, 60.0, 0.0, 270.0, 200.0], "target": [600.0, 0.0, LOW, 60.0, 0.0, 90.0, 200.0]},
}


def make_env(opp_bundle, spawn):
    st = [s for s in importlib.import_module("student.my_curriculum").get_stages() if s.index == 35][0]
    pre = {"step_ratio": 6, "observation_mode": "custom", "observation_module": "student.my_observation",
           "reward_module": "student.my_reward", "target_mode": "fixed", "ownship_control_mode": "rl"}
    e0 = tc.env_creator(pre)
    base = {**pre, "observation_mode": e0.config["observation_mode"], "reward": dict(e0.config["reward"]),
            "wez": dict(e0.config["wez"]), "observation_summary": dict(e0.config.get("observation_summary", {}))}
    e0.close()
    cfg = tc.build_stage_env_config(base, st)
    cfg["target_pool"] = [dict(cfg["target_pool"][0], weight=1.0, bundle=opp_bundle, spawn=spawn)]
    cfg.pop("live_tune_file", None)
    return tc.env_creator(cfg)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--a", required=True); ap.add_argument("--b", required=True)
    ap.add_argument("--episodes", type=int, default=20); ap.add_argument("--out", default="artifacts/eval_visual/crash_samples.png")
    a = ap.parse_args()
    pol = ro._BundleModule(a.a); names = list(SPAWNS); runs = []
    for i in range(a.episodes):
        name = names[i % len(names)]; env = make_env(a.b, SPAWNS[name])
        obs, _ = env.reset(seed=3000 + i); pol.reset(); done = False; n = 0
        alt, dist, oalt = [], [], []
        while not done and n < 2200:
            act = pol.act(np.asarray(obs, dtype=np.float32)); obs, r, t, tr, info = env.step(np.asarray(act, dtype=np.float32)); done = t or tr; n += 1
            s, ts = env._sim.get_state(), env._target_sim.get_state()
            alt.append(float(s[StateIndex.ALT])); oalt.append(float(ts[StateIndex.ALT]))
            dist.append(float(env._geo_info._get_distance(s, ts)))
        env.close()
        runs.append((name, info.get("outcome"), info.get("end_condition", ""), n, alt, oalt, dist))
        print(f"{i:2d} {name:18s} {str(info.get('outcome')):9s} {n:5d} steps  min_alt {min(alt):6.0f} m  {info.get('end_condition','')}"); sys.stdout.flush()
    crashes = [r for r in runs if "altitude" in (r[2] or "")]
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    show = crashes if crashes else runs[:6]
    k = min(6, len(show)); fig, axes = plt.subplots(2, k, figsize=(3.2 * k, 6.5), squeeze=False)
    for j, r in enumerate(show[:k]):
        name, oc, ec, n, alt, oalt, dist = r; tt = np.arange(n) / 10.0
        ax = axes[0][j]; ax.plot(tt, alt, "b", label="ours"); ax.plot(tt, oalt, "r", label="opp")
        for y, c in ((914, "orange"), (762, "orange"), (305, "red")): ax.axhline(y, ls=":", lw=0.8, color=c)
        ax.set_title(f"{name}\n{oc} {n/10:.0f}s  {ec[:22]}", fontsize=8); ax.set_ylim(0, 2500); ax.set_ylabel("alt m"); ax.legend(fontsize=6)
        ax2 = axes[1][j]; ax2.plot(tt, dist, "g"); ax2.axhline(914, ls="--", lw=0.8, color="gray"); ax2.set_ylim(0, 3000); ax2.set_xlabel("s"); ax2.set_ylabel("dist m")
    plt.suptitle(f"crash samples  A={os.path.basename(a.a)} vs B={os.path.basename(a.b)}  ({len(crashes)}/{len(runs)} crashed; dotted 914 spawn / 762 deck / 305 crash)")
    plt.tight_layout(); os.makedirs(os.path.dirname(a.out), exist_ok=True); plt.savefig(a.out, dpi=90)
    print("crashed", len(crashes), "of", len(runs), "->", a.out)


if __name__ == "__main__":
    main()
