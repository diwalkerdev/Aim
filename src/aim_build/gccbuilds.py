import functools
from typing import Dict
from aim_build.utils import *
from ninja_syntax import Writer

PrefixIncludePath = functools.partial(prefix, "-I")
PrefixSystemIncludePath = functools.partial(prefix, "-isystem")
PrefixQuoteIncludePath = functools.partial(prefix, "-iquote")
PrefixLibraryPath = functools.partial(prefix, "-L")
PrefixLibrary = functools.partial(prefix, "-l")
PrefixHashDefine = functools.partial(prefix, "-D")
ToObjectFiles = src_to_o

FileExtensions = ["*.cpp", "*.cc", ".c"]


def get_src_files(build):
    directory = build["directory"]
    srcs = prepend_paths(directory, build["srcDirs"])
    src_dirs = [path for path in srcs if path.is_dir()]
    explicit_src_files = [path for path in srcs if path.is_file()]
    src_files = []
    for glob_pattern in FileExtensions:
        glob_files = flatten(glob(glob_pattern, src_dirs))
        src_files += glob_files

    src_files += explicit_src_files
    assert src_files, f"Fail to find any source files in {to_str(src_dirs)}."
    build_path = build["buildPath"] / ".."
    src_files = relpaths(src_files, build_path)
    return src_files


def get_include_paths(build):
    directory = build["buildPath"] / ".."
    include_paths = build.get("includePaths", [])
    include_paths = [Path(p) for p in include_paths]
    abs_paths = [p for p in include_paths if p.is_absolute()]
    rel_paths = [p for p in include_paths if not p.is_absolute()]
    rel_paths = relpaths(rel_paths, directory)

    includes = PrefixIncludePath(abs_paths) + PrefixIncludePath(rel_paths)
    return includes

def get_quote_include_paths(build):
    directory = build["buildPath"] / ".."
    include_paths = build.get("localIncludePaths", [])
    includes = relpaths(include_paths, directory)
    includes = PrefixQuoteIncludePath(includes)
    return includes

def get_system_include_paths(build):
    system_include_paths = build.get("systemIncludePaths", [])
    system_includes = PrefixSystemIncludePath(system_include_paths)
    return system_includes


def get_library_paths(build):
    directory = build["directory"]
    library_paths = build.get("libraryPaths", [])
    library_paths = prepend_paths(directory, library_paths)
    library_paths = PrefixLibraryPath(library_paths)
    return library_paths


def get_library_information(build):
    libraries = build.get("libraries", [])
    link_libraries = PrefixLibrary(libraries)
    return libraries, link_libraries


def find_build(build_name, builds):
    # Note, this should never fail, as required dependencies are checked by the schema.
    for build in builds:
        if build["name"] == build_name:
            return build


class GCCBuilds:
    def build(self, build, parsed_toml, project_writer: Writer):
        build_name = build["name"]
        the_build = build["buildRule"]
        project_dir = build["directory"]
        build_dir = build["build_dir"]

        build_path = build_dir / build_name
        build_path.mkdir(parents=True, exist_ok=True)

        build["buildPath"] = build_path

        if the_build == "staticlib":
            self.build_static_library(
                project_writer, build, parsed_toml
            )
        elif the_build == "exe":
            self.build_executable(
                project_writer, build, parsed_toml
            )
        elif the_build == "dynamiclib":
            self.build_dynamic_library(
                project_writer, build, parsed_toml
            )
        else:
            raise RuntimeError(f"Unknown build type {the_build}.")

    def add_compile_rule(self, pfw: Writer, build: Dict, parsed_toml, extra_flags: StringList = None):
        local_flags = build.get("flags", None)
        local_defines = build.get("defines", None)
        local_compiler = build.get("compiler", None)

        build_name = build["name"]
        build_path = build["buildPath"]

        cxxflags = local_flags if local_flags else build["global_flags"]
        if extra_flags:
            cxxflags = extra_flags + cxxflags
        defines = local_defines if local_defines else build["global_defines"]
        defines = PrefixHashDefine(defines)
        compiler = local_compiler if local_compiler else build["global_compiler"]

        src_files = get_src_files(build)
        includes = get_include_paths(build)
        includes += get_system_include_paths(build)
        includes += get_quote_include_paths(build)
        includes += self.get_required_include_information(build, parsed_toml)

        build_path = build["buildPath"]
        obj_files = ToObjectFiles(src_files)
        obj_files = prepend_paths(Path(build_name), obj_files)

        file_pairs = zip(to_str(src_files), to_str(obj_files))
        for src_file, obj_file in file_pairs:
            pfw.build(
                outputs=obj_file,
                rule="compile",
                inputs=src_file,
                variables={
                    "compiler": compiler,
                    "includes": includes,
                    "flags": cxxflags,
                    "defines": defines,
                },
            )
            pfw.newline()

        return obj_files

    def build_static_library(self, pfw: Writer, build: Dict, parsed_toml: Dict):
        build_name = build["name"]
        library_name = self.add_static_library_naming_convention(build["outputName"])

        local_flags = build.get("flags", None)
        local_defines = build.get("defines", None)
        local_archiver = build.get("archiver", None)

        cxxflags = local_flags if local_flags else build["global_flags"]
        defines = local_defines if local_defines else build["global_defines"]
        defines = PrefixHashDefine(defines)
        archiver = local_archiver if local_archiver else build["global_archiver"]

        build_path = build["buildPath"]

        includes = get_include_paths(build)
        includes += get_system_include_paths(build)
        includes += get_quote_include_paths(build)
        includes += self.get_required_include_information(build, parsed_toml)

        obj_files = self.add_compile_rule(pfw, build, parsed_toml)

        relative_output_name = str(Path(build_name) / library_name)

        pfw.build(
            outputs=relative_output_name,
            rule="archive",
            inputs=to_str(obj_files),
            variables={
                "archiver": archiver,
                "includes": includes,
                "flags": cxxflags,
                "defines": defines,
            },
        )

        pfw.newline()
        pfw.build(rule="phony", inputs=relative_output_name, outputs=library_name)
        pfw.newline()
        pfw.build(rule="phony", inputs=library_name, outputs=build_name)
        pfw.newline()

    def build_executable(self, pfw: Writer, build: Dict, parsed_toml: Dict):
        build_name = build["name"]
        exe_name = self.add_exe_naming_convention(build["outputName"])

        local_flags = build.get("flags", None)
        local_defines = build.get("defines", None)
        local_compiler = build.get("compiler", None)

        cxxflags = local_flags if local_flags else build["global_flags"]
        defines = local_defines if local_defines else build["global_defines"]
        defines = PrefixHashDefine(defines)
        compiler = local_compiler if local_compiler else build["global_compiler"]

        requires = build.get("requires", [])
        build_path = build["buildPath"]

        includes = get_include_paths(build)
        includes += get_system_include_paths(build)
        includes += get_quote_include_paths(build)
        includes += self.get_required_include_information(build, parsed_toml)

        library_paths = get_library_paths(build)
        (
            requires_libraries,
            requires_link_libraries,
            requires_library_paths,
            requires_library_types,
        ) = self.get_required_library_information(build, parsed_toml)
        libraries, link_libraries = get_library_information(build)

        rpath = self.get_rpath(build, parsed_toml)
        linker_args = (
            [rpath]
            + requires_library_paths
            + requires_link_libraries
            + library_paths
            + link_libraries
        )

        obj_files = self.add_compile_rule(pfw, build, parsed_toml)

        # Here we just need to manage the fact that the linker's library flag (-l) needs the library name without
        # lib .a/.so but the build dependency rule does need the full convention to find the build rule in the library's
        # build.ninja file.
        full_library_names = []
        for name, build_type in zip(requires_libraries, requires_library_types):
            if build_type == "staticlib":
                full_library_names.append(
                    self.add_static_library_naming_convention(name)
                )
            else:
                full_library_names.append(
                    self.add_dynamic_library_naming_convention(name)
                )

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
        pfw.newline()
        pfw.build(rule="phony", inputs=exe_name, outputs=build_name)
        pfw.newline()

    def build_dynamic_library(self, pfw: Writer, build: Dict, parsed_toml: Dict):
        build_name = build["name"]
        library_name = self.add_dynamic_library_naming_convention(build["outputName"])

        local_flags = build.get("flags", None)
        local_defines = build.get("defines", None)
        local_compiler = build.get("compiler", None)

        cxxflags = local_flags if local_flags else build["global_flags"]
        defines = local_defines if local_defines else build["global_defines"]
        compiler = local_compiler if local_compiler else build["global_compiler"]

        includes = get_include_paths(build)
        includes += get_system_include_paths(build)
        includes += get_quote_include_paths(build)
        includes += self.get_required_include_information(build, parsed_toml)

        library_paths = get_library_paths(build)

        (
            requires_libraries,
            requires_link_libraries,
            requires_library_paths,
            requires_library_types,
        ) = self.get_required_library_information(build, parsed_toml)
        libraries, link_libraries = get_library_information(build)

        linker_args = (
            requires_link_libraries
            + requires_library_paths
            + library_paths
            + link_libraries
        )

        requires = build.get("requires", [])
        build_path = build["buildPath"]

        extra_flags = ["-DEXPORT_DLL_PUBLIC",
                       "-fvisibility=hidden",
                      "-fPIC"]
        obj_files = self.add_compile_rule(pfw, build, parsed_toml, extra_flags)

        build_path = build["buildPath"]

        relative_output_name = str(Path(build_name) / library_name)

        # Here we just need to manage the fact that the linker's library flag (-l) needs the library name without
        # lib .a/.so but the build dependency rule does need the full convention to find the build rule in the library's
        # build.ninja file.
        full_library_names = []
        for name, build_type in zip(requires_libraries, requires_library_types):
            if build_type == "staticlib":
                full_library_names.append(
                    self.add_static_library_naming_convention(name)
                )
            else:
                full_library_names.append(
                    self.add_dynamic_library_naming_convention(name)
                )

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
        pfw.newline()
        pfw.build(rule="phony", inputs=library_name, outputs=build_name)
        pfw.newline()

    def get_required_library_information(self, build, parsed_toml):
        requires = build.get("requires", [])
        if not requires:
            return [], [], [], []

        library_names = []
        library_paths = []
        library_types = []
        for required in requires:
            the_dep = find_build(required, parsed_toml["builds"])
            library_types.append(the_dep["buildRule"])
            library_names.append(the_dep["outputName"])
            dep_name = the_dep["name"]
            library_paths.append(dep_name)

        # library_paths = prepend_paths(build["build_dir"], library_paths)
        library_paths = PrefixLibraryPath(library_paths)
        return library_names, PrefixLibrary(library_names), library_paths, library_types

    def get_required_include_information(self, build, parsed_toml):
        requires = build.get("requires", [])
        if not requires:
            return []

        include_paths = []
        system_include_paths = []
        quote_include_paths = []
        for required in requires:
            the_dep = find_build(required, parsed_toml["builds"])
            directory = build["buildPath"] / ".."

            includes = the_dep.get("includePaths", [])
            includes = relpaths(includes, directory)
            include_paths += includes

            quote_includes = the_dep.get("localIncludePaths", [])
            quote_includes = relpaths(quote_includes, directory)
            quote_include_paths += quote_includes

            system_includes = the_dep.get("systemIncludePaths", [])
            system_include_paths += system_include_paths

        include_args = PrefixIncludePath(include_paths)
        system_include_args = PrefixSystemIncludePath(system_include_paths)
        quote_args = PrefixQuoteIncludePath(quote_include_paths)
        return include_args + system_include_args + quote_args

    def get_rpath(self, build: Dict, parsed_toml: Dict):
        # Good blog post about rpath:
        # https://medium.com/@nehckl0/creating-relocatable-linux-executables-by-setting-rpath-with-origin-45de573a2e98
        requires = build.get("requires", [])
        library_paths = []

        for required in requires:
            the_dep = find_build(required, parsed_toml["builds"])
            if the_dep["buildRule"] == "dynamiclib":
                library_paths.append(the_dep["name"])

        build_dir = Path(build["build_dir"])
        current_build_dir = build_dir / build["name"]
        library_paths = prepend_paths(build_dir, library_paths)
        relative_paths = [
            relpath(Path(lib_path), current_build_dir) for lib_path in library_paths
        ]

        relative_paths = [f"$$ORIGIN/{rel_path}" for rel_path in relative_paths]
        relative_paths = ["$$ORIGIN"] + relative_paths

        relative_paths_string = escape_path(":".join(relative_paths))
        return f"-Wl,-rpath='{relative_paths_string}'"

    def add_naming_convention(self, output_name, build_type):
        if build_type == "staticlib":
            new_name = self.add_static_library_naming_convention(output_name)
        elif build_type == "dynamiclib":
            new_name = self.add_dynamic_library_naming_convention(output_name)
        else:
            new_name = self.add_exe_naming_convention(output_name)

        return new_name

    # TODO: These should take version strings as well.
    def add_static_library_naming_convention(self, library_name):
        return f"lib{library_name}.a"

    def add_dynamic_library_naming_convention(self, library_name):
        return f"lib{library_name}.so"

    def add_exe_naming_convention(self, exe_name):
        return f"{exe_name}.exe"


def log_build_information(build):
    build_name = build["name"]
    cxxflags = build["global_flags"] + build.get("flags", [])
    defines = build["global_defines"] + build.get("defines", [])
    includes = build["includes"]
    library_paths = build["libraryPaths"]
    output = build["outputName"]

    print(f"Running build: f{build_name}")
    print(f"FLAGS: {cxxflags}")
    print(f"DEFINES: {defines}")
    print(f"INCLUDE_PATHS: {includes}")
    print(f"LIBRARY_PATHS: {library_paths}")
    print(f"OUTPUT NAME: {output}")
    print("")
