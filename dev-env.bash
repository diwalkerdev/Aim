#!/bin/bash

if [[ $_ != "$0" ]]; then
  alias aim="PYTHONPATH=${PWD} $(poetry env info -p)/bin/python ${PWD}/aim_build/main.py"
else
  echo "Please source this file"
fi
