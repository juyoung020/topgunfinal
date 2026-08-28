@echo off
set "CONDA_ENV=C:\Users\user one\anaconda3\envs\aip"
cd /d "%~dp0"
rem training dashboard (docs: DogFightEnv_Log_Check_CLI_YAML_Guide.md) -> http://127.0.0.1:7860
rem --logdir = artifacts/replays (all runs; reader picks *[Blue]*.csv / *[Red]*.csv recursively)
"%CONDA_ENV%\python.exe" -u tools\dashboard.py --training-logdir artifacts\dashboard --logdir artifacts\replays --port 7860
pause
