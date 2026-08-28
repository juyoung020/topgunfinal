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
rem   --lag-steps 1,1,1,1,1,1,1,1,1,1 = self slot 2 (front / swapped spawn), both = previous snapshot (100 iter ago)
echo ==== [FINAL] snapshot sidecar for final_sp / stage 35 ====
"%CONDA_ENV%\python.exe" -u student\tools\snapshot_sidecar.py --tag %FINAL_SP_TAG% --name AeroFlyer --stage 35 --keep 100000 --lag-steps 1,1,1,1,1,1,1,1,1,1 --poll-seconds 30
echo ==== sidecar exited ====
pause
