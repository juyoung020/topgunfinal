# -*- coding: utf-8 -*-
"""실서버 검증 — 학습을 멈춘 뒤 한 판 재고 세 가지를 판정한다.

**측정이다, 학습이 아니다.** 실행 전에 트레이너·sidecar 를 반드시 멈춘다:
배경 부하가 있으면 서버 틱이 39 Hz 로 떨어져 같은 매치업의 승패가 뒤집힌 전례가 있다.
아래 가드가 살아 있는 프로세스를 찾으면 스스로 거부한다.

판정 3가지 (사전 등록)
  1. [HZ]      서버 틱이 60 근처인가. 45 미만이면 그 판은 버린다.
  2. 나선 추락  마지막 8 초에 |롤|>90 & 피치<0 이 지속되는가.
               실측 기준: 추락판 51.9% / 비추락 14.8% -> 35% 넘으면 징후.
  3. 결착       붙어서 격추로 끝나는가, 200 초 시간종료인가.

가중치 해시도 찍는다 — 오프라인에서 잰 것과 같은 정책이 돌았는지 즉시 대조된다.
    nocrash0_snap_0281 = fa4807512fc9ae26
    hp1x_snap_0260     = 9020e4df72791112
    sub_cand_peak3100  = 8fe5c6316719e7c5   (현 submission_v1)

사용법
    python tools/server_verify.py                      # submission_v1
    python tools/server_verify.py nocrash0_snap_0281    # 번들 지정
    python tools/server_verify.py <번들> 9998 210        # 포트·측정초
"""
import os, sys, time, math, hashlib, threading, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "src"))

BUNDLE = sys.argv[1] if len(sys.argv) > 1 else "submission_v1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9998
SEC = float(sys.argv[3]) if len(sys.argv) > 3 else 210.0

# ── 가드: 학습이 돌고 있으면 거부한다 ──────────────────────────────────
# wmic 은 Windows 11 에서 빠졌다. PowerShell 로 본다.
try:
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
          "ForEach-Object { $_.CommandLine }")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True, timeout=30).stdout or ""
    busy = [n for n in ("train_curriculum", "snapshot_sidecar") if n in out]
    if busy:
        print("!! 아직 돌고 있다: %s" % ", ".join(busy))
        print("   배경 부하가 서버 틱을 39 Hz 로 떨어뜨린다. 먼저 멈춰라:")
        print("     ray stop --force   그리고 트레이너/sidecar 창을 닫는다")
        sys.exit(2)
except subprocess.TimeoutExpired:
    print("[가드] 프로세스 확인 실패 -- 학습이 멈췄는지 직접 확인하라")

bundle_dir = os.path.join(ROOT, "artifacts", "models", "AeroFlyer", BUNDLE)
wf = os.path.join(bundle_dir, "policy_weights.pkl.gz")
if not os.path.isfile(wf):
    print("!! 번들 없음: %s" % bundle_dir); sys.exit(1)
sha = hashlib.sha256(open(wf, "rb").read()).hexdigest()[:16]
print("번들   %s" % BUNDLE)
print("해시   %s   <- 오프라인 값과 같아야 한다" % sha)
print()

# ── 제출 경로 그대로 구성한다 (my_submission.main 과 동일 순서) ────────
import student.my_submission as SUB
from dogfight.ai.student_hooks import load_observation_hook
from dogfight.ai.bt_rule_manager import activate_rule_xml
from dogfight.unreal import ProviderCommandPolicy, UnrealAIPilotUDPClient

SUB.BUNDLE_DIR = os.path.join("artifacts", "models", "AeroFlyer", BUNDLE)


class Probe(ProviderCommandPolicy):
    """정책은 손대지 않고 호출 시각과 자세만 곁들여 기록한다."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.stamps = []
        self.rows = []          # (t, alt, roll, pitch, dist)

    def compute_command(self, context):
        cmd = super().compute_command(context)
        self.stamps.append(time.perf_counter())
        try:
            me, en = context.my_plane, context.enemy_plane
            self.rows.append((self.stamps[-1], float(me.position[2]),
                              float(me.rotation[0]), float(me.rotation[1]),
                              math.dist(tuple(me.position), tuple(en.position))))
        except Exception:
            pass
        return cmd


with activate_rule_xml(SUB.BT_RULE_XML, SUB.ROOT):
    provider = SUB.build_action_provider()
    hook = (load_observation_hook(SUB.OBSERVATION_MODULE)
            if SUB.OBSERVATION_MODULE else None)
    pol = Probe(
        action_provider=provider,
        observation_mode=hook["mode"] if hook else SUB.OBSERVATION_MODE,
        observation_fn=hook["build_observation"] if hook else None,
        ownship_force_side=1, target_force_side=2,
        action_repeat=SUB.ACTION_REPEAT,
        debug_action_repeat=SUB.DEBUG_ACTION_REPEAT,
    )
    client = UnrealAIPilotUDPClient(
        command_policy=pol, server_ip=SUB.SERVER_IP, server_port=PORT,
        team_name=SUB.TEAM_NAME, ai_type=SUB.AI_TYPE,
        heartbeat_interval_sec=SUB.HEARTBEAT_SEC,
        command_delay_sec=SUB.COMMAND_DELAY_SEC,
        recv_timeout_sec=SUB.RECV_TIMEOUT_SEC,
        enable_terminal_monitor=False)

    print("127.0.0.1:%d 접속. 뷰어에서 Start 를 눌러라. %.0f초 측정." % (PORT, SEC))
    threading.Thread(target=client.run, daemon=True).start()
    t_end = time.time() + SEC + 30.0
    while time.time() < t_end:
        time.sleep(1.0)
        if pol.stamps and (time.perf_counter() - pol.stamps[0]) >= SEC:
            break
    try:
        client.stop()
    except Exception:
        pass
    try:
        provider.close()
    except Exception:
        pass

n = len(pol.stamps)
print()
if n < 30:
    print("PlaneInfo 를 %d개만 받았다 -- Start 를 안 눌렀거나 접속 실패." % n)
    sys.exit(1)

dur = pol.stamps[-1] - pol.stamps[0]
hz = (n - 1) / dur * SUB.ACTION_REPEAT      # 정책 호출은 ACTION_REPEAT 프레임마다
print("=" * 60)
print("1) 서버 틱   %.1f Hz   %s" % (hz, "OK" if hz >= 45 else "!! 이 판은 버린다"))
print("   정책 주기 %.1f Hz  (학습 10.0)" % (hz / SUB.ACTION_REPEAT))

R = pol.rows
if len(R) > 20:
    dt = max((R[-1][0] - R[0][0]) / max(len(R) - 1, 1), 1e-6)
    seg = R[-max(int(8.0 / dt), 5):]
    bad = sum(1 for _, _, ro, pi, _ in seg if abs(ro) > 90 and pi < 0) / len(seg)
    alts = [a for _, a, _, _, _ in R]
    ds = sorted(d for _, _, _, _, d in R)
    print()
    print("2) 나선 추락  마지막 8초 |롤|>90 & 피치<0  %.1f%%   %s"
          % (bad * 100, "!! 나선 징후" if bad > 0.35 else "정상"))
    print("   기준: 추락판 51.9%% / 비추락 14.8%%")
    print("   고도  시작 %.0f  최저 %.0f  끝 %.0f m" % (alts[0], min(alts), alts[-1]))
    print()
    print("3) 교전     거리 중앙 %.0f m  최소 %.0f m" % (ds[len(ds) // 2], ds[0]))
    print("   판 길이 %.0f초 %s" % (dur, "(200초 = 시간종료)" if dur > 195 else ""))
print("=" * 60)
print("해시 %s -- 오프라인 값과 다르면 다른 정책이 돌았다는 뜻이다." % sha)
