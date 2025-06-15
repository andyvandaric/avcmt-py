import os
import shutil


def main():
    print("Cleaning pycache...")
    for root, dirs, files in os.walk("."):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                shutil.rmtree(os.path.join(root, dir_name))
        for file in files:
            if file.endswith((".pyc", ".pyo")):
                os.remove(os.path.join(root, file))
