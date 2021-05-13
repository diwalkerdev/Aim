@echo off
set PYTHONPATH=%cd%
for /f %%i in ('poetry env info -p') do %%i\Scripts\python %cd%\aim_build\main.py
