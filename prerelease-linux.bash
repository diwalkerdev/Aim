#!/bin/bash

set -e
shopt -s expand_aliases

echo "Running ${0}"

python package.py
source ./dev-env.bash

rm -rf ../AimTestProject || true
mkdir ../AimTestProject
pushd ../AimTestProject

aim init --demofiles
aim list --target=builds/linux-clang++-debug
aim build --target=builds/linux-clang++-debug calculatortests
aim build --target=builds/linux-clang++-debug calculatorapp

./builds/linux-clang++-debug/calculatortests/CalculatorTests.exe
./builds/linux-clang++-debug/calculatorapp/CalculatorApp.exe

aim clobber --target=builds/linux-clang++-debug

popd

rm -rf ../AimTestProject
