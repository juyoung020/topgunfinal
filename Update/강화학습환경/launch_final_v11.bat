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
rem ==== [2026-09-12 user request] final_v11: lineage swap to final_v2r6_iter7200, iteration count restarts ====
rem   ASCII comments only: cmd reads .bat as CP949 and UTF-8 Korean comments break into commands (measured).
rem   Lineage only. Spawn stays head-on 100% and reward stays the teammate daeil original values.
rem   Why: in final_v10 (head-on) the 7200 opponent went from 0.426 to 0.742 loss rate over 2517 games,
rem        so we continue from the lineage that beat us (same pattern as v7 -> v8).
rem   OBSERVATION IS 16-DIM here: final_v2r6 was trained with student.my_observation at 16 dims
rem        (bundle metadata observation_size=16, first layer 256x16). v10 was 17-dim - do not copy that line.
rem   Pool: v10 list minus final_v2r6_iter7200 (that is us now) and minus recv_scrim_exp025 (0.928 win).
rem   Sidecar must run separately with --tag final_v11 and FINAL_SP_TAG=final_v11.
set "FINAL_SP_TAG=final_v11"

set "CKPT=%~dp0artifacts\curriculum\AeroFlyer\final_v2r6\stage_35_selfplay_final\checkpoints\iter_7200"
if not exist "%CKPT%" (
  echo #### restore checkpoint missing: %CKPT%
  pause
  exit /b 1
)
set "RUNDIR=%~dp0artifacts\curriculum\AeroFlyer\%FINAL_SP_TAG%"
if not exist "%RUNDIR%" mkdir "%RUNDIR%"
set "RUNLOG=%RUNDIR%\console.log"
echo ==== [FINAL] LINEAGE SWAP tag %FINAL_SP_TAG% from %CKPT%  ^>  %RUNLOG% ====
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
