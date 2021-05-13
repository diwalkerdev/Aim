import functools
from pathlib import PurePosixPath, PurePath, Path
from typing import Dict, Tuple, Callable, List

from aim_build import commonbuilds
from aim_build.typedefs import PathList, StringList
from aim_build.utils import (
    prefix,
    src_to_o,
    relpaths,
    prepend_paths,
    to_str,
    relpath,
    escape_path,
)
from ninja_syntax import Writer

PrefixIncludePath = functools.partial(prefix, "-I")
PrefixSystemIncludePath = functools.partial(prefix, "-isystem")
PrefixQuoteIncludePath = functools.partial(prefix, "-iquote")
PrefixLibraryPath = functools.partial(prefix, "-L")
PrefixLibrary = functools.partial(prefix, "-l")
PrefixHashDefine = functools.partial(prefix, "-D")
ToObjectFiles = src_to_o


# TODO: Should take version strings as well?
def linux_add_static_library_naming_convention(library_name: str) -> str:
    return f"lib{library_name}.a"


def linux_add_dynamic_library_naming_convention(library_name: str) -> str:
    return f"lib{library_name}.so"


def linux_add_exe_naming_convention(exe_name: str) -> str:
    return f"{exe_name}.exe"


def get_quote_include_paths(build: Dict, build_dir: Path) -> List[PurePath]:
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


def get_src_for_build(build: Dict, parsed_toml: Dict) -> List[PurePosixPath]:
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
    relative_paths = [relpath(Path(lib_path), build_dir) for lib_path in library_paths]

    relative_paths = [f"$$ORIGIN/{rel_path}" for rel_path in relative_paths]
    relative_paths = ["$$ORIGIN"] + relative_paths

    relative_paths_string = escape_path(":".join(relative_paths))
    return f"-Wl,-rpath='{relative_paths_string}'"


def generate_linker_args(build, parsed_toml):
    lib_infos = commonbuilds.get_required_library_information(build, parsed_toml)

    rpath = get_rpath(build, parsed_toml)

    # Requires Libraries:
    #
    requires_libraries = PrefixLibrary([info.name for info in lib_infos])
    requires_library_paths = PrefixLibraryPath([info.path for info in lib_infos])

    # External Libraries:
    #
    (
        external_libraries_names,
        external_libraries_paths,
    ) = get_external_libraries_information(build)

    external_libraries_names = PrefixLibrary(external_libraries_names)
    external_libraries_paths = PrefixLibraryPath(external_libraries_paths)

    # Reference Libraries:
    #
    (
        ref_libraries,
        ref_library_paths,
    ) = commonbuilds.get_reference_library_information(build, parsed_toml)

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
    return linker_args


class GCCBuilds:
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
                linux_add_static_library_naming_convention,
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
        relative_output_name = str(PurePosixPath(build_name) / library_name)

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
        linker_args = generate_linker_args(build, parsed_toml)

        full_library_names = commonbuilds.get_full_library_name_convention(
            lib_infos,
            linux_add_static_library_naming_convention,
            linux_add_dynamic_library_naming_convention,
        )

        exe_name = linux_add_exe_naming_convention(build["outputName"])
        relative_output_name = str(Path(build_name) / exe_name)
        pfw.build(
            rule="exe",
            outputs=relative_output_name,
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
    def build_dynamic_library(pfw: Writer, build: Dict, parsed_toml: Dict):
        build_name = build["name"]
        extra_flags = ["-DEXPORT_DLL_PUBLIC", "-fvisibility=hidden", "-fPIC"]

        compiler, _, cxxflags, defines = commonbuilds.get_toolchain_and_flags(
            build, parsed_toml
        )
        defines = PrefixHashDefine(defines)

        includes = get_includes_for_build(build, parsed_toml)
        obj_files = add_compile_rule(pfw, build, parsed_toml, includes, extra_flags)

        lib_infos = commonbuilds.get_required_library_information(build, parsed_toml)
        linker_args = generate_linker_args(build, parsed_toml)

        full_library_names = commonbuilds.get_full_library_name_convention(
            lib_infos,
            linux_add_static_library_naming_convention,
            linux_add_dynamic_library_naming_convention,
        )

        library_name = linux_add_dynamic_library_naming_convention(build["outputName"])
        relative_output_name = str(PurePosixPath(build_name) / library_name)
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


def add_naming_convention(
    output_name: str,
    build_type: str,
    static_convention_func=linux_add_static_library_naming_convention,
    dynamic_convention_func=linux_add_dynamic_library_naming_convention,
    exe_convention_func=linux_add_exe_naming_convention,
):
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
