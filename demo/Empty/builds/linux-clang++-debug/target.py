projectRoot = "../.."
compilerFrontend = "gcc"
compiler = "clang++"
ar = "ar"
flags = [
    "-std=c++20",
    "-O3",
    "-g",
    "-fsanitize=address",
    "-fno-omit-frame-pointer",
    "-fsanitize=undefined",
    "-Wall"
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
