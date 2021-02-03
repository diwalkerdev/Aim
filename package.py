from pathlib import Path
import zipfile

DemoFileExtensionsToZip = [".cpp", ".c", ".h", ".hpp", ".toml"]


def zip_dir(path: Path, zip_handle: zipfile.ZipFile):
    for the_file in path.glob("**/*"):
        if the_file.is_file() and the_file.suffix in DemoFileExtensionsToZip:
            zip_handle.write(str(the_file))


if __name__ == '__main__':
    demo_path = Path('./demo')
    assert demo_path.exists(), f"Failed to find {str(demo_path)} directory."

    zip_file = zipfile.ZipFile('demo.zip', 'w', zipfile.ZIP_DEFLATED)
    zip_dir(demo_path, zip_file)
    zip_file.close()
