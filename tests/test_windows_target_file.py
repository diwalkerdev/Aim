from pathlib import Path, PurePath
from unittest import TestCase
from aim_build.msvcbuilds import *
import tempfile

# TODO check that schema prevents local and system includes when frontend is msvc.

global_target_file = {
    "projectRoot": "../..",
    "compilerFrontend": "msvc",
    "compiler": "clang-cl",
    "archiver": "clang-ar",
    "flags": ["/std:c++17", "/Zi"],
    "defines": ["EnableFeature"],

    "builds": [
        {
            "name": "a",
            "buildRule": "exe",
            "requires": ["b", "c", "r", "i"],
            "includePaths": ["a/include"],
            "sourceFiles": ["a/src/*.cpp"],
            "outputName": "a",
            "libraryPaths": ["C:/SDL2"],
            "libraries": ["SDL2", "SDL2_image"]
        },
        {
            "compiler": "gcc",
            "archiver": "gcc-ar",
            "flags": ["/std=c99"],
            "defines": ["EnableOtherFeature"],
            "name": "b",
            "buildRule": "staticLib",
            "sourceFiles": ["b/src/file_0.c"],
            "includePaths": ["b/include", "C:/include", "b/local/include"],
            "outputName": "b"
        },
        {
            "name": "c",
            "buildRule": "dynamicLib",
            "includePaths": ["c/include"],
            "sourceFiles": ["c/src/*.cpp"],
            "outputName": "c"
        },
        {
            "name": "i",
            "buildRule": "headerOnly",
            "includePaths": ["i/include"]
        },
        {
            "name": "r",
            "buildRule": "libraryReference",
            "libraries": ["specialLibrary"],
            "libraryPaths": ["C:/SpecialLibrary"]
        }
    ],
}


def setup_build(target_file: Dict,
                build_name: str,
                root=None):
    # Note(DW): this can be used to validate the target file.
    #
    # from aim_build.schema import target_schema
    # target_schema(toml, project_path)

    build = commonbuilds.find_build(build_name, target_file["builds"])

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


def find_str(string: str, paths: List[PurePath]):
    found = False
    for p in paths:
        if string == str(p):
            found = True
            break
    return found


class TestTargetFiles(TestCase):
    # We begin by covering the major functions for building static libraries.
    #
    def test_includes_for_build(self):
        # Notes:
        #   + include paths are relative to build directory.
        build = setup_build(global_target_file, "a")
        result = get_includes_for_build(build, global_target_file)

        self.assertEqual(len(result), 6)
        self.assertTrue("/I..\\..\\a\\include" in result)
        self.assertTrue("/I..\\..\\b\\include" in result)
        self.assertTrue("/I..\\..\\c\\include" in result)
        self.assertTrue("/I..\\..\\i\\include" in result)
        self.assertTrue("/IC:\\include" in result)
        self.assertTrue("/I..\\..\\b\\local\\include" in result)

    def test_toolchain_and_flags(self):
        build = setup_build(global_target_file, "a")
        cxx, ar, cxx_flags, defines, _, __ = commonbuilds.get_toolchain_and_flags(build, global_target_file)

        self.assertEqual(cxx, "clang-cl")
        self.assertEqual(ar, "clang-ar")
        self.assertEqual(cxx_flags, ["/std:c++17", "/Zi"])
        self.assertEqual(defines, ["EnableFeature"])

    def test_toolchain_and_flags_with_local_overrides(self):
        build = setup_build(global_target_file, "b")
        cxx, ar, cxx_flags, defines, _, __ = commonbuilds.get_toolchain_and_flags(build, global_target_file)

        # Note, these overrides don't make any sense, but it is ok since we're not actually building anything
        # so it doesn't matter.
        self.assertEqual(cxx, "gcc")
        self.assertEqual(ar, "gcc-ar")
        self.assertEqual(cxx_flags, ["/std=c99"])
        self.assertEqual(defines, ["EnableOtherFeature"])

    def test_get_src_files(self):
        # Notes:
        #   + src files are relative to build directory.
        #   + sourceFiles accepts directories or specific src files.
        tmp_dir = make_tmp_directory_structure()
        with tmp_dir:
            build_a = setup_build(global_target_file, "a", tmp_dir.name)
            paths = get_src_for_build(build_a, global_target_file)

            self.assertEqual(len(paths), 2)
            self.assertTrue(find_str("..\\..\\a\\src\\file_0.cpp", paths))
            self.assertTrue(find_str("..\\..\\a\\src\\file_1.cpp", paths))

            obj_files = ToObjectFiles(paths)
            obj_files = prepend_paths(PureWindowsPath(build_a["name"]), obj_files)
            obj_files = convert_posix_to_windows(obj_files)

            self.assertEqual(len(obj_files), 2)
            self.assertTrue(find_str("a\\file_0.obj", obj_files))
            self.assertTrue(find_str("a\\file_1.obj", obj_files))

            build_b = setup_build(global_target_file, "b", tmp_dir.name)
            paths = get_src_for_build(build_b, global_target_file)

            self.assertEqual(len(paths), 1)
            self.assertTrue(find_str("..\\..\\b\\src\\file_0.c", paths))

            obj_files = ToObjectFiles(paths)
            obj_files = prepend_paths(PureWindowsPath(build_b["name"]), obj_files)
            obj_files = convert_posix_to_windows(obj_files)

            self.assertEqual(len(obj_files), 1)
            self.assertTrue(find_str("b\\file_0.obj", obj_files))

    # Next we cover dynamic libraries.
    #
    # def test_rpath(self):
    #     build_a = setup_build(global_target_file, "a")
    #     paths = get_rpath(build_a, global_target_file)
    #
    #     # Note, $ and : must be escaped, hence the extra $s.
    #     self.assertEqual(paths, "-Wl,-rpath=\'$$ORIGIN$:$$ORIGIN/../c\'")
    #
    #     build_b = setup_build(global_target_file, "b")
    #     paths = get_rpath(build_b, global_target_file)
    #
    #     self.assertEqual(paths, "-Wl,-rpath=\'$$ORIGIN\'")

    def test_external_library_information(self):
        build_a = setup_build(global_target_file, "a")
        external_libraries_names, external_libraries_paths = get_external_libraries_information(build_a)
        external_libraries_names = PrefixLibrary(external_libraries_names)
        external_libraries_paths = PrefixLibraryPath(external_libraries_paths)

        self.assertEqual(len(external_libraries_names), 2)
        self.assertTrue("SDL2" in external_libraries_names)
        self.assertTrue("SDL2_image" in external_libraries_names)

        self.assertEqual(len(external_libraries_paths), 1)
        self.assertTrue("/LIBPATH:C:\\SDL2" in external_libraries_paths)

    def test_required_library_information(self):
        build_a = setup_build(global_target_file, "a")

        # Note, get_required_library_information ignores headerOnly and LibraryReference build rules.
        lib_info = commonbuilds.get_required_library_information(build_a, global_target_file)

        self.assertEqual(lib_info[0].name, "b")
        self.assertEqual(lib_info[0].path, "b")
        self.assertEqual(lib_info[0].type, "staticLib")

        self.assertEqual(lib_info[1].name, "c")
        self.assertEqual(lib_info[1].path, "c")
        self.assertEqual(lib_info[1].type, "dynamicLib")

        requires_libraries = PrefixLibrary([info.name for info in lib_info])
        requires_library_paths = PrefixLibraryPath([info.path for info in lib_info])

        self.assertTrue("b" in requires_libraries)
        self.assertTrue("c" in requires_libraries)

        self.assertTrue("/LIBPATH:b" in requires_library_paths)
        self.assertTrue("/LIBPATH:c" in requires_library_paths)

    def test_library_reference(self):
        build_a = setup_build(global_target_file, "a")

        ref_libraries, ref_library_paths = commonbuilds.get_reference_library_information(build_a, global_target_file)
        ref_libraries = PrefixLibrary(ref_libraries)
        ref_library_paths = PrefixLibraryPath(convert_posix_to_windows(ref_library_paths))

        self.assertTrue(len(ref_libraries), 1)
        self.assertTrue("specialLibrary" in ref_libraries)

        self.assertTrue(len(ref_library_paths), 1)
        self.assertTrue("/LIBPATH:C:\\SpecialLibrary" in ref_library_paths)

    def test_full_library_names(self):
        build_a = setup_build(global_target_file, "a")

        lib_info = commonbuilds.get_required_library_information(build_a, global_target_file)

        # Note, full library names are required as an implicit rule for the build.
        # Note, static is used twice because on windows we don't link against the dll but its
        # corresponding lib file.
        full_library_names = commonbuilds.get_full_library_name_convention(lib_info,
                                                                           windows_add_static_library_naming_convention,
                                                                           windows_add_static_library_naming_convention)

        self.assertTrue("libb.lib" in full_library_names)
        self.assertTrue("libc.lib" in full_library_names)
