import cerberus
from pathlib import Path
from typing import Union,List


class UniqueNameChecker:
    def __init__(self):
        self.name_lookup = []

    def check(self, field, value, error):
        if value in self.name_lookup:
            error(
                field,
                f"The name field must be unique. The name {value} has already been used.",
            )
        else:
            self.name_lookup.append(value)


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
                error(field, f"{value} does not match any build name. Check spelling.")


class AbsProjectDirPathChecker:
    def check(self, field, paths, error):
        paths = [ Path(the_path).resolve() for the_path in paths]

        for directory in paths:
            # Remember paths can now be directories or specific paths to files.
            if not directory.exists():
                error(field, f"{str(directory)} does not exist.")
                break

class RelProjectDirPathChecker:
    def __init__(self, project_dir):
        self.project_dir = project_dir

    def check(self, field, paths, error):
        paths = [(self.project_dir / the_path).resolve() for the_path in paths]

        for directory in paths:
            # Remember paths can now be directories or specific paths to files.
            if not directory.exists():
                error(field, f"{str(directory)} does not exist.")
                break


class AimCustomValidator(cerberus.Validator):
    def _check_with_output_naming_convention(self, field, value: Union[str, list]):
        # if you need more context then you can get it using the line below.
        # if self.document["buildRule"] in ["staticlib", "dynamiclib"]:

        # TODO: should we also check that the names are camelCase?
        # TODO: check outputNames are unique to prevent dependency cycle.

        def check_convention(_field, _value):
            the_errors = []
            if _value.startswith("lib"):
                the_error_str = "You should not prefix names with 'lib'."
                the_errors.append(the_error_str)

            suffix = Path(_value).suffix
            if suffix:
                the_error_str = f"You should not specify the suffix."
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
        "ar": {"required": True, "type": "string"},
        "compilerFrontend": {
            "required": True,
            "type": "string",
            "allowed": ["msvc", "gcc", "osx"],
        },
        "flags": {"type": "list", "schema": {"type": "string"}, "empty": False},
        "defines": {"type": "list",
                    "schema": {"type": "string"},
                    "empty": False,
                    "check_with": defines_checker.check},
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
                    "compiler": {"required": False, "type": "string"},
                    "defines": {
                        "type": "list",
                        "schema": {"type": "string"},
                        "empty": False,
                        "check_with": defines_checker.check,
                    },
                    "flags": {
                        "type": "list",
                        "schema": {"type": "string"},
                        "empty": False,
                    },
                    "requires": {
                        "type": "list",
                        "empty": False,
                        "schema": {"type": "string"},
                        "check_with": requires_exist_checker.check,
                    },
                    "buildRule": {
                        "required": True,
                        "type": "string",
                        "allowed": ["exe", "staticlib", "dynamiclib"],
                    },
                    "outputName": {
                        "required": True,
                        "type": "string",
                        "check_with": "output_naming_convention",
                    },
                    "srcDirs": {
                        "required": True,
                        "empty": False,
                        "type": "list",
                        "schema": {"type": "string"},
                        "check_with": path_checker.check,
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
                    },
                    "localIncludePaths": {
                        "type": "list",
                        "empty": False,
                        "schema": {"type": "string"},
                        "check_with": path_checker.check,
                    },
                    "libraryPaths": {
                        "type": "list",
                        "empty": False,
                        "schema": {"type": "string"},
                        # you can't check the library dirs as they may not exist if the project not built before.
                        # "check_with": path_checker.check,
                        "dependencies": {"buildRule": ["exe", "dynamiclib"]},
                    },
                    "libraries": {
                        "type": "list",
                        "empty": False,
                        "schema": {"type": "string"},
                        "dependencies": {"buildRule": ["exe", "dynamiclib"]},
                        "check_with": "output_naming_convention",
                    },
                },
            },
        },
    }

    validator = AimCustomValidator()
    validator.validate(document, schema)

    # TODO: Handle schema errors. https://docs.python-cerberus.org/en/stable/errors.html
    if validator.errors:
        raise RuntimeError(validator.errors)
