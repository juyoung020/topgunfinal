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

rem ==== [본선] stage 35 selfplay_final — 학습 v1(s48) iter_1120 / 상대 v1 사본 70% + v2(ladder5220) 30% (사용자 결정 8/28) ====
rem   보상 = 8/16 v2 코드값 (피딜·고고도·과속·WEZ·스냅 = 0, 저고도선 2,500 ft) / 상대 = v1 자기 사본 70% + v2 고정 30%
rem   스폰 = 2000ft line abreast (서버 실측 첫 프레임, 옆구리 배치)
rem   ** launch_final_sidecar.bat 을 먼저 띄울 것 ** (self 슬롯 갱신. 없으면 self 슬롯이 v1 출발점 사본에 고정)
rem   승급 없음. 300 iter 마다 실서버 판정(컷오프·r9980 양 슬롯)으로 정점을 잡아 보존할 것.
set "CKPT=%~dp0artifacts\curriculum\AeroFlyer\0824_r48\stage_48_ladder_12241_c2\checkpoints\iter_1120"
if not exist "%CKPT%" (
  echo #### restore checkpoint missing: %CKPT%
  pause
  exit /b 1
)
set "RUNDIR=%~dp0artifacts\curriculum\AeroFlyer\final_sp"
if not exist "%RUNDIR%" mkdir "%RUNDIR%"
set "RUNLOG=%RUNDIR%\console.log"
echo ==== [FINAL] stage 35 selfplay_final: base v1 iter_1120 vs snap_0000=v2  ^>  %RUNLOG% ====
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
  --start-stage 35 ^
  --restore-checkpoint "%CKPT%" ^
  --output-name AeroFlyer --output-tag final_sp ^
  2>&1 | "%CONDA_ENV%\python.exe" tools\tee.py "%RUNLOG%"
echo.
echo ==== trainer exited ====
pause
