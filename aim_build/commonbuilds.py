from dataclasses import dataclass
from pathlib import PurePath
from typing import Dict, Tuple, Callable, List

from aim_build.typedefs import StringList
from aim_build.utils import prepend_paths, flatten, to_str, relpaths, glob

FileExtensions = ["*.cpp", "*.cxx", "*.cc", ".c"]


@dataclass
class LibraryInformation:
    name: str
    path: str
    type: str


def get_project_dir(build: Dict, target_file: Dict):
    root_dir = target_file["projectRoot"]
    project_dir = build["build_dir"] / root_dir
    return project_dir


def find_build(build_name: str, builds: Dict) -> Dict:
    # Note, this should never fail, as required dependencies are checked by the schema.
    for build in builds:
        if build["name"] == build_name:
            return build

    raise RuntimeError(f"Failed to find build with name: {build_name}")


def find_builds_of_type(build_type: str, builds: Dict) -> List[Dict]:
    return [build for build in builds if build["buildRule"] == build_type]


def get_include_paths(
    include_paths: List[PurePath], build_dir: PurePath
) -> List[PurePath]:
    abs_paths = [p for p in include_paths if p.is_absolute()]
    rel_paths = [p for p in include_paths if not p.is_absolute()]
    rel_paths = prepend_paths(build_dir, rel_paths)

    includes = abs_paths + rel_paths
    return includes


def get_toolchain_and_flags(
    build: Dict, target_file: Dict
) -> Tuple[str, str, StringList, StringList]:
    local_compiler = build.get("compiler", None)
    local_archiver = build.get("archiver", None)
    local_flags = build.get("flags", None)
    local_defines = build.get("defines", None)

    compiler = local_compiler if local_compiler else target_file["compiler"]
    archiver = local_archiver if local_archiver else target_file["archiver"]
    cxx_flags = local_flags if local_flags else target_file.get("flags", [])
    defines = local_defines if local_defines else target_file.get("defines", [])
    return compiler, archiver, cxx_flags, defines


def get_src_files(build: Dict, target_file: Dict) -> StringList:
    project_dir = get_project_dir(build, target_file)

    srcs = prepend_paths(project_dir, build["srcDirs"])
    src_dirs = [path for path in srcs if path.is_dir()]
    explicit_src_files = [path for path in srcs if path.is_file()]
    src_files = []
    for glob_pattern in FileExtensions:
        glob_files = flatten(glob(glob_pattern, src_dirs))
        src_files += glob_files

    src_files += explicit_src_files
    assert src_files, f"Fail to find any source files in {to_str(src_dirs)}."

    build_path = build["build_dir"]
    src_files = relpaths(src_files, build_path)

    return [str(file) for file in src_files]


def get_required_library_information(
    build: Dict, parsed_toml: Dict
) -> List[LibraryInformation]:
    requires = build.get("requires", [])
    if not requires:
        return []

    build_names = []  # Used to prevent duplicates.
    result = []

    for required in requires:
        the_dep = find_build(required, parsed_toml["builds"])
        if not the_dep["buildRule"] in ["staticLib", "dynamicLib"]:
            continue

        build_name = the_dep["name"]
        if build_name not in build_names:
            build_names.append(build_name)
            lib_info = LibraryInformation(
                the_dep["outputName"], the_dep["name"], the_dep["buildRule"]
            )
            result.append(lib_info)

    return result


def get_reference_library_information(
    build: Dict, parsed_toml: Dict
) -> Tuple[List[str], List[str]]:
    requires = build.get("requires", [])
    if not requires:
        return [], []

    build_names = []  # Used to prevent duplicates.
    libraries = []
    library_paths = []
    for required in requires:
        the_dep = find_build(required, parsed_toml["builds"])
        if the_dep["buildRule"] != "libraryReference":
            continue

        build_name = the_dep["name"]
        if build_name not in build_names:
            build_names.append(build_name)
            libraries += the_dep.get("libraries", [])
            library_paths += the_dep.get("libraryPaths", [])

    return libraries, library_paths


def get_full_library_name_convention(
    lib_infos: List[LibraryInformation],
    static_convention_func: Callable[[str], str],
    dynamic_convention_func: Callable[[str], str],
) -> StringList:
    # Here we just need to manage the fact that the linker's library flag (-l) needs the library name without
    # lib{name}.a/.so but the build dependency rule does need the full convention to find the build rule in the
    # build.ninja file.
    full_library_names = []
    for info in lib_infos:
        if info.type == "staticLib":
            full_library_names.append(static_convention_func(info.name))
        elif info.type == "dynamicLib":
            full_library_names.append(dynamic_convention_func(info.name))

    return full_library_names
