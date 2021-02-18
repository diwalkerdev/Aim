#!/usr/bin/fish

status -f

python package.py
source dev-env.fish

eval $AIM_CMD --help || exit

rm -rf ../AimTestProject || true
mkdir ../AimTestProject || exit
pushd ../AimTestProject || exit

eval $AIM_CMD --help
eval $AIM_CMD list --help
eval $AIM_CMD init --help
eval $AIM_CMD build --help
eval $AIM_CMD clobber --help
eval $AIM_CMD init --demo-files
eval $AIM_CMD list --target=builds/linux-clang++-debug
eval $AIM_CMD build --target=builds/linux-clang++-debug calculatortests --profile-build
eval $AIM_CMD build --target=builds/linux-clang++-debug calculatorapp --args=-ftime-trace

./builds/linux-clang++-debug/calculatortests/CalculatorTests.exe
./builds/linux-clang++-debug/calculatorapp/CalculatorApp.exe

aim clobber --target=builds/linux-clang++-debug

popd || exit

rm -rf ../AimTestProject || exit
