#!/bin/bash

set -e
shopt -s expand_aliases

echo "Running ${0}"

python3 package.py
source ./dev-env.bash

rm -rf ../AimTestProject || true
mkdir ../AimTestProject
pushd ../AimTestProject

aim --help
aim list --help
aim init --help
aim build --help
aim clobber --help
aim init --demo-files
aim list --target=builds/windows-clang++-debug
aim build --target=builds/windows-clang++-debug calculatortests --profile-build
aim build --target=builds/windows-clang++-debug calculatorapp --args=-ftime-trace

./builds/windows-clang++-debug/calculatortests/CalculatorTests.exe
./builds/windows-clang++-debug/calculatorapp/CalculatorApp.exe

aim clobber --target=builds/windows-clang++-debug

popd

rm -rf ../AimTestProject
