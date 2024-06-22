import os
import sys
import datetime
import subprocess
from pathlib import Path

IGNORE_PATTERNS = [
    '.venv', 'venv', 'output', 'logs', 'snapshot',  # Original ignores
    '__pycache__', '.git', '.idea', '.vscode',  # Additional common ignores
    'node_modules', 'build', 'dist'  # More common ignores
]


def should_ignore(path):
    return any(ignored in path for ignored in IGNORE_PATTERNS)


def get_directory_structure(directory):
    structure = []
    for root, dirs, files in os.walk(directory):
        if should_ignore(root):
            continue
        level = root.replace(directory, '').count(os.sep)
        indent = '  ' * level
        structure.append(f"{indent}{os.path.basename(root)}/")
        for file in files:
            if not should_ignore(os.path.join(root, file)):
                structure.append(f"{indent}  {file}")
    return '\n'.join(structure)


def create_snapshot(output_dir='snapshot'):
    current_date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    parent_folder = os.path.basename(os.getcwd())
    output_file = f"{output_dir}/{parent_folder}_python_files_{current_date}.txt"

    os.makedirs(output_dir, exist_ok=True)

    with open(output_file, 'w') as f:
        f.write("PROJECT_SNAPSHOT_START\n")
        f.write(f"Timestamp: {current_date}\n")
        f.write(f"Parent Folder: {parent_folder}\n\n")

        f.write("PROJECT_METADATA_START\n")
        f.write(f"Python Version: {sys.version}\n")
        f.write(f"Virtual Environment: {os.environ.get('VIRTUAL_ENV', 'None')}\n")

        if os.path.exists('.git'):
            try:
                branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
                commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
                f.write(f"Git Branch: {branch}\n")
                f.write(f"Git Commit: {commit}\n")
            except subprocess.CalledProcessError:
                pass
        f.write("PROJECT_METADATA_END\n\n")

        f.write("DIRECTORY_STRUCTURE_START\n")
        f.write(get_directory_structure('.'))
        f.write("\nDIRECTORY_STRUCTURE_END\n\n")

        if os.path.exists('requirements.txt'):
            f.write("REQUIREMENTS_START\n")
            with open('requirements.txt', 'r') as req:
                f.write(req.read())
            f.write("\nREQUIREMENTS_END\n\n")  # Add a newline before REQUIREMENTS_END

        for root, _, files in os.walk('.'):
            if should_ignore(root):
                continue
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    f.write(f"FILE_START\n")
                    f.write(f"File Name: {file}\n")
                    f.write(f"Path: {file_path}\n")
                    f.write(f"Size: {os.path.getsize(file_path)} bytes\n")
                    f.write(f"Last Modified: {datetime.datetime.fromtimestamp(os.path.getmtime(file_path))}\n")
                    f.write("CONTENT_START\n")
                    with open(file_path, 'r') as py_file:
                        f.write(py_file.read())
                    f.write("\nCONTENT_END\n")
                    f.write("FILE_END\n\n")

        f.write("PROJECT_SNAPSHOT_END\n")

    print(f"Python files snapshot has been saved to {output_file}")
    print(f"Output file size: {os.path.getsize(output_file) / 1024:.2f} KB")


if __name__ == "__main__":
    create_snapshot()