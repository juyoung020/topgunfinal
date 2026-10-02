# -*- coding: utf-8 -*-
"""[측정] 실제 추락 상태를 관통 N초 전에 앉혀 옛 식 발동선 vs 실측표 발동선 비교.
2초 전은 둘 다 이미 늦어 구분이 안 된다(5/40 동일). 더 이른 시점에 앉혀 표가 먼저 켜져 살리는지 본다."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crash_replay as cr
import student.deck_guard as dg

_TABLE = dg.h_table_m
def _old_law(v, g, r):   # 옛 식을 표 자리에 끼운다 (여유 15%+15 는 guard_step 이 10%+15 로 붙이므로 비율 보정)
    return dg.h_needed_m(v, g) * 1.15 / (1.0 + dg.ENV_MARGIN)

def main():
    lead = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    cases = cr.load_states(lead)[:40]
    print("관통 %.0f초 전 상태 재생 · %d판 — 옛 식 vs 실측표 (가드 제어는 동일, 발동선만 다름)" % (lead, len(cases)))
    res = {}
    for name, law in (("old", _old_law), ("table", _TABLE)):
        dg.h_table_m = law
        crashes = 0; mins = []
        for _, spawn, intent, _ in cases:
            c, m = cr.run(spawn, intent, True)
            crashes += int(c); mins.append(m)
        res[name] = (crashes, sorted(mins)[len(mins) // 2])
        dg.h_table_m = _TABLE
    for k, (c, m) in res.items():
        print("  %-6s 추락 %2d/%d   최저고도 중앙 %.0f m" % (k, c, len(cases), m))

if __name__ == "__main__":
    main()
