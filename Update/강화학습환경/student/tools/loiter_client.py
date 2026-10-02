# -*- coding: utf-8 -*-
"""[2026-09-04 사용자 지시] 실서버용 룰베이스 loiter 상대.
받은 AeroFlyer_LowAltitude_Loiter_3000ft_20260904.zip 은 가중치가 없는 환경 설정(JSON)이라
BattleServer 클라이언트로 못 붙는다. 그 설정(target_mode=loiter, bank 30deg, pitch 0)을
같은 동작의 클라이언트로 구현해 교전서버에 접속시킨다.

액션 부호(실측, deck_guard.py 와 동일 근거): pitch -1 = 기수 up / +1 = 숙임, roll +1 = 우측 롤 증가.
사용: python student/tools/loiter_client.py --team-name loiter3000 [--bank 30] [--pitch 0] [--throttle 0.7]
"""
import argparse, sys, pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))

from dogfight.ai.action_provider import ActionProvider, ActionResult

ROLL_IDX, PITCH_IDX = 3, 4


class LoiterProvider(ActionProvider):
    """뱅크/피치를 목표값으로 유지하는 P 제어. RL 무관, 상수 선회."""

    def __init__(self, bank=30.0, pitch=0.0, throttle=0.7):
        self.bank = float(bank); self.pitch = float(pitch); self.throttle = float(throttle)

    def compute_action(self, context):
        s = getattr(context, "ownship_state", None)
        if s is None:
            return ActionResult(action=np.array([0.0, 0.0, 0.0, self.throttle], np.float32), source="loiter")
        roll = ((float(s[ROLL_IDX]) + 180.0) % 360.0) - 180.0
        pit = float(s[PITCH_IDX])
        a_roll = float(np.clip((self.bank - roll) / 30.0, -1.0, 1.0))
        a_pitch = float(np.clip((pit - self.pitch) / 30.0, -1.0, 1.0))
        return ActionResult(action=np.array([a_roll, a_pitch, 0.0, self.throttle], np.float32), source="loiter")


ap = argparse.ArgumentParser(add_help=True)
ap.add_argument("--bank", type=float, default=30.0)
ap.add_argument("--pitch", type=float, default=0.0)
ap.add_argument("--throttle", type=float, default=0.7)
known, rest = ap.parse_known_args()

import student.my_submission as ms
ms.build_action_provider = lambda: LoiterProvider(known.bank, known.pitch, known.throttle)
print(f"[loiter] bank={known.bank} pitch={known.pitch} throttle={known.throttle}", flush=True)

sys.argv = ["my_submission.py"] + rest
ms._apply_cli_overrides()
ms.main()
