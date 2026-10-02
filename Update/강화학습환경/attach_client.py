# -*- coding: utf-8 -*-
"""교전 서버 클라이언트 래퍼 — my_submission.py 를 수정하지 않고 BUNDLE_DIR 만 바꿔 띄운다.
사용: python attach_client.py --bundle <경로> --team-name <이름> [--server-ip ...] [--server-port ...]
"""
import argparse, sys, pathlib

ap = argparse.ArgumentParser(add_help=True)
ap.add_argument("--bundle", required=True)
known, rest = ap.parse_known_args()

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import student.my_submission as ms

bundle = known.bundle
ms.BUNDLE_DIR = bundle
print(f"[attach] BUNDLE_DIR = {bundle}", flush=True)

# [MOD-OBSSLICE 2026-09-10] 16차원 번들을 17차원 관측으로 붙일 때의 차원 정합.
#   my_observation 이 17채널이 된 뒤(tail_aspect 를 **맨 뒤**에 추가), 옛 16차원
#   번들에 그대로 넣으면 첫 층에서 즉사한다:
#     RuntimeError: mat1 and mat2 shapes cannot be multiplied (1x17 and 16x256)
#   학습 경로(student/rl_opponent.py)는 같은 이유로 이미 앞 16개를 잘라 쓴다.
#   제출 경로(student/my_submission.py)는 바이트 동일 유지 대상이라 손대지 않고,
#   래퍼인 여기서 관측 빌더를 감싼다. 앞 16채널은 의미가 그대로다.
import json as _json, pathlib as _pl
try:
    _md = _json.loads((_pl.Path(bundle) / "metadata.json").read_text(encoding="utf-8"))
    _need = int((_md.get("metadata") or _md)["observation_size"])
except Exception:
    _need = 0
if _need:
    import student.my_observation as _mo
    _full = int(_mo.OBSERVATION_SIZE)
    if _full != _need:
        _orig = _mo.build_observation

        def _sliced(*a, **kw):
            # build_observation 내부에 len(feats) == OBSERVATION_SIZE 단언이 있다.
            # 그래서 호출 동안에는 원래 값(17)으로 되돌려 두고, 반환값만 자른다.
            _mo.OBSERVATION_SIZE = _full
            try:
                v = _orig(*a, **kw)
            finally:
                _mo.OBSERVATION_SIZE = _need
            return v[:_need]

        _mo.build_observation = _sliced
        _mo.OBSERVATION_SIZE = _need
        print(f"[attach] obs {_full} -> {_need}차원으로 잘라서 공급 (번들 요구치)", flush=True)

sys.argv = ["my_submission.py"] + rest
ms._apply_cli_overrides()
ms.main()
