import functools
from typing import Dict
from ninja_syntax import Writer
from pathlib import PureWindowsPath

from aim_build.msvcbuildrules import *
from aim_build.utils import *
from aim_build import commonbuilds

PrefixIncludePath = functools.partial(prefix, "/I")
PrefixLibraryPath = functools.partial(prefix, "/LIBPATH:")
PrefixLibrary = functools.partial(prefix, "")
ToObjectFiles = src_to_obj


def implicit_library_inputs(libraries):
    implicits = []
    for library in libraries:
        parts = library.split(".")
        if parts[1] == "dll":
            implicits.append(parts[0] + ".exp")
            implicits.append(parts[0] + ".lib")
        implicits.append(library)

    return implicits


def implicit_library_outputs(libraries):
    implicits = []
    for library in libraries:
        parts = library.split(".")
        if parts[1] == "dll":
            implicits.append(parts[0] + ".exp")
            implicits.append(parts[0] + ".lib")

    return implicits


def convert_dlls_to_lib(libraries):
    new_libraries = []
    for library in libraries:
        parts = library.split(".")
        if parts[1] == "dll":
            new_libraries.append(parts[0] + ".lib")
        else:
            new_libraries.append(library)

    return new_libraries


def get_src_files(build):
    directory = build["directory"]
    src_dirs = build["srcDirs"]
    src_paths = prepend_paths(directory, src_dirs)
    src_files = flatten(glob("*.cpp", src_paths)) + flatten(glob("*.c", src_paths))
    assert src_files, "Fail to find any source files."
    return src_files


def get_library_paths(build):
    directory = build["directory"]
    library_paths = build.get("libraryPaths", [])
    library_paths = prepend_paths(directory, library_paths)
    library_paths = PrefixLibraryPath(add_quotes(library_paths))
    return library_paths


def get_library_information(build):
    libraries = build.get("libraries", [])
    implicits = implicit_library_inputs(libraries)
    link_libraries = PrefixLibrary(convert_dlls_to_lib(libraries))
    return libraries, implicits, link_libraries


def get_third_party_library_information(build):
    third_libraries = build.get("thirdPartyLibraries", [])
    third_libraries = PrefixLibrary(convert_dlls_to_lib(third_libraries))
    return third_libraries


def convert_posix_to_windows(paths: StringList):
    return [path.replace("/", "\\") for path in paths]


def convert_strings_to_paths(paths: StringList):
    return [PureWindowsPath(path) for path in convert_posix_to_windows(paths)]


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


class MSVCBuilds:
    def __init__(self, cxx_compiler, c_compiler, archiver):
        self.cxx_compiler = cxx_compiler
        self.c_compiler = c_compiler
        self.archiver = archiver

    def add_rules(self, build):
        directory = build["directory"]
        ninja_path = directory / "rules.ninja"
        with ninja_path.open("w+") as ninja_file:
            writer = Writer(ninja_file)
            add_compile(writer)
            add_ar(writer)
            add_exe(writer)
            add_shared(writer)

    def build(self, build):
        the_build = build["buildRule"]

        build_name = build["name"]
        project_dir = build["directory"]

        build_path = project_dir / build_name
        build_path.mkdir(parents=True, exist_ok=True)

        ninja_path = build_path / "build.ninja"
        build["buildPath"] = build_path

        self.add_rules(build)

        with ninja_path.open("w+") as ninja_file:
            ninja_writer = Writer(ninja_file)
            rule_path = (project_dir / "rules.ninja").resolve()
            ninja_writer.include(escape_path(str(rule_path)))
            ninja_writer.newline()

            if the_build == "staticLib":
                self.build_static_library(ninja_writer, build)
            elif the_build == "exe":
                self.build_executable(ninja_writer, build)
            elif the_build == "dynamicLib":
                self.build_dynamic_library(ninja_writer, build)
            else:
                raise RuntimeError(f"Unknown build type {the_build}.")

    def add_compile_rule(self, nfw: Writer, build: Dict):
        cxxflags = build["flags"]
        defines = build["defines"]

        src_files = get_src_files(build)
        includes = commonbuilds.get_include_paths(build)

        # Its very important to specify the absolute path to the obj files.
        # This prevents recompilation of files when an exe links against a library.
        # Without the absolute path to the obj files, it would build the files again
        # in the current (exe's) build location.
        build_path = build["buildPath"]
        obj_files = ToObjectFiles(src_files)
        obj_files = prepend_paths(build_path, obj_files)

        file_pairs = zip(to_str(src_files), to_str(obj_files))
        for src_file, obj_file in file_pairs:
            nfw.build(
                outputs=obj_file,
                rule="compile",
                inputs=src_file,
                variables={
                    "compiler": self.cxx_compiler,
                    "includes": includes,
                    "flags": cxxflags,
                    "defines": defines,
                },
            )
            nfw.newline()

        return obj_files

    def build_static_library(self, nfw: Writer, build: Dict):
        build_name = build["name"]
        library_name = build["outputName"]

        obj_files = self.add_compile_rule(nfw, build)

        nfw.build(outputs=library_name, rule="ar", inputs=to_str(obj_files))
        nfw.newline()

        nfw.build(rule="phony", inputs=library_name, outputs=build_name)
        nfw.newline()

    def build_executable(self, nfw, build: Dict):
        build_name = build["name"]
        exe_name = build["outputName"]
        cxxflags = build["flags"]
        defines = build["defines"]
        requires = build.get("requires", [])
        build_path = build["buildPath"]

        includes = commonbuilds.get_include_paths(build)
        library_paths = get_library_paths(build)
        libraries, implicits, link_libraries = get_library_information(build)
        third_libraries = get_third_party_library_information(build)

        linker_args = library_paths + link_libraries + third_libraries

        for requirement in requires:
            ninja_file = (build_path.parent / requirement / "build.ninja").resolve()
            assert ninja_file.exists(), f"Failed to find {str(ninja_file)}."
            nfw.subninja(escape_path(str(ninja_file)))
            nfw.newline()

        obj_files = self.add_compile_rule(nfw, build)

        nfw.build(
            outputs=exe_name,
            rule="exe",
            inputs=to_str(obj_files),
            implicit=implicits,
            variables={
                "compiler": self.cxx_compiler,
                "includes": includes,
                "flags": cxxflags,
                "defines": defines,
                "exe_name": exe_name,
                "linker_args": " ".join(linker_args),
            },
        )
        nfw.newline()

        nfw.build(rule="phony", inputs=exe_name, outputs=build_name)
        nfw.newline()

    def build_dynamic_library(self, nfw, build: Dict):
        build_name = build["name"]
        lib_name = build["outputName"]
        cxxflags = build["flags"]
        defines = build["defines"]

        includes = commonbuilds.get_include_paths(build)
        library_paths = get_library_paths(build)
        libraries, implicits, link_libraries = get_library_information(build)
        third_libraries = get_third_party_library_information(build)

        linker_args = library_paths + link_libraries + third_libraries
        implicit_outputs = implicit_library_outputs([lib_name])

        obj_files = self.add_compile_rule(nfw, build)

        nfw.build(
            rule="shared",
            inputs=to_str(obj_files),
            outputs=lib_name,
            implicit=implicits,
            implicit_outputs=implicit_outputs,
            variables={
                "compiler": self.cxx_compiler,
                "includes": includes,
                "flags": " ".join(cxxflags),
                "defines": " ".join(defines),
                "lib_name": lib_name,
                "linker_args": " ".join(linker_args),
            },
        )
        nfw.newline()

        nfw.build(rule="phony", inputs=lib_name, outputs=build_name)
        nfw.newline()


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
