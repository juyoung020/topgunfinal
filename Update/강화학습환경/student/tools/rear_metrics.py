# -*- coding: utf-8 -*-
"""[측정 — 학습 아님] 후방 포지션 3대 지표. [MOD-POSPOT] 효과를 보는 기준선.

사용자 목표: "후방을 선점하고 안 놔주고 계속 패면 다 이긴다."
그 셋을 그대로 잰다.

  선점  후방 반구 점유율      적ATA > 90도 인 스텝 비율
  유지  연속 유지 시간        적ATA > 150도 & 거리 < 900 m 연속 구간 길이
  놓침  추월 횟수             유지 중이던 상태가 적ATA < 90 로 깨진 횟수 (판당)

옆구리(거리프리셋) 스폰만 센다 — 꼬리잡기는 시작 자리가 결과를 정해 비교가 안 된다.
--split 으로 iteration 구간을 갈라 전후 비교한다.

사용: python student/tools/rear_metrics.py [--tag final_v7] [--split 483]
"""
import argparse
import csv
import glob
import io
import math
import os
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
D2R = math.pi / 180.0
R = 6378137.0


def load(p):
    out = []
    for r in csv.DictReader(io.open(p, encoding="utf-8")):
        try:
            out.append((float(r["Longitude"]), float(r["Latitude"]), float(r["Altitude"]),
                        float(r["Yaw (deg)"]), float(r["Pitch (deg)"])))
        except Exception:
            pass
    return out


def geo(me, foe):
    e = (foe[0] - me[0]) * D2R * R * math.cos(me[1] * D2R)
    n = (foe[1] - me[1]) * D2R * R
    u = foe[2] - me[2]
    d = math.sqrt(e * e + n * n + u * u)
    cp = math.cos(me[4] * D2R)
    c = (e * math.sin(me[3] * D2R) * cp + n * math.cos(me[3] * D2R) * cp
         + u * math.sin(me[4] * D2R)) / max(d, 1e-6)
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))), d


def episodes(tag):
    base = "artifacts/replays/AeroFlyer_%s/engagement_replays" % tag
    for d in sorted(glob.glob(base + "/stage_35_iter_*/episode_*")):
        m = os.path.basename(os.path.dirname(d))
        try:
            it = int(m.split("_")[-1])
        except Exception:
            continue
        ow = glob.glob(d + "/*ownship*.csv"); tg = glob.glob(d + "/*target*.csv")
        if not ow or not tg:
            continue
        try:
            o, t = load(ow[0]), load(tg[0])
        except Exception:
            continue
        n = min(len(o), len(t))
        if n < 40:
            continue
        dy = abs(((o[0][3] - t[0][3]) + 180.0) % 360.0 - 180.0)
        if dy < 45.0:
            continue                       # 꼬리잡기 스폰 제외
        yield it, o, t, n


def analyse(tag, split):
    buckets = {"전": [], "후": []}
    for it, o, t, n in episodes(tag):
        rear = 0; hold_runs = []; run = 0.0; overshoot = 0; holding = False
        for i in range(n):
            fa, d = geo(t[i], o[i])
            if fa > 90.0:
                rear += 1
            good = (fa > 150.0 and d < 900.0)
            if good:
                run += 0.1; holding = True
            else:
                if run > 0:
                    hold_runs.append(run)
                if holding and fa < 90.0:
                    overshoot += 1          # 유지하다 정측 앞으로 넘어갔다
                    holding = False
                run = 0.0
        if run > 0:
            hold_runs.append(run)
        buckets["후" if (split and it >= split) else "전"].append(
            (rear / n, st.median(hold_runs) if hold_runs else 0.0,
             max(hold_runs) if hold_runs else 0.0, overshoot))
    return buckets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=os.environ.get("FINAL_SP_TAG", "final_v7"))
    ap.add_argument("--split", type=int, default=0, help="이 iteration 이상을 '후'로 가른다")
    a = ap.parse_args()
    b = analyse(a.tag, a.split)
    print("%s · 옆구리 스폰만 (꼬리잡기 제외)\n" % a.tag)
    print("%-6s %5s %9s %9s %9s %9s" % ("구간", "판", "후방점유", "유지중앙", "유지최장", "추월/판"))
    print("-" * 56)
    for k in ("전", "후"):
        v = b[k]
        if not v:
            continue
        print("%-6s %5d %8.1f%% %8.1fs %8.1fs %9.2f"
              % (k, len(v), 100 * st.median(x[0] for x in v),
                 st.median(x[1] for x in v), st.median(x[2] for x in v),
                 st.mean(x[3] for x in v)))
    print("\n선점 = 적ATA>90 스텝 비율 · 유지 = 적ATA>150 & 900m 안 연속 구간")
    print("추월 = 유지하다 적ATA<90 으로 깨진 횟수(판당)")


if __name__ == "__main__":
    main()
