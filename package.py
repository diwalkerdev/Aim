from pathlib import Path
import zipfile

DemoFileExtensionsToZip = [".cpp", ".c", ".h", ".hpp", ".py"]

# TODO would be nice if there was a way to shared these variables with common.py and pyproject.toml
DemoDirectory = "./demo"
DemoZipFileName = "aim_build/zipdemo.zip"


def zip_dir(path: Path, zip_handle: zipfile.ZipFile):
    for the_file in path.glob("**/*"):
        if the_file.is_file() and the_file.suffix in DemoFileExtensionsToZip:
            zip_handle.write(str(the_file))


def main():
    demo_path = Path(DemoDirectory)
    assert demo_path.exists(), f"Failed to find {str(demo_path)} directory."

    zip_file = zipfile.ZipFile(DemoZipFileName, "w", zipfile.ZIP_DEFLATED)
    zip_dir(demo_path, zip_file)
    zip_file.close()


if __name__ == '__main__':
    print(f"Running {__file__}")
    main()
