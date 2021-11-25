projectRoot = "../../"
compiler = "clang-cl"
archiver = "llvm-ar"
compilerFrontend = "msvc"
flags = [
    "/std:c++17",
    "/Zi"
]
builds = [
    {
        "name": "calculatorstatic",
        "buildRule": "staticLibrary",
        "outputName": "CalculatorStatic",
        "sourceFiles": [
            "lib/*.cpp"
        ],
        "includePaths": [
            "include"
        ]
    },
    {
        "name": "calculatordynamic",
        "buildRule": "dynamicLibrary",
        "outputName": "CalculatorShared",
        "sourceFiles": [
            "lib/*.cpp"
        ],
        "includePaths": [
            "include"
        ]
    },
    {
        "name": "calculatortests",
        "buildRule": "executable",
        "requires": [
            "calculatordynamic"
        ],
        "outputName": "CalculatorTests.exe",
        "sourceFiles": [
            "tests/*.cpp"
        ],
        "includePaths": [
            "include"
        ]
    },
    {
        "name": "calculatorapp",
        "buildRule": "executable",
        "requires": [
            "calculatordynamic"
        ],
        "outputName": "CalculatorApp.exe",
        "sourceFiles": [
            "src/*.cpp"
        ],
        "includePaths": [
            "include"
        ]
    }
]
