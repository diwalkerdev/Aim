#!/bin/bash

set -e
shopt -s expand_aliases

echo "Running ${0}"

python package.py
source ./dev-env.bash

rm -rf AimTestProject || true # allowed to fail if doesn't exist.
mkdir AimTestProject
pushd AimTestProject

set -e -o xtrace

aim --help
aim init --demo-files
aim list builds/linux-clang++-debug
aim build builds/linux-clang++-debug calculatortests
aim build builds/linux-clang++-debug calculatorapp

aim run builds/linux-clang++-debug calculatortests
aim run builds/linux-clang++-debug calculatorapp

aim clobber builds/linux-clang++-debug

aim exec builds/linux-clang++-debug calculatorapp list build run clobber

popd

rm -rf AimTestProject
