<p align="center">
<img src="https://github.com/diwalkerdev/Assets/blob/master/Aim/aim.png" width="300" height="300">
</p>

![GitHub release (latest SemVer including pre-releases)](https://img.shields.io/github/v/release/diwalkerdev/aim?include_prereleases)
![GitHub commits since latest release (by SemVer including pre-releases)](https://img.shields.io/github/commits-since/diwalkerdev/aim/latest/dev?include_prereleases)
![Python package](https://github.com/diwalkerdev/Aim/workflows/Python%20package/badge.svg?branch=dev)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/aim-build)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![PyPI - Downloads](https://img.shields.io/pypi/dm/aim-build)
![GitHub contributors](https://img.shields.io/github/contributors/diwalkerdev/aim)
![GitHub](https://img.shields.io/github/license/diwalkerdev/aim)

# Aim
A command line tool for building C++ projects. 

## Introduction
Aim is an attempt to make building C++ projects from source as simple as possible while encouraging a modular approach 
to software development.

Aim only requires a `target.toml` file which is used to specify the builds of your project. Each build specifies a
component of your project, like a static library, dynamic library, or an executable.


## Getting Started
### Prerequisites
Aim requires the following dependencies:
* [python](https://www.python.org/) - version 3.7 or above.
* [ninja](https://ninja-build.org/)
* [poetry](https://python-poetry.org/) - for development only

### Installation
Aim is a `python` project and is installed using `pip`.

```
pip install --user aim-build
```

### Using

There are 3 main commands:
* `init` - initialises a directory with an empty project structure
* `list --target=path/to/target_toml_dir` - displays the builds for the target
* `build --target=path/to/target_toml_dir <build name>` - executes a build

For more information run:
```
aim <command> --help
```

The easiest way to get started is to use:

`aim init --demo-files`

`aim init` can be used to generate an empty
project structure and the `--demo-files` flags will copy a small test application into the current directory for 
demonstration purposes.

You can then list the available builds of a target by specifying:

`aim list --target=builds/linux-clang++-debug`

And to build:

`aim build --target=builds/linux-clang++-debug <build name>`

<img src="https://github.com/diwalkerdev/Assets/blob/master/Aim/aim-init-demo.gif?raw=true" width="600px">

## Target files
A `target.toml` file describes a project and its build components.

Begin by specifying `projectRoot` which is the path from the target file to your source files. All relative paths 
will be relative to this directory.

The compiler frontend informs Aim how to construct compiler arguments (Note, only the `gcc` frontend is currently supported, but `msvc` will be added soon). Next specify the `compiler`, `archiver`, `flags` and
any `defines`. 
```
projectRoot = "../.."

compilerFrontend="gcc"
compiler = "clang++"
ar = "ar"

flags = [
    "-std=c++17",
    "-O3",
    "-g",
    "-Wall",
]

# defines = [...] # Defines do not need the -D prefix.
```

Next specify your builds. For each build you must specify the `name` and `buildRule`. Valid build rules are `staticLib`,
`dynamicLib`, `exe`, `headerOnly` or `libraryReference`. A build typically looks like:

```
[[builds]]
    name = "calculatorApp"
    buildRule = "exe"
    requires = ["calculatorDynamic"] # A list of dependencies for this build.
    outputName = "CalculatorApp"     # The output name. Aim will manage any prefixes or suffixes required.
    srcDirs = ["src"]                # A list of source directories.
    includePaths = ["include"]       # A list of include paths.
    # The libraryPaths and libraries fields can be used to specify additional
    # libraries and paths to the build. This allows for linking against third
    # party libraries.
    #libraryPaths = []
    #libraries = []
```

Other notes:

* The `requires` field is important as it is how you specify the dependencies for a build. For example, if you create a static library named "myAwesomeLibrary", this can be used in other builds simply by specifying  `requires=["myAwesomeLibrary"]`. 

* A `headerOnly` build does not have an `outputName` or `srcDirs` as it is not built. The `headerOnly` rule is not essential and is mostly for convenience. If you have a header only library, repeating the include paths across several builds can be become repetitive. Instead, create a `headerOnly` build to capture the include paths and use it in other builds by adding the rule to the builds `requires` field. 

* A `libraryReference` does not have `srcDirs` as it is not built. Like the `headerOnly` rule it is mostly for convience to reduce duplication. The primary use case is for capturing the `includePaths`, `libraryPaths` and `libraries` of a third party library that you need to use in a build. A `libraryReference` can then be used by other builds by adding it to a builds `requires` field.


* The fields `compiler`, `flags` and `defines` are normally written at the top of the target file before the builds section. By default, all builds will use these fields i.e. they are global, but they can also be overridden by specifying them again in a build. Note that when these fields are specified specifically for a build, they completely replace the global definition; any `flags` or `defines` that you specify must be written out in full as they will not share any values with the global definition.

## Supporting Multiple Targets
Aim treats any build variation as its own unique build target with its own unique `target.toml`. 

A build target is some combination of _things_ that affects the output binary such as:
 * operating system (Windows, OSX, Gnu Linux)
 * compiler (MSVC, GCC, Clang)
 * build type (Release, Debug, Sanitized)
 * etc. 
 
Each build target and corresponding `target.toml` file must have its own directory ideally named using a unique 
identifier that comprises the 'parts' that make up the build. For example, `builds/linux-clang++-release/target.toml` indicates that the target file describes a project that is a `release` build, uses the `clang++` compiler and is for the `linux` operating system. 

Note: each `target.toml` file must be written out in full for each target that you need to support. There is no way for
target files to share information or to depend on another. While this leads to duplication between target files, it 
makes them very explicit and makes debugging builds much easier.

## Developing Aim

Aim is a Python project and uses the [poetry](https://python-poetry.org/) dependency manager. See [poetry installation](https://python-poetry.org/docs/#installation) for instructions.

Once you have cloned the project, the virtual environment and dependencies can be installed simply by executing:

```
poetry install
```

### Dev Install
Unfortunately, unlike `setuptools`, there is no means to do a 'dev install' using poetry. A dev install uses the
active source files under development, so the application can be tested without being installed each time.

In order to use Aim on the command line, is it recommended creating an alias. The alias needs to:
* adds Aim to `PYTHONPATH` to resolve import/module paths 
* execute the main Aim script using virtualenv's python

Aim provides a `dev-env.bash` and `dev-env.fish` for setting an alias to mimic a 'dev' install. These files must be
sourced.

   
## Known Limitations
* Windows support is still in development but is coming soon.
