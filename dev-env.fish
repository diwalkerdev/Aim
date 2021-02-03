#!/usr/bin/fish

if test "$_" = source
  alias aim="PYTHONPATH=$PWD/src "(poetry env info -p)"/bin/python $PWD/src/aim_build/main.py"
else
  echo "Please source the file."
  set AIM_CMD "PYTHONPATH=$PWD/src "(poetry env info -p)"/bin/python $PWD/src/aim_build/main.py"
end
