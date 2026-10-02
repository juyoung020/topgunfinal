"""
[학생 작성 파일] 경진대회 제출 — Unreal 서버 연결
=====================================================
학습한 모델을 경진대회 서버에 연결합니다.
BUNDLE_DIR 경로와 팀 이름을 설정한 뒤 이 파일을 실행하세요.

커맨드라인으로 직접 실행하는 방법 (권장)
-------------------------------------------
  # RL 모델 사용
  python run_unreal_inference.py --mode rl \\
      --bundle-dir artifacts/models/team01/v1 \\
      --team-name team01 \\
      --server-ip <서버IP> --server-port 9999

  # BT만 사용 (모델 없이)
  python run_unreal_inference.py --mode bt \\
      --bt-dll AIP_BASE.dll \\
      --bt-rule-xml Rule_forTraining.xml \\
      --team-name team01 \\
      --server-ip <서버IP>

  # RL + BT 하이브리드
  python run_unreal_inference.py --mode hybrid \\
      --bundle-dir artifacts/models/team01/v1 \\
      --bt-dll AIP_BASE.dll \\
      --bt-rule-xml Rule_팀이름.xml \\
      --hybrid-mode residual --residual-scale 0.35 \\
      --team-name team01 \\
      --server-ip <서버IP>

이 파일에서 직접 실행하려면
----------------------------
  python student/my_submission.py

아래 설정을 수정한 뒤 실행하면 됩니다.
"""
from __future__ import annotations

import time

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for p in (ROOT, SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from dogfight.ai.bt_action_provider import BTActionProvider
from dogfight.ai.bt_rule_manager import activate_rule_xml
from dogfight.ai.hybrid_action_provider import HybridActionProvider
from dogfight.ai.rl_action_provider import RLActionProvider
from dogfight.ai.rllib_utils import build_algorithm_from_bundle
from dogfight.ai.student_hooks import load_observation_hook
from dogfight.unreal import AIType, ProviderCommandPolicy, UnrealAIPilotUDPClient
from student.deck_guard import DeckGuardProvider  # [2026-08-31] 저고도 pitch 강제 가드


# =============================================================================
# Ray-free 추론 팩토리  [2026-08-19]
# =============================================================================
# 배포본 기본 팩토리 build_algorithm_from_bundle() 은 rllib_utils.py:740 에서
# **ray.init() 로 로컬 Ray 클러스터를 띄운다**. 추론에는 전혀 필요 없는데
#   - 기동에 수십 초가 걸리고
#   - 실제로 이 PC 에서 학습이 도는 중에 raylet 기동 타임아웃으로 **실패**했다
#     ("The current node timed out during startup")
#   - 운영진이 자기 PC 에서 직접 실행하므로 여기서 죽으면 참가 제한이다
# RLActionProvider 는 algorithm_factory 를 **주입**받으므로(rl_action_provider.py:17)
# src/ 를 건드리지 않고 student/ 쪽에서만 대체할 수 있다.
#
# 필요한 인터페이스는 딱 둘이다:
#   * 가중치 적용 — get_policy() 가 AttributeError 면 env_runner.set_state() 로 폴백
#   * 추론      — get_module(policy_id) 가 RLModule 반환
# judge10.py 가 쓰는 것과 같은 경로다(수천 판 검증됨).
USE_RAY_FREE_INFERENCE = True


class _RayFreeAlgorithm:
    """ray.init() 없이 번들 가중치만 올리는 최소 알고리즘 대역."""

    def __init__(self, metadata: dict):
        import numpy as np
        from gymnasium.spaces import Box
        from ray.rllib.algorithms.ppo.torch.ppo_torch_rl_module import PPOTorchRLModule
        from ray.rllib.core.rl_module.rl_module import RLModuleSpec

        md = metadata["metadata"]
        obs_size = int(md["observation_size"])
        act_dim = int(md["action_dim"])
        self._module = RLModuleSpec(
            module_class=PPOTorchRLModule,
            observation_space=Box(-np.inf, np.inf, (obs_size,), np.float32),
            action_space=Box(-1.0, 1.0, (act_dim,), np.float32),
            inference_only=True,
            model_config=dict(md["model_config"]),
        ).build()

    # get_policy 를 **정의하지 않는다** — RLActionProvider 가 AttributeError 를
    # 잡아 아래 env_runner.set_state() 경로로 폴백하게 하려는 의도다.
    @property
    def env_runner(self):
        return self

    def set_state(self, state: dict) -> None:
        self._module.set_state(state["rl_module"])
        self._module.eval()

    def get_module(self, policy_id=None):
        return self._module

    def stop(self) -> None:
        pass


def _algorithm_factory(metadata: dict):
    if USE_RAY_FREE_INFERENCE:
        return _RayFreeAlgorithm(metadata)
    return build_algorithm_from_bundle(metadata)


# =============================================================================
# TODO: 아래 설정을 팀에 맞게 수정하세요.
# =============================================================================

TEAM_NAME = "에어프라이어"     # [2026-08-19 사용자 확정] '에어로프라이어' 아님.
                               # 서버 등록명(한글). UTF-8 18바이트 < 프로토콜 버퍼 29바이트라 안전.
                               # 로컬 폴더는 AeroFlyer 를 쓴다 — 한글 폴더는 cp949 콘솔에서 깨진다.
SERVER_IP = "221.151.77.208"                       # TODO: 경진대회 서버 IP
SERVER_PORT = 9999

# 사용할 백엔드 모드 선택: "rl" | "bt" | "hybrid"
MODE = "rl"

# RL 모드 설정
# [2026-08-19] v3b 는 **존재하지 않는 경로**였다(제출 시 즉시 FileNotFoundError).
# submission_v1 = snap_12241 사본. 10 Hz(step_ratio=6) 학습물이라 ACTION_REPEAT=6 과 짝이다.
#   근거: 고정 챔피언 ladder_iter5220 상대 판정 16회 중 최고 마진 +0.089,
#         대회 공식 컷오프 모델(unreal_bt_client.exe) 상대 1승.
# 20 Hz 학습물로 교체하려면 ACTION_REPEAT 을 3 으로 같이 바꿔야 한다.
BUNDLE_DIR = "artifacts/models/AeroFlyer/sub_cand_ladder5220"   # 학습 산출물 경로
OBSERVATION_MODE = "custom"                        # 학습 시 사용한 관측 모드와 동일해야 함
OBSERVATION_MODULE = "student.my_observation"      # 우리 관측 파일 (my_train과 동일하게 맞춤)

# BT 모드 설정
# - 기본 배포 Rule은 Rule_forTraining.xml입니다.
# - 팀별 BT DLL/XML을 제출하는 경우 파일을 Release 루트에 두고 아래 이름을 바꾸세요.
BT_DLL = "AIP_BASE.dll"
BT_RULE_XML = "Rule_forTraining.xml"  # 예: "Rule_team01.xml"

# Hybrid 모드 설정 (MODE="hybrid" 일 때만 사용)
HYBRID_MODE = "residual"   # "residual" | "blend" | "switch"
RESIDUAL_SCALE = 0.35      # residual 모드 강도 (0~1, 클수록 RL 비중 증가)
ALPHA = 0.5                # blend 모드 비율 (alpha × RL + (1-alpha) × BT)

# 연결 설정
AI_TYPE = AIType.ReinforcementLearning
HEARTBEAT_SEC = 1.0
COMMAND_DELAY_SEC = 0.0
RECV_TIMEOUT_SEC = 0.2
ACTION_REPEAT = 6          # 학습 step_ratio=6과 맞춰 6개 PlaneInfo pair마다 새 policy 호출
DEBUG_ACTION_REPEAT = False


# =============================================================================
# 예시: 학습 결과 확인 (로컬 테스트용 백엔드)
# =============================================================================
# 경진대회 제출 전 로컬에서 결과 확인:
#   python run_local_dogfight.py \\
#       --ownship-backend rl \\
#       --ownship-bundle-dir artifacts/models/team01/v1 \\
#       --target-backend bt \\
#       --save-log


# =============================================================================
# 실행 로직 (수정 불필요)
# =============================================================================

def build_action_provider():
    if MODE == "bt":
        print(f"[{TEAM_NAME}] BT 백엔드 사용: {BT_DLL}")
        return BTActionProvider(dll_name=BT_DLL)

    bundle_path = ROOT / BUNDLE_DIR
    if not bundle_path.exists():
        raise FileNotFoundError(
            f"모델 번들을 찾을 수 없습니다: {bundle_path}\n"
            f"먼저 학습을 완료하고 BUNDLE_DIR 경로를 확인하세요."
        )

    print(f"[{TEAM_NAME}] RL 모델 로드: {bundle_path}")
    rl_provider = RLActionProvider(
        bundle_dir=str(bundle_path),
        algorithm_factory=_algorithm_factory,
    )

    if MODE == "rl":
        print(f"[{TEAM_NAME}] RL 전용 모드")
        if os.environ.get("DECK_GUARD", "1") != "0":
            print(f"[{TEAM_NAME}] 덱 가드 활성: (alt<1500ft 또는 지면도달<4s) & vz<-10m/s -> 롤수평 + 당김(|roll|<=100deg) + throttle idle/max (DECK_GUARD=0 비활성)")
            return DeckGuardProvider(rl_provider)
        return rl_provider

    # hybrid
    bt_provider = BTActionProvider(dll_name=BT_DLL)
    print(f"[{TEAM_NAME}] Hybrid 모드: {HYBRID_MODE} (scale={RESIDUAL_SCALE}, alpha={ALPHA})")
    return HybridActionProvider(
        primary_provider=rl_provider,
        secondary_provider=bt_provider,
        mode=HYBRID_MODE,
        alpha=ALPHA,
        residual_scale=RESIDUAL_SCALE,
    )


def main():
    print(f"=== {TEAM_NAME} 경진대회 클라이언트 시작 ===")
    print(f"서버: {SERVER_IP}:{SERVER_PORT}")
    print(f"모드: {MODE}")
    if MODE in {"bt", "hybrid"}:
        print(f"BT DLL/XML: {BT_DLL} / {BT_RULE_XML}")

    with activate_rule_xml(BT_RULE_XML, ROOT):
        action_provider = build_action_provider()
        observation_hook = (
            load_observation_hook(OBSERVATION_MODULE)
            if OBSERVATION_MODULE
            else None
        )
        command_policy = ProviderCommandPolicy(
            action_provider=action_provider,
            observation_mode=observation_hook["mode"] if observation_hook else OBSERVATION_MODE,
            observation_fn=observation_hook["build_observation"]
            if observation_hook
            else None,
            ownship_force_side=1,
            target_force_side=2,
            action_repeat=ACTION_REPEAT,
            debug_action_repeat=DEBUG_ACTION_REPEAT,
        )

        client = UnrealAIPilotUDPClient(
            command_policy=command_policy,
            server_ip=SERVER_IP,
            server_port=SERVER_PORT,
            team_name=TEAM_NAME,
            ai_type=AI_TYPE,
            heartbeat_interval_sec=HEARTBEAT_SEC,
            command_delay_sec=COMMAND_DELAY_SEC,
            recv_timeout_sec=RECV_TIMEOUT_SEC,
            enable_terminal_monitor=True,   # 패킷 모니터 표시
        )

        # [MOD-RECONNECT] 2026-08-21 — 한 번 끊기면 그 판을 통째로 잃는다.
        #
        # src/dogfight/unreal/client.py:244 의 _receive_loop 는 OSError 에서
        # 즉시 break 한다. 윈도우 UDP 는 서버가 잠깐 안 받으면 ICMP
        # port-unreachable 을 돌려주고, 그게 ConnectionResetError(OSError)로
        # 올라온다. 실측: 로컬 교전서버에서 판이 끝나거나 OpenServer 가 잠깐
        # 꺼질 때마다 클라이언트가 **에러 한 줄 없이** 종료됐다.
        #
        # 대회에서 이러면 그 판은 몰수다. 플랫폼 파일은 손대지 않고 여기서
        # 새 소켓으로 다시 붙는다. 정상 진행 중에는 이 루프가 한 번만 돈다.
        try:
            while True:
                try:
                    client.run()
                except Exception as exc:
                    print(f"[{TEAM_NAME}] 접속 예외: {exc}")
                print(f"[{TEAM_NAME}] 서버 연결이 끊겼습니다. 3초 뒤 재접속합니다.")
                time.sleep(3.0)
                client = UnrealAIPilotUDPClient(
                    command_policy=command_policy,
                    server_ip=SERVER_IP,
                    server_port=SERVER_PORT,
                    team_name=TEAM_NAME,
                    ai_type=AI_TYPE,
                    heartbeat_interval_sec=HEARTBEAT_SEC,
                    command_delay_sec=COMMAND_DELAY_SEC,
                    recv_timeout_sec=RECV_TIMEOUT_SEC,
                    enable_terminal_monitor=True,
                )
        except KeyboardInterrupt:
            print(f"[{TEAM_NAME}] 사용자 중단(Ctrl+C)")
        finally:
            action_provider.close()
            print(f"[{TEAM_NAME}] 클라이언트 종료")


def _apply_cli_overrides() -> None:
    """[2026-08-20] 서버 주소·포트·팀명을 명령행으로 받는다.

    왜 여기인가: 대회 배포본의 run_unreal_inference.py 가 정식 CLI 진입점이지만
    그 파일은 rllib_utils.build_algorithm_from_bundle 을 쓰고, 그 함수는 추론에
    필요도 없는 ray.init() 으로 로컬 Ray 클러스터를 띄운다(부하 중 기동 실패 실측).
    run_unreal_inference.py 는 제출 시 배포본과 바이트 동일하게 유지해야 하므로
    고칠 수 없다. 그래서 실행은 이 파일로 하고, 필요한 인자만 여기서 받는다.

    인자를 안 주면 위쪽 상수를 그대로 쓴다(종전 동작과 동일).
    """
    import argparse

    global SERVER_IP, SERVER_PORT, TEAM_NAME, MODE, ACTION_REPEAT

    ap = argparse.ArgumentParser(
        description="에어프라이어 대회 클라이언트 (RL, Ray-free 추론)")
    ap.add_argument("--server-ip", default=None, help="경진대회 서버 IP")
    ap.add_argument("--server-port", type=int, default=None, help="서버 UDP 포트")
    ap.add_argument("--team-name", default=None, help="서버에 등록할 팀명")
    ap.add_argument("--mode", default=None, choices=["rl", "bt", "hybrid"])
    ap.add_argument("--action-repeat", type=int, default=None,
                    help="정책 재계산 주기(PlaneInfo 쌍 단위). 학습 step_ratio 와 맞출 것")
    args = ap.parse_args()

    if args.server_ip:
        SERVER_IP = args.server_ip
    if args.server_port:
        SERVER_PORT = args.server_port
    if args.team_name:
        TEAM_NAME = args.team_name
    if args.mode:
        MODE = args.mode
    if args.action_repeat:
        ACTION_REPEAT = args.action_repeat


if __name__ == "__main__":
    _apply_cli_overrides()
    main()
