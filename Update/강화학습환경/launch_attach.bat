@echo off
set "CONDA_ENV=C:\Users\user one\anaconda3\envs\aip"
set "PYTHONUTF8=1"
cd /d "%~dp0"
rem usage: launch_attach.bat <bundle_dir> <team_name> [server_ip] [port]   (real-server client via attach_client.py)
set "B=%~1"
if "%B%"=="" set "B=artifacts\models\AeroFlyer\cand_s48_snap12241"
set "T=%~2"
if "%T%"=="" set "T=cand"
set "IP=%~3"
if "%IP%"=="" set "IP=127.0.0.1"
set "PORT=%~4"
if "%PORT%"=="" set "PORT=9999"
title attach %T% - %B%
"%CONDA_ENV%\python.exe" -u attach_client.py --bundle "%B%" --team-name %T% --server-ip %IP% --server-port %PORT%
echo [client exited]
pause
