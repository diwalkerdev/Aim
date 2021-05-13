@echo off
set PYTHONPATH=%cd%\src
for /f %%i in ('poetry env info -p') do %%i\Scripts\python %cd%\src\aim_build\main.py