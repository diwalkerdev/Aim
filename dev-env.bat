@echo off
REM set PYTHONPATH=%cd%
REM for /f %%i in ('poetry env info -p') do %%i\Scripts\python %cd%\aim_build\main.py

set PYTHONPATH=%cd%
set AIMCMD=poetry run python %cd%\aim_build\main.py
