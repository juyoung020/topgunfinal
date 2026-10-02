# -*- coding: utf-8 -*-
"""엔벨로프 실측표 → 물리식 상수 피팅.

  H = V·sinγ·(t_react + |φ|/p)  +  V²(1−cosγ) / (g·(n_avail − 1))
  n_avail = min(N_struct, (V/V_s)²)        (양력 한계 G — 2차)
  n_avail − 1 ≤ 0 이면 H = ∞ (회복 불가)

미지수 4개 (V_s, N_struct, t_react, p) 를 격자탐색으로 맞춘다. 목적함수는 두 단계:
  ① 모든 실측 칸에서 식 ≥ 실측 (안전 쪽으로만 틀림) 을 만족하는 해 중
  ② 과잉(식−실측)의 합이 최소인 것.
그래야 발동이 필요 이상으로 빨라지지(공격 강하 방해) 않으면서 어느 칸도 안 놓친다.
"""
import io
import math
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
G = 9.80665
P = r"artifacts/eval_visual/envelope_map.txt"


def parse(path):
    rows = []
    roll = None
    gammas = None
    for line in io.open(path, encoding="utf-8"):
        m = re.match(r"\[roll (\d+)", line)
        if m:
            roll = float(m.group(1)); continue
        if line.strip().startswith("V\\"):
            gammas = [float(x) for x in re.findall(r"(\d+)", line.split("|", 1)[1])]; continue
        m = re.match(r"\s*(\d+)\s*\|(.*)", line)
        if m and gammas and roll is not None:
            v = float(m.group(1))
            cells = re.findall(r"(X|\d+)/(\d+)", m.group(2))
            for g, (ht, hf) in zip(gammas, cells):
                rows.append((v, g, roll, None if ht == "X" else float(ht), float(hf)))
    return rows


def model(v, g, phi, vs, nstr, tr, p):
    n = min(nstr, (v / vs) ** 2)
    if n - 1.0 <= 0.05:
        return float("inf")
    gr = math.radians(g)
    return v * math.sin(gr) * (tr + math.radians(abs(phi)) / math.radians(p)) \
        + v * v * (1.0 - math.cos(gr)) / (G * (n - 1.0))


def main():
    rows = parse(P)
    meas = [r for r in rows if r[3] is not None]
    unrec = [r for r in rows if r[3] is None]
    print("실측 칸 %d · 회복불가(X) 칸 %d" % (len(meas), len(unrec)))
    best = None
    for vs in [x for x in range(50, 131, 5)]:
        for nstr in [6.0, 7.0, 8.0, 9.0, 10.0, 12.0]:
            for tr in [x * 0.05 for x in range(0, 21)]:
                for p in [60.0, 90.0, 120.0, 150.0, 200.0, 250.0]:
                    under = 0; over = 0.0; bad = False
                    for v, g, phi, ht, _ in meas:
                        h = model(v, g, phi, vs, nstr, tr, p)
                        if h == float("inf"):
                            bad = True; break     # 실측은 회복됐는데 식이 불가라 함 → 탈락
                        d = h - ht
                        if d < 0:
                            under += 1
                        else:
                            over += d
                    if bad or under > 0:
                        continue
                    # 회복불가 칸은 식도 크게(≥1700) 나와야 정합
                    for v, g, phi, _, _ in unrec:
                        h = model(v, g, phi, vs, nstr, tr, p)
                        if h < 1700.0:
                            over += (1700.0 - h) * 2.0   # 위험 쪽 오차는 2배 가중
                    if best is None or over < best[0]:
                        best = (over, vs, nstr, tr, p)
    if best is None:
        print("모든 칸을 덮는 해 없음 — 격자 범위를 넓혀야 함")
        return
    over, vs, nstr, tr, p = best
    print("\n[해] V_s=%.0f m/s · N_struct=%.0f · t_react=%.2f s · 롤률 p=%.0f°/s   과잉합 %.0f m" % (vs, nstr, tr, p, over))
    print("\n%6s %5s %5s | %8s %8s %8s" % ("V", "γ", "roll", "실측", "새식", "차이"))
    for v, g, phi, ht, _ in meas:
        h = model(v, g, phi, vs, nstr, tr, p)
        print("%6.0f %5.0f %5.0f | %8.0f %8.0f %+8.0f" % (v, g, phi, ht, h, h - ht))
    for v, g, phi, _, _ in unrec:
        h = model(v, g, phi, vs, nstr, tr, p)
        print("%6.0f %5.0f %5.0f | %8s %8s" % (v, g, phi, "불가", "∞" if h == float("inf") else "%.0f" % h))
    print("\nn_avail(V): " + "  ".join("V%d→%.1fG" % (v, min(nstr, (v / vs) ** 2)) for v in (80, 100, 130, 160, 200, 250, 300)))


if __name__ == "__main__":
    main()
