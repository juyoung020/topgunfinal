# -*- coding: utf-8 -*-
"""[측정 - 학습 아님] 꼬리 가드 A/B.

같은 번들·같은 상대·같은 시드로 가드 on/off 를 번갈아 돌려 비교한다.
정책은 rl_opponent.RLOpponent 로 직접 굴린다(eval_winrate 는 삭제된 모듈을 참조해 깨짐).

사용:
  python student/tools/tail_ab.py --bundle artifacts/models/AeroFlyer/peak_v8_iter19140 \
      --opponent artifacts/models/AeroFlyer/cand_v7_iter4880 --episodes 12
"""
from __future__ import annotations

import argparse, io, json, math, os, sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "src", ROOT / "student"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from DogFightEnvWrapper import DogFightWrapper                       # noqa: E402
from dogfight.ai.student_hooks import load_observation_hook, load_reward_hook  # noqa: E402
from student.rl_opponent import _BundleModule                          # noqa: E402
import student.tail_guard as TG                                       # noqa: E402
from student.tail_guard import geometry                               # noqa: E402


def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", required=True)
    p.add_argument("--opponent", required=True)
    p.add_argument("--episodes", type=int, default=12)
    p.add_argument("--seed0", type=int, default=1000)
    p.add_argument("--max-engage-time", type=float, default=200.0)
    p.add_argument("--json-out", default="")
    return p.parse_args()


def build(opponent_bundle, guard, max_t):
    obs = load_observation_hook("student.my_observation")
    rfn, rcfg = load_reward_hook("student.my_reward")
    cfg = {
        "step_ratio": 6,
        "observation_mode": obs["mode"],
        "observation_module": "student.my_observation",
        "ownship_control_mode": "rl",
        "target_mode": "policy",
        "target_policy_bundle": opponent_bundle,
        "max_engage_time": max_t,
        "episode_step_limit": int(max_t * 60 / 6) + 200,
        "reward": rcfg,
        "tail_guard": bool(guard),
        "ownship_randomization": {"enabled": True, "radius": 900.0,
                                  "r_roll": 10.0, "r_pitch": 8.0, "r_heading": 180.0},
    }
    return DogFightWrapper(cfg, reward_fn=rfn,
                           observation_fn=obs["build_observation"],
                           observation_size=obs["size"])


def run(bundle, opponent, guard, episodes, seed0, max_t):
    env = build(opponent, guard, max_t)
    pol = _BundleModule(bundle)
    e = env.env if hasattr(env, "env") else env
    out = Counter()
    steps_l, wez_l, mind_l, fire_l, clo_l = [], [], [], [], []
    for k in range(episodes):
        np.random.seed(seed0 + k)
        ob, _ = env.reset()
        pol.reset()
        TG.reset_counter()
        n = wez = 0
        mind = 1e9
        clos = []
        done = False
        while not done:
            a = pol.act(np.asarray(ob, dtype=np.float32))
            ob, _r, term, trunc, info = env.step(a)
            done = bool(term or trunc)
            n += 1
            if getattr(e, "_in_wez", False):
                wez += 1
            d, aim, foe, cl, spd, bank = geometry(e._ownship_state, e._target_state)
            mind = min(mind, d)
            if aim < 40 and foe > 110 and 400 < d < 3000:
                clos.append(cl)
        out[str(info.get("outcome", "?"))] += 1
        steps_l.append(n); wez_l.append(wez); mind_l.append(mind)
        fire_l.append(TG.FIRE_COUNT[0])
        if clos:
            clo_l.append(float(np.median(clos)))
    return {
        "outcome": dict(out),
        "win": (out["win"] + out["judge_win"]) / max(episodes, 1),
        "loss": (out["loss"] + out["judge_loss"] + out["crash"]) / max(episodes, 1),
        "draw": (out["draw"] + out["timeout"]) / max(episodes, 1),
        "steps": float(np.median(steps_l)),
        "wez": float(np.median(wez_l)),
        "min_dist": float(np.median(mind_l)),
        "guard_steps": float(np.median(fire_l)),
        "approach_closure": float(np.median(clo_l)) if clo_l else float("nan"),
    }


def main():
    a = parse()
    res = {}
    for tag, g in (("가드 OFF", False), ("가드 ON", True)):
        print("== %s ==" % tag, flush=True)
        res[tag] = run(a.bundle, a.opponent, g, a.episodes, a.seed0, a.max_engage_time)
    print("\n%-12s %6s %6s %6s %8s %7s %9s %9s %9s"
          % ("", "승률", "패율", "무", "판길이", "WEZ", "최소거리", "가드스텝", "접근율"))
    print("-" * 82)
    for tag in ("가드 OFF", "가드 ON"):
        r = res[tag]
        print("%-12s %6.2f %6.2f %6.2f %8.0f %7.0f %9.0f %9.0f %9.0f"
              % (tag, r["win"], r["loss"], r["draw"], r["steps"], r["wez"],
                 r["min_dist"], r["guard_steps"], r["approach_closure"]))
    if a.json_out:
        io.open(a.json_out, "w", encoding="utf-8").write(
            json.dumps(res, ensure_ascii=False, indent=1))
        print("\n저장:", a.json_out)


if __name__ == "__main__":
    main()
