import os


def read_file(path: str) -> str:
    """
    Reads a file and returns the content.
    Args:
        path: The path to the file to read.
    Returns:
        The content of the file.
    """
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return "File not found"
    with open(path, "r") as f:
        return f.read()

def list_directory(path: str) -> list[str]:
    """
    Lists the files in a directory recursively.
    Args:
        path: The path to the directory to list.
    Returns:
        A list of the files in the directory and its subdirectories.
    """
    if not os.path.exists(path):
        print(f"Directory not found: {path}")
        return "Directory not found"

    result = []
    for root, dirs, files in os.walk(path):
        # Get relative path from the input path
        rel_path = os.path.relpath(root, path)
        if rel_path == ".":
            # Files in the root directory
            for file in files:
                result.append(file)
        else:
            # Files in subdirectories
            for file in files:
                result.append(os.path.join(rel_path, file))
    if result:
        return "\n".join(result)
    else:
        return f"No files found in directory {path}"
