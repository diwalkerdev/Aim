import os

projectRoot = "../.."

compilerFrontend = "gcc"
compiler = "avr-gcc"
archiver = "avr-gcc-ar"


# Custom variables must begin with '_' so they are ignored by the schema.
_sflags = [
    "-c -g -x assembler-with-cpp -flto -MMD -mmcu=atmega328p -DF_CPU=16000000L -DARDUINO=10815 -DARDUINO_AVR_UNO -DARDUINO_ARCH_AVR"
]

_cflags = [
    "-c -g -Os -w -std=gnu11 -ffunction-sections -fdata-sections -MMD -flto -fno-fat-lto-objects -mmcu=atmega328p -DF_CPU=16000000L -DARDUINO=10815 -DARDUINO_AVR_UNO -DARDUINO_ARCH_AVR"
]

_cxxflags = [
    "-c -g -Os -w -std=gnu++11 -fpermissive -fno-exceptions -ffunction-sections -fdata-sections -fno-threadsafe-statics -Wno-error=narrowing -MMD -flto -mmcu=atmega328p -DF_CPU=16000000L -DARDUINO=10815 -DARDUINO_AVR_UNO -DARDUINO_ARCH_AVR"
]

# The default install location can be overridden using an environment variable.
_ARD_DIR = os.environ.get("ARDUINO_DIR", "C:/Program Files (x86)/Arduino")

builds = [
    {
        "name": "AVR",
        "buildRule": "libraryReference",
        "includePaths": [f"{_ARD_DIR}/hardware/tools/avr/avr/include"],
        "libraryPaths": [f"{_ARD_DIR}/hardware/tools/avr/avr/lib"],
    },
    {

        "name": "Pins",
        "buildRule": "headerOnly",
        "includePaths": [f"{_ARD_DIR}/hardware/arduino/avr/variants/standard"],
    },
    {
        "name": "CoreS",
        "requires": ["AVR", "Pins"],
        "buildRule": "staticLibrary",
        "outputName": "cores",
        "sourceFiles": [f"{_ARD_DIR}/hardware/arduino/avr/cores/arduino/*.S"],
        "flags": _sflags,
    },
    {
        "name": "CoreC",
        "requires": ["AVR", "Pins"],
        "buildRule": "staticLibrary",
        "outputName": "corec",
        "sourceFiles": [f"{_ARD_DIR}/hardware/arduino/avr/cores/arduino/*.c"],
        "includePaths": [f"{_ARD_DIR}/hardware/arduino/avr/cores/arduino"],
        "flags": _cflags,
    },
    {
        "name": "Core",
        "requires": ["AVR", "Pins"],
        "buildRule": "staticLibrary",
        "outputName": "core",
        "sourceFiles": [f"{_ARD_DIR}/hardware/arduino/avr/cores/arduino/*.cpp"],
        "includePaths": [f"{_ARD_DIR}/hardware/arduino/avr/cores/arduino"],
        "compiler": "avr-g++",
        "flags": _cxxflags,
    },
    {
        "name": "ArduinoLib",
        "requires": ["Wire", "WireC", "Core", "CoreC", "CoreS", "Pins", "AVR"],
        "buildRule": "staticLibrary",
        "sourceFiles": ["lib/Lib/*.cpp"],
        "includePaths": ["lib"],
        "outputName": "arduinolib",
        "compiler": "avr-g++",
        "flags": _cxxflags,

        # "linker" : "avr-gcc"
        # "linker_flags" : ["-w -Os -g -flto -fuse-"linker"-plugin -Wl,--gc-sections -mmcu=atmega328p"]
        # "libraries" : ["m"]
    },

    {
        "name": "WireC",
        "requires": ["AVR", "Pins", "CoreS", "CoreC", "Core"],
        "buildRule": "staticLibrary",
        "outputName": "wirec",
        "compiler": "avr-gcc",
        "flags": _cflags,
        "sourceFiles": [f"{_ARD_DIR}/hardware/arduino/avr/libraries/Wire/src/utility/*.c"],
        "includePaths": [f"{_ARD_DIR}/hardware/arduino/avr/libraries/Wire/src/utility"],
    },
    {
        "name": "Wire",
        "requires": ["AVR", "Pins", "CoreS", "CoreC", "Core", "WireC"],
        "buildRule": "staticLibrary",
        "outputName": "wire",
        "compiler": "avr-g++",
        "flags": _cxxflags,
        "sourceFiles": [f"{_ARD_DIR}/hardware/arduino/avr/libraries/Wire/src/*.cpp", ],
        "includePaths": [f"{_ARD_DIR}/hardware/arduino/avr/libraries/Wire/src", ],
    },

    # The application.
    # Note, aim only generates the elf file. To program the arduino, you need to look at the final steps from the
    # arduino IDE.
    {
        "name": "Blink",
        "requires": ["ArduinoLib", "Wire", "WireC", "Core", "CoreC", "CoreS", "Pins", "AVR"],
        "buildRule": "executable",
        "sourceFiles": ["src/blink.cpp"],
        "includePaths": ["src"],
        # Link script requires elf to have same name as the project.
        "outputName": "Blink.elf",
        "compiler": "avr-g++",
        "flags": _cxxflags,
        "linker": "avr-gcc",
        "linker_flags": ["-w -Os -g -flto -fuse-linker-plugin -Wl,--gc-sections -mmcu=atmega328p"],
        "libraries": ["m"],
    },
    # Other libraries that are built by the Arduino build system by default,
    # but are not needed for simple projects.
    # {
    #     "name" : "EEPROM"
    #     "buildRule" : "headerOnly"
    #     "includePaths" : [f"{_ARD_DIR}/hardware/arduino/avr/libraries/EEPROM/src"]
    # },{
    #     "name" : "HID"
    #     "requires" : ["Pins"]
    #     "buildRule" : "staticLib"
    #     "outputName" : "hid"
    #     "sourceFiles" : [f"{_ARD_DIR}/hardware/arduino/avr/libraries/HID/src"]
    #     "includePaths" : [f"{_ARD_DIR}/hardware/arduino/avr/libraries/HID/src"]
    # },{
    #     "name" : "SoftwareSerial"
    #     "requires" : ["Pins"]
    #     "buildRule" : "staticLib"
    #     "outputName" : "softwareserial"
    #     "sourceFiles" : [f"{_ARD_DIR}/hardware/arduino/avr/libraries/SoftwareSerial/src"]
    #     "includePaths" : [f"{_ARD_DIR}/hardware/arduino/avr/libraries/SoftwareSerial/src"]
    # },{
    #     "name" : "SPI"
    #     "requires" : ["Pins"]
    #     "buildRule" : "staticLib"
    #     "outputName" : "spi"
    #     "sourceFiles" : [f"{_ARD_DIR}/hardware/arduino/avr/libraries/SPI/src"]
    #     "includePaths" : [f"{_ARD_DIR}/hardware/arduino/avr/libraries/SPI/src"]
    # }
]
