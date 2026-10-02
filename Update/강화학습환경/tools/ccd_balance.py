# -*- coding: utf-8 -*-
"""[학습 아님 · 속도 보조] 일하는 러너를 물리코어 하나씩에 고정한다.

2026-09-11 실측: Windows 가 러너 16개를 CCD0(논리 0~15)에 몰거나 SMT 짝에 겹쳐 올려
물리코어 3~8개가 놀고, iteration 이 8.0 -> 10.4 초로 느려졌다.
  CCD 반반 고정          10.40 -> 9.58 초
  물리코어 하나씩 고정    -> 8.11 초 (재기동 직후 빠른 구간 7.98 초와 같음)
60초마다: default_worker 러너의 10초 CPU 사용량을 재서 바쁜 러너만 골라 PID 순으로
물리코어 k 의 SMT 짝(mask 0b11 << 2k)을 준다. 16개를 넘으면 CCD 반반.
한가한 러너는 0xFFFFFFFF 로 되돌린다. 러너가 교체되면 다음 주기에 새로 잡는다.
학습 프로세스를 죽이거나 재시작하지 않는다. 트레이너는 건드리지 않는다(학습 단계에 16코어 사용).
"""
import ctypes, subprocess, sys, time, datetime
from ctypes import wintypes

sys.stdout.reconfigure(encoding="utf-8")
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.OpenProcess.restype = wintypes.HANDLE
ACCESS = 0x0200 | 0x0400 | 0x1000  # SET_INFORMATION | QUERY_INFORMATION | QUERY_LIMITED
CCD0, CCD1, ALL = 0x0000FFFF, 0xFFFF0000, 0xFFFFFFFF
BUSY_FRAC = 0.3      # 10초 중 30% 이상 CPU 를 쓰면 일하는 러너
PERIOD, SAMPLE = 60, 10


def runner_pids():
    cmd = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
           "Where-Object { $_.CommandLine -match 'default_worker' } | "
           "ForEach-Object { $_.ProcessId }")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                         capture_output=True, text=True, timeout=60).stdout
    return sorted(int(x) for x in out.split() if x.strip().isdigit())


def cpu_seconds(pid):
    h = k32.OpenProcess(ACCESS, False, pid)
    if not h:
        return None
    try:
        c, e, kt, ut = (wintypes.FILETIME() for _ in range(4))
        if not k32.GetProcessTimes(wintypes.HANDLE(h), ctypes.byref(c), ctypes.byref(e),
                                   ctypes.byref(kt), ctypes.byref(ut)):
            return None
        f = lambda t: ((t.dwHighDateTime << 32) | t.dwLowDateTime) / 1e7
        return f(kt) + f(ut)
    finally:
        k32.CloseHandle(wintypes.HANDLE(h))


def get_mask(pid):
    h = k32.OpenProcess(ACCESS, False, pid)
    if not h:
        return None
    try:
        pm, sm = ctypes.c_size_t(), ctypes.c_size_t()
        k32.GetProcessAffinityMask(wintypes.HANDLE(h), ctypes.byref(pm), ctypes.byref(sm))
        return pm.value
    finally:
        k32.CloseHandle(wintypes.HANDLE(h))


def set_mask(pid, m):
    h = k32.OpenProcess(ACCESS, False, pid)
    if not h:
        return False
    try:
        return bool(k32.SetProcessAffinityMask(wintypes.HANDLE(h), ctypes.c_size_t(m)))
    finally:
        k32.CloseHandle(wintypes.HANDLE(h))


def once():
    pids = runner_pids()
    t0 = {p: cpu_seconds(p) for p in pids}
    time.sleep(SAMPLE)
    busy, idle = [], []
    for p in pids:
        a, b = t0.get(p), cpu_seconds(p)
        if a is None or b is None:
            continue
        (busy if (b - a) / SAMPLE >= BUSY_FRAC else idle).append(p)
    busy.sort()
    # [2026-09-12] 10초 표본이 학습 단계에 통째로 걸리면 러너가 전부 쉬는 것으로 보인다.
    # 그때 전원 해제해 버리면 다음 주기까지 최대 60초 동안 고정이 풀린다(실측: 11:46 사고).
    # 바쁜 러너가 절반도 안 잡히면 표본을 못 믿고 이번 주기를 건너뛴다.
    if len(busy) < 8:
        return len(pids), len(busy), 0
    changed = 0
    for i, p in enumerate(busy):
        want = (0b11 << (2 * i)) if len(busy) <= 16 else (CCD0 if i % 2 == 0 else CCD1)
        if get_mask(p) != want and set_mask(p, want):
            changed += 1
    for p in idle:
        if get_mask(p) not in (ALL, None) and set_mask(p, ALL):
            changed += 1
    return len(pids), len(busy), changed


if __name__ == "__main__":
    print("%s ccd_balance 시작" % datetime.datetime.now().strftime("%H:%M:%S"), flush=True)
    while True:
        try:
            n, b, c = once()
            if c:
                print("%s 러너 %d · 일하는 러너 %d · 마스크 변경 %d"
                      % (datetime.datetime.now().strftime("%H:%M:%S"), n, b, c), flush=True)
        except Exception as ex:
            print("오류:", ex, flush=True)
        time.sleep(PERIOD)
