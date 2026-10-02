# -*- coding: utf-8 -*-
"""[측정 — 학습 아님] 상대별 전적을 두 출처로 나란히 본다.

  전체 로그  opp_log/opp_<pid>.csv — 판마다 한 줄. 표본이 크다(수천 판).
  리플레이   engagement_replays/replay_index.csv — 25 iter 마다 6판만. 궤적이 남는다.

둘을 같이 내는 이유: 리플레이는 표본이 작아 상대별로는 5할처럼 보이는 상대가
전체 로그에서는 승률 0.18 인 경우가 있다(v2r8_10400 실측). 반대로 리플레이는
"왜 졌는지"를 궤적으로 볼 수 있는 유일한 출처다. 숫자는 로그, 원인은 리플레이.

주의: iter 0 행은 체크포인트 복원 시 딸려온 누적값이라 뺀다(실측 64,076판).

사용: python student/tools/opp_record.py [--tag final_v7] [--min-iter 1]
"""
import argparse
import collections
import csv
import glob
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

WIN_K = ("격추", "적추락", "판정승", "승")
LOSS_K = ("피격추", "추락", "판정패", "패")


def classify(outcome, end_condition, own_hp=None, tgt_hp=None):
    """env 가 찍은 outcome 을 **먼저** 믿는다.

    [2026-09-06 사용자 지적 "무승부가 없다는건 개구라야"] 앞선 판은 end_condition 만 보고
    갈라서, env 가 draw 로 찍은 동시격추 1,498판(18.4%)을 전부 피격추로 세고 있었다.
    동시격추는 종료조건이 "ownship destroyed" 로 같게 남기 때문이다.
    실측 outcome 분포: win 50.6 / loss 26.2 / draw 18.4 / judge_win 1.5 / crash 1.4
                      / judge_loss 1.3 / timeout 0.6 (%)"""
    o = (outcome or "").lower()
    e = (end_condition or "").lower()
    if o == "draw":
        return "무"
    if o == "timeout":
        return "무"
    if o == "crash":
        return "추락"
    if o == "judge_win":
        return "판정승"
    if o == "judge_loss":
        return "판정패"
    if o == "win" or ("target" in e and ("destroy" in e or "hp" in e)):
        if "target altitude" in e:
            return "적추락"
        if "destroy" in e or "hp" in e:
            return "격추"
        return "승"
    if "target altitude" in e:
        return "적추락"
    if o == "judge_win":
        return "판정승"
    if o == "loss" or ("ownship" in e and ("destroy" in e or "hp" in e)):
        if "ownship altitude" in e:
            return "추락"
        return "피격추"
    if "ownship altitude" in e:
        return "추락"
    if o == "judge_loss":
        return "판정패"
    if own_hp is not None and tgt_hp is not None:
        if own_hp > tgt_hp + 1e-6:
            return "판정승"
        if tgt_hp > own_hp + 1e-6:
            return "판정패"
    return "무"


def from_log(tag, min_iter):
    tab = collections.defaultdict(collections.Counter)
    n = 0
    for f in glob.glob(os.path.join("artifacts", "curriculum", "AeroFlyer", tag,
                                    "opp_log", "opp_*.csv")):
        for line in io.open(f, encoding="utf-8", errors="ignore"):
            p = line.rstrip("\n").split(",")
            if len(p) < 4:
                continue
            name = p[1].replace("frozen_", "")
            oh = float(p[4]) if len(p) > 4 and p[4] else None
            th = float(p[5]) if len(p) > 5 and p[5] else None
            tab[name][classify(p[2], p[3], oh, th)] += 1
            n += 1
    return tab, n


def from_replays(tag, min_iter):
    base = os.path.join("artifacts", "replays", "AeroFlyer_" + tag, "engagement_replays")
    idx = os.path.join(base, "replay_index.csv")
    tab = collections.defaultdict(collections.Counter)
    n = 0
    if not os.path.exists(idx):
        return tab, n
    for r in csv.DictReader(io.open(idx, encoding="utf-8")):
        try:
            if int(float(r["iteration"])) < min_iter:
                continue
        except Exception:
            continue
        s = None
        for c in (r.get("summary_json", ""), os.path.join(base, r.get("summary_json", ""))):
            if c and os.path.exists(c):
                s = json.load(io.open(c, encoding="utf-8")); break
        if not s:
            continue
        name = str(s.get("opponent", "?")).replace("frozen_", "")
        try:
            oh, th = float(r["ownship_health"]), float(r["target_health"])
        except Exception:
            oh = th = None
        tab[name][classify(r.get("outcome"), r.get("end_condition"), oh, th)] += 1
        n += 1
    return tab, n


def wl(c):
    return sum(c[k] for k in WIN_K), sum(c[k] for k in LOSS_K), c["무"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=os.environ.get("FINAL_SP_TAG", "final_v7"))
    ap.add_argument("--min-iter", type=int, default=1)
    a = ap.parse_args()
    lg, nlg = from_log(a.tag, a.min_iter)
    rp, nrp = from_replays(a.tag, a.min_iter)
    names = sorted(set(lg) | set(rp),
                   key=lambda k: (wl(lg[k])[0] / max(sum(lg[k].values()), 1)) if k in lg else 9)
    print("%s · 전체 로그 %d판 · 리플레이 %d판 (iter %d~)\n" % (a.tag, nlg, nrp, a.min_iter))
    print("%-28s | %7s %7s %7s | %s"
          % ("상대", "승률", "패율", "무승부율", "리플레이 전적"))
    print("-" * 76)
    for k in names:
        lw, ll, ld = wl(lg[k]) if k in lg else (0, 0, 0)
        lt = lw + ll + ld
        rw, rl, rd = wl(rp[k]) if k in rp else (0, 0, 0)
        rt = rw + rl + rd
        lr = lw / lt if lt else None
        rr = rw / rt if rt else None
        gap = ("%+.2f" % (rr - lr)) if (lr is not None and rr is not None and rt >= 1) else "-"
        f = lambda v, t: ("%.2f" % (v / t)) if t else "  -  "
        rep = ("%d승 %d패 %d무" % (rw, rl, rd)) if rt else "-"
        print("%-28s | %7s %7s %7s | %s"
              % (k[:28], f(lw, lt), f(ll, lt), f(ld, lt), rep))
    tl = collections.Counter()
    for c in lg.values():
        tl.update(c)
    tr = collections.Counter()
    for c in rp.values():
        tr.update(c)
    lw, ll, ld = wl(tl); rw, rl, rd = wl(tr)
    print("-" * 76)
    lt = lw + ll + ld; rt = rw + rl + rd
    f = lambda v, t: ("%.2f" % (v / t)) if t else "  -  "
    print("%-28s | %7s %7s %7s | %d승 %d패 %d무"
          % ("합계", f(lw, lt), f(ll, lt), f(ld, lt), rw, rl, rd))
    print("\n괴리 = 리플레이 승률 − 로그 승률. 리플레이는 25 iter 마다 6판이라 표본이 작다.")
    print("숫자는 로그를 믿고, 리플레이는 궤적으로 원인을 볼 때 쓴다.")


if __name__ == "__main__":
    main()
