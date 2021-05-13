#!/usr/bin/fish

if test "$_" = source
  alias aim="PYTHONPATH=$PWD "(poetry env info -p)"/bin/python $PWD/aim_build/main.py"
else
  echo "Please source the file."
end
