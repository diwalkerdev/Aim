#!/usr/bin/fish

status -f

set AIM_CMD "PYTHONPATH=$PWD "(poetry env info -p)"/bin/python $PWD/aim_build/main.py"

python package.py || exit

eval $AIM_CMD --help || exit

rm -rf ../AimTestProject || exit
mkdir ../AimTestProject || exit
pushd ../AimTestProject || exit

eval $AIM_CMD --help || exit
eval $AIM_CMD list --help || exit
eval $AIM_CMD init --help || exit
eval $AIM_CMD build --help || exit
eval $AIM_CMD clobber --help || exit
eval $AIM_CMD init --demo-files || exit
eval $AIM_CMD list --target=builds/linux-clang++-debug || exit
eval $AIM_CMD build --target=builds/linux-clang++-debug calculatortests --profile-build || exit
eval $AIM_CMD build --target=builds/linux-clang++-debug calculatorapp --args=-ftime-trace || exit

./builds/linux-clang++-debug/calculatortests/CalculatorTests.exe || exit
./builds/linux-clang++-debug/calculatorapp/CalculatorApp.exe || exit

eval $AIM_CMD clobber --target=builds/linux-clang++-debug || exit

popd || exit

rm -rf ../AimTestProject || exit
