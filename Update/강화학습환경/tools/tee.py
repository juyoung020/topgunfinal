# -*- coding: utf-8 -*-
"""stdin 을 화면과 파일에 동시에 쓴다 (Windows cmd 에는 tee 가 없다).

왜 필요한가 (2026-08-16):
  학습 창 출력을 `> console.log` 로 파일에만 보냈더니 창이 조용해졌다. 반대로
  파일로 안 남기면 죽었을 때 원인을 볼 수 없다 — 실제로 그것 때문에 사망 원인을
  세 번 오진했다(Ray 크래시로 단정했는데 실은 max_iterations 도달이었다).
  둘 다 필요하므로 tee 한다.

사용:
    <프로그램> 2>&1 | python -u tools\\tee.py <로그파일>

flush 를 매 줄 하는 이유: 파이프를 거치면 블록 버퍼링이 걸려 창에 수십 초씩
늦게 뜬다. 학습 창은 "살아 있는지" 보는 용도라 지연되면 쓸모가 없다.
"""
import re
import sys

# [2026-08-17] 창에만 필터를 건다. **파일에는 전부 남긴다.**
# 실측: 학습 로그 44,601 줄 중 37,645 줄(84%)이 네이티브 DLL 의
# `[JSB][Init]` / `[JSB][Reset]` 수명주기 로그였다. 체크포인트 줄은 42 줄.
# DLL 이 stdout 에 직접 찍어 파이썬에서 끌 수 없으므로 여기서 거른다.
# 사후 분석에는 원본이 필요하니 파일은 손대지 않는다.
_DROP = re.compile(
    r"\[JSB\]\[(Init|Reset|CreateBattleSpace)\]"
    r"|^total: \d+\s*$"
    r"|Remove Space Complete"
    r"|^init ID:"
    r"|JSBSim Flight Dynamics Model"
    r"|JSBSim startup beginning"
    r"|\[JSBSim-ML"
)
# 무슨 일이 있어도 창에 띄울 것 — _DROP 보다 우선.
_KEEP = re.compile(
    r"Traceback|Error|ERROR|FAILED|EMERGENCY|GATEFAIL|Warning|WARNING"
    r"|Checkpoint\]|Stage |\[Restore\]|LIVETUNE|advance|Gate|exited"
)
_ANSI = re.compile(r"\[[0-9;]*m")


def _to_window(line: str) -> bool:
    s = _ANSI.sub("", line)
    if not s.strip():
        return False
    return bool(_KEEP.search(s)) or not _DROP.search(s)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: tee.py <logfile> [--raw]", file=sys.stderr)
        return 2
    path = sys.argv[1]
    raw = "--raw" in sys.argv[2:]          # 창에도 원본 그대로 보고 싶을 때
    with open(path, "a", encoding="utf-8", errors="replace") as fh:
        for line in sys.stdin:
            if raw or _to_window(line):
                sys.stdout.write(line)
                sys.stdout.flush()
            fh.write(line)                  # 파일은 언제나 전부
            fh.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
