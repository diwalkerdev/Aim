import toml
import argparse
import sys
import os
from pathlib import Path
import subprocess


def release():
    ret = subprocess.run(["git", "branch", "--show-current"], capture_output=True)
    branch_name = ret.stdout.decode("utf-8")[:-1]
    if branch_name != "dev":
        print(f"Please release from dev branch. Current branch is {branch_name}")
        exit(-1)

    toml_path = Path("pyproject.toml")

    with toml_path.open("r") as toml_file:
        parsed_toml = toml.loads(toml_file.read())

    parser = argparse.ArgumentParser(description="Tool for automating releases.")
    group = parser.add_mutually_exclusive_group()

    group.add_argument("--major", action="store_true")
    group.add_argument("--minor", action="store_true")
    group.add_argument("--micro", action="store_true")

    args = parser.parse_args()

    version = parsed_toml["tool"]["poetry"]["version"]
    version = version.split(".")
    version = tuple(int(part) for part in version)

    if args.major:
        new_version_tuple = version[0] + 1, 0, 0
    elif args.minor:
        new_version_tuple = version[0], version[1] + 1, 0
    elif args.micro:
        new_version_tuple = version[0], version[1], version[2] + 1
    else:
        parser.print_help(sys.stdout)
        return

    new_version_string = [str(part) for part in new_version_tuple]
    new_version_string = ".".join(new_version_string)

    version_path = Path("aim_build/version.py")
    version_info = [
        f'__version__ = "{new_version_string}"',
        f"__version_info__ = ({new_version_tuple[0]}, {new_version_tuple[1]}, {new_version_tuple[2]})",
    ]

    subprocess.run(["poetry", "version", new_version_string])

    with version_path.open("w") as version_file:
        for line in version_info:
            version_file.write(line + os.linesep)

    commands = [
        ["git", "add", "."],
        ["git", "commit", "-m", f"Releasing version {new_version_string}"],
        ["rm", "-rf", "dist"],
        ["poetry", "build"],
        # ["poetry", "publish"],
        # fmt: off
        ["git", "tag", "-a", f"v{new_version_string}", "-m", f"Release: version {new_version_string}"],
        # fmt: on
        ["git", "push"],
        ["git", "push", "origin", f"v{new_version_string}"],
    ]

    for command in commands:
        print(f'{" ".join(command)}')
        ret = subprocess.run(command, capture_output=True)
        assert ret.returncode == 0, f"The command {command} failed."

    print("Please run poetry publish manually. Requires authentication.")
    print('    poetry publish --username "" --password ""')


if __name__ == "__main__":
    release()
