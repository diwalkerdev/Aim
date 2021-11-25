projectRoot = "../.."
compilerFrontend = "gcc"
compiler = "clang++"
archiver = "ar"
flags = [
    "-std=c++17",
    "-O3",
    "-g",
    "-fsanitize=address",
    "-fno-omit-frame-pointer",
    "-fsanitize=undefined",
    "-Wall"
]
builds = [
    {
        "name": "calculatorstatic",
        "buildRule": "staticLibrary",
        "outputName": "CalculatorStatic",
        "sourceFiles": ["lib/*.cpp"],
        "includePaths": [
            "include"
        ]
    },
    {
        "name": "calculatordynamic",
        "buildRule": "dynamicLibrary",
        "outputName": "CalculatorShared",
        "sourceFiles": ["lib/*.cpp"],
        "includePaths": [
            "include"
        ]
    },
    {
        "name": "calculatortests",
        "buildRule": "executable",
        "requires": ["calculatorstatic"],
        "outputName": "CalculatorTests",
        "sourceFiles": ["tests/*.cpp"],
        "includePaths": ["include"]
    },
    {
        "name": "calculatorapp",
        "buildRule": "executable",
        "requires": ["calculatordynamic"],
        "outputName": "CalculatorApp",
        "sourceFiles": ["src/*.cpp"],
        "includePaths": ["include"]
    }
]
