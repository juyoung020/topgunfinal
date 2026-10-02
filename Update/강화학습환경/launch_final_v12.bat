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
rem ==== [2026-09-13 user request] final_v12: rollback to final_v11 iter_2660, head-on specialist ====
rem   ASCII comments only: cmd reads .bat as CP949 and UTF-8 Korean comments break into commands (measured).
rem   Restore point: artifacts/models/AeroFlyer/peak_v11_iter2660/checkpoint
rem     (final_v11 peak: fixed-opponent margin +0.593, win 0.759 / loss 0.167; it fell to +0.117 afterwards).
rem   Two submission slots, so this run is the HEAD-ON SPECIALIST. Spawn stays head-on 100 percent.
rem   Pool change vs v11: opponents that know head-on go from 21 to 76 percent
rem     self snapshots 40 + head-on bundles 36 (peak_v11_1920/2120, peak_v10_headon_11900, final_v10_last_12740)
rem     + line-abreast-trained 11 kept at 24 percent for basics.
rem   Reward unchanged (teammate daeil original values). OBSERVATION IS 16-DIM (student.my_observation16).
rem   Sidecar must run separately with --tag final_v12 and FINAL_SP_TAG=final_v12.
set "FINAL_SP_TAG=final_v12"

set "CKPT=%~dp0artifacts\models\AeroFlyer\peak_v11_iter2660\checkpoint"
if not exist "%CKPT%" (
  echo #### restore checkpoint missing: %CKPT%
  pause
  exit /b 1
)
set "RUNDIR=%~dp0artifacts\curriculum\AeroFlyer\%FINAL_SP_TAG%"
if not exist "%RUNDIR%" mkdir "%RUNDIR%"
set "RUNLOG=%RUNDIR%\console.log"
echo ==== [FINAL] HEADON SPECIALIST tag %FINAL_SP_TAG% from %CKPT%  ^>  %RUNLOG% ====
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
