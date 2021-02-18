#!/bin/bash

set -e
shopt -s expand_aliases

echo "Running ${0}"

python package.py
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
aim list --target=builds/linux-clang++-debug
aim build --target=builds/linux-clang++-debug calculatortests --profile-build
aim build --target=builds/linux-clang++-debug calculatorapp --args=-ftime-trace

./builds/linux-clang++-debug/calculatortests/CalculatorTests.exe
./builds/linux-clang++-debug/calculatorapp/CalculatorApp.exe

aim clobber --target=builds/linux-clang++-debug

popd

rm -rf ../AimTestProject
