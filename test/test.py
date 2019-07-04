import toml

from aim.schema import target_schema

TargetFile = """
unknown = ""
cxx = "clang-cl"
cc = "clang-cl"
ar = "llvm-ar"
compilerFrontend="msvc"

flags = [
    "/std:c++17",
    "/Zi",
]

defines = []

[[builds]]
    name = "parameterestimation"
    buildRule = "staticlib"
    requires = []
    outputName = "libParameterEstimation.lib"
    srcDirs = ["../../parameterestimation"]
    includePaths = [
        "../../parameterestimation/include",
        "../../include",
        "../../../../3rdParty/eigen-eigen-323c052e1731",
    ]

[[builds]]
    name = "parameterestimationdll"
    buildRule = "dynamiclib"
    outputName = "ParameterEstimation.dll"
    requires = []
    srcDirs = ["../../parameterestimation"]
    includePaths = [
        "../../parameterestimation/include",
        "../../include",
        "../../../../3rdParty/eigen-eigen-323c052e1731",
    ]
    libraryPaths = []
    libraries = []

[[builds]]
    name = "demo"
    buildRule = "exe"
    requires = ["parameterestimation"]
    outputName = "Demo.exe"
    srcDirs = ["../../demo"]
    includePaths = [
        "../../demo/include",
        "../../include",
        "../../../../3rdParty/eigen-eigen-323c052e1731",
    ]
    libraryPaths = []
    libraries = ["ParameterEstimation.lib"]

[[builds]]
    name = "test"
    buildRule = "exe"
    requires = ["parameterestimation"]
    outputName = "Tests.exe"
    srcDirs = ["../../test"]
    includePaths = [
        "../../include",
        "../../../../3rdParty/eigen-eigen-323c052e1731",
    ]
    libraryPaths = []
    libraries = ["ParameterEstimation.lib"]
"""


def check_validation():
    parsed_toml = toml.loads(TargetFile)
    target_schema(parsed_toml)


if __name__ == '__main__':
    check_validation()
