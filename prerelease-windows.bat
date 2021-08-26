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
call %AIMCMD% list --help
call %AIMCMD% init --help
call %AIMCMD% build --help
call %AIMCMD% clobber --help
call %AIMCMD% init --demo-files
call %AIMCMD% list --target=builds/windows-clangcl-debug
call %AIMCMD% build --target=builds/windows-clangcl-debug calculatortests
call %AIMCMD% build --target=builds/windows-clangcl-debug calculatorapp

REM Remember, all outputs get dumped into the same directory on Windows.
builds\windows-clangcl-debug\CalculatorTests.exe
builds\windows-clangcl-debug\CalculatorApp.exe

call %AIMCMD% clobber --target=builds/windows-clangcl-debug

cd ..
rmdir /s /q %PROJECT_DIR%
