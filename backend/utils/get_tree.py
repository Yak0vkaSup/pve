#!/usr/bin/env python3
import os
import sys
from pathspec import PathSpec

def load_gitignore(gitignore_path):
    """
    Load and parse .gitignore patterns using pathspec.
    Returns a PathSpec object or None if no .gitignore exists.
    """
    if not os.path.isfile(gitignore_path):
        return None
    with open(gitignore_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    return PathSpec.from_lines("gitwildmatch", lines)

def should_ignore(pathspec, project_root, path):
    """
    Check if a path should be ignored based on .gitignore patterns.
    We supply the path as relative to 'project_root'.
    """
    if not pathspec:
        return False
    relative_path = os.path.relpath(path, project_root)
    return pathspec.match_file(relative_path)

def print_directory_tree(start_path, pathspec=None, project_root=None, prefix=""):
    """
    Recursively prints a directory tree, skipping any items
    that match the .gitignore pattern in 'pathspec',
    and also ignores the .git folder.
    """
    if not os.path.isdir(start_path):
        print(f"Error: '{start_path}' is not a valid directory.")
        return

    entries = sorted(os.listdir(start_path))
    valid_entries = []

    for entry in entries:
        if entry == ".git":
            # Always skip the .git folder
            continue

        entry_path = os.path.join(start_path, entry)

        if should_ignore(pathspec, project_root, entry_path):
            continue

        valid_entries.append(entry)

    # Separate directories and files
    dirs = [e for e in valid_entries if os.path.isdir(os.path.join(start_path, e))]
    files = [e for e in valid_entries if os.path.isfile(os.path.join(start_path, e))]

    total_entries = len(dirs) + len(files)
    count = 0

    for d in dirs:
        count += 1
        connector = "└── " if count == total_entries else "├── "
        print(prefix + connector + d + "/")
        new_prefix = prefix + ("    " if count == total_entries else "│   ")
        print_directory_tree(
            os.path.join(start_path, d),
            pathspec=pathspec,
            project_root=project_root,
            prefix=new_prefix
        )

    for f in files:
        count += 1
        connector = "└── " if count == total_entries else "├── "
        print(prefix + connector + f)

def main():
    if len(sys.argv) > 1:
        root_path = os.path.abspath(sys.argv[1])
    else:
        root_path = os.path.abspath("../..")

    # Attempt to load .gitignore from the top-level directory
    gitignore_path = os.path.join(root_path, ".gitignore")
    pathspec = load_gitignore(gitignore_path)

    print(f"Project structure for: {root_path}")
    if pathspec:
        print("Ignoring patterns from .gitignore...")
    else:
        print("No .gitignore loaded (none found or empty).")

    print_directory_tree(root_path, pathspec=pathspec, project_root=root_path)

if __name__ == "__main__":
    main()
