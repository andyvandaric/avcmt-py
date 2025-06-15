# File: avcmt/__init__.py
from .ai import generate_with_ai
from .commit import (
    get_changed_files,
    get_diff_for_files,
    group_files_by_directory,
    render_prompt,
)
