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
rem ==== [2026-09-12 user request] final_v10: restart from our v9 lineage, head-on spawn 100% ====
rem   ASCII comments only: cmd reads .bat as CP949 and UTF-8 Korean comments break into commands (measured 2026-09-12).
rem   Restore point: final_v9 stage 35 checkpoint iter_11840 (latest of that run).
rem   Spawn: head-on only (_HEADON_ONLY in my_curriculum.py) = server HABFM measurement,
rem          5662.9 m nose-to-nose, 182.1 m lateral offset, yaw 180/0, 200 m/s.
rem   Reward: teammate daeil original values (live_tune from live_tune_BEFORE_REWARD_V9AIM_20260911.json),
rem           i.e. damage_taken 150 / loss -400 / draw -100 + health scale 400 / close_pot 15 / far 0.12 / tailslow off.
rem   Sidecar must run separately with --tag final_v10 and FINAL_SP_TAG=final_v10.
rem   OBSERVATION IS 17-DIM here, not 16: final_v9 was trained with student.my_observation
rem   (tail_aspect appended last, first layer 256x17). Using my_observation16 fails at restore
rem   with "size mismatch ... [256,17] vs [256,16]" (measured 2026-09-12).
set "FINAL_SP_TAG=final_v10"

set "CKPT=%~dp0artifacts\curriculum\AeroFlyer\final_v9\stage_35_selfplay_final\checkpoints\iter_11840"
if not exist "%CKPT%" (
  echo #### restore checkpoint missing: %CKPT%
  pause
  exit /b 1
)
set "RUNDIR=%~dp0artifacts\curriculum\AeroFlyer\%FINAL_SP_TAG%"
if not exist "%RUNDIR%" mkdir "%RUNDIR%"
set "RUNLOG=%RUNDIR%\console.log"
echo ==== [FINAL] HEADON tag %FINAL_SP_TAG% from %CKPT%  ^>  %RUNLOG% ====
"%CONDA_ENV%\python.exe" -u train_curriculum.py ^
  --algorithm ppo --use-lstm --lstm-cell-size 128 --max-seq-len 32 ^
  --num-env-runners 16 ^
  --train-batch-size 16384 --minibatch-size 1024 ^
  --gamma 0.995 --lr 2e-4 --num-epochs 3 --kl-coeff 0.1 --kl-target 0.02 --vf-loss-coeff 0.5 --model-vf-share-layers false ^
  --observation-mode custom --observation-module student.my_observation ^
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
