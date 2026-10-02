@echo off
chcp 65001 > nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "CONDA_ENV=C:\Users\user one\anaconda3\envs\aip"
cd /d "%~dp0"
if "%FINAL_SP_TAG%"=="" set "FINAL_SP_TAG=final_sp"
rem ==== [본선] stage 35 self-play 스냅샷 sidecar — 트레이너보다 먼저 띄운다. 반드시 1개만 ====
rem   killfloor_probe(100 iter 마다) -> snapshots\snap_<iter> 승격 -> final_sp\live_tune.json 의 target_pool self 슬롯 갱신
rem   --keep 100000 = GC 끄기 (sidecar 2개가 서로 스냅샷을 지워 러너가 죽은 전례)
rem   --lag-steps 0,20,60 = self slot 3개 (v7): 지금 / -400 iter / -1200 iter. 연속 스냅샷만 쓰면
rem     상대 셋이 전부 '거의 지금의 나'가 되어 순환(A>B>C>A)이 생긴다
echo ==== [FINAL] snapshot sidecar for final_sp / stage 35 ====
"%CONDA_ENV%\python.exe" -u student\tools\snapshot_sidecar.py --tag %FINAL_SP_TAG% --name AeroFlyer --stage 35 --keep 100000 --lag-steps 0,20,60 --poll-seconds 30
echo ==== sidecar exited ====
pause
