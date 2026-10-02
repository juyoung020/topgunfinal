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
rem ==== [2026-09-14 user request] resume daeil_headon from the kept iter_0420 peak ====
rem   ASCII comments only: cmd reads .bat as CP949 and UTF-8 Korean comments break into commands.
rem
rem   WHY: the first daeil_headon run plateaued at win 0.75 over iter 400-479 and was stopped at 508.
rem   iter 400-419 was the best block (reward 879.0 / win 0.772), preserved as peak_daeilheadon_iter0420.
rem   Restarting from there with a FINER checkpoint interval (20 -> 10, set in my_curriculum.py
rem   stage 35) so the peak can be captured more precisely.
rem
rem   Restore point is the kept bundle's checkpoint, NOT the run directory's latest -
rem   train_curriculum.py:1358 restores --restore-checkpoint and returns, so whatever is named
rem   here is what actually loads. Verified complete: 24 files / 6.3 MB (count RECURSIVELY;
rem   the top level alone shows only 3).
rem
rem   snap_0000 already exists in this run dir (snap_0000..snap_0501), so the runner crash that
rem   killed the first launch (FileNotFoundError on a missing self snapshot) cannot recur here.
rem
rem   Everything else identical to launch_daeil_headon.bat: head-on 100 percent spawn, 16-dim
rem   observation, teammate daeil reward, stage 35, lr 1e-4.
rem   Sidecar must run separately with --tag daeil_headon and FINAL_SP_TAG=daeil_headon.
set "FINAL_SP_TAG=daeil_headon"

set "CKPT=%~dp0artifacts\models\AeroFlyer\peak_daeilheadon_iter0420\checkpoint"
if not exist "%CKPT%" (
  echo #### restore checkpoint missing: %CKPT%
  pause
  exit /b 1
)
set "RUNDIR=%~dp0artifacts\curriculum\AeroFlyer\%FINAL_SP_TAG%"
if not exist "%RUNDIR%" mkdir "%RUNDIR%"
set "RUNLOG=%RUNDIR%\console.log"
echo ==== [FINAL] HEADON RESUME from iter_0420 tag %FINAL_SP_TAG%  ^>  %RUNLOG% ====
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
