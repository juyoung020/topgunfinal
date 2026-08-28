@echo off
chcp 65001 > nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUNBUFFERED=1"
set "CONDA_ENV=C:\Users\user one\anaconda3\envs\aip"
if not exist "%CONDA_ENV%\python.exe" (
  echo #### CONDA_ENV path is wrong: %CONDA_ENV%
  pause
  exit /b 1
)
set "PATH=%CONDA_ENV%;%CONDA_ENV%\Library\bin;%CONDA_ENV%\Scripts;%CONDA_ENV%\Library\mingw-w64\bin;%PATH%"
cd /d "%~dp0"

rem ==== [본선] stage 35 selfplay_final 이어받기 (--resume + 최신 체크포인트). 첫 기동은 launch_final_selfplay.bat ====
rem   보상 = 8/16 v2 코드값 (피딜·고고도·과속·WEZ·스냅 = 0, 저고도선 2,500 ft) / 상대 = 우리 성장 스냅샷 3슬롯(Elo-PFSP)
rem   스폰 = 정면 2000ft (서버 실측 첫 프레임) 하나
rem   ** launch_final_sidecar.bat 을 먼저 띄울 것 ** (스냅샷 풀 갱신. 없으면 snap_0000=5220 하고만 싸운다)
rem   승급 없음. 300 iter 마다 실서버 판정(컷오프·r9980 양 슬롯)으로 정점을 잡아 보존할 것.
rem 최신 체크포인트를 자동으로 고른다 (final_sp/stage_35_selfplay_final/checkpoints/iter_NNNN 중 가장 큰 번호)
set "CKPT="
for /f "delims=" %%D in ('dir /b /ad /o-n "%~dp0artifacts\curriculum\AeroFlyer\final_sp\stage_35_selfplay_final\checkpoints\iter_*"') do if not defined CKPT set "CKPT=%~dp0artifacts\curriculum\AeroFlyer\final_sp\stage_35_selfplay_final\checkpoints\%%D"
if not exist "%CKPT%" (
  echo #### restore checkpoint missing: %CKPT%
  pause
  exit /b 1
)
set "RUNDIR=%~dp0artifacts\curriculum\AeroFlyer\final_sp"
if not exist "%RUNDIR%" mkdir "%RUNDIR%"
set "RUNLOG=%RUNDIR%\console.log"
echo ==== [FINAL] RESUME stage 35 from %CKPT%  ^>  %RUNLOG% ====
"%CONDA_ENV%\python.exe" -u train_curriculum.py ^
  --algorithm ppo --use-lstm --lstm-cell-size 128 --max-seq-len 32 ^
  --num-env-runners 16 ^
  --train-batch-size 16384 --minibatch-size 1024 ^
  --gamma 0.995 --lr 1e-4 --num-epochs 3 --kl-coeff 0.2 --vf-loss-coeff 0.5 --model-vf-share-layers false ^
  --observation-mode custom --observation-module student.my_observation ^
  --reward-module student.my_reward ^
  --stages-module student.my_curriculum ^
  --engagement-log-interval 25 --engagement-log-episodes 3 --engagement-log-steps 2200 ^
  --policy-probe-interval 25 ^
  --gate-eval-episodes 0 ^
  --policy-std-cap 0.10 --log-std-clip -1.2 ^
  --start-stage 35 --resume ^
  --restore-checkpoint "%CKPT%" ^
  --output-name AeroFlyer --output-tag final_sp ^
  2>&1 | "%CONDA_ENV%\python.exe" tools\tee.py "%RUNLOG%"
echo.
echo ==== trainer exited ====
pause
