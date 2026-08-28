# -*- coding: utf-8 -*-
"""학습 로그 실시간 보기 — DLL 스팸을 걸러 창에 필요한 줄만 띄운다.

왜 필요한가 (2026-08-17 실측)
----------------------------
학습 창 44,601 줄 중 **37,645 줄(84%)이 `[JSB][Init]` / `[JSB][Reset]`** 이다.
네이티브 JSBSimAIPLib.dll 이 stdout 에 직접 찍는 디버그 로그라 파이썬에서 끌 수
없다. 여기에 `total: 2`, `Remove Space Complete.`, `init ID:...` 까지 더하면
실제로 봐야 할 줄(학습 진행 행, 체크포인트, 오류)은 창에서 사실상 안 보인다.
체크포인트 줄은 44,601 줄 중 42 줄이었다.

그래서 **파일에는 전부 남기고(사후 분석에 필요) 창에서만 거른다.**
tools/tee.py 도 같은 정책으로 고쳤다. 이 파일은 **이미 돌고 있는 학습**을
재기동 없이 깨끗하게 보고 싶을 때 쓴다.

사용
    python tools\\watch_log.py                      # 최신 실행 자동
    python tools\\watch_log.py --tag 0817_timefix
    python tools\\watch_log.py --all                # 필터 끄기(원본 그대로)
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
import time
from pathlib import Path

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

ROOT = Path(__file__).resolve().parents[1]
CURR = ROOT / "artifacts" / "curriculum" / "AeroFlyer"

# 버릴 것: 네이티브 DLL 수명주기 로그와 그 부산물. 전부 파일에는 남아 있다.
DROP = re.compile(
    r"\[JSB\]\[(Init|Reset|CreateBattleSpace)\]"
    r"|^total: \d+\s*$"
    r"|Remove Space Complete"
    r"|^init ID:"
    r"|JSBSim Flight Dynamics Model"
    r"|JSBSim startup beginning"
    r"|\[JSBSim-ML"
)
# 무슨 일이 있어도 보여줄 것: 오류·중단·관문. DROP 보다 우선한다.
KEEP = re.compile(
    r"Traceback|Error|ERROR|FAILED|EMERGENCY|GATEFAIL|Warning|WARNING"
    r"|Checkpoint\]|Stage |\[Restore\]|LIVETUNE|advance|Gate|exited"
)
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def latest_tag() -> str | None:
    cands = [(p.stat().st_mtime, p.name) for p in CURR.glob("*")
             if (p / "console.log").exists()]
    return max(cands)[1] if cands else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--all", action="store_true", help="필터 없이 원본 그대로")
    ap.add_argument("--tail", type=int, default=40, help="시작 시 보여줄 과거 줄 수")
    a = ap.parse_args()
    tag = a.tag or latest_tag()
    if not tag:
        print("실행을 찾지 못했다"); return 1
    log = CURR / tag / "console.log"
    print(f"=== {tag} 실시간 보기 ({'원본' if a.all else 'DLL 스팸 제거'}) ===")
    print(f"    {log}\n", flush=True)

    def show(line: str) -> None:
        s = ANSI.sub("", line.rstrip("\r\n"))
        if not s.strip():
            return
        if a.all or KEEP.search(s) or not DROP.search(s):
            print(s, flush=True)

    with open(log, encoding="utf-8", errors="replace") as fh:
        fh.seek(0, os.SEEK_END)
        end = fh.tell()
        fh.seek(max(0, end - 200_000))
        fh.readline()
        for line in fh.readlines()[-a.tail * 40:][-a.tail * 40:]:
            show(line)
        while True:
            line = fh.readline()
            if line:
                show(line)
            else:
                time.sleep(0.4)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass
