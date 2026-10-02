# -*- coding: utf-8 -*-
"""리플레이 판정 (학습 아님, 시뮬레이션 안 돌림): 학습이 25 iter 마다 저장하는 교전 리플레이(summary.json + Tacview CSV)만 읽어
상대별(고정 상대 = v2 또는 우리 번들 / self 사본) 결과를 센다. 사용자 결정(2026-08-29): 별도 판정 실행 대신 리플레이를 본다.
사용: python student/tools/replay_judge.py [--tag final_sp2] [--since 2400] [--block 500] [--opp fixed|self|all] [--plot]
결과 분류(아군 시점): 격추승 / 적추락승 / 동시격추 / 격추패 / 추락(우리) / 종료우위(HP) / 종료열위 / 종료동률
지표: 시간(s) · 스폰고도 · 최소거리 · 교차 횟수(거리 극소 < 914 m) · 152 m 안쪽 교차 · 사거리(152~914) 체류 % · 딜 / 피딜
"""
import argparse, csv, glob, json, math, os, re, sys
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
R_MIN, R_MAX = 152.4, 914.4


def read_csv(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    g = lambda k: np.array([float(r[k]) for r in rows])
    return {"t": g("Time"), "lon": g("Longitude"), "lat": g("Latitude"), "alt": g("Altitude"), "hp": g("Health")}


def distance(a, b):
    n = min(len(a["t"]), len(b["t"]))
    lat0 = math.radians(a["lat"][0])
    dx = (b["lon"][:n] - a["lon"][:n]) * 111320.0 * math.cos(lat0)
    dy = (b["lat"][:n] - a["lat"][:n]) * 110540.0
    dz = b["alt"][:n] - a["alt"][:n]
    return np.sqrt(dx * dx + dy * dy + dz * dz)


def passes(d):
    """거리 극소점(양옆보다 작고 914 m 미만). 같은 교차가 여러 극소로 쪼개지지 않게 1초(10샘플) 안의 극소는 하나로 센다."""
    idx = [i for i in range(1, len(d) - 1) if d[i] < R_MAX and d[i] <= d[i - 1] and d[i] < d[i + 1]]
    out = []
    for i in idx:
        if out and i - out[-1] < 10:
            if d[i] < d[out[-1]]: out[-1] = i
        else: out.append(i)
    return out


def classify(s, ec, own_hp, tgt_hp):
    if "target altitude" in ec: return "적추락승"   # env 는 win 으로 집계(crash_rate 는 우리 추락만) — 여기서 분리
    if "altitude" in ec or "crash" in ec: return "추락"
    if own_hp <= 0 and tgt_hp <= 0: return "동시격추"
    if tgt_hp <= 0 < own_hp: return "격추승"
    if own_hp <= 0 < tgt_hp: return "격추패"
    if abs(own_hp - tgt_hp) < 1e-6: return "종료동률"
    return "종료우위" if own_hp > tgt_hp else "종료열위"


def opp_kind(name):
    """self = 자기 사본(snap_*), 그 외는 고정 상대(v2 = ladder5220, 우리 번들 = final_sp3_iter0400 등) -> "fixed"."""
    return "self" if "snap_" in name else "fixed"


def analyze(ep_dir):
    sj = glob.glob(os.path.join(ep_dir, "*summary.json"))
    own = glob.glob(os.path.join(ep_dir, "*ownship*.csv")); tgt = glob.glob(os.path.join(ep_dir, "*target*.csv"))
    if not (sj and own and tgt): return None
    s = json.load(open(sj[0], encoding="utf-8"))
    a, b = read_csv(own[0]), read_csv(tgt[0])
    d = distance(a, b); p = passes(d)
    inrng = (d >= R_MIN) & (d <= R_MAX)
    m = re.search(r"iter_(\d+)", ep_dir)
    return {
        "iter": int(m.group(1)) if m else -1, "ep": os.path.basename(ep_dir), "opp": s.get("opponent", "?"),
        "kind": opp_kind(s.get("opponent", "?")), "ec": s.get("end_condition", ""),
        "own_hp": float(s.get("ownship_health", 0)), "tgt_hp": float(s.get("target_health", 0)),
        "cls": classify(s, s.get("end_condition", ""), float(s.get("ownship_health", 0)), float(s.get("target_health", 0))),
        "dur": float(a["t"][-1]), "alt0": float(a["alt"][0]), "min_alt": float(a["alt"].min()),
        "min_d": float(d.min()), "n_pass": len(p), "n_inside": sum(1 for i in p if d[i] < R_MIN),
        "in_range": float(inrng.mean()), "dealt": 1.0 - float(b["hp"][-1]), "taken": 1.0 - float(a["hp"][-1]),
        "d": d, "alt": a["alt"], "oalt": b["alt"], "t": a["t"],
    }


CLS = ("격추승", "적추락승", "동시격추", "격추패", "추락", "종료우위", "종료열위", "종료동률")
ASCII = {"격추승": "KILL", "적추락승": "OPPCRASH", "동시격추": "MUTUAL", "격추패": "KILLED", "추락": "CRASH", "종료우위": "TO+", "종료열위": "TO-", "종료동률": "TO="}


def table(rows, title):
    c = {k: sum(1 for r in rows if r["cls"] == k) for k in CLS}
    n = len(rows)
    if not n: print(f"{title}: 0판"); return
    dur = np.mean([r["dur"] for r in rows]); dealt = np.mean([r["dealt"] for r in rows]); taken = np.mean([r["taken"] for r in rows])
    ins = np.mean([r["n_inside"] for r in rows])
    print(f"{title}: {n}판  " + "  ".join(f"{k} {c[k]}" for k in CLS) + f"  | 평균 {dur:.0f}s  딜 {dealt:.2f} 피딜 {taken:.2f}  152m안쪽교차 {ins:.1f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=os.environ.get("FINAL_SP_TAG", "final_sp2"))
    ap.add_argument("--since", type=int, default=0, help="이 iter 이상만"); ap.add_argument("--until", type=int, default=10**9)
    ap.add_argument("--block", type=int, default=500, help="iter 구간별 집계 폭")
    ap.add_argument("--opp", default="all", choices=["all", "fixed", "self"])
    ap.add_argument("--plot", action="store_true", help="v2 상대 판의 거리·고도 곡선 그림 저장")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = f"artifacts/replays/AeroFlyer_{a.tag}/engagement_replays"
    eps = sorted(glob.glob(os.path.join(root, "stage_*_iter_*", "episode_*")))
    rows = [r for r in (analyze(e) for e in eps) if r and a.since <= r["iter"] <= a.until]
    if a.opp != "all": rows = [r for r in rows if r["kind"] == a.opp]
    print(f"tag={a.tag}  리플레이 {len(rows)}판 (iter {a.since}~)  상대: " + ", ".join(f"{k} {sum(1 for r in rows if r['kind']==k)}" for k in sorted({r['kind'] for r in rows})))
    fixed_names = sorted({r["opp"] for r in rows if r["kind"] == "fixed"})
    print("\n[구간별 · 고정 상대 " + ", ".join(fixed_names) + "]")
    v2 = [r for r in rows if r["kind"] == "fixed"]
    if v2:
        lo = (min(r["iter"] for r in v2) // a.block) * a.block; hi = max(r["iter"] for r in v2)
        for b0 in range(lo, hi + 1, a.block):
            table([r for r in v2 if b0 <= r["iter"] < b0 + a.block], f"  iter {b0:5d}~{b0+a.block-1:5d}")
    table(v2, "  고정상대 전체"); table([r for r in rows if r["kind"] == "self"], "  self 전체")
    if len(fixed_names) > 1:   # [2026-08-29] 혼합 풀: 상대 이름별 집계 (수렴 판단은 상대별로)
        print("\n[상대별 · 전체 구간]")
        for nm in fixed_names: table([r for r in v2 if r["opp"] == nm], f"  {nm.replace('frozen_', ''):28s}")
    print("\n[고정 상대 판별]  iter  ep   결과     시간  스폰고도 최저고도 최소거리 교차 152m안쪽 사거리%  딜   피딜")
    for r in v2:
        print(f"  {r['iter']:5d} {r['ep'][-2:]}  {r['cls']:5s} {r['dur']:6.0f}s {r['alt0']:7.0f} {r['min_alt']:7.0f} {r['min_d']:7.0f} {r['n_pass']:4d} {r['n_inside']:6d} {100*r['in_range']:6.0f}% {r['dealt']:4.2f} {r['taken']:4.2f}")
    if a.plot and v2:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        k = len(v2); cols = 6; nr = (k + cols - 1) // cols
        fig, axes = plt.subplots(nr, cols, figsize=(3.0 * cols, 2.6 * nr), squeeze=False)
        for j, r in enumerate(v2):
            ax = axes[j // cols][j % cols]; n = len(r["d"])
            ax.plot(r["t"][:n], r["d"], "g", lw=0.9); ax.axhline(R_MAX, ls="--", lw=0.6, color="gray"); ax.axhline(R_MIN, ls=":", lw=0.6, color="red")
            ax2 = ax.twinx(); ax2.plot(r["t"], r["alt"], "b", lw=0.6, alpha=0.6); ax2.set_ylim(0, 6000); ax2.tick_params(labelsize=5)
            ax.set_ylim(0, 3000); ax.set_title(f"it{r['iter']} {ASCII[r['cls']]} {r['dur']:.0f}s alt0 {r['alt0']:.0f}\nmin {r['min_d']:.0f}m pass {r['n_pass']}/{r['n_inside']}in  deal {r['dealt']:.2f} take {r['taken']:.2f}", fontsize=6); ax.tick_params(labelsize=5)
        for j in range(k, nr * cols): axes[j // cols][j % cols].axis("off")
        plt.suptitle(f"replay_judge {a.tag} vs {','.join(fixed_names)} (green dist m / blue alt m; dashed 914 max, dotted 152 min range)", fontsize=8)
        out = a.out or f"artifacts/eval_visual/replay_judge_{a.tag}.png"; os.makedirs(os.path.dirname(out), exist_ok=True)
        plt.tight_layout(); plt.savefig(out, dpi=95); print("->", out)


if __name__ == "__main__":
    main()
