from unittest import TestCase
from aim_build.gccbuilds import *
from aim_build.schema import target_schema
import tempfile

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
            "srcDirs": ["a/src"],
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
            "srcDirs": ["b/src/file_0.c"],
            "includePaths": ["b/include"],
            "systemIncludePaths": ["/usr/include"],
            "localIncludePaths": ["b/local/include"],
            "outputName": "b"
        },
    ],
}


def setup_build(target_file, build_name, root=None):
    # Note(DW): this can be used to validate the target file.
    #
    # target_schema(toml, project_path)

    build = find_build(build_name, target_file["builds"])

    # Note(DW): build_dir is the path provided to the target file.
    #
    build_dir = Path("builds") / "os"
    if root:
        build_dir = Path(root) / build_dir

    build["build_dir"] = build_dir

    # TODO: Remove the need of project_dir / directory
    # project dir/directory is needed by get_src_files to resolve the directory location.
    # If we pass the target file to get_src_files we can resolve the location without adding
    # random variables into the build.
    root_dir = target_file["projectRoot"]
    project_dir = build_dir / root_dir
    build["directory"] = project_dir

    # Note(DW): buildPath is the path where the build actually happens.
    #
    build_path = build_dir / build_name

    build["buildPath"] = build_path
    return build


def make_tmp_directory_structure():
    tmp_dir = tempfile.TemporaryDirectory()

    directories = [
        "builds/os"
    ]

    tmp_files_a = [
        "a/src/file_0.cpp",
        "a/src/file_1.cpp"
    ]

    tmp_files_b = [
        "b/src/file_0.c",
        "b/src/file_1.c"
    ]

    for directory in directories:
        path = Path(tmp_dir.name) / directory
        path.mkdir(parents=True, exist_ok=False)

    all_files = tmp_files_a + tmp_files_b
    for file in all_files:
        path = Path(tmp_dir.name) / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=False)

    return tmp_dir


def find_str(string: str, paths: List[Path]):
    found = False
    for p  in paths:
        if string == str(p):
            found = True
            break
    return found


class TestTargetFiles(TestCase):
    def test_includes_for_build(self):
        # Notes:
        #   + include paths are relative to build directory.
        build = setup_build(global_target_file, "a")
        result = get_includes_for_build(build, global_target_file)

        self.assertEqual(len(result), 4)
        self.assertTrue("-I../../a/include" in result)
        self.assertTrue("-I../../b/include" in result)
        self.assertTrue("-isystem/usr/include" in result)
        self.assertTrue("-iquote../../b/local/include" in result)

    def test_toolchain_and_flags(self):
        build = setup_build(global_target_file, "a")
        cxx, ar, cxx_flags, defines = get_toolchain_and_flags(build, global_target_file)

        self.assertEqual(cxx, "g++")
        self.assertEqual(ar, "ar")
        self.assertEqual(cxx_flags, ["-std=c++17", "-Wall"])
        self.assertEqual(defines, ["-DEnableFeature"])

    def test_toolchain_and_flags_with_local_overrides(self):
        build = setup_build(global_target_file, "b")
        cxx, ar, cxx_flags, defines = get_toolchain_and_flags(build, global_target_file)

        self.assertEqual(cxx, "gcc")
        self.assertEqual(ar, "gcc-ar")
        self.assertEqual(cxx_flags, ["-std=c99"])
        self.assertEqual(defines, ["-DEnableOtherFeature"])

    def test_get_src_files(self):
        # Notes:
        #   + src files are relative to build directory.
        #   + srcDirs accepts directories or specific src files.
        tmp_dir = make_tmp_directory_structure()
        with tmp_dir:
            build_a = setup_build(global_target_file, "a", tmp_dir.name)
            paths = get_src_files(build_a, global_target_file)

            obj_files = ToObjectFiles(paths)
            obj_files = prepend_paths(Path(build_a["name"]), obj_files)

            self.assertEqual(len(paths), 2)
            self.assertTrue(find_str("../../a/src/file_0.cpp", paths))
            self.assertTrue(find_str("../../a/src/file_1.cpp", paths))

            self.assertEqual(len(obj_files), 2)
            self.assertTrue(find_str("a/file_0.o", obj_files))
            self.assertTrue(find_str("a/file_1.o", obj_files))

            build_b = setup_build(global_target_file, "b", tmp_dir.name)
            paths = get_src_files(build_b, global_target_file)

            obj_files = ToObjectFiles(paths)
            obj_files = prepend_paths(Path(build_b["name"]), obj_files)

            self.assertEqual(len(paths), 1)
            self.assertTrue(find_str("../../b/src/file_0.c", paths))

            self.assertEqual(len(obj_files), 1)
            self.assertTrue(find_str("b/file_0.o", obj_files))

