# -*- coding: utf-8 -*-
"""뷰어(DogFightViewer) 제어 — 주 모니터 (0,0) 에 창을 놓고 창 기준 좌표로 클릭한다 (server_ui.py 의 모니터2 절대좌표 대신).
사용: python tools/viewer_ctl.py kill | find | click <2000ft|openserver|start> [n] | key <k> | shot <png> | hp <png>
뷰어 프로세스 실제 이름은 DogFightViewer-Win64-Shipping (Stop-Process DogFightViewer 로는 안 죽는다 — 8/29 두 개가 겹쳐 떠서 클릭이 옛 창에 갔던 사고).
프리셋(2000ft 등)·OpenServer 는 첫 클릭이 창 활성화에 먹히므로 2회 클릭.
창 기준 좌표(1920x1080 창, server_ui 의 모니터2 좌표 + (1920, 40)): 2000ft (593,865) openserver (846,984) start (970,1036)
"""
import ctypes, ctypes.wintypes as w, sys, time
u = ctypes.windll.user32; u.SetProcessDPIAware()
BTN = {"2000ft": (593, 865), "2500ft": (740, 865), "3000ft": (886, 865), "openserver": (846, 984), "start": (970, 1036),
       # [2026-09-04] 둘째 줄 시나리오 IC (거리 프리셋 아래). 화면 캡처로 좌표 확인: HABFM(594,915) OBFM_RED(740,919) SCISSORS(886,915).
       #   HABFM=정면 고애스펙트(헤드온), OBFM_RED=Red 가 뒤에 붙은 상태(꼬리잡기), SCISSORS=시저스.
       "habfm": (594, 915), "obfm_red": (740, 919), "scissors": (886, 915)}
# [2026-09-04 사용자 지시] 저고도 시작 판을 위해 Alt(ft)/Speed(m/s) 입력칸 추가.
#   좌표는 뷰어 캡처에서 직접 특정(크롭 x1050~1600,y850~960 3배 확대 -> Alt 박스 중심 (1207,915), Speed (1207,866)).
#   언리얼 텍스트박스라 클릭 -> Ctrl+A -> 타이핑 -> Enter 순서로 넣는다. 넣은 뒤 shot 으로 눈으로 확인할 것.
FIELD = {"alt": (1207, 915), "speed": (1207, 866)}

def settext(h, name, text):
    place(h)   # TOPMOST + 포커스. 이게 없으면 클릭·키 입력이 다른 창으로 간다(실측: 값이 안 바뀜)
    r = rect(h); x, y = FIELD[name]; X, Y = r.left + x, r.top + y
    u.SetCursorPos(X, Y); time.sleep(0.2)
    for _ in range(2):
        u.mouse_event(2, 0, 0, 0, 0); time.sleep(0.05); u.mouse_event(4, 0, 0, 0, 0); time.sleep(0.15)
    time.sleep(0.2)
    u.keybd_event(0x11, 0, 0, 0); u.keybd_event(0x41, 0, 0, 0); time.sleep(0.05)
    u.keybd_event(0x41, 0, 2, 0); u.keybd_event(0x11, 0, 2, 0); time.sleep(0.2)
    for ch in str(text):
        vk = ord(ch) if ch.isdigit() else (0xBE if ch == "." else None)
        if vk is None: continue
        u.keybd_event(vk, 0, 0, 0); time.sleep(0.04); u.keybd_event(vk, 0, 2, 0); time.sleep(0.06)
    u.keybd_event(0x0D, 0, 0, 0); time.sleep(0.05); u.keybd_event(0x0D, 0, 2, 0); time.sleep(0.3)
    print(f"set {name} = {text} at ({X},{Y})")

def find():
    # [2026-09-13] 창 클래스가 UnrealWindow 인 것만 고른다. 제목만 보면 대시보드 크롬 탭
    #   ("DogFight Dashboard - Chrome", class Chrome_WidgetWin_1)이 같이 잡히고, hw[-1] 이 그 크롬을
    #   고르는 바람에 클릭이 전부 브라우저로 갔다 — 프리셋 8회 클릭에도 green px 0, 뷰어 3회 재시작 후
    #   ABORT(실측 2026-09-13). 예전 "뷰어가 클릭을 안 받는다" 미해결 건도 같은 원인으로 보인다.
    hw = []
    def cb(h, l):
        n = ctypes.create_unicode_buffer(256); u.GetWindowTextW(h, n, 256)
        c = ctypes.create_unicode_buffer(256); u.GetClassNameW(h, c, 256)
        if "DogFight" in n.value and c.value == "UnrealWindow" and u.IsWindowVisible(h): hw.append(h)
        return True
    u.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(cb), 0)
    if not hw: print("viewer not found"); sys.exit(1)
    if len(hw) > 1: print(f"WARNING: viewer windows x{len(hw)} — kill 먼저")
    return hw[-1]

def rect(h):
    r = w.RECT(); u.GetWindowRect(h, ctypes.byref(r)); return r

def place(h):
    # HWND_TOPMOST (-1): keep the viewer above every other window for the whole match. SetForegroundWindow alone is refused
    # by Windows when another app (terminal/editor) has focus -> clicks landed on that window, preset/OpenServer never applied (8/30).
    # HWND args must be pointer-sized: a bare -1 goes through ctypes as 32-bit 0xFFFFFFFF -> invalid handle -> SetWindowPos silently fails and the window stays where it spawned (clicks then land at +312,+125) (8/30)
    u.SetWindowPos.argtypes = [w.HWND, w.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.UINT]
    u.ShowWindow(h, 9)
    ok = u.SetWindowPos(h, w.HWND(-1), 0, 0, 1920, 1080, 0x0040); u.SetForegroundWindow(h); time.sleep(0.4)
    if not ok: print("SetWindowPos failed:", ctypes.GetLastError())
    r = rect(h); print(f"placed ({r.left},{r.top})-({r.right},{r.bottom})")

def click(h, name, n=1):
    r = rect(h); x, y = BTN[name]; X, Y = r.left + x, r.top + y
    for _ in range(n):
        u.SetCursorPos(X, Y); time.sleep(0.15); u.mouse_event(2, 0, 0, 0, 0); time.sleep(0.08); u.mouse_event(4, 0, 0, 0, 0); time.sleep(0.35)
    print(f"clicked {name} at ({X},{Y}) x{n}")

def key(h, k):
    u.SetForegroundWindow(h); time.sleep(0.2); vk = ord(k.upper()); u.keybd_event(vk, 0, 0, 0); time.sleep(0.05); u.keybd_event(vk, 0, 2, 0); print("key", k)

def shot(h, path, strip=False):
    from PIL import ImageGrab
    r = rect(h); img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom), all_screens=True)
    if strip: img = img.crop((0, 0, r.right - r.left, 140))
    img.save(path); print("shot", path)

def hp_from_img(img):
    """상단 HP 바의 채워진 열 비율 = HP%. 창 캡처(1920x1080, 제목줄 포함) 기준 Blue 바 x 94~861, Red 바 x 1058~1825, y 52~76.
    8/30 검증: 화면 숫자 60.72/55.57/94.1/16.7/7.46 ↔ 측정 60.8/55.5/94.4/16.6/7.2 (오차 ≤0.3)."""
    import numpy as np
    a = np.asarray(img.convert("RGB")).astype(int)
    def frac(x0, x1, y0, y1, is_col):
        band = a[y0:y1, x0:x1]; col = is_col(band).mean(axis=0) > 0.5
        return 100.0 * float(col.mean())
    blue = lambda b: (b[..., 2] > 150) & (b[..., 0] < 120) & (b[..., 1] < 140)
    orange = lambda b: (b[..., 0] > 180) & (b[..., 1] > 60) & (b[..., 1] < 160) & (b[..., 2] < 80)
    return frac(94, 861, 52, 76, blue), frac(1058, 1825, 52, 76, orange)

def hpwatch(h, out_csv, max_sec=220.0, period=0.25):
    """판이 도는 동안 HP 바를 period 초마다 읽어 CSV(t,blue,red)로 남긴다 — 패킷엔 HP 가 없어서(9개뿐) 화면이 유일한 HP 시계열.
    match_run.ps1 이 Start 직후 백그라운드로 띄우고 판이 끝나면 역할명(hpwatch)으로 종료한다."""
    from PIL import ImageGrab
    t0 = time.time(); r = rect(h)
    with open(out_csv, "w", encoding="utf-8") as f:
        f.write("t,blue_hp,red_hp\n")
        while time.time() - t0 < max_sec:
            img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom), all_screens=True)
            b, rd = hp_from_img(img); f.write(f"{time.time() - t0:.2f},{b:.1f},{rd:.1f}\n"); f.flush()
            time.sleep(period)

# 측정 방법: viewer_ctl.py click <프리셋> 2 -> preset_check (창 기준 x 600~1320, y 330~450 의 초록 픽셀 수).
#   클릭 직후 바로 읽으면 화면 갱신 전 값이라 세 프리셋이 뭉쳐 나온다 — 1초 대기 후 읽을 것.
# [2026-09-13 정정] 같은 날 오전에 2028/3825/5290 으로 "재측정"해서 넣었던 값은 오측정이었다.
#   오늘 토너먼트에서 **패킷 스폰 거리로 2000ft 적용이 확인된 판**(611.4/608.6/613.8/610.8 m)의
#   green px 가 6판 연속 3393 — 8/29 옛값 3390 과 동일하다. 그래서 옛값으로 되돌린다.
#   2000ft 만 패킷 교차검증됨. 2500/3000 은 미검증이지만 이제 픽셀 실패가 판을 죽이지 않는다
#   (match_run.ps1 은 스폰 거리 하나로만 유효성을 판정한다).
GREEN_PX = {"2000ft": 3393, "2500ft": 4720, "3000ft": 5945}

def green_pixels(h):
    from PIL import ImageGrab
    u.SetForegroundWindow(h); time.sleep(0.25)   # 다른 창이 덮고 있으면 캡처가 0 이 된다 (8/29 peak3100 시도: green px 0 x24)
    r = rect(h); img = ImageGrab.grab(bbox=(r.left + 600, r.top + 330, r.left + 1320, r.top + 450), all_screens=True).convert("RGB")
    px = img.load(); n = 0
    for y in range(img.size[1]):
        for x in range(img.size[0]):
            R, G, B = px[x, y]
            if G > 150 and R < 120 and B < 120: n += 1
    return n

def preset_selected(h, name):
    """프리셋이 선택되면 중앙에 초록 양방향 화살표가 그려지고 길이가 거리별로 다르다 — 픽셀 수로 어느 프리셋인지 판별."""
    # [2026-09-13] 허용오차 400 -> 250. 새 실측값 간격이 527~1331 이라 400 이면 겹친다
    #   (2500ft 를 눌렀는데 3327 이 2000ft 기준 3390 과 63 차이라 "2000ft 선택됨"으로 오판한 실측이 있다).
    n = green_pixels(h); return abs(n - GREEN_PX[name]) < 250, n

def preset(h, name, tries=8):
    """프리셋 버튼을 '그 프리셋의 선택 표시가 보일 때까지' 한 번씩 클릭 (고정 횟수 클릭 금지 — 창 활성화에 먹히거나 다른 프리셋이 남는다)."""
    for i in range(tries):
        ok, n = preset_selected(h, name)
        if ok: print(f"preset {name} selected (green px {n}, after {i} clicks)"); return True
        # [2026-09-13] 0.6 -> 1.0초. 클릭 직후에 읽으면 화면 갱신 전이라 세 프리셋이 같은 값(2099)으로
        #   뭉쳐 나오고, 맞게 눌렀는데도 "선택 안 됨"으로 읽혀 8회 클릭 -> 뷰어 재시작 -> ABORT 로 갔다(실측).
        click(h, name, 1); time.sleep(1.0)
    ok, n = preset_selected(h, name); print(f"preset {name} selected={ok} (green px {n}) after {tries} clicks"); return ok

def kill():
    import subprocess
    subprocess.run(["powershell","-NoProfile","-Command","Get-Process | Where-Object { $_.ProcessName -like 'DogFightViewer*' -or $_.ProcessName -in @('unreal_bt_client') } | Stop-Process -Force -Confirm:$false -ErrorAction SilentlyContinue"], check=False)
    # wait until the viewer process is really gone (8/30: a 2 s fixed sleep left the old window alive -> "viewer windows x2" -> preset click went to the old window -> whole-viewer restart every match)
    for _ in range(20):
        alive = subprocess.run(["powershell","-NoProfile","-Command","@(Get-Process | Where-Object { $_.ProcessName -like 'DogFightViewer*' }).Count"], capture_output=True, text=True).stdout.strip()
        if alive == "0": break
        time.sleep(0.5)
    print("killed viewer/cutoff")

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "kill": kill(); sys.exit(0)
    h = find()
    if cmd == "find": place(h)
    elif cmd == "click": click(h, sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    elif cmd == "alt": settext(h, "alt", sys.argv[2])
    elif cmd == "speed": settext(h, "speed", sys.argv[2])
    elif cmd == "preset": sys.exit(0 if preset(h, sys.argv[2]) else 3)
    elif cmd == "preset_check":
        # [2026-09-13] 허용오차를 preset_selected 와 같은 250 으로 맞춤(400 이면 프리셋끼리 겹친다).
        #   green_pixels 를 두 번 부르던 것도 한 번으로 — 두 번 캡처하면 값이 달라 표가 자기모순을 냈다.
        _n = green_pixels(h); print("green px", _n, {k: abs(_n - v) < 250 for k, v in GREEN_PX.items()})
    elif cmd == "key": key(h, sys.argv[2])
    elif cmd == "shot": shot(h, sys.argv[2])
    elif cmd == "hp": shot(h, sys.argv[2], strip=True)
    elif cmd == "hpread":
        from PIL import Image; b, rd = hp_from_img(Image.open(sys.argv[2])); print(f"blue {b:.1f} red {rd:.1f}")
    elif cmd == "hpwatch": hpwatch(h, sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 220.0)
