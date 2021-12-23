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
call %AIMCMD% init --help
call %AIMCMD% target --help
call %AIMCMD% target builds/windows-clangcl-debug list --help
call %AIMCMD% target builds/windows-clangcl-debug build --help
call %AIMCMD% target builds/windows-clangcl-debug clobber --help
call %AIMCMD% init --demo-files
call %AIMCMD% target builds/windows-clangcl-debug list
call %AIMCMD% target builds/windows-clangcl-debug build calculatortests
call %AIMCMD% target builds/windows-clangcl-debug build calculatorapp

REM Remember, all outputs get dumped into the same directory on Windows.
call %AIMCMD% target builds/windows-clangcl-debug run calculatortests
call %AIMCMD% target builds/windows-clangcl-debug run calculatorapp

call %AIMCMD% target builds/windows-clangcl-debug clobber

cd ..
rmdir /s /q %PROJECT_DIR%
