# -*- coding: utf-8 -*-
"""[측정 — 학습 아님] 실제 추락 상태를 JSBSim 에 그대로 앉혀 새 가드로 빠져나오는지.

합성 강하가 아니라, 재기동 후 실제 crash dump 에서 **바닥 관통 T초 전의 실측 상태**
(위치·자세·속도 벡터)를 뽑아 그 자리에 기체를 스폰한 뒤, 그때의 실측 조종 의도를
계속 주면서 가드를 켠다. 같은 상태를 (a)가드 off (b)새 가드 로 각각 돌려 비교한다.

핵심: 물리 엔진도 실물, 초기 상태도 실측. 달라지는 건 가드뿐이다.
"""
import argparse
import csv
import datetime
import glob
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

FLOOR = 304.8
_ROLL, _PITCH = 3, 4


def make_env(guard_on, spawn):
    st = [s for s in importlib.import_module("student.my_curriculum").get_stages() if s.index == 35][0]
    pre = {"step_ratio": 6, "observation_mode": "custom", "observation_module": "student.my_observation",
           "reward_module": "student.my_reward", "target_mode": "fixed", "ownship_control_mode": "rl"}
    e0 = tc.env_creator(pre)
    base = {**pre, "observation_mode": e0.config["observation_mode"], "reward": dict(e0.config["reward"]),
            "wez": dict(e0.config["wez"]), "observation_summary": dict(e0.config.get("observation_summary", {}))}
    e0.close()
    cfg = tc.build_stage_env_config(base, st)
    rnd = {"enabled": False, "radius": 0.0, "r_roll": 0.0, "r_pitch": 0.0, "r_heading": 0.0}
    far = {"ownship": spawn, "target": [spawn[0] + 8000.0, spawn[1], -3000.0, 0.0, 0.0, 180.0, 200.0]}
    cfg["target_pool"] = [{"weight": 1.0, "mode": "policy", "bundle": "artifacts/models/AeroFlyer/cand_c13280_s45",
                           "randomization": rnd, "spawn": far, "pair": "rep", "side": "blue"}]
    cfg["pair_slots"] = False
    cfg["deck_guard"] = bool(guard_on)
    cfg["deck_guard_penalty"] = 0.0
    cfg["spawn_alt_m"] = [-spawn[2], -spawn[2]]
    cfg["spawn_speed_mps"] = [spawn[6], spawn[6]]
    cfg.pop("live_tune_file", None)
    return tc.env_creator(cfg)


def sr(r):
    return ((float(r) + 180.0) % 360.0) - 180.0


def load_states(lead_s=2.0):
    """각 dump 에서 바닥 관통 lead_s 초 전의 [n,e,alt,roll,pitch,yaw,V] 와 그때 실측 조종을 뽑는다."""
    fs = [f for f in glob.glob("artifacts/crash_dumps/final_v6/*.csv")
          if os.path.getmtime(f) > datetime.datetime(2026, 9, 5, 23, 6).timestamp() and "engagement" not in f]
    out = []
    for f in fs:
        lines = [l for l in open(f, encoding="utf-8").read().splitlines() if not l.startswith("#")]
        rd = list(csv.reader(lines)); hdr = rd[0]
        try:
            A = np.array([[float(x) for x in r] for r in rd[1:]])
        except Exception:
            continue
        if len(A) < 25:
            continue
        ci = {h: i for i, h in enumerate(hdr)}
        alt = A[:, ci['own_alt']]
        ic = int(np.argmin(alt))              # 바닥 관통 지점
        k = max(0, ic - int(lead_s / 0.1))    # lead_s 초 전
        dn = A[k + 1, ci['own_n']] - A[k, ci['own_n']] if k + 1 < len(A) else 0.0
        de = A[k + 1, ci['own_e']] - A[k, ci['own_e']] if k + 1 < len(A) else 0.0
        da = A[k + 1, ci['own_alt']] - A[k, ci['own_alt']] if k + 1 < len(A) else 0.0
        V = math.sqrt(dn * dn + de * de + da * da) / 0.1
        if V < 20 or alt[k] < FLOOR:
            continue
        yaw = math.degrees(math.atan2(de, dn))
        spawn = [float(A[k, ci['own_n']]), float(A[k, ci['own_e']]), -float(alt[k]),
                 float(A[k, ci['roll']]), float(A[k, ci['pitch']]), yaw, float(V)]
        intent = [float(A[k, ci['a_roll']]), float(A[k, ci['a_pitch']]),
                  float(A[k, ci['a_yaw']]), float(A[k, ci['a_thr']])]
        out.append((os.path.basename(f)[6:], spawn, intent, float(alt[k])))
    return out


def run(spawn, intent, guard_on, max_steps=400):
    env = make_env(guard_on, spawn)
    try:
        env.reset(seed=1234)
        min_alt = 1e9
        prev = None
        for n in range(max_steps):
            s = env._sim.get_state()
            alt, roll, pit = float(s[StateIndex.ALT]), float(s[_ROLL]), float(s[_PITCH])
            vz = 0.0 if prev is None else (alt - prev) / 0.1
            prev = alt
            if n >= 1:
                min_alt = min(min_alt, alt)
            # 실측 조종 의도를 계속 준다(가드가 켜지면 덧씌운다)
            _, _, term, trunc, info = env.step(np.asarray(intent, dtype=np.float32))
            if term or trunc:
                return "ownship altitude" in str(info.get("end_condition", "")), min_alt
            if n > 12 and vz > 2 and alt > min_alt + 120:
                return False, min_alt
        return False, min_alt
    finally:
        env.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lead", type=float, default=2.0, help="관통 몇 초 전 상태를 앉힐지")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--out", default="artifacts/eval_visual/crash_replay.txt")
    a = ap.parse_args()
    cases = load_states(a.lead)[:a.limit]
    lines = []

    def out(s=""):
        print(s, flush=True); lines.append(s)

    out("실측 추락 상태 재생 — 관통 %.1f초 전 상태를 JSBSim 에 앉히고 실측 조종 지속. 가드만 바꾼다." % a.lead)
    out("표본 %d판 (재기동 후 실제 crash dump)" % len(cases))
    off_c = grd_c = 0
    saved = 0
    out("\n%-22s %7s %8s | %8s %8s | %s" % ("dump", "앉힌고도", "V", "가드off", "새가드", "판정"))
    out("-" * 74)
    for name, spawn, intent, alt0 in cases:
        c_off, m_off = run(spawn, intent, False)
        c_grd, m_grd = run(spawn, intent, True)
        off_c += int(c_off); grd_c += int(c_grd)
        if c_off and not c_grd:
            saved += 1
        verdict = ""
        if c_off and not c_grd:
            verdict = "가드가 살림 ★"
        elif c_off and c_grd:
            verdict = "둘다 추락(물리한계)"
        elif not c_off and not c_grd:
            verdict = "원래 회복가능"
        else:
            verdict = "가드가 악화 ✗"
        out("%-22s %7.0f %8.0f | %8s %8s | %s"
            % (name[:20], alt0, spawn[6], "추락" if c_off else "생존", "추락" if c_grd else "생존", verdict))
    out("\n가드 off 추락 %d/%d  ->  새 가드 추락 %d/%d   (가드가 구한 판 %d · 악화 %d)"
        % (off_c, len(cases), grd_c, len(cases), saved,
           sum(1 for _ in [] )))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    out("-> %s" % a.out)


if __name__ == "__main__":
    main()
