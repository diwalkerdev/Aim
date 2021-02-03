set -e

mkdir ../AimTestProject
pushd ../AimTestProject
aim init --demofiles
aim build --target=builds/linux-clang++-debug tests
aim build --target=builds/linux-clang++-debug calculatorapp

./builds/linux-clang++-debug/tests/Tests.exe
./builds/linux-clang++-debug/calculatorapp/CalculatorApp.exe

popd

rm -rf ../AimTestProject
