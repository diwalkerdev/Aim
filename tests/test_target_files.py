from unittest import TestCase
from pathlib import Path

from aim_build.gccbuilds import get_includes_for_build, get_include_paths, find_build
from aim_build.schema import target_schema

global_target_file = {
    "projectRoot": "../..",
    "ar": "ar",
    "compiler": "gcc",
    "compilerFrontend": "gcc",

    "builds": [
        {
            "name": "a",
            "buildRule": "exe",
            "requires": ["b"],
            "includePaths": ["a/include"],
            "outputName": "a"
        },
        {
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


def setup_build_a(target_file):
    # Note(DW): this can be used to validate the target file.
    #
    # target_schema(toml, project_path)

    build = find_build("a", target_file["builds"])

    # Note(DW): build_dir is the path provided to the target file.
    #
    build["build_dir"] = Path("builds") / "os"

    build_name = build["name"]
    build_dir = build["build_dir"]

    # Note(DW): buildPath is the path where the build actually happens.
    #
    build_path = build_dir / build_name

    build["buildPath"] = build_path
    return build


class TestTargetFiles(TestCase):
    def test_get_include_paths(self):
        build = setup_build_a(global_target_file)
        result = get_include_paths(build)

        self.assertEqual(len(result), 1)
        self.assertTrue("-I../../a/include" in result)

    def test_includes_for_build(self):
        build = setup_build_a(global_target_file)
        result = get_includes_for_build(build, parsed_toml=global_target_file)

        self.assertEqual(len(result), 4)
        self.assertTrue("-I../../a/include" in result)
        self.assertTrue("-I../../b/include" in result)
        self.assertTrue("-isystem/usr/include" in result)
        self.assertTrue("-iquote../../b/local/include" in result)
