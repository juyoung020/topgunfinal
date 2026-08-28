# -*- coding: utf-8 -*-
"""[측정] 학습 상태 확인 — 학습 곡선 + 기동 궤적 두 장. 학습 아님, 측정임.

═══════════════════════════════════════════════════════════════════════════
왜 대전 판정을 버렸나 (2026-08-17 사용자 결정)
═══════════════════════════════════════════════════════════════════════════
판정 하네스가 **아군 슬롯에 앉기만 하면 +0.937 을 거저 준다.** 역할 교대로
측정한 값이다 (snap_0180 vs ladder_iter5220, 5쌍 정·역):

    우리가 아군 슬롯      +1.009
    챔프가 아군 슬롯      +0.865
    역할 교대 평균(진짜)  +0.072      <- 실제 실력차
    하네스 편향          +0.937      <- 실력차의 13배

같은 정책끼리 붙여도 아군이 5승 0패(마진 +0.988)가 나온다. 즉 "실력차 0" 의
기준선이 0 이 아니라 +0.99 다. 그래서 그동안 보고한 "32승 0패", "+1.004",
"5승 0패" 는 93%가 자리값이고 7%만 실력이었다. 한 방향 판정은 세대 비교조차
잡음에 묻힌다. 원인은 못 찾았다(배제 목록은 변경사항.md 2026-08-17 참조).

역할 교대로 상쇄할 수는 있지만 비용이 2배이고, 무엇보다 **판정 숫자로는 보이지
않던 문제가 궤적을 그리자 1분 만에 드러났다** — 마진 +1.0 · 5승 0패 로는
"잘하고 있다" 로만 읽혔는데, 실제 기동은 스침 후 3~4 km 이탈의 반복이었고
WEZ 체류는 판당 6~9% 뿐이었다.

═══════════════════════════════════════════════════════════════════════════
그래서 지금 쓰는 판정: 이 파일이 뽑는 두 장
═══════════════════════════════════════════════════════════════════════════
1. **학습 곡선 개형** (`curves.png`)
   보상 / 딜 / WEZ 체류 / 교전거리 / 에피소드 길이 / 추락률, 15-iter 이동평균.
   실행 여러 개를 겹쳐 그린다. 마지막 재기동 구간만 자른다(iter 되감기 기준).
   *한계*: 상대가 자기 자신이라 **절대 실력은 못 말한다.** 방향만 본다.

2. **기동 궤적** (`traj.png`)
   최신 리플레이 3판의 평면 궤적 + 거리·ATA 시계열.
   사격밴드(152~914 m)와 1도 선을 같이 그려 WEZ 진입 순간이 눈에 보이게 한다.
   *여기서 봐야 할 것*: 거리 곡선이 큰 사인파면 "스침 후 이탈" 이고,
   낮게 눌려 있으면 근접전이다. 평균 교전거리 숫자만 보면 이 둘이 구분 안 된다.

읽는 규칙 (지키지 않으면 예전 실수를 반복한다)
  * 곡선이 좋아졌다고 실력이 늘었다고 말하지 말 것 — 미러 지표다.
  * 교전거리 평균이 줄었다고 근접전이라고 말하지 말 것 — 궤적을 봐야 한다.
  * 숫자와 그림이 어긋나면 **그림을 믿는다**(2026-08-16 뷰어 피치 부호 버그 전례).

사용법
    python student/tools/eval_visual.py [--tag final_sp] [--out <디렉터리>]
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import json
import math
import os
import sys
from pathlib import Path

# 콘솔이 cp949 라 한글 출력이 깨진다(실측: "곡선 ->" 가 "? ->" 로).
# 파이프/리다이렉트로 넘길 때도 같은 문제라 stdout 을 UTF-8 로 감싼다.
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Malgun Gothic"   # 한글 라벨
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

CURR = ROOT / "artifacts" / "curriculum" / "AeroFlyer"
REPL = ROOT / "artifacts" / "replays"
EARTH_R = 6371000.0
PANELS = [("reward_mean", "보상"), ("ep_reward_damage", "딜"),
          ("ep_wez_steps", "WEZ 체류"), ("ep_mean_distance", "교전거리(m)"),
          ("ep_len_mean", "에피소드 길이"), ("crash_rate", "추락률")]


def _last_run(rows):
    """iter 가 되감기면 새 실행 — 마지막 구간만 남긴다."""
    start, prev = 0, -1
    for i, r in enumerate(rows):
        try:
            it = int(r["iter_in_stage"])
        except (KeyError, ValueError):
            continue
        if it < prev:
            start = i
        prev = it
    return rows[start:]


def curves(tags, out: Path):
    fig, axes = plt.subplots(2, 3, figsize=(15, 7))
    for tag in tags:
        p = CURR / tag / "training_log.csv"
        if not p.exists():
            print(f"  건너뜀(없음): {p}")
            continue
        rows = _last_run(list(csv.DictReader(open(p, encoding="utf-8"))))
        for ax, (k, name) in zip(axes.ravel(), PANELS):
            y = []
            for r in rows:
                try:
                    y.append(float(r[k]))
                except (KeyError, ValueError, TypeError):
                    y.append(np.nan)
            y = np.asarray(y, dtype=float)
            if np.all(np.isnan(y)):
                continue
            ys = np.convolve(y, np.ones(15) / 15, mode="valid") if len(y) >= 15 else y
            ax.plot(np.arange(len(ys)), ys, lw=1.4, label=tag)
            ax.set_title(name, fontsize=11)
            ax.grid(alpha=0.3)
    for ax in axes.ravel():
        ax.set_xlabel("iteration", fontsize=8)
        ax.legend(fontsize=8)
    plt.suptitle("학습 곡선 (15-iter 이동평균) — 미러 지표이므로 **방향만** 본다",
                 fontsize=13)
    plt.tight_layout()
    f = out / "curves.png"
    plt.savefig(f, dpi=110); plt.close()
    return f


def traj(tag, out: Path, episodes: int = 3):
    import student.my_observation as MO
    from GeoMathUtil import GeometryInfo
    d = REPL / f"AeroFlyer_{tag}" / "engagement_replays"
    its = sorted([x for x in os.listdir(d) if x.startswith("stage_")],
                 key=lambda s: int(s.split("_")[-1]))
    if not its:
        print("  리플레이 없음"); return None
    it = its[-1]
    eps = sorted(os.listdir(d / it))[:episodes]
    fig, axes = plt.subplots(2, len(eps), figsize=(5.4 * len(eps), 8), squeeze=False)
    for col, ep in enumerate(eps):
        o = glob.glob(str(d / it / ep / "*ownship*.csv"))
        t = glob.glob(str(d / it / ep / "*target*.csv"))
        s = glob.glob(str(d / it / ep / "*summary.json"))
        if not o or not t:
            continue
        ro = list(csv.DictReader(open(o[0], encoding="utf-8")))
        rt = list(csv.DictReader(open(t[0], encoding="utf-8")))
        n = min(len(ro), len(rt))
        la0 = math.radians(float(ro[0]["Latitude"]))
        lo0 = math.radians(float(ro[0]["Longitude"]))

        def xy(r):
            la = math.radians(float(r["Latitude"]))
            lo = math.radians(float(r["Longitude"]))
            return ((la - la0) * EARTH_R, (lo - lo0) * EARTH_R * math.cos(la0))

        ox, oy = zip(*[xy(r) for r in ro[:n]])
        tx, ty = zip(*[xy(r) for r in rt[:n]])
        oa = [float(r["Altitude"]) for r in ro[:n]]
        ta = [float(r["Altitude"]) for r in rt[:n]]
        dist, ata = [], []
        for i in range(n):
            so, stt = np.zeros(51), np.zeros(51)
            so[0], so[1], so[2] = ox[i], oy[i], -oa[i]
            stt[0], stt[1], stt[2] = tx[i], ty[i], -ta[i]
            for k, key in ((3, "Roll (deg)"), (4, "Pitch (deg)"), (5, "Yaw (deg)")):
                so[k] = float(ro[i][key]); stt[k] = float(rt[i][key])
            dist.append(math.dist((ox[i], oy[i], oa[i]), (tx[i], ty[i], ta[i])))
            ata.append(MO._ata_deg(so, stt))
        res = ""
        if s:
            try:
                j = json.load(open(s[0], encoding="utf-8"))
                res = f"{j.get('end_condition','')} / 적HP {float(j.get('target_health',0)):.2f}"
            except Exception:
                pass
        a = axes[0][col]
        a.plot(oy, ox, lw=1.2, color="tab:blue", label="아군")
        a.plot(ty, tx, lw=1.2, color="tab:red", label="적기")
        a.plot(oy[0], ox[0], "o", color="tab:blue")
        a.plot(ty[0], tx[0], "o", color="tab:red")
        a.set_title(f"{ep} 평면궤적 {n}스텝\n{res}", fontsize=9)
        a.set_aspect("equal"); a.grid(alpha=0.3); a.legend(fontsize=7)
        a.set_xlabel("East (m)", fontsize=7); a.set_ylabel("North (m)", fontsize=7)
        b = axes[1][col]
        b.plot(dist, color="tab:green", lw=1.0)
        b.axhline(914.4, ls="--", c="gray", lw=0.8)
        b.axhline(152.4, ls="--", c="gray", lw=0.8)
        b.set_ylabel("거리(m)", fontsize=8); b.grid(alpha=0.3)
        b.set_xlabel("스텝", fontsize=7)
        b2 = b.twinx()
        b2.plot(ata, color="tab:orange", lw=0.9, alpha=0.85)
        b2.axhline(1.0, ls=":", c="red", lw=0.9)
        b2.set_ylim(0, 60); b2.set_ylabel("ATA(deg)", fontsize=8)
        wez = sum(1 for i in range(n) if 152.4 <= dist[i] <= 914.4 and ata[i] <= 1.0)
        b.set_title(f"WEZ 안 {wez}스텝 ({wez/max(n,1)*100:.0f}%)  "
                    f"회색=152~914m, 빨강점선=1도", fontsize=8)
    plt.suptitle(f"기동 궤적 — {tag} {it}   거리곡선이 큰 사인파면 '스침 후 이탈'",
                 fontsize=13)
    plt.tight_layout()
    f = out / "traj.png"
    plt.savefig(f, dpi=105); plt.close()
    return f


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", default=__import__("os").environ.get("FINAL_SP_TAG", "final_sp"))
    ap.add_argument("--compare", nargs="*", default=[],
                    help="곡선에 같이 겹쳐 그릴 예전 태그")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = Path(a.out) if a.out else (ROOT / "artifacts" / "eval_visual")
    out.mkdir(parents=True, exist_ok=True)
    print("곡선 ->", curves(list(a.compare) + [a.tag], out))
    print("궤적 ->", traj(a.tag, out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
