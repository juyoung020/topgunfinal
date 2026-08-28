# -*- coding: utf-8 -*-
"""재기동 전 준비 — 최신 체크포인트로 런처를 갱신하고 **위험 항목을 검사**한다.

왜 스크립트로 만들었나 (2026-08-17)
-----------------------------------
러너 누수 때문에 7~9시간마다 재기동해야 하는데, 손으로 할 때마다 같은 자리에서
사고가 났다. 실제로 겪은 것:

  * `^` 로 이어지는 **명령 중간에 `rem` 주석**을 넣어 줄 연결이 끊겼다.
    트레이너만 조용히 안 뜨고 sidecar 는 떠서, 겉보기엔 정상인데 학습만 멈췄다.
  * `--restore-checkpoint` 를 옛 iter 로 둔 채 재기동 → 진행분을 날릴 뻔했다.
  * `--resume` 과 `--init-bundle` 은 상호 배타(train_curriculum.py:403)인데
    같이 있으면 정책이 번들로 되감긴다.
  * 배트에 한글이 들어가면 cmd 가 콘솔 코드페이지로 파싱해 mojibake 를 실행한다.

그래서 재기동 전에 이 네 가지를 기계가 확인하게 한다. 하나라도 걸리면 0 이 아닌
코드로 끝나므로, 통과하지 못하면 재기동하지 않는다.

사용
    python tools\\prep_resume.py                       # 검사 + 최신 체크포인트로 갱신
    python tools\\prep_resume.py --check-only          # 검사만
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

ROOT = Path(__file__).resolve().parents[1]


def latest_checkpoint(tag: str, stage_dir_name: str) -> tuple[str, int] | None:
    d = ROOT / "artifacts" / "curriculum" / "AeroFlyer" / tag / stage_dir_name / "checkpoints"
    if not d.is_dir():
        return None
    cands = []
    for p in d.glob("iter_*"):
        m = re.match(r"iter_(\d+)$", p.name)
        if p.is_dir() and m:
            cands.append((int(m.group(1)), p.name))
    if not cands:
        return None
    it, name = max(cands)
    return name, it


def check(bat: Path) -> list[str]:
    """재기동을 막아야 하는 문제만 반환한다."""
    raw = bat.read_bytes()
    problems = []
    if any(b > 127 for b in raw):
        problems.append("배트에 비ASCII 문자가 있다 — cmd 가 cp949 로 파싱해 mojibake 를 실행한다")
    lines = raw.decode("ascii", "replace").splitlines()
    for i in range(len(lines) - 1):
        if lines[i].rstrip().endswith("^") and lines[i + 1].lstrip().lower().startswith("rem"):
            problems.append(f"{i+2}번째 줄: `^` 연결 중간에 rem — 명령이 여기서 끊긴다")
    args = [l.strip() for l in lines if not l.strip().lower().startswith("rem")]
    has_resume = any(a.startswith("--resume") for a in args)
    has_init = any(a.startswith("--init-bundle") for a in args)
    if has_resume and has_init:
        problems.append("--resume 과 --init-bundle 동시 사용 — 정책이 번들로 되감긴다")
    for a in args:
        if a.startswith("--restore-checkpoint"):
            m = re.search(r'"([^"]+)"', a)
            if m and not (m.group(1).startswith("%~dp0") or re.match(r"^[A-Za-z]:", m.group(1))):
                problems.append("--restore-checkpoint 가 상대 경로 — pyarrow 'URI has empty scheme' 로 즉사")
    if not any("tee.py" in l for l in lines):
        problems.append("tee.py 파이프가 없다 — 창이 조용해지거나 console.log 가 안 남는다")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bat", default="launch_timefix_resume.bat")
    ap.add_argument("--tag", default="0817_timefix")
    ap.add_argument("--stage-dir", default="stage_34_turnalt_gunnery")
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()
    bat = ROOT / a.bat
    if not bat.exists():
        print(f"런처 없음: {bat}"); return 2

    if not a.check_only:
        got = latest_checkpoint(a.tag, a.stage_dir)
        if not got:
            print("체크포인트를 찾지 못했다"); return 2
        name, it = got
        s = bat.read_text(encoding="ascii")
        before = re.search(r"checkpoints\\(iter_\d+)", s)
        s2 = re.sub(r"(checkpoints\\)iter_\d+", lambda m: m.group(1) + name, s)
        bat.write_text(s2, encoding="ascii")
        print(f"복원 지점: {before.group(1) if before else '?'} -> {name}  (iter {it})")

    problems = check(bat)
    if problems:
        print("\n[재기동 금지] 문제 발견:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("검사 통과 — 비ASCII 0 / 명령블록 내 rem 없음 / resume·init-bundle 배타 / "
          "절대경로 / tee 연결")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
