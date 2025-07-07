#!/usr/bin/env python3

import os
import json


def gather_js_files_in_script_directory():
    """
    Recursively walk the directory where this script is located
    and gather all .js files.

    Returns a dict {relative_file_path: file_content}.
    """
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    js_files_data = {}
    for root, dirs, files in os.walk(script_dir):
        for filename in files:
            if filename.endswith('.js'):
                full_path = os.path.join(root, filename)
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Store with a path relative to the script directory
                relative_path = os.path.relpath(full_path, script_dir)
                js_files_data[relative_path] = content

    return js_files_data


if __name__ == '__main__':
    result = gather_js_files_in_script_directory()

    # Write out to a JSON file named "js_files.json" in the same directory
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "js_files.json")
    with open(output_path, 'w', encoding='utf-8') as out:
        json.dump(result, out, indent=2, ensure_ascii=False)

    print(f"Collected JS files have been saved to: {output_path}")
