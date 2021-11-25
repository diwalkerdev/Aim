projectRoot = "../../"
compiler = "clang-cl"
ar = "llvm-ar"
compilerFrontend = "msvc"
flags = [
    "/std:c++17",
    "/Zi"
]
builds = [
    {
        "name": "libraryname",
        "buildRule": "staticLibrary",
        "outputName": "LibraryName",
        "sourceFiles": [
            "lib/*.cpp"
        ],
        "includePaths": [
            "include"
        ]
    },
    {
        "name": "tests",
        "buildRule": "executable",
        "requires": [
            "libraryname"
        ],
        "outputName": "Tests",
        "sourceFiles": [
            "tests/*.cpp"
        ],
        "includePaths": [
            "include"
        ]
    },
    {
        "name": "application",
        "buildRule": "executable",
        "requires": [
            "libraryname"
        ],
        "outputName": "Applicatoin",
        "sourceFiles": [
            "src/*.cpp"
        ],
        "includePaths": [
            "include"
        ]
    }
]
