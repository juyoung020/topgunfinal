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
rem ==== [2026-09-14 user request] daeil_headon: light head-on fine-tune from the daeil lineage ====
rem   ASCII comments only: cmd reads .bat as CP949 and UTF-8 Korean comments break into commands.
rem
rem   BASE: peak_daeil_r16_iter21100 (NATIVE checkpoint, 24 files / 6.4 MB verified recursively).
rem     The actual submitted model recv_daeil_iter8820 has NO native checkpoint anywhere locally
rem     (weights sha256 06E59085... matches nothing under artifacts/curriculum/AeroFlyer/daeil_*),
rem     so resuming from it would need --init-bundle, which throws away optimizer state
rem     (that cost 712 iterations once). Same lineage, optimizer intact -> use r16.
rem
rem   MINIMAL CHANGE ON PURPOSE: opponent pool is identical to daeil_r16; only the SPAWN changes
rem   to head-on 100 percent (tag registered in _HEADON_ONLY). daeil meets the opponents it already
rem   knows, but nose-to-nose.
rem     Why not raise the head-on-trained opponent share: final_v12 did that (76 percent) and
rem     REGRESSED - head-on margin +0.13 -> -0.28 while beating only its own snapshots (+0.27).
rem
rem   LR 2e-4 -> 1e-4 on purpose. This is a light adaptation of our best model, not a new run;
rem   a smaller step reduces the risk of wrecking what daeil already does well. Everything else
rem   (observation 16-dim, reward, stage 35, batch, kl, std cap) is byte-identical to launch_daeil_r16.bat.
rem
rem   Checkpoints land every 20 iterations -> preserve the best point as a bundle before it decays.
rem   Sidecar must run separately with --tag daeil_headon and FINAL_SP_TAG=daeil_headon.
set "FINAL_SP_TAG=daeil_headon"

set "CKPT=%~dp0artifacts\models\AeroFlyer\peak_daeil_r16_iter21100\checkpoint"
if not exist "%CKPT%" (
  echo #### restore checkpoint missing: %CKPT%
  pause
  exit /b 1
)
set "RUNDIR=%~dp0artifacts\curriculum\AeroFlyer\%FINAL_SP_TAG%"
if not exist "%RUNDIR%" mkdir "%RUNDIR%"
set "RUNLOG=%RUNDIR%\console.log"
echo ==== [FINAL] HEADON FINE-TUNE tag %FINAL_SP_TAG% from %CKPT%  ^>  %RUNLOG% ====
"%CONDA_ENV%\python.exe" -u train_curriculum.py ^
  --algorithm ppo --use-lstm --lstm-cell-size 128 --max-seq-len 32 ^
  --num-env-runners 16 ^
  --train-batch-size 16384 --minibatch-size 1024 ^
  --gamma 0.995 --lr 1e-4 --num-epochs 3 --kl-coeff 0.1 --kl-target 0.02 --vf-loss-coeff 0.5 --model-vf-share-layers false ^
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
