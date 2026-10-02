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
rem ==== [2026-09-14] final_v12 RESUME - continue the head-on specialist, do NOT rewind ====
rem   ASCII comments only: cmd reads .bat as CP949 and UTF-8 Korean comments break into commands.
rem
rem   WHY THIS FILE EXISTS (do not just re-run launch_final_v12.bat):
rem     train_curriculum.py:1358 _restore_weights() restores --restore-checkpoint and RETURNS,
rem     skipping the resume-from-own-checkpoint path. The flag _explicit_checkpoint_restored is
rem     per-process, so re-running launch_final_v12.bat would restore peak_v11_iter2660 again
rem     and throw away the work already done. Measured in console.log:
rem       [Resume] Loaded state ... resume_from=0
rem       [Restore] Explicit native checkpoint -> ...\peak_v11_iter2660\checkpoint
rem     So the restore point here is v12's OWN latest checkpoint instead.
rem
rem   Checkpoint validated: iter_0060 has 24 files / 6.3 MB, byte-structure identical to the
rem   known-good peak_v11_iter2660 checkpoint (top-level file count alone is misleading - it is 3).
rem   Note: the previous run reached iter 75 (training_log.csv) but checkpoints are written every
rem   20 iterations, so iter_0060 is the newest one and about 15 iterations get redone. Cheap.
rem
rem   Everything else is unchanged from launch_final_v12.bat:
rem     head-on spawn 100 percent (_HEADON_ONLY), 16-dim observation (student.my_observation16),
rem     reward = teammate daeil original values, stage 35.
rem   Sidecar must run separately with --tag final_v12 and FINAL_SP_TAG=final_v12.
set "FINAL_SP_TAG=final_v12"

rem   [2026-09-14 updated] iter_0060 -> iter_0220. Pool trimmed to head-on 4 + self, continue from here.
rem   iter_0220 verified complete: 24 files / 6.3 MB counted RECURSIVELY (top level alone shows only 3).
set "CKPT=%~dp0artifacts\curriculum\AeroFlyer\final_v12\stage_35_selfplay_final\checkpoints\iter_0220"
if not exist "%CKPT%" (
  echo #### resume checkpoint missing: %CKPT%
  echo #### check for a newer iter_* under that checkpoints folder and update CKPT
  pause
  exit /b 1
)
set "RUNDIR=%~dp0artifacts\curriculum\AeroFlyer\%FINAL_SP_TAG%"
if not exist "%RUNDIR%" mkdir "%RUNDIR%"
set "RUNLOG=%RUNDIR%\console.log"
echo ==== [FINAL] HEADON SPECIALIST RESUME tag %FINAL_SP_TAG% from %CKPT%  ^>  %RUNLOG% ====
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
