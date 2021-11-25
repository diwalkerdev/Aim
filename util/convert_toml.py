import json
import sys
from pathlib import Path

import toml


# toml_data = {
#     "a": {
#         "a": "x",
#         "b": ["y"],
#     },
#     "b": ["x"],
#     "c": 5,
# }


def dump_variable(name: str, the_var: dict):
    return f"{name} = {json.dumps(the_var, indent=4)}\n"


def convert_dict(the_dict):
    lines = []
    for k, v in the_dict.items():
        lines.append(dump_variable(k, v))

    return lines


def main():
    cwd = Path().cwd()

    input_file = cwd / sys.argv[1]
    assert input_file.exists()

    output_file = input_file.parent / "target.py"

    with open(str(input_file), "r") as fd:
        data = toml.loads(fd.read())
        py_code = convert_dict(data)

        with open(str(output_file), "w+") as od:
            od.writelines(py_code)


if __name__ == '__main__':
    main()
