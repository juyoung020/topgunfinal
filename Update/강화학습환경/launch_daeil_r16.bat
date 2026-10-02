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
rem ==== [2026-09-12 user request] branch daeil_r16 from daeil_r15 checkpoint iter_19380 ====
rem   ASCII comments only: cmd reads .bat as CP949 and UTF-8 Korean comments break into commands (measured).
rem   Branch point: daeil_r15 fixed-opponent win-loss margin peaked at +0.621 (win 0.710 / loss 0.088)
rem   over iter 19280-19372, then fell monotonically to +0.514 by 20108-20200.
rem   Restore path points at the daeil_r15 tree on purpose (tag differs, so auto-latest would not match).
rem   Reward / observation / hyperparameters are byte-identical to launch_daeil_resume.bat.
rem   Sidecar must run separately with --tag daeil_r16 and FINAL_SP_TAG=daeil_r16.
set "FINAL_SP_TAG=daeil_r16"

set "CKPT=%~dp0artifacts\curriculum\AeroFlyer\daeil_r15\stage_35_selfplay_final\checkpoints\iter_19380"
if not exist "%CKPT%" (
  echo #### restore checkpoint missing: %CKPT%
  pause
  exit /b 1
)
set "RUNDIR=%~dp0artifacts\curriculum\AeroFlyer\%FINAL_SP_TAG%"
if not exist "%RUNDIR%" mkdir "%RUNDIR%"
set "RUNLOG=%RUNDIR%\console.log"
echo ==== [FINAL] BRANCH tag %FINAL_SP_TAG% from %CKPT%  ^>  %RUNLOG% ====
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
