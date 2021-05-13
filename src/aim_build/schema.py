import pprint
import sys
from pathlib import Path
from typing import Union, List

import cerberus


class UniqueNameChecker:
    def __init__(self):
        self.name_lookup = []

    def check(self, field, value, error):
        if value in self.name_lookup:
            error(
                field,
                f'The build name must be unique. "{value}" has already been used.',
            )
        else:
            self.name_lookup.append(value)


# TODO: DefinesPrefixChecker could be a function.
class DefinesPrefixChecker:
    def check(self, field, defines: List[str], error):
        for value in defines:
            if value.startswith("-D"):
                error(
                    field,
                    f"Unnecessary -D prefix in {field}: {defines}. Aim will add this automatically.",
                )


class RequiresExistChecker:
    def __init__(self, document):
        self.doc = document

    def check(self, field, requires, error):
        builds = self.doc["builds"]
        for value in requires:
            for build in builds:
                if value == build["name"]:
                    break
            else:
                error(field, f"Build name does not exist: {value}")


# TODO: class could be a function.
class AbsProjectDirPathChecker:
    def check(self, field, paths, error):
        paths = [Path(the_path) for the_path in paths]

        for directory in paths:
            if not directory.is_absolute():
                error(field, f"Directory path should be absolute: {str(directory)}")
                break

            # Remember paths can now be directories or specific paths to files.
            if not directory.exists():
                error(field, f"Directory does not exist: {str(directory)}")
                break


class RelProjectDirPathChecker:
    def __init__(self, project_dir):
        self.project_dir = project_dir

    def check(self, field, paths, error):
        paths = [(self.project_dir / the_path) for the_path in paths]

        for directory in paths:
            # Remember paths can now be directories or specific paths to files.
            if not directory.exists():
                error(field, f'Directory does not exist: "{str(directory)}"')
                break


class AimCustomValidator(cerberus.Validator):
    def _check_with_output_naming_convention(self, field, value: Union[str, list]):
        # if you need more context then you can get it using the line below.
        # if self.document["buildRule"] in ["staticLib", "dynamicLib"]:

        # TODO: should we also check that the names are camelCase?
        # TODO: check outputNames are unique to prevent dependency cycle.

        def check_convention(_field, _value):
            the_errors = []
            if _value.startswith("lib"):
                the_error_str = f"Unnecessary 'lib' prefix in {_value}. Aim will add this automatically."
                the_errors.append(the_error_str)

            suffix = Path(_value).suffix
            if suffix:
                the_error_str = (
                    f'Unecessary suffix "{suffix}". Aim will add this automatically.'
                )
                the_errors.append(the_error_str)

            return the_errors

        # Bit of a hack so strings go through the same code path as lists.
        if isinstance(value, str):
            value = [value]

        for item in value:
            errors = check_convention(field, item)

            if errors:
                plural = ""
                if len(errors) > 1:
                    plural = "s"

                error_str = f"Naming convention error{plural}: {item}. " + " ".join(
                    errors
                )
                self._error(field, error_str)


def target_schema(document, project_dir):
    unique_name_checker = UniqueNameChecker()
    requires_exist_checker = RequiresExistChecker(document)
    path_checker = RelProjectDirPathChecker(project_dir)
    abs_path_checker = AbsProjectDirPathChecker()
    defines_checker = DefinesPrefixChecker()

    schema = {
        "compiler": {"required": True, "type": "string"},
        "archiver": {"required": True, "type": "string"},
        "compilerFrontend": {
            "required": True,
            "type": "string",
            "allowed": ["msvc", "gcc", "osx"],
        },
        "flags": {"type": "list", "schema": {"type": "string"}, "empty": False},
        "defines": {
            "type": "list",
            "schema": {"type": "string"},
            "empty": False,
            "check_with": defines_checker.check,
        },
        "projectRoot": {"required": True, "type": "string", "empty": False},
        "builds": {
            "required": True,
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "name": {
                        "required": True,
                        "type": "string",
                        "check_with": unique_name_checker.check,
                    },
                    "buildRule": {
                        "required": True,
                        "type": "string",
                        # "allowed": ["exe", "staticLib", "dynamicLib", "headerOnly", "libraryReference"],
                        "oneof": [
                            {
                                "excludes": "outputName",
                                "allowed": ["headerOnly", "libraryReference"],
                            },
                            {
                                "dependencies": ["outputName"],
                                "allowed": ["exe", "staticLib", "dynamicLib"],
                            },
                        ],
                    },
                    "compiler": {
                        "required": False,
                        "type": "string",
                        "dependencies": {
                            "buildRule": ["exe", "staticLib", "dynamicLib"]
                        },
                    },
                    "defines": {
                        "type": "list",
                        "schema": {"type": "string"},
                        "empty": False,
                        "check_with": defines_checker.check,
                        "dependencies": {
                            "buildRule": ["exe", "staticLib", "dynamicLib"]
                        },
                    },
                    "flags": {
                        "type": "list",
                        "schema": {"type": "string"},
                        "empty": False,
                        "dependencies": {
                            "buildRule": ["exe", "staticLib", "dynamicLib"]
                        },
                    },
                    "requires": {
                        "type": "list",
                        "empty": False,
                        "schema": {"type": "string"},
                        "check_with": requires_exist_checker.check,
                        "dependencies": {
                            "buildRule": ["exe", "staticLib", "dynamicLib"]
                        },
                    },
                    # Required but the requirement is handled by build rule.
                    "outputName": {
                        "type": "string",
                        "empty": False,
                        "check_with": "output_naming_convention",
                    },
                    "srcDirs": {
                        "required": False,
                        "empty": False,
                        "type": "list",
                        "schema": {"type": "string"},
                        "check_with": path_checker.check,
                        "dependencies": {
                            "buildRule": ["exe", "staticLib", "dynamicLib"]
                        },
                    },
                    "includePaths": {
                        "type": "list",
                        "empty": False,
                        "schema": {"type": "string"},
                        "check_with": path_checker.check,
                    },
                    "systemIncludePaths": {
                        "type": "list",
                        "empty": False,
                        "schema": {"type": "string"},
                        "check_with": abs_path_checker.check,
                        "dependencies": {"compilerFrontend": "gcc"},
                    },
                    "localIncludePaths": {
                        "type": "list",
                        "empty": False,
                        "schema": {"type": "string"},
                        "check_with": path_checker.check,
                        "dependencies": {"compilerFrontend": "gcc"},
                    },
                    "libraryPaths": {
                        "type": "list",
                        "empty": False,
                        "schema": {"type": "string"},
                        # you can't check the library dirs as they may not exist if the project not built before.
                        # "check_with": path_checker.check,
                        "dependencies": {
                            "buildRule": ["exe", "dynamicLib", "libraryReference"]
                        },
                    },
                    "libraries": {
                        "type": "list",
                        "empty": False,
                        "schema": {"type": "string"},
                        "check_with": "output_naming_convention",
                        "dependencies": {
                            "buildRule": ["exe", "dynamicLib", "libraryReference"]
                        },
                    },
                },
            },
        },
    }

    validator = AimCustomValidator()
    validator.validate(document, schema)

    pretty = pprint.PrettyPrinter(indent=2, width=100)

    # TODO: Handle schema errors. https://docs.python-cerberus.org/en/stable/errors.html
    if validator.errors:
        for key, value in validator.errors.items():
            if key != "builds":
                print(f'Error for field "{key}"')
                pretty.pprint(f"{value}")
                print()

        builds_errors = validator.errors.get("builds", {})
        if builds_errors:
            assert len(builds_errors) == 1, "Build error list size is greater than 1."
            for key, value in builds_errors[0].items():
                builds = document["builds"]
                the_build = builds[key]
                the_build_name = the_build["name"]

                print(f'Error in build: "{the_build_name}"')
                assert (
                    len(value) == 1
                ), "Length is not 1. Not sure if it can ever be more than."
                pretty.pprint(value[0])
                print()
        sys.exit(-1)
