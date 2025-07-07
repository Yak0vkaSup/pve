import os


def get_directory_structure(root_dir):
    """
    Generate the directory structure with file information.
    """
    dir_structure = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        rel_dir = os.path.relpath(dirpath, root_dir)
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = os.path.join(rel_dir, filename)
                dir_structure.append(filepath)
            if filename.endswith('.java'):
                filepath = os.path.join(rel_dir, filename)
                dir_structure.append(filepath)
    return dir_structure


def read_file_content(file_path):
    """
    Read the content of a file.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def save_to_txt(file_path, content):
    """
    Save content to a text file.
    """
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)


def generate_project_summary(root_dir):
    """
    Generate a summary of the project including directory structure and file contents.
    """
    project_summary = []
    project_summary.append("Project Architecture and Code Summary\n")
    project_summary.append("=" * 40 + "\n")

    dir_structure = get_directory_structure(root_dir)
    if not dir_structure:
        return "No Python files found in the specified directory."

    project_summary.append("Directory Structure:\n")
    for filepath in dir_structure:
        project_summary.append(filepath + "\n")

    project_summary.append("\n" + "=" * 40 + "\n")
    project_summary.append("File Contents:\n")

    for filepath in dir_structure:
        abs_path = os.path.join(root_dir, filepath)
        file_content = read_file_content(abs_path)
        project_summary.append(f"File: {filepath}\n")
        project_summary.append("-" * 40 + "\n")
        project_summary.append(file_content + "\n")
        project_summary.append("-" * 40 + "\n")

    return "".join(project_summary)


def main():
    root_dir = input("Enter the root directory of your project: ").strip()

    if not os.path.isdir(root_dir):
        print(f"The directory '{root_dir}' does not exist.")
        return

    output_file = "project_summary.txt"

    print("Generating project summary...")
    project_summary = generate_project_summary(root_dir)

    if project_summary == "No Python files found in the specified directory.":
        print(project_summary)
    else:
        save_to_txt(output_file, project_summary)
        print(f"Project summary saved to {output_file}")


if __name__ == "__main__":
    main()