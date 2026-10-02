# -*- coding: utf-8 -*-
"""실서버 판의 궤적·교전 기하 (학습 아님, 측정): 뷰어가 남기는 60 Hz 서버 CSV(M_D_H_M_{0,1}.csv: 위경도·고도·자세)로
거리·ATA·AA·WEZ(152.4~914.4 m, 페이즈 각 1°/2°/3°) 를 계산해 "어디서부터 쏘기 시작했나(첫 WEZ 거리)" 를 본다.
사용: python tools/server_traj.py --tag i7200_vs_cutoff [--tag ...] | --all-7200   (--csv0/--csv1 로 직접 지정 가능)
판 ↔ CSV 매칭: 큐 로그의 "started HH:MM:SS" 와 CSV 이름의 시각(M_D_H_M) 으로. 출력: artifacts/eval_visual/traj_<Tag>.png + 표.
yaw 규약은 추측하지 않고 위치 미분으로 진행방위를 재서 맞는 쪽(북기준 시계방향 / 동기준 반시계)을 고른다.
"""
import argparse, csv, glob, math, os, re, sys
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
LOGDIR = r"C:\topgunfinal\BattleServer_V1.2_VeryLow\DogFightViewer\Binaries\Win64\Log"
R_MIN, R_MAX = 152.4, 914.4
# 8/30 실서버 화면 판정 (BattleServer_V1.2_VeryLow/CLAUDE.md 표와 동일). 결과는 7200 시점: W 승 / D 무 / L 패
RESULTS = {
 "iter7200_vs_cutoff": ("W", 60.7, 0), "cutoff_vs_iter7200": ("W", 0, 55.6),
 "i7200_vs_champion_v2r5_iter1000": ("W", 65.1, 0), "champion_v2r5_iter1000_vs_i7200": ("W", 0, 66.8),
 "i7200_vs_s52_ladder5220_beaten": ("W", 50.5, 0), "s52_ladder5220_beaten_vs_i7200": ("W", 0, 53.7),
 "i7200_vs_final_sp3_iter0400": ("W", 53.5, 0), "final_sp3_iter0400_vs_i7200": ("W", 0, 51.1),
 "i7200_vs_cand_s48_snap12241": ("L", 0, 0.05), "cand_s48_snap12241_vs_i7200": ("D", 0, 0),
 "i7200_vs_recv_aimcur_0823": ("W", 94.1, 0), "recv_aimcur_0823_vs_i7200": ("W", 0, 95.6),
 "i7200_vs_recv_aimangle_v4_0824": ("W", 94.5, 0), "recv_aimangle_v4_0824_vs_i7200": ("W", 0, 95.6),
 "i7200_vs_recv_league_v4_best60": ("W", 82.3, 0), "recv_league_v4_best60_vs_i7200": ("W", 0, 87.7),
 "i7200_vs_sub_cand_peak3100": ("D", 0, 0), "sub_cand_peak3100_vs_i7200": ("L", 1.5, 0),
 "i7200_vs_sub_cand_snap12241": ("W", 3.2, 0), "sub_cand_snap12241_vs_i7200": ("W", 0, 2.3),
 "i7200_vs_recv_snap9980": ("W", 16.7, 0), "recv_snap9980_vs_i7200": ("W", 0, 7.5),
 "i7200_vs_recv_scrim_exp025": ("D", 0, 0), "recv_scrim_exp025_vs_i7200": ("D", 0, 0),
 "i7200_vs_symmetric_iter1920": ("W", 78.9, 0), "symmetric_iter1920_vs_i7200": ("W", 0, 78.9),
}
def our_slot(tag):
    """7200 이 Blue(plane0) 면 0, Red 면 1."""
    return 0 if tag.startswith(("i7200", "iter7200")) else 1


def read_csv(p):
    keys = ("Time", "Latitude", "Longitude", "Altitude", "Roll (deg)", "Pitch (deg)", "Yaw (deg)")
    rows = [r for r in csv.DictReader(open(p, encoding="utf-8")) if all(r.get(k) not in (None, "") for k in keys)]   # 뷰어 종료 시 마지막 줄이 잘린다
    g = lambda k: np.array([float(r[k]) for r in rows])
    t = g("Time")
    if len(t) > 2 and abs(float(np.median(np.diff(t))) - 1.0) < 1e-6: t = t / 60.0   # Time 열은 60 Hz 프레임 번호(실측: 22 s 판 = 1331행) → 초로
    return {"t": t, "lat": g("Latitude"), "lon": g("Longitude"), "alt": g("Altitude"),
            "roll": g("Roll (deg)"), "pitch": g("Pitch (deg)"), "yaw": g("Yaw (deg)")}


def enu(a, lat0, lon0):
    x = (a["lon"] - lon0) * 111320.0 * math.cos(math.radians(lat0))
    y = (a["lat"] - lat0) * 110540.0
    return np.stack([x, y, a["alt"]], axis=1)


def fwd_vec(yaw_deg, pitch_deg, conv):
    y = np.radians(yaw_deg); p = np.radians(pitch_deg)
    if conv == "north_cw":     # 북 0°, 시계방향 → east=sin, north=cos
        h = np.stack([np.sin(y), np.cos(y)], axis=1)
    else:                       # east 0°, 반시계 → east=cos, north=sin
        h = np.stack([np.cos(y), np.sin(y)], axis=1)
    return np.stack([h[:, 0] * np.cos(p), h[:, 1] * np.cos(p), np.sin(p)], axis=1)


def pick_yaw_convention(P, yaw, pitch):
    """위치 미분(진행방향)과 yaw 로 만든 전방벡터의 평균 코사인이 큰 규약을 택한다 (실측으로 결정)."""
    v = np.gradient(P, axis=0); vn = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
    best = None
    for conv in ("north_cw", "east_ccw"):
        f = fwd_vec(yaw, pitch, conv); c = float(np.mean(np.sum(f * vn, axis=1)[10:]))
        if best is None or c > best[1]: best = (conv, c)
    return best


def phase_angle(t):
    return np.where(t < 100, 1.0, np.where(t < 150, 2.0, 3.0))


def phase_rate(t):
    return np.where(t < 100, 1.0, np.where(t < 150, 0.3, 0.1))


def analyze(csv0, csv1, tag, plot=True):
    a, b = read_csv(csv0), read_csv(csv1)
    n = min(len(a["t"]), len(b["t"])); t = a["t"][:n]
    lat0, lon0 = a["lat"][0], a["lon"][0]
    P0, P1 = enu(a, lat0, lon0)[:n], enu(b, lat0, lon0)[:n]
    conv, cos = pick_yaw_convention(P0, a["yaw"][:n], a["pitch"][:n])
    F0 = fwd_vec(a["yaw"][:n], a["pitch"][:n], conv); F1 = fwd_vec(b["yaw"][:n], b["pitch"][:n], conv)
    LOS = P1 - P0; d = np.linalg.norm(LOS, axis=1); u = LOS / (d[:, None] + 1e-9)
    ata0 = np.degrees(np.arccos(np.clip(np.sum(F0 * u, axis=1), -1, 1)))     # 0번기(Blue) 기수↔적 LOS
    ata1 = np.degrees(np.arccos(np.clip(np.sum(F1 * -u, axis=1), -1, 1)))    # 1번기(Red)
    aa0 = np.degrees(np.arccos(np.clip(np.sum(F1 * u, axis=1), -1, 1)))      # 적 기수↔LOS (0 = 적이 나를 등짐)
    pa = phase_angle(t); inr = (d >= R_MIN) & (d <= R_MAX)
    fire0 = inr & (ata0 <= pa); fire1 = inr & (ata1 <= pa)
    dt = float(np.median(np.diff(t))) if n > 1 else 1 / 60
    dmg0 = float(np.sum(phase_rate(t)[fire0]) * dt); dmg1 = float(np.sum(phase_rate(t)[fire1]) * dt)   # 상대에게 준 "WEZ 체류 가중 초"
    def first(f):
        i = np.argmax(f) if f.any() else None
        return (float(t[i]), float(d[i]), float(ata0[i] if f is fire0 else ata1[i])) if i is not None else None
    def bins(f):
        e = [152.4, 300, 500, 700, 914.4]; c = np.histogram(d[f], bins=e)[0]
        return " ".join(f"{e[i]:.0f}-{e[i+1]:.0f}m:{c[i]*dt:4.1f}s" for i in range(4))
    res = dict(tag=tag, n=n, dur=float(t[-1]), conv=conv, cos=cos, min_d=float(d.min()), t_min_d=float(t[np.argmin(d)]),
               first0=first(fire0), first1=first(fire1), fire0_s=float(fire0.sum() * dt), fire1_s=float(fire1.sum() * dt),
               dmg0=dmg0, dmg1=dmg1, bins0=bins(fire0), bins1=bins(fire1),
               inr_s=float(inr.sum() * dt), d_at_fire0=float(np.median(d[fire0])) if fire0.any() else None,
               d_at_fire1=float(np.median(d[fire1])) if fire1.any() else None,
               n_pass=int(np.sum((d[1:-1] < R_MAX) & (d[1:-1] <= d[:-2]) & (d[1:-1] < d[2:]))),
               _d=d, _t=t, _ata0=ata0, _ata1=ata1, _fire0=fire0, _fire1=fire1, _inr=inr, _dt=dt)
    if plot:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False
        fig, ax = plt.subplots(2, 2, figsize=(14, 10))
        A = ax[0][0]; A.plot(P0[:, 0], P0[:, 1], "b-", lw=1, label="plane0 Blue"); A.plot(P1[:, 0], P1[:, 1], "r-", lw=1, label="plane1 Red")
        A.plot(P0[fire0, 0], P0[fire0, 1], "b.", ms=6, label="Blue in WEZ (firing)"); A.plot(P1[fire1, 0], P1[fire1, 1], "r.", ms=6, label="Red in WEZ (firing)")
        A.plot(P0[0, 0], P0[0, 1], "b^", ms=10); A.plot(P1[0, 0], P1[0, 1], "r^", ms=10); A.plot(P0[-1, 0], P0[-1, 1], "bx", ms=10); A.plot(P1[-1, 0], P1[-1, 1], "rx", ms=10)
        for k in range(0, n, max(1, int(5 / dt))): A.annotate(f"{t[k]:.0f}", (P0[k, 0], P0[k, 1]), fontsize=7, color="b"); A.annotate(f"{t[k]:.0f}", (P1[k, 0], P1[k, 1]), fontsize=7, color="r")
        A.set_aspect("equal"); A.set_title(f"{tag}  top-down ENU (m)  ^ start  x end  dots = in WEZ  ★ first shot"); A.legend(fontsize=8); A.grid(alpha=.3)
        B = ax[0][1]; B.plot(t, d, "k-", lw=1); B.axhline(R_MAX, ls="--", c="gray"); B.axhline(R_MIN, ls=":", c="red")
        B.fill_between(t, 0, d, where=fire0, color="b", alpha=.25, label="Blue firing"); B.fill_between(t, 0, d, where=fire1, color="r", alpha=.25, label="Red firing")
        B.set_ylim(0, max(1500, float(d.max()) * 1.05)); B.set_xlabel("t (s)"); B.set_ylabel("distance (m)"); B.set_title("distance  (dashed 914 max / dotted 152 min)"); B.legend(fontsize=8); B.grid(alpha=.3)
        # 숫자 표기: 각 기체 첫 WEZ 진입점(t·거리·ATA), 사격 시간·중앙거리, 최소거리 — 그림만으론 "몇 m 부터 때리는지" 안 보인다는 지적(8/30)
        lines = []
        for lab, fr, fs, dm, colr in (("Blue", res["first0"], res["fire0_s"], res["d_at_fire0"], "b"), ("Red", res["first1"], res["fire1_s"], res["d_at_fire1"], "r")):
            if fr:
                B.plot(fr[0], fr[1], marker="o", ms=9, mfc="none", mec=colr, mew=2); B.annotate(f"{lab} 첫 사격 {fr[1]:.0f} m @ {fr[0]:.1f} s", (fr[0], fr[1]), xytext=(-90, 18 if lab == "Blue" else -22), textcoords="offset points", fontsize=9, color=colr, arrowprops=dict(arrowstyle="->", color=colr))
                lines.append(f"{lab}: 첫 사격 {fr[1]:.0f} m / {fr[0]:.1f} s / ATA {fr[2]:.1f}°   사격 {fs:.2f} s   사격 중앙거리 {dm:.0f} m")
            else:
                lines.append(f"{lab}: WEZ 진입 없음")
        lines.append(f"최소거리 {res['min_d']:.0f} m @ {res['t_min_d']:.1f} s   판 길이 {res['dur']:.0f} s")
        B.text(0.02, 0.97, "\n".join(lines), transform=B.transAxes, va="top", ha="left", fontsize=9, family="Malgun Gothic", bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=.9))
        for fr, colr in ((res["first0"], "b"), (res["first1"], "r")):
            if fr:
                k = int(np.argmin(np.abs(t - fr[0]))); P = P0 if colr == "b" else P1
                A.plot(P[k, 0], P[k, 1], marker="*", ms=14, color=colr); A.annotate(f"첫 사격 {fr[1]:.0f} m", (P[k, 0], P[k, 1]), xytext=(8, 8), textcoords="offset points", fontsize=9, color=colr, family="Malgun Gothic")
        C = ax[1][0]; C.plot(t, ata0, "b-", lw=1, label="Blue ATA"); C.plot(t, ata1, "r-", lw=1, label="Red ATA"); C.plot(t, pa, "g--", lw=1, label="WEZ angle")
        C.set_ylim(0, 60); C.set_xlabel("t (s)"); C.set_ylabel("deg"); C.set_title("ATA (nose-to-LOS)  ≤ WEZ angle & in range = firing"); C.legend(fontsize=8); C.grid(alpha=.3)
        D = ax[1][1]; D.plot(t, P0[:, 2], "b-", lw=1, label="Blue alt"); D.plot(t, P1[:, 2], "r-", lw=1, label="Red alt"); D.plot(t, aa0, "m-", lw=.8, alpha=.7, label="AA (enemy nose vs LOS, right axis=deg)")
        D.set_xlabel("t (s)"); D.set_ylabel("alt (m) / AA (deg)"); D.set_title("altitude & aspect"); D.legend(fontsize=8); D.grid(alpha=.3)
        out = f"artifacts/eval_visual/traj_{tag}.png"; plt.tight_layout(); plt.savefig(out, dpi=100); plt.close(fig); res["png"] = out
    return res


def match_starts():
    """큐 로그(UTF-16)에서 Tag → (Blue, Red, HH:MM:SS) 를 모은다."""
    out = {}
    for lg in glob.glob("artifacts/eval_visual/match_queue*.log"):
        try: txt = open(lg, encoding="utf-16").read()
        except Exception: txt = open(lg, encoding="utf-8", errors="ignore").read()
        for m in re.finditer(r"\[([^\]]+)\] Blue=(\S+) Red=(\S+) started (\d\d:\d\d:\d\d)", txt):
            out[m.group(1)] = (m.group(2), m.group(3), m.group(4), None)
        for m in re.finditer(r"\[([^\]]+)\] done (\d+)s", txt):
            if m.group(1) in out: out[m.group(1)] = out[m.group(1)][:3] + (int(m.group(2)),)
    return out


def csv_for(start_hms, day="8_30", done_s=None):
    h, mi, s = map(int, start_hms.split(":")); sec = h * 3600 + mi * 60 + s
    cands = []
    for p in glob.glob(os.path.join(LOGDIR, f"{day}_*_0.csv")):
        m = re.search(r"_(\d+)_(\d+)_0\.csv$", os.path.basename(p)); cs = int(m.group(1)) * 3600 + int(m.group(2)) * 60
        # CSV 이름의 시각은 파일 생성 분(뷰어 기동/Start 무렵, 초는 잘림) → Start 시각보다 같거나 이른 분. 실측: 19:36:29 시작 → 8_30_19_36.
        # 프리셋 실패로 뷰어를 재시작하면 빈 CSV 가 같은 분에 여럿 남는다 → 행 수가 가장 많은 것(실제 판)을 고른다.
        # CSV 는 뷰어 기동 시각(Start 약 30 s 전)의 분으로 만들어진다 → (start-30 s) 에 가장 가까운 분. 실측: aimangle Red 19:46:0x 시작 → 8_30_19_45
        ref = sec - 30
        if abs(cs - ref) <= 50:
            try: nrow = sum(1 for _ in open(p, encoding="utf-8")) - 1
            except Exception: nrow = 0
            if nrow > 100:
                # 판 길이 검증: CSV 프레임수/60 ↔ 큐 로그 done 초 (종료 감지 지연·캡처 1~3 s 포함). 안 맞으면 다른 판(같은 분 덮어쓰기)의 파일
                if done_s is not None and abs(nrow / 60.0 - done_s) > 4.0: continue
                cands.append((abs(cs - ref), p))
    if not cands: return None
    p0 = sorted(cands)[0][1]; return p0, p0.replace("_0.csv", "_1.csv")


def summary(results, png, md, title):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False
    rows = []
    for r in results:
        me = our_slot(r["tag"]); op = 1 - me
        fm, fo = (r["first0"], r["first1"]) if me == 0 else (r["first1"], r["first0"])
        sm, so = (r["fire0_s"], r["fire1_s"]) if me == 0 else (r["fire1_s"], r["fire0_s"])
        dm, do = (r["d_at_fire0"], r["d_at_fire1"]) if me == 0 else (r["d_at_fire1"], r["d_at_fire0"])
        res = RESULTS.get(r["tag"], ("?", None, None))
        rows.append(dict(tag=r["tag"], slot="Blue" if me == 0 else "Red", res=res[0], hpB=res[1], hpR=res[2], dur=r["dur"], min_d=r["min_d"],
                         fm=fm, fo=fo, sm=sm, so=so, dm=dm, do=do, csv=r.get("csv", ""), png=r.get("png", "")))
    col = {"W": "tab:blue", "D": "tab:gray", "L": "tab:red"}
    fig, ax = plt.subplots(2, 2, figsize=(14, 10))
    A = ax[0][0]; A.hist([x["fm"][1] for x in rows if x["fm"]], bins=np.arange(600, 930, 20), color="tab:blue", alpha=.7)
    A.axvline(R_MAX, ls="--", c="k"); A.set_xlabel("our first-WEZ distance (m)"); A.set_title("우리 첫 WEZ 진입 거리 (914 m = 최대 사거리)")
    B = ax[0][1]; B.hist([x["fm"][0] for x in rows if x["fm"]], bins=np.arange(15, 35, 1), color="tab:green", alpha=.7); B.set_xlabel("t (s)"); B.set_title("우리 첫 WEZ 진입 시각")
    C = ax[1][0]
    for x in rows: C.scatter(x["so"], x["sm"], c=col.get(x["res"], "k"), s=60 if x["res"] != "W" else 30); C.annotate(x["tag"].replace("final_v2r6_", "").replace("i7200", "7200")[:26], (x["so"], x["sm"]), fontsize=6)
    lim = max([x["sm"] for x in rows] + [x["so"] for x in rows] + [1.6]) * 1.05; C.plot([0, lim], [0, lim], "k:", lw=.8); C.set_xlim(0, lim); C.set_ylim(0, lim)
    C.set_xlabel("opponent WEZ time on us (s)"); C.set_ylabel("our WEZ time on opponent (s)"); C.set_title("사격 시간 (자세 1° 원뿔·사거리 안)  파랑=승 회색=무 빨강=패")
    D = ax[1][1]; names = [x["tag"].replace("final_v2r6_", "").replace("i7200", "7200")[:24] for x in rows]; idx = np.arange(len(rows))
    D.barh(idx - 0.2, [x["sm"] for x in rows], 0.4, color="tab:blue", label="ours"); D.barh(idx + 0.2, [x["so"] for x in rows], 0.4, color="tab:red", label="opponent")
    D.set_yticks(idx); D.set_yticklabels(names, fontsize=6); D.invert_yaxis(); D.set_xlabel("WEZ time (s)"); D.legend(fontsize=8); D.set_title("판별 사격 시간")
    plt.suptitle(title); plt.tight_layout(); plt.savefig(png, dpi=100); plt.close(fig)
    with open(md, "w", encoding="utf-8") as f:
        f.write("| 판 | 슬롯 | 결과 | HP B:R | 길이 | 최소거리 | 우리 첫WEZ t/거리/ATA | 우리 사격s | 우리 사격 중앙거리 | 상대 첫WEZ t/거리/ATA | 상대 사격s | 상대 중앙거리 | CSV | 그림 |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        g = lambda x: f"{x[0]:.1f}s / {x[1]:.0f}m / {x[2]:.1f}°" if x else "WEZ 없음"
        h = lambda x: f"{x:.0f}m" if x else "-"
        for x in rows:
            f.write(f"| {x['tag']} | {x['slot']} | {x['res']} | {x['hpB']}:{x['hpR']} | {x['dur']:.0f}s | {x['min_d']:.0f}m | {g(x['fm'])} | {x['sm']:.2f} | {h(x['dm'])} | {g(x['fo'])} | {x['so']:.2f} | {h(x['do'])} | {x['csv']} | {os.path.basename(x['png'])} |\n")
    return rows


def aggregate(results, png):
    """전 판 누적 두 장: (1) 거리별 사격 시간 — 어디서 때렸나 (2) 사거리 안 ATA 분포 — 어떤 각도로 있었나. 우리(7200) vs 상대."""
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False
    dm, do, am, ao, fm, fo, wm, wo, tm, to = [], [], [], [], [], [], [], [], [], []
    for r in results:
        me = our_slot(r["tag"]); fme, fop = (r["_fire0"], r["_fire1"]) if me == 0 else (r["_fire1"], r["_fire0"])
        ame, aop = (r["_ata0"], r["_ata1"]) if me == 0 else (r["_ata1"], r["_ata0"])
        d = r["_d"]; inr = r["_inr"]; dt = r["_dt"]; tt = r["_t"]
        dm.append(d[fme]); do.append(d[fop]); wm.append(np.full(fme.sum(), dt)); wo.append(np.full(fop.sum(), dt)); tm.append(tt[fme]); to.append(tt[fop])
        am.append(ame[inr]); ao.append(aop[inr]); fm.append(np.full(inr.sum(), dt)); fo.append(np.full(inr.sum(), dt))
    dm, do, wm, wo, tm, to = map(np.concatenate, (dm, do, wm, wo, tm, to)); am, ao, fm, fo = map(np.concatenate, (am, ao, fm, fo))
    plt.rcParams.update({"font.size": 11})
    fig = plt.figure(figsize=(16, 12)); gs = fig.add_gridspec(2, 5)
    # ── 그래프 1: 시간 — 언제 때렸나. 위 = 우리, 아래(뒤집음) = 상대. 1 s 칸. (거리 분포는 초반 정면전에 묻혀 의미가 없다는 지적 8/30)
    A = fig.add_subplot(gs[0, :]); tmax = float(max(tm.max() if len(tm) else 0, to.max() if len(to) else 0, 30)) + 2
    e = np.arange(0, tmax + 1, 1.0); c = (e[:-1] + e[1:]) / 2
    hm_, _ = np.histogram(tm, bins=e, weights=wm); ho_, _ = np.histogram(to, bins=e, weights=wo)
    A.bar(c, hm_, width=1.0, color="tab:blue", alpha=.85, label=f"우리(7200) 사격 시간  합 {wm.sum():.1f} s")
    A.bar(c, -ho_, width=1.0, color="tab:red", alpha=.75, label=f"상대 사격 시간  합 {wo.sum():.1f} s  (아래로)")
    A.axhline(0, c="k", lw=1)
    for x_, lab in ((100, "WEZ ±2°"), (150, "WEZ ±3°")):
        if x_ < tmax: A.axvline(x_, ls="--", c="gray"); A.annotate(lab, (x_, 0), xytext=(3, 3), textcoords="offset points", fontsize=8, color="gray")
    top = max(hm_.max(), ho_.max()) * 1.25; A.set_ylim(-top, top)
    A.set_yticks(A.get_yticks()); A.set_yticklabels([f"{abs(v):.1f}" for v in A.get_yticks()])
    A.set_xlabel("판 시작 후 경과 시간 (s)   [막대 1개 = 1 s]"); A.set_ylabel("사격 시간 합 (s, 21판 누적)   ↑ 우리  ↓ 상대")
    A.set_title("① 언제 때렸나 — 시간별 사격 시간 (위 우리 / 아래 상대)"); A.legend(loc="upper right"); A.grid(alpha=.3)
    for lo_, hi_ in ((0, 20), (20, 30), (30, 60), (60, 120), (120, 200)):
        m_ = (c >= lo_) & (c < hi_)
        if m_.any() and lo_ < tmax: A.annotate(f"{lo_}~{hi_} s\n우리 {hm_[m_].sum():.1f} s\n상대 {ho_[m_].sum():.1f} s", (min((lo_ + hi_) / 2, tmax - 3), -top * 0.97), ha="center", va="bottom", fontsize=9, bbox=dict(fc="white", ec="none", alpha=.7))
    A.text(0.01, 0.97, f"첫 사격 시각(우리)  최소 {min(r['first0'][0] if our_slot(r['tag']) == 0 else r['first1'][0] for r in results if (r['first0'] if our_slot(r['tag']) == 0 else r['first1'])):.1f} s · 중앙 {np.median([r['first0'][0] if our_slot(r['tag']) == 0 else r['first1'][0] for r in results if (r['first0'] if our_slot(r['tag']) == 0 else r['first1'])]):.1f} s\n사격 거리 중앙  우리 {np.median(dm):.0f} m / 상대 {np.median(do):.0f} m", transform=A.transAxes, ha="left", va="top", fontsize=10, bbox=dict(fc="white", ec="gray", alpha=.9))
    # ── 그래프 2: 각도 — 위 = 우리, 아래 = 상대. 0~5° 0.1° 칸(넓게) | 5~180° 2.5° 칸(좁게), 축 분할
    B1 = fig.add_subplot(gs[1, :3]); B2 = fig.add_subplot(gs[1, 3:], sharey=B1)
    e2 = np.arange(0, 5.01, 0.1); c2 = (e2[:-1] + e2[1:]) / 2; h1m, _ = np.histogram(am, bins=e2, weights=fm); h1o, _ = np.histogram(ao, bins=e2, weights=fo)
    e3 = np.arange(5, 181, 2.5); c3 = (e3[:-1] + e3[1:]) / 2; h3m, _ = np.histogram(am, bins=e3, weights=fm); h3o, _ = np.histogram(ao, bins=e3, weights=fo)
    for AX, cc, hm2, ho2, w in ((B1, c2, h1m, h1o, 0.1), (B2, c3, h3m, h3o, 2.5)):
        AX.bar(cc, hm2, width=w, color="tab:blue", alpha=.85, label="우리 ATA (사거리 안 체류 시간)"); AX.bar(cc, -ho2, width=w, color="tab:red", alpha=.75, label="상대 ATA (아래로)")
        AX.axhline(0, c="k", lw=1); AX.grid(alpha=.3)
    B1.axvspan(0, 1.0, color="green", alpha=.15, label="WEZ ±1° = 실제 타격 구간"); B1.axvline(1.0, ls="--", c="green")
    top2 = max(h1m.max(), h1o.max(), h3m.max(), h3o.max()) * 1.25; B1.set_ylim(-top2, top2); B1.set_xlim(0, 5); B2.set_xlim(5, 180)
    B1.set_yticks(B1.get_yticks()); B1.set_yticklabels([f"{abs(v):.0f}" for v in B1.get_yticks()]); plt.setp(B2.get_yticklabels(), visible=False)
    B1.set_xlabel("기수↔적 각도 ATA (°)   [0~5°: 막대 1개 = 0.1°]"); B2.set_xlabel("ATA (°)   [5~180°: 막대 1개 = 2.5°]"); B1.set_ylabel("사거리(152~914 m) 안 체류 시간 (s, 누적)   ↑ 우리  ↓ 상대")
    B1.set_title("② 어떤 각도로 있었나 — 사거리 안 ATA 분포 (위 우리 / 아래 상대)   왼쪽 0~5° 확대"); B2.set_title("오른쪽 5~180°"); B1.legend(loc="upper right")
    B1.text(0.99, 0.60, f"0~1°  우리 {fm[am < 1].sum():.1f} s / 상대 {fo[ao < 1].sum():.1f} s\n1~2°  우리 {fm[(am >= 1) & (am < 2)].sum():.1f} s / 상대 {fo[(ao >= 1) & (ao < 2)].sum():.1f} s\n2~5°  우리 {fm[(am >= 2) & (am < 5)].sum():.1f} s / 상대 {fo[(ao >= 2) & (ao < 5)].sum():.1f} s", transform=B1.transAxes, ha="right", va="top", fontsize=10, bbox=dict(fc="white", ec="gray", alpha=.9))
    B2.text(0.02, 0.97, f"5~30°  우리 {fm[(am >= 5) & (am < 30)].sum():.1f} s / 상대 {fo[(ao >= 5) & (ao < 30)].sum():.1f} s\n30~90°  우리 {fm[(am >= 30) & (am < 90)].sum():.1f} s / 상대 {fo[(ao >= 30) & (ao < 90)].sum():.1f} s\n90~180°  우리 {fm[am >= 90].sum():.1f} s / 상대 {fo[ao >= 90].sum():.1f} s", transform=B2.transAxes, ha="left", va="top", fontsize=10, bbox=dict(fc="white", ec="gray", alpha=.9))
    plt.suptitle(f"실서버 {len(results)}판 누적 (Blue/Red 양 슬롯, 7200 시점)", fontsize=14); plt.tight_layout(); plt.savefig(png, dpi=110); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", action="append", default=[]); ap.add_argument("--all-7200", action="store_true")
    ap.add_argument("--csv0"); ap.add_argument("--csv1"); ap.add_argument("--no-plot", action="store_true"); ap.add_argument("--day", default="8_30")
    ap.add_argument("--summary", help="요약 그림 png 경로"); ap.add_argument("--md", help="판별 표 markdown 경로"); ap.add_argument("--agg", help="누적 2장(거리·각도) png 경로")
    a = ap.parse_args()
    starts = match_starts(); tags = a.tag
    if a.all_7200: tags = [k for k in starts if "7200" in k]
    jobs = []
    if a.csv0: jobs.append((a.tag[0] if a.tag else "manual", a.csv0, a.csv1))
    claimed = {}   # csv0 -> (start_hms, tag): 같은 분에 뷰어가 두 번 뜨면 서버가 같은 이름으로 덮어써 앞 판 데이터는 사라진다 → 늦게 시작한 판만 유효
    for tg in tags:
        if tg not in starts: print("no start time for", tg); continue
        pair = csv_for(starts[tg][2], a.day, starts[tg][3])
        if not pair: print("LOST (no csv with matching length -> overwritten in the same minute):", tg, starts[tg]); continue
        prev = claimed.get(pair[0])
        if prev and prev[0] > starts[tg][2]: print(f"LOST (csv overwritten by later match {prev[1]}): {tg}"); continue
        if prev: print(f"LOST (csv overwritten by later match {tg}): {prev[1]}"); jobs = [j for j in jobs if j[0] != prev[1]]
        claimed[pair[0]] = (starts[tg][2], tg); jobs.append((tg, *pair))
    print(f"{'tag':38s} {'dur':>5s} {'minD':>5s} | Blue 첫WEZ t/거리/ATA   사격s  중앙거리 | Red 첫WEZ t/거리/ATA   사격s  중앙거리 | yaw규약(cos)")
    results = []
    for tg, c0, c1 in jobs:
        r = analyze(c0, c1, tg, plot=not a.no_plot); r["csv"] = os.path.basename(c0); results.append(r)
        f = lambda x: f"{x[0]:5.1f}s {x[1]:4.0f}m {x[2]:4.1f}°" if x else "   -  (no WEZ)     "
        md = lambda x: f"{x:4.0f}m" if x else "  - "
        print(f"{tg:38s} {r['dur']:4.0f}s {r['min_d']:4.0f}m | {f(r['first0'])} {r['fire0_s']:5.2f} {md(r['d_at_fire0'])} | {f(r['first1'])} {r['fire1_s']:5.2f} {md(r['d_at_fire1'])} | {r['csv']}")
        print(f"{'':38s}   Blue 사격 거리분포 {r['bins0']}   Red {r['bins1']}")
    if a.agg and results: aggregate(results, a.agg); print("->", a.agg)
    if a.summary and results: summary(results, a.summary, a.md or a.summary.replace(".png", ".md"), f"실서버 교전 기하 요약 ({len(results)}판)"); print("->", a.summary)


if __name__ == "__main__":
    main()
