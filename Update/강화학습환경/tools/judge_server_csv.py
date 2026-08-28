# -*- coding: utf-8 -*-
"""교전서버 Log CSV 두 장(plane0/plane1)으로 승패를 판정한다.

서버 CSV 에는 HP 가 없다 — 위치·자세뿐. 그래서 env 와 **같은 공식**으로
데미지를 재적분한다 (single_agent_env.py:_wez_damage / update_damage 과 동일):
    페이즈(개전 후 초):  0s  ±1°  152.4~914.4 m   x1.0
                       100s  ±2°  152.4~1066.8 m  x0.3
                       150s  ±3°  152.4~1219.2 m  x0.1
    damage = ((max-d)/(max-min)) * dt * scale,  이른 페이즈 우선
    dt = 1/60 (서버 60 Hz, Time 열은 프레임 번호)
근거: 조준 기하 20개 항목 재계산 오차 0.0000 실측(관측 계약 검증에서).

판정: crash(고도<304.8) > kill(HP<=0) > timeout(HP 마진).
사용: python tools/judge_server_csv.py <plane0.csv> <plane1.csv> [--name0 A --name1 B]
"""
import csv, math, sys

FEET = 0.3048
MIN_ALT = 1000.0 * FEET          # 304.8 m 추락선
MIN_RANGE = 500.0 * FEET         # 152.4 m
PHASES = [                        # (after_s, half_angle_deg, max_range, scale)
    (150.0, 3.0, 4000.0 * FEET, 0.1),
    (100.0, 2.0, 3500.0 * FEET, 0.3),
    (0.0,   1.0, 3000.0 * FEET, 1.0),
]
HZ = 60.0


def load(path):
    rows = []
    for r in csv.DictReader(open(path, encoding="utf-8")):
        try:
            rows.append((float(r["Time"]), float(r["Latitude"]), float(r["Longitude"]),
                         float(r["Altitude"]), float(r["Pitch (deg)"]), float(r["Yaw (deg)"])))
        except Exception:
            pass
    return rows


def enu(lat, lon, alt, lat0, lon0, alt0):
    # 작은 영역이라 평면 근사로 충분 (경기장 20 km, 오차 << 1 m)
    R = 6378137.0
    dn = math.radians(lat - lat0) * R
    de = math.radians(lon - lon0) * R * math.cos(math.radians(lat0))
    return de, dn, alt - alt0


def fwd(yaw_deg, pitch_deg):
    # 서버 yaw 는 나침반 규약(0=북, 90=동) — 실측 검증됨(중앙오차 0.54도)
    y, p = math.radians(yaw_deg), math.radians(pitch_deg)
    return (math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p))


def ata_deg(from_pos, from_fwd, to_pos):
    dx = (to_pos[0] - from_pos[0], to_pos[1] - from_pos[1], to_pos[2] - from_pos[2])
    d = math.sqrt(sum(v * v for v in dx))
    if d < 1e-6:
        return 0.0, 0.0
    dot = sum(a * b / d for a, b in zip(from_fwd, dx))
    return math.degrees(math.acos(max(-1.0, min(1.0, dot)))), d


def dmg(sim_t, dis, ata):
    for after_s, half, mx, scale in PHASES:
        if sim_t >= after_s:
            if MIN_RANGE <= dis <= mx and ata <= half:
                return ((mx - dis) / (mx - MIN_RANGE)) / HZ * scale
            return 0.0   # 이른(위쪽에서 마지막 매칭) 페이즈 우선 — env 는 첫 비영값
    return 0.0


def dmg_env_order(sim_t, dis, ata):
    # env 순서 재현: 이른 페이즈부터 검사, 첫 번째 0 아닌 값 채택
    for after_s, half, mx, scale in sorted(PHASES):
        if sim_t < after_s:
            continue
        if MIN_RANGE <= dis <= mx and ata <= half:
            return ((mx - dis) / (mx - MIN_RANGE)) / HZ * scale
    return 0.0


def judge(f0, f1, name0="plane0", name1="plane1"):
    a, b = load(f0), load(f1)
    n = min(len(a), len(b))
    hp = [1.0, 1.0]
    wez = [0, 0]         # 프레임 수 (자기가 상대를 무는)
    end = None
    t_end = 0.0
    lat0, lon0 = a[0][1], a[0][2]
    for i in range(n):
        ta, tb = a[i], b[i]
        sim_t = ta[0] / HZ
        t_end = sim_t
        pa = enu(ta[1], ta[2], ta[3], lat0, lon0, 0.0)
        pb = enu(tb[1], tb[2], tb[3], lat0, lon0, 0.0)
        fa, fb = fwd(ta[5], ta[4]), fwd(tb[5], tb[4])
        ata_a, dis = ata_deg(pa, fa, pb)
        ata_b, _ = ata_deg(pb, fb, pa)
        da = dmg_env_order(sim_t, dis, ata_a)   # a 가 b 에 주는 딜
        db = dmg_env_order(sim_t, dis, ata_b)
        if da > 0:
            wez[0] += 1
        if db > 0:
            wez[1] += 1
        hp[1] -= da
        hp[0] -= db
        if ta[3] < MIN_ALT:
            end = ("crash", 0); break
        if tb[3] < MIN_ALT:
            end = ("crash", 1); break
        if hp[0] <= 0 and hp[1] <= 0:
            end = ("mutual_kill", None); break
        if hp[1] <= 0:
            end = ("kill", 0); break
        if hp[0] <= 0:
            end = ("kill", 1); break
    if end is None:
        end = ("timeout", None)
    kind, who = end
    if kind == "crash":
        winner = 1 - who
        detail = f"{[name0, name1][who]} 추락"
    elif kind == "kill":
        winner = who
        detail = f"{[name0, name1][who]} 가 격추"
    elif kind == "mutual_kill":
        winner = 0 if hp[0] > hp[1] else (1 if hp[1] > hp[0] else None)
        detail = "동시 격추"
    else:
        winner = 0 if hp[0] > hp[1] else (1 if hp[1] > hp[0] else None)
        detail = "시간종료 HP 마진"
    return {
        "end": kind, "winner": None if winner is None else [name0, name1][winner],
        "detail": detail, "t_end_s": round(t_end, 1), "frames": n,
        "hp": [round(hp[0], 4), round(hp[1], 4)],
        "wez_s": [round(wez[0] / HZ, 1), round(wez[1] / HZ, 1)],
    }


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    kw = dict(zip(*[iter([x.lstrip("-") for x in sys.argv[1:] if x.startswith("--")] )]*1)) if False else {}
    name0, name1 = "plane0", "plane1"
    if "--name0" in sys.argv:
        name0 = sys.argv[sys.argv.index("--name0") + 1]
    if "--name1" in sys.argv:
        name1 = sys.argv[sys.argv.index("--name1") + 1]
    r = judge(args[0], args[1], name0, name1)
    print(r)
