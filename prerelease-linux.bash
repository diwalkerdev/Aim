#!/bin/bash

set -e
shopt -s expand_aliases

echo "Running ${0}"

python package.py
source ./dev-env.bash

rm -rf AimTestProject || true # allowed to fail if doesn't exist.
mkdir AimTestProject
pushd AimTestProject


aim --help
aim init --help
aim target --help
aim target builds/linux-clang++-debug list --help
aim target builds/linux-clang++-debug build --help
aim target builds/linux-clang++-debug clobber --help
aim init --demo-files
aim target builds/linux-clang++-debug list
aim target builds/linux-clang++-debug build calculatortests
aim target builds/linux-clang++-debug build calculatorapp
#aim build --target=builds/linux-clang++-debug calculatortests --profile-build
#aim build --target=builds/linux-clang++-debug calculatorapp --args=-ftime-trace

aim target builds/linux-clang++-debug run calculatortests
aim target builds/linux-clang++-debug run calculatorapp

aim target builds/linux-clang++-debug clobber

popd

rm -rf AimTestProject
