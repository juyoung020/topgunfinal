# -*- coding: utf-8 -*-
"""교전서버 뷰어(DogFightViewer) UI 자동화 — 창 이동·버튼 클릭·키 입력·화면 캡처. (Ray/학습 무관, 측정용)

사용:
  python tools/server_ui.py find                 # 뷰어 창 찾기 + 모니터2 (-1920,-40) 로 이동
  python tools/server_ui.py click openserver     # 버튼 이름으로 클릭 (아래 BUTTONS)
  python tools/server_ui.py click 2000ft
  python tools/server_ui.py key 5                # 키 입력 (예: '5' = 관전 시점)
  python tools/server_ui.py shot out.png         # 모니터2 전체 캡처
좌표는 창을 모니터2 (-1920,-40,1920,1080) 에 두었을 때의 절대 좌표 (2026-08-24 실측).
"""
import ctypes, sys, time
from ctypes import wintypes

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

BUTTONS = {
    "openserver": (-1074, 944),
    "start": (-950, 996),
    "2000ft": (-1327, 825),
    "2500ft": (-1180, 825),
    "3000ft": (-1034, 825),
    "habfm": (-1327, 875),
    "obfm_red": (-1180, 879),
    "scissors": (-1034, 875),
}
WIN_RECT = (-1920, -40, 1920, 1080)   # x, y, w, h


def find_window():
    found = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        n = user32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if "DogFightViewer" in buf.value and user32.IsWindowVisible(hwnd):
                found.append((hwnd, buf.value))
        return True

    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return found


def move_window(hwnd):
    x, y, w, h = WIN_RECT
    user32.ShowWindow(hwnd, 9)          # SW_RESTORE
    user32.SetWindowPos(hwnd, 0, x, y, w, h, 0x0040)   # SWP_SHOWWINDOW
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)


def click(x, y, n=1):
    for _ in range(n):
        user32.SetCursorPos(x, y)
        time.sleep(0.15)
        user32.mouse_event(2, 0, 0, 0, 0)   # LEFTDOWN
        time.sleep(0.05)
        user32.mouse_event(4, 0, 0, 0, 0)   # LEFTUP
        time.sleep(0.4)


def key(ch):
    vk = user32.VkKeyScanW(ord(ch)) & 0xFF
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(vk, 0, 2, 0)


def shot(path):
    from PIL import ImageGrab
    x, y, w, h = WIN_RECT
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
    img.save(path)
    return img.size


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "find"
    wins = find_window()
    if cmd == "find":
        if not wins:
            print("viewer window NOT found"); return 2
        for hwnd, title in wins:
            move_window(hwnd); print(f"moved: {title} (hwnd {hwnd}) -> {WIN_RECT}")
        return 0
    if not wins:
        print("viewer window NOT found"); return 2
    hwnd = wins[0][0]
    user32.SetForegroundWindow(hwnd); time.sleep(0.3)
    if cmd == "click":
        name = argv[2].lower(); n = int(argv[3]) if len(argv) > 3 else 1
        x, y = BUTTONS[name]; click(x, y, n); print(f"clicked {name} at ({x},{y}) x{n}"); return 0
    if cmd == "key":
        key(argv[2]); print(f"key {argv[2]}"); return 0
    if cmd == "shot":
        print("shot", shot(argv[2]), argv[2]); return 0
    print(__doc__); return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
