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

sys.argv = ["my_submission.py"] + rest
ms._apply_cli_overrides()
ms.main()
