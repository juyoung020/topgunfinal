# -*- coding: utf-8 -*-
"""제출 zip 을 만든다 — 운영진이 그대로 풀어 실행할 수 있는 최소 구성.

왜 최소 구성인가: 운영진이 **동일 환경에서 직접 실행**하고 실패하면 참가가 제한된다.
학습 산출물(수 GB)·리플레이·체크포인트가 섞이면 용량만 키우고 실행에는 쓰이지 않는다.

포함
    student/            my_submission.py · my_observation.py 등 (BT 관련 제외 안 함: import 함)
    src/dogfight/       클라이언트·정책·액션 프로바이더
    artifacts/models/AeroFlyer/<번들>/   가중치 1개
    GeoMathUtil.py, run_unreal_inference.py   제출 경로 원본
    제출_실행방법.txt

제외
    artifacts/curriculum/  학습 로그·체크포인트·스냅샷 (수 GB)
    artifacts/replays/     리플레이
    __pycache__, *.pyc

MODE="rl" 이라 BT DLL(AIP_BASE.dll)은 실행 경로에 들어오지 않는다 —
build_action_provider() 가 MODE=="bt" 또는 "hybrid" 일 때만 BTActionProvider 를 만든다.
그래도 import 는 하므로 src/dogfight/ai/bt_*.py 는 포함한다.

사용법
    python tools/make_submission_zip.py                       # submission_v1
    python tools/make_submission_zip.py nocrash0_snap_0281     # 번들 지정
"""
import os, sys, zipfile, fnmatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE = sys.argv[1] if len(sys.argv) > 1 else "submission_v1"

bundle_rel = os.path.join("artifacts", "models", "AeroFlyer", BUNDLE)
if not os.path.isdir(os.path.join(ROOT, bundle_rel)):
    print("!! 번들 없음: %s" % bundle_rel); sys.exit(1)

# [2026-08-22] 압축을 풀어 실행해 보니 ModuleNotFoundError: FighterSim 이 났다.
# 원인: src/dogfight/__init__.py 가 envs/single_agent_env.py 를 즉시 import 하고,
# 그 파일이 최상위 FighterSim 을 부른다. 제출 경로가 시뮬레이터를 쓰지 않아도
# **import 사슬 때문에** 딸려온다. JSBSimWrapper 는 모듈 최상위에서
# ct.cdll.LoadLibrary(JSBSimAIPLib.dll) 을 하므로 DLL 과 aircraft/ 도 필요하다.
# 운영진이 실행에 실패하면 참가가 제한되므로 넉넉히 넣는다(추가 4.5 MB).
INCLUDE_DIRS = ["student", os.path.join("src", "dogfight"), bundle_rel, "aircraft"]
# [2026-08-22] Rule_forTraining.xml 누락으로 **압축 푼 상태에서 기동 실패**했다.
# my_submission.main() 은 MODE="rl" 이어도 `with activate_rule_xml(...)` 안으로
# 들어가고(my_submission.py:220), bt_rule_manager 는 XML 이 없으면 예외를 던진다.
# 작업 트리에는 있어서 안 드러났고 zip 을 풀어 실행해서야 잡혔다.
# 운영진이 실행에 실패하면 참가가 제한되므로 반드시 포함한다.
INCLUDE_FILES = ["GeoMathUtil.py", "run_unreal_inference.py", "README.txt",
                 "FighterSim.py", "JSBSimWrapper.py", "DogFightEnvWrapper.py",
                 "JSBSimAIPLib.dll", "Rule_forTraining.xml"]
# [2026-08-24] 제출_실행방법.txt(한글 파일명) -> README.txt(ASCII).
# zip 안 한글 파일명이 운영진 환경의 압축 해제 도구에 따라 깨져 나왔다
# (Python zipfile 은 UTF-8 플래그를 세우지만, 일부 도구는 그 플래그를
# 무시하고 로컬 코드페이지로 읽는다). 내용은 그대로, 파일명만 ASCII 로.
SKIP_PAT = ["*__pycache__*", "*.pyc", "*.pyo", "*_BEFORE_*", "*_DEPRECATED_*",
            "*.lock"]   # [2026-08-23] filelock 이 실행 중 만드는 잠금 파일. 잠겨 있어 PermissionError


def skip(rel):
    return any(fnmatch.fnmatch(rel.replace(os.sep, "/"), p.replace(os.sep, "/"))
               for p in SKIP_PAT)


# [2026-08-22] 수정 금지 영역은 **작업 트리가 아니라 배포본에서** 담는다.
# 이유: aircraft/f16/f16_init.xml 은 JSBSimWrapper.py:139 가 매 리셋마다
# doc.write() 로 덮어쓴다. 학습이 도는 한 작업 트리 값은 계속 바뀌므로
# "복원해 두기"로는 보장이 안 된다. 압축 시점에 원본에서 가져와야 확실하다.
# 나머지(DLL·engine·제출 경로 파일)도 같은 원칙으로 원본을 쓴다.
PRISTINE = os.path.join(ROOT, "artifacts", "pristine_260803")
PRISTINE_PREFIX = ["aircraft/", "engine/"]
PRISTINE_FILES = ["GeoMathUtil.py", "FighterSim.py", "JSBSimWrapper.py",
                  "DogFightEnvWrapper.py", "JSBSimAIPLib.dll",
                  "src/dogfight/unreal/policies.py",
                  "src/dogfight/ai/rl_action_provider.py",
                  "run_unreal_inference.py",
                  "Rule_forTraining.xml"]


def source_for(rel):
    """이 파일을 어디서 읽을지. 수정 금지 영역이면 배포본 원본."""
    r = rel.replace(os.sep, "/")
    if any(r.startswith(x) for x in PRISTINE_PREFIX) or r in PRISTINE_FILES:
        cand = os.path.join(PRISTINE, rel)
        if os.path.isfile(cand):
            return cand, True
    return os.path.join(ROOT, rel), False


out = os.path.join(ROOT, "AeroFlyer_submission_%s.zip" % BUNDLE)
n = 0
total = 0
pristine_used = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for d in INCLUDE_DIRS:
        base = os.path.join(ROOT, d)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x != "__pycache__"]
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT)
                if skip(rel):
                    continue
                full, from_pristine = source_for(rel)
                if from_pristine:
                    pristine_used += 1
                z.write(full, rel)
                n += 1
                total += os.path.getsize(full)
    for fn in INCLUDE_FILES:
        full, from_pristine = source_for(fn)
        if os.path.isfile(full):
            if from_pristine:
                pristine_used += 1
            z.write(full, fn); n += 1; total += os.path.getsize(full)
        else:
            print("   (없음, 건너뜀) %s" % fn)

print("배포본 원본에서 담은 파일 %d개 (수정 금지 영역)" % pristine_used)
print("zip   %s" % out)
print("파일  %d개 · 원본 %.1f MB · 압축 %.1f MB"
      % (n, total / 1e6, os.path.getsize(out) / 1e6))
print()
print("번들  %s  (my_submission.py 의 BUNDLE_DIR 이 이것을 가리켜야 한다)" % BUNDLE)
import re
src = open(os.path.join(ROOT, "student", "my_submission.py"), encoding="utf-8").read()
m = re.search(r'^BUNDLE_DIR\s*=\s*"([^"]+)"', src, re.M)
cur = m.group(1) if m else "?"
ok = cur.rstrip("/").endswith(BUNDLE)
print("      현재 BUNDLE_DIR = %s   %s" % (cur, "OK" if ok else "!! 불일치 — 수정 필요"))
