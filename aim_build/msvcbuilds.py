import functools
from pathlib import PureWindowsPath, PurePosixPath
from typing import Callable
from typing import Dict, Tuple, List, Union

from aim_build import commonbuilds
from aim_build.typedefs import StringList, PathList
from aim_build.utils import prefix, postfix, src_to_obj, prepend_paths, to_str
from ninja_syntax import Writer

USING_RELATIVE_OUTPUTS = False

PrefixIncludePath = functools.partial(prefix, "/I")
PrefixLibraryPath = functools.partial(prefix, "/LIBPATH:")
PrefixLibrary = functools.partial(prefix, "")
PrefixHashDefine = functools.partial(prefix, "/D")
PostFixLib = functools.partial(postfix, ".lib")
ToObjectFiles = src_to_obj


# TODO: Should take version strings as well?
def windows_add_static_library_naming_convention(library_name: str) -> str:
    return f"lib{library_name}.lib"


def windows_add_dynamic_library_naming_convention(library_name: str) -> str:
    return f"lib{library_name}.dll"


def windows_add_exe_naming_convention(exe_name: str) -> str:
    return f"{exe_name}.exe"


def convert_posix_to_windows(paths: Union[StringList, List[PurePosixPath]]):
    return [str(path).replace("/", "\\") for path in paths]


def convert_strings_to_paths(paths: StringList):
    return [PureWindowsPath(path) for path in convert_posix_to_windows(paths)]


def convert_to_implicit_library_files(library):
    return "lib" + library + ".exp", "lib" + library + ".lib"


def implicit_library_outputs(libraries):
    implicits = []
    for library in libraries:
        parts = library.split(".")
        if parts[1] == "dll":
            implicits.append("lib" + parts[0] + ".exp")
            implicits.append("lib" + parts[0] + ".lib")

    return implicits


def convert_dlls_to_lib(libraries):
    new_libraries = []
    for library in libraries:
        parts = library.split(".")
        if parts[1] == "dll":
            new_libraries.append("lib" + parts[0] + ".lib")
        else:
            new_libraries.append("lib" + library)

    return new_libraries


def get_external_libraries_paths(build):
    directory = PureWindowsPath(build["directory"])
    library_paths = build.get("libraryPaths", [])
    library_paths = convert_posix_to_windows(library_paths)
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


def get_library_information(
    lib_infos: List[commonbuilds.LibraryInformation],
) -> Tuple[List, List, List, List]:
    exps = []
    libs = []
    # This is a bit confusing, we need just the library names and exp file names as this is what the linker needs, but
    # ninja needs the full path to the exp file.
    implicit_exps = []
    implicit_libs = []

    for info in lib_infos:
        if info.type == "dynamicLib":
            exp, lib = convert_to_implicit_library_files(info.name)
            exps.append(exp)
            libs.append(lib)
            if USING_RELATIVE_OUTPUTS:
                implicit_exps.append(str(PureWindowsPath(info.path) / exp))
                implicit_libs.append(str(PureWindowsPath(info.path) / lib))
            else:
                implicit_exps.append(exp)
                implicit_libs.append(lib)
        else:
            lib = "lib" + info.name + ".lib"
            libs.append(lib)

    return exps, libs, implicit_exps, implicit_libs


def get_includes_for_build(build: Dict, parsed_toml: Dict) -> StringList:
    requires = [build["name"]] + build.get("requires", [])

    include_paths = set()

    project_root = PureWindowsPath(parsed_toml["projectRoot"])

    for required in requires:
        the_dep = commonbuilds.find_build(required, parsed_toml["builds"])

        includes = the_dep.get("includePaths", [])
        includes = convert_strings_to_paths(includes)
        includes = commonbuilds.get_include_paths(includes, project_root)
        include_paths.update(includes)

    include_paths = [str(path) for path in include_paths]

    include_paths.sort()
    include_args = PrefixIncludePath(include_paths)

    return include_args


def get_src_for_build(build: Dict, parsed_toml: Dict) -> List[PureWindowsPath]:
    files = commonbuilds.get_src_files(build, parsed_toml)
    return convert_strings_to_paths(files)


def add_compile_rule(
    writer: Writer,
    build: Dict,
    target_file: Dict,
    includes: StringList,
    extra_flags: StringList = None,
):
    build_name = build["name"]

    compiler, _, cxx_flags, defines = commonbuilds.get_toolchain_and_flags(
        build, target_file
    )
    defines = PrefixHashDefine(defines)

    if extra_flags:
        cxx_flags = extra_flags + cxx_flags

    src_files = get_src_for_build(build, target_file)
    obj_files = ToObjectFiles(src_files)
    obj_files = prepend_paths(PureWindowsPath(build_name), obj_files)
    obj_files = convert_posix_to_windows(obj_files)

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


def generate_linker_args(build: Dict, parsed_toml: Dict):
    lib_infos = commonbuilds.get_required_library_information(build, parsed_toml)

    (
        _,
        link_libraries,
        __,
        ___,
    ) = get_library_information(lib_infos)

    # Requires Libraries:
    #
    requires_libraries = PrefixLibrary(link_libraries)
    requires_library_paths = PrefixLibraryPath([info.path for info in lib_infos])

    # External Libraries:
    #
    (
        external_libraries_names,
        external_libraries_paths,
    ) = get_external_libraries_information(build)

    external_libraries_names = PrefixLibrary(PostFixLib(external_libraries_names))
    external_libraries_paths = PrefixLibraryPath(external_libraries_paths)

    # Reference Libraries:
    #
    (
        ref_libraries,
        ref_library_paths,
    ) = commonbuilds.get_reference_library_information(build, parsed_toml)

    ref_libraries = PrefixLibrary(PostFixLib(ref_libraries))
    ref_library_paths = PrefixLibraryPath(convert_posix_to_windows(ref_library_paths))

    linker_args = (
        requires_library_paths
        + external_libraries_paths
        + ref_library_paths
        + requires_libraries
        + external_libraries_names
        + ref_libraries
    )
    return linker_args


class MSVCBuilds:
    def build(self, build: Dict, parsed_toml: Dict, ninja_writer: Writer, args):
        # TODO forward args
        build_name = build["name"]
        the_build = build["buildRule"]
        build_dir = build["build_dir"]

        build_path = build_dir / build_name
        build_path.mkdir(parents=True, exist_ok=True)

        build["buildPath"] = build_path

        if the_build == "staticLib":
            self.build_static_library(
                ninja_writer,
                build,
                parsed_toml,
                windows_add_static_library_naming_convention,
            )
        elif the_build == "exe":
            self.build_executable(ninja_writer, build, parsed_toml)
        elif the_build == "dynamicLib":
            self.build_dynamic_library(ninja_writer, build, parsed_toml)
        elif the_build == "headerOnly":
            pass
        elif the_build == "libraryReference":
            pass
        else:
            raise RuntimeError(f"Unknown build type {the_build}.")

    @staticmethod
    def build_static_library(
        pfw: Writer, build: Dict, parsed_toml: Dict, lib_name_func: Callable[[str], str]
    ):
        build_name = build["name"]

        includes = get_includes_for_build(build, parsed_toml)
        obj_files = add_compile_rule(pfw, build, parsed_toml, includes)

        library_name = lib_name_func(build["outputName"])
        relative_output_name = str(PureWindowsPath(build_name) / library_name)

        _, archiver, cxx_flags, defines = commonbuilds.get_toolchain_and_flags(
            build, parsed_toml
        )
        defines = PrefixHashDefine(defines)

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
    def build_executable(pfw: Writer, build: Dict, parsed_toml: Dict):
        build_name = build["name"]

        compiler, _, cxxflags, defines = commonbuilds.get_toolchain_and_flags(
            build, parsed_toml
        )
        defines = PrefixHashDefine(defines)

        includes = get_includes_for_build(build, parsed_toml)
        obj_files = add_compile_rule(pfw, build, parsed_toml, includes)

        lib_infos = commonbuilds.get_required_library_information(build, parsed_toml)

        (_, __, implicit_exps, implicit_libs,) = get_library_information(lib_infos)

        linker_args = generate_linker_args(build, parsed_toml)

        exe_name = windows_add_exe_naming_convention(build["outputName"])
        if USING_RELATIVE_OUTPUTS:
            build_output = str(PureWindowsPath(build_name) / exe_name)
        else:
            build_output = exe_name

        pfw.build(
            rule="exe",
            inputs=to_str(obj_files),
            implicit=implicit_exps + implicit_libs,
            outputs=build_output,
            variables={
                "compiler": compiler,
                "includes": includes,
                "flags": " ".join(cxxflags),
                "defines": " ".join(defines),
                "exe_name": build_output,
                "linker_args": " ".join(linker_args),
            },
        )
        pfw.newline()
        if USING_RELATIVE_OUTPUTS:
            pfw.build(rule="phony", inputs=build_output, outputs=exe_name)
        pfw.build(rule="phony", inputs=exe_name, outputs=build_name)
        pfw.newline()

    @staticmethod
    def build_dynamic_library(pfw: Writer, build: Dict, parsed_toml: Dict):
        build_name = build["name"]

        extra_flags = ["/DEXPORT_DLL_PUBLIC"]

        compiler, _, cxxflags, defines = commonbuilds.get_toolchain_and_flags(
            build, parsed_toml
        )
        defines = PrefixHashDefine(defines)

        includes = get_includes_for_build(build, parsed_toml)
        obj_files = add_compile_rule(pfw, build, parsed_toml, includes, extra_flags)

        lib_infos = commonbuilds.get_required_library_information(build, parsed_toml)

        (_, __, implicit_exps, implicit_libs,) = get_library_information(lib_infos)

        linker_args = generate_linker_args(build, parsed_toml)

        lib, exp = convert_to_implicit_library_files(build["outputName"])

        if USING_RELATIVE_OUTPUTS:
            implicit_outputs = [
                str(PureWindowsPath(build_name) / lib),
                str(PureWindowsPath(build_name) / exp),
            ]
        else:
            implicit_outputs = [lib, exp]

        library_name = windows_add_dynamic_library_naming_convention(
            build["outputName"]
        )

        if USING_RELATIVE_OUTPUTS:
            build_output = str(PureWindowsPath(build_name) / library_name)
        else:
            build_output = library_name

        pfw.build(
            rule="shared",
            inputs=to_str(obj_files),
            implicit=implicit_exps + implicit_libs,
            outputs=build_output,
            implicit_outputs=implicit_outputs,
            variables={
                "compiler": compiler,
                "includes": includes,
                "flags": " ".join(cxxflags),
                "defines": " ".join(defines),
                "lib_name": build_output,
                "linker_args": " ".join(linker_args),
            },
        )
        pfw.newline()
        if USING_RELATIVE_OUTPUTS:
            pfw.build(rule="phony", inputs=build_output, outputs=library_name)
        pfw.build(rule="phony", inputs=library_name, outputs=build_name)
        pfw.newline()


def log_build_information(build):
    build_name = build["name"]
    cxxflags = build["flags"]
    defines = build["defines"]
    includes = build["includes"]
    library_paths = build["libraryPaths"]
    output = build["outputName"]

    print(f"Running build: f{build_name}")
    print(f"CXXFLAGS: {cxxflags}")
    print(f"DEFINES: {defines}")
    print(f"INCLUDE_PATHS: {includes}")
    print(f"LIBRARY_PATHS: {library_paths}")
    print(f"OUTPUT NAME: {output}")
    print("")
