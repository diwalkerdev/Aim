import functools
from typing import Dict, Tuple, Callable
from aim_build.utils import *
from ninja_syntax import Writer
from dataclasses import dataclass
from aim_build import commonbuilds
from pathlib import PurePosixPath

PrefixIncludePath = functools.partial(prefix, "-I")
PrefixSystemIncludePath = functools.partial(prefix, "-isystem")
PrefixQuoteIncludePath = functools.partial(prefix, "-iquote")
PrefixLibraryPath = functools.partial(prefix, "-L")
PrefixLibrary = functools.partial(prefix, "-l")
PrefixHashDefine = functools.partial(prefix, "-D")
ToObjectFiles = src_to_o

FileExtensions = ["*.cpp", "*.cxx", "*.cc", ".c"]


# TODO: Should take version strings as well?
def linux_add_static_library_naming_convention(library_name: str) -> str:
    return f"lib{library_name}.a"


def linux_add_dynamic_library_naming_convention(library_name: str) -> str:
    return f"lib{library_name}.so"


def linux_add_exe_naming_convention(exe_name: str) -> str:
    return f"{exe_name}.exe"


@dataclass
class LibraryInformation:
    name: str
    path: str
    type: str


def get_project_dir(build: Dict, target_file: Dict):
    root_dir = target_file["projectRoot"]
    project_dir = build["build_dir"] / root_dir
    return project_dir


def get_src_files(build: Dict, target_file: Dict) -> PathList:
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
    return src_files


def get_quote_include_paths(build: Dict, build_dir: Path) -> PathList:
    include_paths = build.get("localIncludePaths", [])
    includes = relpaths(include_paths, build_dir)
    return includes


def get_system_include_paths(build: Dict) -> PathList:
    paths = build.get("systemIncludePaths", [])
    paths = [Path(path) for path in paths]
    return paths


def convert_strings_to_paths(paths):
    return [PurePosixPath(path) for path in paths]


def get_includes_for_build(build: Dict, parsed_toml: Dict) -> StringList:
    requires = [build["name"]] + build.get("requires", [])

    include_paths = set()
    system_include_paths = set()
    quote_include_paths = set()

    project_root = PurePosixPath(parsed_toml["projectRoot"])

    for required in requires:
        the_dep = commonbuilds.find_build(required, parsed_toml["builds"])

        includes = the_dep.get("includePaths", [])
        includes = convert_strings_to_paths(includes)
        includes = commonbuilds.get_include_paths(includes, project_root)
        include_paths.update(includes)

        quote_includes = get_quote_include_paths(the_dep, build["build_dir"])
        quote_include_paths.update(quote_includes)

        system_includes = get_system_include_paths(the_dep)
        system_include_paths.update(system_includes)

    include_paths = [str(path) for path in include_paths]
    system_include_paths = [str(path) for path in system_include_paths]
    quote_include_paths = [str(path) for path in quote_include_paths]

    include_paths.sort()
    system_include_paths.sort()
    quote_include_paths.sort()

    include_args = PrefixIncludePath(include_paths)
    system_include_args = PrefixSystemIncludePath(system_include_paths)
    quote_args = PrefixQuoteIncludePath(quote_include_paths)

    return include_args + system_include_args + quote_args


def get_toolchain_and_flags(build: Dict, target_file: Dict) -> Tuple[str, str, StringList, StringList]:
    local_compiler = build.get("compiler", None)
    local_archiver = build.get("archiver", None)
    local_flags = build.get("flags", None)
    local_defines = build.get("defines", None)

    compiler = local_compiler if local_compiler else target_file["compiler"]
    archiver = local_archiver if local_archiver else target_file["archiver"]
    cxx_flags = local_flags if local_flags else target_file["flags"]
    defines = local_defines if local_defines else target_file["defines"]
    defines = PrefixHashDefine(defines)
    return compiler, archiver, cxx_flags, defines


def get_external_libraries_paths(build: Dict) -> PathList:
    directory = build["directory"]
    library_paths = build.get("libraryPaths", [])
    library_paths = prepend_paths(directory, library_paths)
    return library_paths


def get_external_libraries_names(build: Dict) -> Tuple[StringList, StringList]:
    libraries = build.get("libraries", [])
    link_libraries = PrefixLibrary(libraries)
    return libraries, link_libraries


def get_external_libraries_information(build: Dict) -> Tuple[StringList, PathList]:
    libraries, _ = get_external_libraries_names(build)
    library_paths = get_external_libraries_paths(build)
    return libraries, library_paths


def add_compile_rule(writer: Writer,
                     build: Dict,
                     target_file: Dict,
                     includes: StringList,
                     extra_flags: StringList = None):
    build_name = build["name"]

    compiler, _, cxx_flags, defines = get_toolchain_and_flags(build, target_file)
    if extra_flags:
        cxx_flags = extra_flags + cxx_flags

    src_files = get_src_files(build, target_file)
    obj_files = ToObjectFiles(src_files)
    obj_files = prepend_paths(Path(build_name), obj_files)

    file_pairs = zip(to_str(src_files), to_str(obj_files))
    for src_file, obj_file in file_pairs:
        writer.build(
            outputs=obj_file,
            rule="compile",
            inputs=src_file,
            variables={
                "compiler": compiler,
                "includes": includes,
                "flags": cxx_flags,
                "defines": defines,
            },
        )
        writer.newline()

    return obj_files


def get_rpath(build: Dict, parsed_toml: Dict) -> str:
    # Good blog post about rpath:
    # https://medium.com/@nehckl0/creating-relocatable-linux-executables-by-setting-rpath-with-origin-45de573a2e98
    requires = build.get("requires", [])
    library_paths = set()

    # find_build_types("dynamicLib", parsed_toml["builds"])
    # TODO: replace the below with the above.
    for required in requires:
        the_dep = commonbuilds.find_build(required, parsed_toml["builds"])
        if the_dep["buildRule"] == "dynamicLib":
            library_paths.update([the_dep["name"]])

    top_build_dir = Path(build["build_dir"])
    build_dir = top_build_dir / build["name"]
    library_paths = list(library_paths)
    library_paths.sort()
    library_paths = prepend_paths(top_build_dir, library_paths)
    relative_paths = [
        relpath(Path(lib_path), build_dir) for lib_path in library_paths
    ]

    relative_paths = [f"$$ORIGIN/{rel_path}" for rel_path in relative_paths]
    relative_paths = ["$$ORIGIN"] + relative_paths

    relative_paths_string = escape_path(":".join(relative_paths))
    return f"-Wl,-rpath='{relative_paths_string}'"


def get_required_library_information(build: Dict, parsed_toml: Dict) -> List[LibraryInformation]:
    requires = build.get("requires", [])
    if not requires:
        return []

    build_names = []  # Used to prevent duplicates.
    result = []

    for required in requires:
        the_dep = commonbuilds.find_build(required, parsed_toml["builds"])
        if not the_dep["buildRule"] in ["staticLib", "dynamicLib"]:
            continue

        build_name = the_dep["name"]
        if build_name not in build_names:
            build_names.append(build_name)
            lib_info = LibraryInformation(the_dep["outputName"], the_dep["name"], the_dep["buildRule"])
            result.append(lib_info)

    return result


def get_full_library_name_convention(lib_infos: List[LibraryInformation],
                                     static_convention_func: Callable[[str], str],
                                     dynamic_convention_func: Callable[[str], str]) -> StringList:
    # Here we just need to manage the fact that the linker's library flag (-l) needs the library name without
    # lib{name}.a/.so but the build dependency rule does need the full convention to find the build rule in the
    # build.ninja file.
    full_library_names = []
    for info in lib_infos:
        if info.type == "staticLib":
            full_library_names.append(
                static_convention_func(info.name)
            )
        elif info.type == "dynamicLib":
            full_library_names.append(
                dynamic_convention_func(info.name)
            )

    return full_library_names


def get_reference_library_information(build: Dict,
                                      parsed_toml: Dict) -> Tuple[List[str], List[str]]:
    requires = build.get("requires", [])
    if not requires:
        return [], []

    build_names = []  # Used to prevent duplicates.
    libraries = []
    library_paths = []
    for required in requires:
        the_dep = commonbuilds.find_build(required, parsed_toml["builds"])
        if the_dep["buildRule"] != "libraryReference":
            continue

        build_name = the_dep["name"]
        if build_name not in build_names:
            build_names.append(build_name)
            libraries += the_dep.get("libraries", [])
            library_paths += the_dep.get("libraryPaths", [])

    return libraries, library_paths


class GCCBuilds:
    def build(self, build, parsed_toml, ninja_writer: Writer, args):
        # TODO forward args
        build_name = build["name"]
        the_build = build["buildRule"]
        build_dir = build["build_dir"]

        build_path = build_dir / build_name
        build_path.mkdir(parents=True, exist_ok=True)

        build["buildPath"] = build_path

        if the_build == "staticLib":
            self.build_static_library(
                ninja_writer, build, parsed_toml, linux_add_static_library_naming_convention
            )
        elif the_build == "exe":
            self.build_executable(
                ninja_writer, build, parsed_toml
            )
        elif the_build == "dynamicLib":
            self.build_dynamic_library(
                ninja_writer, build, parsed_toml
            )
        elif the_build == "headerOnly":
            pass
        elif the_build == "libraryReference":
            pass
        else:
            raise RuntimeError(f"Unknown build type {the_build}.")

    @staticmethod
    def build_static_library(pfw: Writer,
                             build: Dict,
                             parsed_toml: Dict,
                             lib_name_func: Callable[[str], str]):
        build_name = build["name"]

        includes = get_includes_for_build(build, parsed_toml)
        obj_files = add_compile_rule(pfw, build, parsed_toml, includes)

        library_name = lib_name_func(build["outputName"])
        relative_output_name = str(Path(build_name) / library_name)

        _, archiver, cxx_flags, defines = get_toolchain_and_flags(build, parsed_toml)
        pfw.build(
            outputs=relative_output_name,
            rule="archive",
            inputs=to_str(obj_files),
            variables={
                "archiver": archiver,
                "includes": includes,
                "flags": cxx_flags,
                "defines": defines,
            },
        )

        pfw.newline()
        pfw.build(rule="phony", inputs=relative_output_name, outputs=library_name)
        pfw.build(rule="phony", inputs=library_name, outputs=build_name)
        pfw.newline()

    @staticmethod
    def build_executable(pfw: Writer,
                         build: Dict,
                         parsed_toml: Dict):
        build_name = build["name"]

        compiler, _, cxxflags, defines = get_toolchain_and_flags(build, parsed_toml)
        includes = get_includes_for_build(build, parsed_toml)
        obj_files = add_compile_rule(pfw, build, parsed_toml, includes)
        rpath = get_rpath(build, parsed_toml)
        external_libraries_names, external_libraries_paths = get_external_libraries_information(build)
        external_libraries_names = PrefixLibrary(external_libraries_names)
        external_libraries_paths = PrefixLibraryPath(external_libraries_paths)

        lib_infos = get_required_library_information(build, parsed_toml)
        requires_libraries = PrefixLibrary([info.name for info in lib_infos])
        requires_library_paths = PrefixLibraryPath([info.path for info in lib_infos])

        ref_libraries, ref_library_paths = get_reference_library_information(build, parsed_toml)
        ref_libraries = PrefixLibrary(ref_libraries)
        ref_library_paths = PrefixLibraryPath(ref_library_paths)

        linker_args = (
            [rpath]
            + requires_library_paths
            + external_libraries_paths
            + ref_library_paths
            + requires_libraries
            + external_libraries_names
            + ref_libraries
        )

        full_library_names = get_full_library_name_convention(lib_infos,
                                                              linux_add_static_library_naming_convention,
                                                              linux_add_dynamic_library_naming_convention)

        exe_name = linux_add_exe_naming_convention(build["outputName"])
        relative_output_name = str(Path(build_name) / exe_name)
        pfw.build(
            outputs=relative_output_name,
            rule="exe",
            inputs=to_str(obj_files),
            implicit=full_library_names,
            variables={
                "compiler": compiler,
                "includes": includes,
                "flags": cxxflags,
                "defines": defines,
                "linker_args": " ".join(linker_args),
            },
        )
        pfw.newline()
        pfw.build(rule="phony", inputs=relative_output_name, outputs=exe_name)
        pfw.build(rule="phony", inputs=exe_name, outputs=build_name)
        pfw.newline()

    @staticmethod
    def build_dynamic_library(pfw: Writer,
                              build: Dict,
                              parsed_toml: Dict):
        build_name = build["name"]

        extra_flags = ["-DEXPORT_DLL_PUBLIC",
                       "-fvisibility=hidden",
                       "-fPIC"]

        compiler, _, cxxflags, defines = get_toolchain_and_flags(build, parsed_toml)
        includes = get_includes_for_build(build, parsed_toml)
        obj_files = add_compile_rule(pfw, build, parsed_toml, includes, extra_flags)
        rpath = get_rpath(build, parsed_toml)
        external_libraries_names, external_libraries_paths = get_external_libraries_information(build)
        external_libraries_names = PrefixLibrary(external_libraries_names)
        external_libraries_paths = PrefixLibraryPath(external_libraries_paths)

        lib_infos = get_required_library_information(build, parsed_toml)
        requires_libraries = [info.name for info in lib_infos]
        requires_libraries = PrefixLibrary(requires_libraries)
        requires_library_paths = [info.path for info in lib_infos]
        requires_library_paths = PrefixLibraryPath(requires_library_paths)

        ref_libraries, ref_library_paths = get_reference_library_information(build, parsed_toml)
        ref_libraries = PrefixLibrary(ref_libraries)
        ref_library_paths = PrefixLibraryPath(ref_library_paths)

        linker_args = (
            [rpath]
            + requires_library_paths
            + external_libraries_paths
            + ref_library_paths
            + requires_libraries
            + external_libraries_names
            + ref_libraries
        )

        full_library_names = get_full_library_name_convention(lib_infos,
                                                              linux_add_static_library_naming_convention,
                                                              linux_add_dynamic_library_naming_convention)

        library_name = linux_add_dynamic_library_naming_convention(build["outputName"])
        relative_output_name = str(Path(build_name) / library_name)
        pfw.build(
            rule="shared",
            inputs=to_str(obj_files),
            implicit=full_library_names,
            outputs=relative_output_name,
            variables={
                "compiler": compiler,
                "includes": includes,
                "flags": " ".join(cxxflags),
                "defines": " ".join(defines),
                "lib_name": library_name,
                "linker_args": " ".join(linker_args),
            },
        )
        pfw.newline()
        pfw.build(rule="phony", inputs=relative_output_name, outputs=library_name)
        pfw.build(rule="phony", inputs=library_name, outputs=build_name)
        pfw.newline()


def add_naming_convention(output_name: str,
                          build_type: str,
                          static_convention_func=linux_add_static_library_naming_convention,
                          dynamic_convention_func=linux_add_dynamic_library_naming_convention,
                          exe_convention_func=linux_add_exe_naming_convention):
    if build_type == "staticLib":
        new_name = static_convention_func(output_name)
    elif build_type == "dynamicLib":
        new_name = dynamic_convention_func(output_name)
    else:
        new_name = exe_convention_func(output_name)

    return new_name


def log_build_information(build):
    build_name = build["name"]
    cxx_flags = build["global_flags"] + build.get("flags", [])
    defines = build["global_defines"] + build.get("defines", [])
    includes = build["includes"]
    library_paths = build["libraryPaths"]
    output = build["outputName"]

    print(f"Running build: f{build_name}")
    print(f"FLAGS: {cxx_flags}")
    print(f"DEFINES: {defines}")
    print(f"INCLUDE_PATHS: {includes}")
    print(f"LIBRARY_PATHS: {library_paths}")
    print(f"OUTPUT NAME: {output}")
    print("")
