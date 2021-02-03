#!/bin/bash

set -e

if [[ $_ != "$0" ]]; then
  alias aim="PYTHONPATH=${PWD}/src $(poetry env info -p)/bin/python ${PWD}/src/aim_build/main.py"
else
  echo "Please source this file"
fi
