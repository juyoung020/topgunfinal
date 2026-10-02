@echo off
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
rem ==== resume stage 35 selfplay_final: latest checkpoint of tag %FINAL_SP_TAG% + --resume ====
rem   run launch_final_sidecar.bat first (snapshot pool). pool/spawn/reward = student/my_curriculum.py stage 35 + live_tune.json
rem   replay log: every 25 iter x 6 episodes (doubled 2026-08-29, judging = student/tools/replay_judge.py)
set "FINAL_SP_TAG=daeil_r15"

set "CKPT="
rem [2026-09-02] dir /o-n is ALPHABETICAL: iter_9980 > iter_17640. numeric sort via powershell (7,700 iter rewind incident)
for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-ChildItem -Directory '%~dp0artifacts\curriculum\AeroFlyer\%FINAL_SP_TAG%\stage_35_selfplay_final\checkpoints' -Filter 'iter_*' | Sort-Object { [int]($_.Name -replace 'iter_','') } | Select-Object -Last 1).Name"') do if not defined CKPT set "CKPT=%~dp0artifacts\curriculum\AeroFlyer\%FINAL_SP_TAG%\stage_35_selfplay_final\checkpoints\%%D"
if not exist "%CKPT%" (
  echo #### restore checkpoint missing: %CKPT%
  pause
  exit /b 1
)
set "RUNDIR=%~dp0artifacts\curriculum\AeroFlyer\%FINAL_SP_TAG%"
if not exist "%RUNDIR%" mkdir "%RUNDIR%"
set "RUNLOG=%RUNDIR%\console.log"
echo ==== [FINAL] RESUME tag %FINAL_SP_TAG% from %CKPT%  ^>  %RUNLOG% ====
"%CONDA_ENV%\python.exe" -u train_curriculum.py ^
  --algorithm ppo --use-lstm --lstm-cell-size 128 --max-seq-len 32 ^
  --num-env-runners 16 ^
  --train-batch-size 16384 --minibatch-size 1024 ^
  --gamma 0.995 --lr 2e-4 --num-epochs 3 --kl-coeff 0.1 --kl-target 0.02 --vf-loss-coeff 0.5 --model-vf-share-layers false ^
  --observation-mode custom --observation-module student.my_observation16 ^
  --reward-module student.my_reward ^
  --stages-module student.my_curriculum ^
  --engagement-log-interval 25 --engagement-log-episodes 6 --engagement-log-steps 2200 ^
  --policy-probe-interval 25 ^
  --gate-eval-episodes 0 ^
  --policy-std-cap 0.10 --log-std-clip -1.2 ^
  --start-stage 35 --resume ^
  --restore-checkpoint "%CKPT%" ^
  --output-name AeroFlyer --output-tag %FINAL_SP_TAG% ^
  2>&1 | "%CONDA_ENV%\python.exe" tools\tee.py "%RUNLOG%"
echo.
echo ==== trainer exited ====
pause
