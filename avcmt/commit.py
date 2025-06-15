# File: avcmt/commit.py
import os
import subprocess
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader

from avcmt.ai import generate_with_ai

def get_changed_files():
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    files = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        status, path = line[:2], line[3:]
        path = path.strip()
        if "D" not in status and os.path.exists(path):
            files.append(path)
        elif "??" in status and os.path.exists(path):
            files.append(path)
    return files

def group_files_by_directory(files):
    grouped = defaultdict(list)
    for file_path in files:
        parent_dir = os.path.dirname(file_path) or "root"
        grouped[parent_dir].append(file_path)
    return grouped

def get_diff_for_files(files, staged=True):
    if staged:
        result = subprocess.run(
            ["git", "--no-pager", "diff", "--staged"] + files,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if not result.stdout.strip():
            result = subprocess.run(
                ["git", "--no-pager", "diff"] + files,
                stdout=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        return result.stdout
    else:
        result = subprocess.run(
            ["git", "--no-pager", "diff"] + files,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.stdout

def render_prompt(group_name, diff_text):
    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "prompt_templates")))
    template = env.get_template("commit_message.j2")
    return template.render(group_name=group_name, diff_text=diff_text)
