# -*- coding: utf-8 -*-
"""[측정 - 학습 아님] 스로틀 -> 속도 응답 실측.

왜: 꼬리 가드가 접근율을 낮추려고 스로틀을 줄이는데, JSBSim 터보팬은 스풀 지연이
있어 속도가 즉시 안 준다. 순시 접근율에 비례 제어를 걸면 진동한다.
그래서 계단 입력을 넣고 실제 응답(무효시간·시정수·최종 속도)을 잰다.

방법: 정책 없이 스크립트 행동만 넣는다. 롤·피치·요 = 0 (수평 직진),
스로틀만 +1 -> 목표값으로 계단. 60 Hz 물리, 매 프레임 속도 기록.

사용:
  python student/tools/throttle_response.py --levels 1.0,0.0,-0.5,-1.0 --hold 20
"""
from __future__ import annotations

import argparse, io, json, math, os, sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "src", ROOT / "student"):
    sys.path.insert(0, str(_p))

from DogFightEnvWrapper import DogFightWrapper                       # noqa: E402
from dogfight.sim.state_schema import StateIndex                     # noqa: E402
from student.my_observation import build_observation, OBSERVATION_SIZE  # noqa: E402


def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--levels", default="1.0,0.5,0.0,-0.5,-1.0")
    p.add_argument("--warmup", type=float, default=6.0, help="계단 전 최대추력 유지 초")
    p.add_argument("--hold", type=float, default=25.0, help="계단 후 유지 초")
    p.add_argument("--bank", type=float, default=0.0, help="선회 뱅크(도). 0 이면 직진")
    p.add_argument("--json-out", default="")
    return p.parse_args()


def make_env():
    cfg = {
        "step_ratio": 1,                     # 60 Hz 로 잘게 본다
        "observation_mode": "custom",
        "observation_module": "student.my_observation",
        "ownship_control_mode": "rl",
        "target_mode": "fixed",
        "max_engage_time": 300.0,
        "episode_step_limit": 30000,
        "reward": {},
        "ownship_randomization": {"enabled": False},
    }
    return DogFightWrapper(cfg, reward_fn=lambda *a, **k: (0.0, {}),
                           observation_fn=build_observation,
                           observation_size=OBSERVATION_SIZE)


def run_level(level, warmup, hold, bank):
    """warmup 동안 목표 뱅크까지 굴려 선회를 세운 뒤 스로틀을 계단으로 내린다.

    선회 유지: 롤 P 제어로 목표 뱅크, 피치는 당김(-)으로 고정.
    [실측] pitch -1 = 당김, roll +1 = 우측 (guard-envelope 기록과 동일)
    """
    env = make_env()
    env.reset()
    e = env.env if hasattr(env, "env") else env
    dt = 1.0 / 60.0
    rec = []
    n_warm = int(warmup / dt)
    n_hold = int(hold / dt)
    for i in range(n_warm + n_hold):
        st = e._ownship_state
        roll = float(st[3])
        if abs(bank) < 1e-6:
            roll_cmd, pitch_cmd = 0.0, 0.0
        else:
            err = bank - roll
            roll_cmd = max(-1.0, min(1.0, err / 30.0))
            pitch_cmd = -0.55                      # 당김 (선회 유지)
        th = 1.0 if i < n_warm else level
        env.step(np.array([roll_cmd, pitch_cmd, 0.0, th], dtype=np.float32))
        st = e._ownship_state
        spd = float(np.linalg.norm(np.asarray(st[6:9], dtype=np.float64)))
        if i >= n_warm - 60:
            rec.append(((i - n_warm) * dt, spd, float(st[StateIndex.ALT])))
    return rec


def fit(rec):
    """1차 지연 근사: v(t) = v_inf + (v0 - v_inf) exp(-(t - td)/tau)."""
    pre = [v for t, v, _ in rec if t <= 0.0]
    post = [(t, v) for t, v, _ in rec if t >= 0.0]
    v0 = float(np.mean(pre[-10:])) if pre else post[0][1]
    v_inf = float(np.mean([v for _, v in post[-30:]]))
    if abs(v0 - v_inf) < 0.5:
        return v0, v_inf, 0.0, 0.0
    # 무효시간: 변화가 v0 에서 2 % 벗어나는 첫 시각
    td = 0.0
    for t, v in post:
        if abs(v - v0) > 0.02 * abs(v0 - v_inf):
            td = t
            break
    # 63.2 % 도달 시각
    tgt = v0 + 0.632 * (v_inf - v0)
    t63 = None
    for t, v in post:
        if (v_inf > v0 and v >= tgt) or (v_inf < v0 and v <= tgt):
            t63 = t
            break
    tau = max((t63 - td), 0.0) if t63 is not None else float("nan")
    return v0, v_inf, td, tau


def main():
    a = parse()
    out = []
    print("스로틀 계단 응답 (수평 %s · 60 Hz)" % ("직진" if abs(a.bank) < 1e-6 else "뱅크 %.0f도" % a.bank))
    print("%8s %9s %9s %9s %8s %10s" % ("스로틀", "v0 m/s", "v∞ m/s", "Δv", "무효 s", "시정수 s"))
    print("-" * 60)
    for s in a.levels.split(","):
        lv = float(s)
        rec = run_level(lv, a.warmup, a.hold, a.bank)
        v0, vi, td, tau = fit(rec)
        print("%8.2f %9.1f %9.1f %+9.1f %8.2f %10.2f" % (lv, v0, vi, vi - v0, td, tau))
        out.append({"level": lv, "v0": v0, "v_inf": vi, "dead_s": td, "tau_s": tau,
                    "series": [[round(t, 3), round(v, 2)] for t, v, _ in rec[::6]]})
    if a.json_out:
        io.open(a.json_out, "w", encoding="utf-8").write(
            json.dumps(out, ensure_ascii=False, indent=1))
        print("\n저장:", a.json_out)


if __name__ == "__main__":
    main()
