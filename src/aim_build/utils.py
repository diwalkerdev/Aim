import itertools
import os
from pathlib import Path, PurePath
from typing import List, Union

from aim_build.typedefs import PathList, StringList, T


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


def postfix(the_postfix, paths) -> StringList:

    return [str(x) + the_postfix for x in paths]


def add_quotes(paths: Union[PathList, StringList]):
    return [f'"{str(x)}"' for x in paths]


def suffix(the_suffix, paths) -> StringList:
    return [str(x) + the_suffix for x in paths]


def prepend_paths(base_path: PurePath, other_paths: Union[List[PurePath], StringList]):
    # Don't need to check if `the_path` is absolute. If it is, the the result of `base_path / the_path` is just the
    # `the_path`. So it does the right thing, even though you might not expect it.
    return [base_path / the_path for the_path in other_paths]


def resolve(paths: PathList):
    return [path.resolve() for path in paths]


def escape_path(word):
    return word.replace("$ ", "$$ ").replace(" ", "$ ").replace(":", "$:")


def relpath(src_path: Path, dst_path: Path):
    return Path(os.path.relpath(str(src_path), str(dst_path)))


def relpaths(src_paths: List[PurePath], dst_path: PurePath) -> List[PurePath]:
    return [
        type(dst_path)(os.path.relpath(str(src_path), str(dst_path)))
        for src_path in src_paths
    ]
