@echo off
set PYTHONPATH=%cd%
echo PYTHONPATH: %PYTHONPATH%

REM Getting the path to python works better than poetry run, because poetry run
REM requires that you are in the aim directory for it to work, and there's no
REM option for switching into another directory like -C<some dir>.
REM Because this is how you expand commands in batch scripts. Facepalm.
for /f %%i in ('poetry env info -p') do set AIM_POETRY=%%i
echo AIM_POETRY: %AIM_POETRY%

set "aimcmd=%AIM_POETRY%\Scripts\python %cd%\aim_build\main.py"
echo aimcmd:     %aimcmd%
