에어프라이어 (AeroFlyer) — 실행 방법
======================================================

1. 라이브러리 설치
   pip install "torch==2.11.0" "ray[rllib]>=2.54.0" numpy "gymnasium>=1.2.2" "dm-tree>=0.1.10" "pymap3d>=3.1.0" "scipy>=1.17.1" filelock

2. 실행 (압축 푼 폴더에서)
   python student/my_submission.py --server-ip <서버IP> --server-port 9999

   인자를 생략하면 student/my_submission.py 의 기본값을 씁니다.
     SERVER_IP = 221.151.77.208 / SERVER_PORT = 9999

3. 접속 확인
   화면 표의 RX 에 MT_SetPlaneID 가 찍히면 접속 성공입니다.

----------------------------------------------------------------------
팀명       에어프라이어
모델       artifacts/models/AeroFlyer/sub_cand_ladder5220
환경       Python 3.11 / Windows x64 / GPU 불필요 (CPU 추론)
기타 인자  --team-name  --mode(rl|bt|hybrid)  --action-repeat(기본 6)
