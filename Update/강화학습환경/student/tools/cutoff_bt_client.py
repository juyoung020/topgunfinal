# -*- coding: utf-8 -*-
"""교전서버에 **컷오프 BT 복원본**(student/cutoff_bt.py)을 붙이는 클라이언트.

제출 경로(my_submission)를 그대로 쓰되 build_action_provider 만 갈아끼운다.
원본 컷오프와 같은 10 Hz 를 쓰도록 action_repeat=6 (exe 기본 --action-repeat 6).

사용: python student/tools/cutoff_bt_client.py --team-name CutoffReplica
                                              [--server-ip 127.0.0.1] [--server-port 9999]
"""
import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

ap = argparse.ArgumentParser(add_help=True)
known, rest = ap.parse_known_args()

import student.cutoff_bt as cbt
import student.my_submission as ms
from dogfight.ai.action_provider import ActionResult


class _ServerProvider(cbt.CutoffBTProvider):
    """교전서버 좌표·단위(frame_server)로 도는 복원본. 홀드는 정책 쪽 action_repeat 이 한다."""

    def __init__(self):
        super().__init__(step_ratio=1, frame=cbt.frame_server)
        self._n = 0

    def compute_action(self, context):
        a = self.bt.step(context.ownship_state, context.target_state, self.frame)
        act = [float(a[0]), float(a[1]), float(a[2]), float(a[3])]
        self._n += 1
        if self._n % 60 == 1:
            bb = self.bt.bb
            print(f"[cbt] t~{self._n / 60:5.1f}s {cbt.PHASE_NAME[bb.phase]:9s} "
                  f"dist {bb.dist:7.1f} LOS {bb.los:6.1f} AO {bb.ao:6.1f} "
                  f"aim {bb.aiming} -> roll {act[0]:+.3f} pitch {act[1]:+.3f} thr {act[3]:.2f}",
                  flush=True)
        return ActionResult(action=act, source="cutoff_bt_replica",
                            info={"phase": cbt.PHASE_NAME[self.bt.bb.phase]})


ms.build_action_provider = lambda: _ServerProvider()
ms.ACTION_REPEAT = 6
ms.MODE = "rl"

sys.argv = ["my_submission.py"] + rest
ms._apply_cli_overrides()
ms.ACTION_REPEAT = 6
print("[cbt] 컷오프 BT 복원본으로 접속 (action_repeat=6)", flush=True)
ms.main()
