from unittest import TestCase
from pathlib import Path

from aim_build.gccbuilds import get_includes_for_build, get_include_paths, find_build, get_toolchain_and_flags
from aim_build.schema import target_schema

global_target_file = {
    "projectRoot": "../..",
    "compilerFrontend": "gcc",
    "compiler": "g++",
    "archiver": "ar",
    "flags": ["-std=c++17", "-Wall"],
    "defines": ["EnableFeature"],

    "builds": [
        {
            "name": "a",
            "buildRule": "exe",
            "requires": ["b"],
            "includePaths": ["a/include"],
            "outputName": "a"
        },
        {
            "compiler": "gcc",
            "archiver": "gcc-ar",
            "flags": ["-std=c99"],
            "defines": ["EnableOtherFeature"],
            "name": "b",
            "buildRule": "staticLib",
            "requires": ["c"],
            "includePaths": ["b/include"],
            "systemIncludePaths": ["/usr/include"],
            "localIncludePaths": ["b/local/include"],
            "outputName": "b"
        },
    ],
}


def setup_build(target_file, build_name):
    # Note(DW): this can be used to validate the target file.
    #
    # target_schema(toml, project_path)

    build = find_build(build_name, target_file["builds"])

    # Note(DW): build_dir is the path provided to the target file.
    #
    build["build_dir"] = Path("builds") / "os"

    build_dir = build["build_dir"]

    # Note(DW): buildPath is the path where the build actually happens.
    #
    build_path = build_dir / build_name

    build["buildPath"] = build_path
    return build


class TestTargetFiles(TestCase):
    def test_get_include_paths(self):
        build = setup_build(global_target_file, "a")
        result = get_include_paths(build)

        self.assertEqual(len(result), 1)
        self.assertTrue("-I../../a/include" in result)

    def test_includes_for_build(self):
        build = setup_build(global_target_file, "a")
        result = get_includes_for_build(build, parsed_toml=global_target_file)

        self.assertEqual(len(result), 4)
        self.assertTrue("-I../../a/include" in result)
        self.assertTrue("-I../../b/include" in result)
        self.assertTrue("-isystem/usr/include" in result)
        self.assertTrue("-iquote../../b/local/include" in result)

    def test_toolchain_and_flags(self):
        build = setup_build(global_target_file, "a")
        cxx, ar, cxx_flags, defines = get_toolchain_and_flags(build, global_target_file)

        self.assertEqual("g++", cxx)
        self.assertEqual("ar", ar)
        self.assertEqual(["-std=c++17", "-Wall"], cxx_flags)
        self.assertEqual(["-DEnableFeature"], defines)

    def test_toolchain_and_flags_with_local_overrides(self):
        build = setup_build(global_target_file, "b")
        cxx, ar, cxx_flags, defines = get_toolchain_and_flags(build, global_target_file)

        self.assertEqual("gcc", cxx)
        self.assertEqual("gcc-ar", ar)
        self.assertEqual(["-std=c99"], cxx_flags)
        self.assertEqual(["-DEnableOtherFeature"], defines)
