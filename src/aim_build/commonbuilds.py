from typing import Dict, Tuple
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
    abs_paths = [p for p in include_paths if p.is_absolute()]
    rel_paths = [p for p in include_paths if not p.is_absolute()]
    rel_paths = prepend_paths(build_dir, rel_paths)

    includes = abs_paths + rel_paths
    return includes


def get_toolchain_and_flags(build: Dict, target_file: Dict) -> Tuple[str, str, StringList, StringList]:
    local_compiler = build.get("compiler", None)
    local_archiver = build.get("archiver", None)
    local_flags = build.get("flags", None)
    local_defines = build.get("defines", None)

    compiler = local_compiler if local_compiler else target_file["compiler"]
    archiver = local_archiver if local_archiver else target_file["archiver"]
    cxx_flags = local_flags if local_flags else target_file["flags"]
    defines = local_defines if local_defines else target_file["defines"]
    return compiler, archiver, cxx_flags, defines
