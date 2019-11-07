import itertools
from pathlib import Path
from typing import *

from aim.typedefs import PathList, StringList, T


def src_to_obj(files) -> StringList:
    return [x.stem + ".obj" for x in files]


def src_to_o(files) -> StringList:
    return [x.stem + ".o" for x in files]


def to_str(paths) -> StringList:
    return [str(x) for x in paths]


def to_paths(string_paths) -> PathList:
    return [Path(x) for x in string_paths]


def glob(glob_string, paths: PathList) -> List[PathList]:
    return [list(x.glob(glob_string)) for x in paths]


def flatten(list_of_lists: List[List[T]]) -> List[T]:
    return list(itertools.chain.from_iterable(list_of_lists))


def prefix(the_prefix, paths) -> StringList:
    return [the_prefix + str(x) for x in paths]


def suffix(the_suffix, paths) -> StringList:
    return [str(x) + the_suffix for x in paths]


def append_paths(base_path: Path, other_paths: PathList):
    return [base_path / the_path for the_path in other_paths]