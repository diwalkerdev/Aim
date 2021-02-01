import argparse
import subprocess
import sys

import toml

from aim_build import gccbuilds
from aim_build import msvcbuilds
from aim_build import osxbuilds
from aim_build.schema import target_schema
from aim_build.utils import *
from aim_build.version import __version__


def find_build(build_name, builds):
    for build in builds:
        if build["name"] == build_name:
            return build
    else:
        raise RuntimeError(f"Failed to find build with name: {build_name}")


def run_ninja(working_dir, build_name):
    command = ["ninja", "-v", f"-C{build_name}", build_name]
    command_str = " ".join(command)
    print(f'Executing "{command_str}"')

    process = subprocess.Popen(
        command, cwd=str(working_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    for line in iter(process.stdout.readline, b""):
        sys.stdout.write(line.decode("utf-8"))
    for line in iter(process.stderr.readline, b""):
        sys.stderr.write(line.decode("utf-8"))


def run_ninja_generation(parsed_toml, project_dir: Path, build_dir: Path):
    compiler = parsed_toml["compiler"]
    archiver = parsed_toml["ar"]
    frontend = parsed_toml["compilerFrontend"]

    flags = parsed_toml.get("flags", [])
    defines = parsed_toml.get("defines", [])
    builds = parsed_toml["builds"]

    project_ninja = build_dir / "build.ninja"
    with project_ninja.open("w+") as project_fd:
        from ninja_syntax import Writer

        project_writer = Writer(project_fd)
        project_writer.include(str(build_dir / "rules.ninja"))

        for build_info in builds:
            print(f'Generating ninja file for {build_info["name"]}')
            build_info["directory"] = project_dir
            build_info["build_dir"] = build_dir
            build_info["global_flags"] = flags
            build_info["global_defines"] = defines
            build_info["global_compiler"] = compiler
            build_info["global_archiver"] = archiver

            if frontend == "msvc":
                # builder = msvcbuilds.MSVCBuilds(compiler, compiler_c, archiver)
                assert False, "MSVC frontend is currently not supported."
            elif frontend == "osx":
                builder = osxbuilds.OsxBuilds()
            else:
                builder = gccbuilds.GCCBuilds()

            builder.build(build_info, parsed_toml, project_writer)


def entry():
    # print("DEV")

    script_path = Path(__file__).parent
    print(str(script_path))
    assert((script_path / "../../demo/Calculator/builds/linux-clang++-debug/target.toml").exists())

    # TODO: Get version automatically from the pyproject.toml file.
    parser = argparse.ArgumentParser(description=f"Version {__version__}")

    parser.add_argument("-v", "--version", action="version", version=__version__)
    sub_parser = parser.add_subparsers(dest="command", help="Commands")

    build_parser = sub_parser.add_parser(
        "list", help="displays the builds for the target"
    )
    build_parser.add_argument(
        "--target", type=str, required=True, help="path to target file directory"
    )

    init_parser = sub_parser.add_parser("init", help="creates a project structure")
    init_parser.add_argument(
        "--demo", help="Create additional demo files", action="store_true"
    )

    build_parser = sub_parser.add_parser("build", help="executes a build")
    build_parser.add_argument("build", type=str, help="The build name")

    build_parser.add_argument(
        "--target", type=str, required=True, help="path to target file directory"
    )

    build_parser.add_argument(
        "--skip_ninja_regen",
        help="by-pass the ninja file generation step",
        action="store_true",
    )

    build_parser = sub_parser.add_parser(
        "clobber", help="deletes all build artifacts for the specified target"
    )
    build_parser.add_argument(
        "--target", type=str, required=True, help="path to target file directory"
    )

    args = parser.parse_args()
    mode = args.command
    if mode == "init":
        run_init(args.demo)
    elif mode == "build":
        run_build(args.build, args.target, args.skip_ninja_regen)
    elif mode == "list":
        run_list(args.target)
    elif mode == "clobber":
        run_clobber(args.target)
    else:
        import sys

        parser.print_help(sys.stdout)


WindowsDefaultTomlFile = """\
cxx = "clang-cl"
cc = "clang-cl"
ar = "llvm-ar"
compilerFrontend="msvc"

flags = [
    "/std:c++17",
    "/Zi",
]

defines = []

#[[builds]]
#    name = "static"
#    buildRule = "staticlib"
#    outputName = "libraryName.lib"
#    srcDirs = ["../lib"]
#    includePaths = ["../include"]

[[builds]]
    name = "shared"
    buildRule = "dynamiclib"
    outputName = "libraryName.dll"
    srcDirs = ["../lib"]
    includePaths = ["../include"]

[[builds]]
    name = "exe"
    requires= ["shared"]
    buildRule = "exe"
    outputName = "exeName.exe"
    srcDirs = ["../app"]
    includePaths = ["../lib"]
    libraryPaths = ["./shared"]
    libraries = [""]
"""

LinuxDefaultTomlFile = """\
projectRoot = "../.."

cxx = "clang++"
cc = "clang"
ar = "ar"
compilerFrontend="gcc"

flags = [
    "-std=c++17",
    "-g"
]

defines = []

[[builds]]                              # a list of builds.
    name = "lib_calculator"             # the unique name for this build.
    buildRule = "staticlib"             # the type of build, in this case create a static library.
    outputName = "Calculator"      # the library output name,
    srcDirs = ["lib"]                   # the src directories  to build the static library from.
    includePaths = ["include"]    # additional include paths to use during the build.

#[[builds]]
#    name = "lib_calculator_so"         # the unique name for this build.
#    buildRule = "dynamiclib"           # the type of build, in this case create a shared library.
#    outputName = "Calculator"    # the library output name,
#    srcDirs = ["lib"]                  # the src directories to build the shared library from.
#    includePaths = ["include"]         # additional include paths to use during the build.

[[builds]]
    name = "exe"                        # the unique name for this build.
    buildRule = "exe"                   # the type of build, in this case an executable.
    requires = ["lib_calculator"]       # build dependencies. Aim figures out the linker flags for you.
    outputName = "the_calculator"   # the exe output name,
    srcDirs = ["src"]                   # the src directories to build the shared library from.
    includePaths = ["include"]          # additional include paths to use during the build.
    #libraryPaths = []                   # additional library paths, used for including third party libraries.
    #libraries = []                      # additional libraries, used for including third party libraries.
"""

CALCULATOR_CPP = """\
#include "calculator.h"

float add(float x, float y)
{
    return x + y;
}
"""

CALCULATOR_H = """\
#ifndef CALCULATOR_H
#define CALCULATOR_H

float add(float x, float y);

#endif
"""

MAIN_CPP = """\
#include "calculator.h"
#include <stdio.h>

int main()
{
    float result = add(40, 2);
    printf("The result is %f\\n", result);
    return 0;
}
"""


def run_init(add_demo_files):
    project_dir = Path().cwd()
    dirs = ["include", "src", "lib", "tests", "builds"]
    dirs = [project_dir / x for x in dirs]
    print(f"Creating directories...")
    for a_dir in dirs:
        print(f"\t{str(a_dir)}")
        a_dir.mkdir(exist_ok=True)

    windows_targets = [
        "windows-clang_cl-debug",
        "windows-clang_cl-release",
    ]

    linux_targets = ["linux-clang++-debug", "linux-clang++-release"]

    print("Creating common build targets...")
    build_dir = project_dir / "builds"
    for target in windows_targets:
        target_dir = build_dir / target
        target_dir.mkdir(exist_ok=True)
        # print(f"\t{str(target_dir)}")

        toml_file = target_dir / "target.toml"
        toml_file.touch(exist_ok=True)
        print(f"\t{str(toml_file)}")

        if add_demo_files:
            toml_file.write_text(WindowsDefaultTomlFile)

    for target in linux_targets:
        target_dir = build_dir / target
        target_dir.mkdir(exist_ok=True)
        # print(f"\t{str(target_dir)}")

        toml_file = target_dir / "target.toml"
        toml_file.touch(exist_ok=True)
        print(f"\t{str(toml_file)}")

        if add_demo_files:
            toml_file.write_text(LinuxDefaultTomlFile)

    if add_demo_files:
        (dirs[0] / "calculator.h").write_text(CALCULATOR_H)
        (dirs[1] / "main.cpp").write_text(MAIN_CPP)
        (dirs[2] / "calculator.cpp").write_text(CALCULATOR_CPP)


def run_build(build_name, target_path, skip_ninja_regen):
    print("Running build...")
    build_dir = Path().cwd()

    if target_path:
        target_path = Path(target_path)
        if target_path.is_absolute():
            build_dir = target_path
        else:
            build_dir = build_dir / Path(target_path)

    # ninja_path = project_dir / "build.ninja"
    toml_path = build_dir / "target.toml"

    with toml_path.open("r") as toml_file:
        parsed_toml = toml.loads(toml_file.read())

        builds = parsed_toml["builds"]
        the_build = find_build(build_name, builds)
        root_dir = parsed_toml["projectRoot"]
        project_dir = (build_dir / root_dir).resolve()
        assert project_dir.exists(), f"{str(project_dir)} does not exist."

        try:
            target_schema(parsed_toml, project_dir)
        except RuntimeError as e:
            print(f"Error: {e.args[0]}")
            exit(-1)

        if not skip_ninja_regen:
            print("Generating ninja files...")
            run_ninja_generation(parsed_toml, project_dir, build_dir)
            with (build_dir.resolve() / "compile_commands.json").open("w+") as cc:
                command = ["ninja", "-C", str(build_dir.resolve()), "-t", "compdb"]
                subprocess.run(command, stdout=cc)

        run_ninja(build_dir, the_build["name"])


def run_list(target_path):
    build_dir = Path().cwd()

    if target_path:
        target_path = Path(target_path)
        if target_path.is_absolute():
            build_dir = target_path
        else:
            build_dir = build_dir / Path(target_path)

    toml_path = build_dir / "target.toml"

    with toml_path.open("r") as toml_file:
        parsed_toml = toml.loads(toml_file.read())

        builds = parsed_toml["builds"]

        frontend = parsed_toml["compilerFrontend"]

        if frontend == "msvc":
            # builder = msvcbuilds.MSVCBuilds("", "", "")
            assert False, "MSVC frontend is currently not supported."
        elif frontend == "osx":
            builder = osxbuilds.OsxBuilds()
        else:
            builder = gccbuilds.GCCBuilds()

        header = ["Item", "Name", "Build Rule", "Output Name"]
        table = []

        for number, build in enumerate(builds):
            output_name = builder.add_naming_convention(
                build["outputName"], build["buildRule"]
            )
            row = [number, build["name"], build["buildRule"], output_name]
            table.append(row)

        from tabulate import tabulate

        print()
        print(tabulate(table, header))
        print()


def run_clobber(target_path):
    build_dir = Path().cwd()

    if target_path:
        target_path = Path(target_path)
        if target_path.is_absolute():
            build_dir = target_path
        else:
            build_dir = build_dir / Path(target_path)

    assert (build_dir / "target.toml").exists(), (
        f"Failed to find target.toml file in {str(build_dir)}.\n"
        "You might be trying to delete a directory that you want to keep."
    )

    print(f"Clobbering {str(build_dir)}...")

    dir_contents = build_dir.glob("*")
    for item in dir_contents:
        if item.name != "target.toml":
            print(f"Deleting {item.name}")
            if item.is_dir():
                import shutil

                shutil.rmtree(str(item))
            else:
                os.remove(str(item))


if __name__ == "__main__":
    entry()
