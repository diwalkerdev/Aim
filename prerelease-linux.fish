#!/usr/bin/fish

status -f

python package.py
source dev-env.fish

eval $AIM_CMD --help || exit

rm -rf ../AimTestProject || true
mkdir ../AimTestProject || exit
pushd ../AimTestProject || exit

eval $AIM_CMD init --demofiles
eval $AIM_CMD list --target=builds/linux-clang++-debug
eval $AIM_CMD build --target=builds/linux-clang++-debug calculatortests
eval $AIM_CMD build --target=builds/linux-clang++-debug calculatorapp

./builds/linux-clang++-debug/calculatortests/CalculatorTests.exe
./builds/linux-clang++-debug/calculatorapp/CalculatorApp.exe

aim clobber --target=builds/linux-clang++-debug

popd || exit

rm -rf ../AimTestProject || exit
