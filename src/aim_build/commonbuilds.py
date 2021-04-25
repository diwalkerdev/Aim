from typing import Dict, Callable
from aim_build.utils import *


def find_build(build_name: str, builds: Dict) -> Dict:
    # Note, this should never fail, as required dependencies are checked by the schema.
    for build in builds:
        if build["name"] == build_name:
            return build


def find_builds_of_type(build_type: str, builds: Dict) -> List[Dict]:
    return [build for build in builds if build["buildRule"] == build_type]


def get_include_paths(include_paths: List[PurePath],
                      build_dir: PurePath) -> List[PurePath]:
    # include_paths = build.get("includePaths", [])
    # include_paths = [Path(p) for p in include_paths]
    abs_paths = [p for p in include_paths if p.is_absolute()]
    rel_paths = [p for p in include_paths if not p.is_absolute()]
    rel_paths = prepend_paths(build_dir, rel_paths)

    includes = abs_paths + rel_paths
    return includes
