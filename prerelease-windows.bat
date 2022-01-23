@echo off
echo Running %0

python package.py

set PYTHONPATH=%cd%
set MAINSCRIPT=%cd%\aim_build\main.py
set AIMCMD=poetry run python %MAINSCRIPT%

set PROJECT_DIR=AimTestProject

if exist %PROJECT_DIR%\ rd /q /s %PROJECT_DIR%
mkdir %PROJECT_DIR%
cd %PROJECT_DIR%

call %AIMCMD% --help
call %AIMCMD% init --demo-files
call %AIMCMD% list builds/windows-clangcl-debug
call %AIMCMD% build builds/windows-clangcl-debug calculatortests
call %AIMCMD% build builds/windows-clangcl-debug calculatorapp

REM Remember, all outputs get dumped into the same directory on Windows.
call %AIMCMD% run builds/windows-clangcl-debug calculatortests
call %AIMCMD% run builds/windows-clangcl-debug calculatorapp

call %AIMCMD% clobber builds/windows-clangcl-debug

call %AIMCMD% exec builds/windows-clangcl-debug calculatorapp list build run clobber

cd ..
rmdir /s /q %PROJECT_DIR%
