# -*- coding: utf-8 -*-
"""클라이언트 로그(attach_client 의 PlaneInfo 줄)에서 첫 프레임 스폰 기하를 뽑는다.
사용: python tools/spawn_geom.py <match_..._a.log>
출력: dist(m) / 두 기체 yaw / 기수차(deg) / 각 기체의 ATA(상대 기수 대비 시선각, deg)
  ATA 0 도 = 상대를 정면으로 보고 있음. 헤드온이면 둘 다 0 근처, 꼬리잡기면 뒤쪽 기체만 0 근처.
거리 프리셋 판정(2000ft=609.6 m 등)은 match_run.ps1 이 하고, 이건 시나리오 IC(HABFM/OBFM_RED/SCISSORS) 확인용.
"""
import io, math, re, sys

RE = re.compile(r"plane_id=([01]) age=\S+ frame=(\d+) pos=\(([-\d.]+),([-\d.]+),([-\d.]+)\) rot=\(([-\d.]+),([-\d.]+),([-\d.]+)\)")

def read(path):
    best = {}
    for enc in ("utf-16", "utf-8", "cp949"):
        try:
            txt = io.open(path, encoding=enc, errors="ignore").read()
        except Exception:
            continue
        if "plane_id=" in txt:
            break
    for m in RE.finditer(txt):
        pid, fr = m.group(1), int(m.group(2))
        if pid not in best or fr < best[pid][0]:
            best[pid] = (fr, [float(m.group(i)) for i in (3, 4, 5)], [float(m.group(i)) for i in (6, 7, 8)])
    return best

def main(path):
    b = read(path)
    if len(b) < 2:
        print("no spawn packets"); return 1
    (f0, p0, r0), (f1, p1, r1) = b["0"], b["1"]
    d = math.dist(p0, p1)
    def ata(p, yaw, q):
        # 서버 좌표 x=North y=East 로 두고 시선 방위각과 기수의 차 (부호 무시, 0~180)
        los = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
        a = (los - yaw + 180) % 360 - 180
        return abs(a)
    hd = abs((r1[2] - r0[2] + 180) % 360 - 180)
    print(f"frame {f0}/{f1}  dist {d:.1f} m  alt {p0[2]:.0f}/{p1[2]:.0f} m")
    print(f"yaw blue {r0[2]:.1f}  red {r1[2]:.1f}  heading diff {hd:.1f} deg")
    print(f"ATA blue->red {ata(p0, r0[2], p1):.1f}  red->blue {ata(p1, r1[2], p0):.1f} deg")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
