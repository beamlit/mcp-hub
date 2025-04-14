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
        return "File not found"
    with open(path, "r") as f:
        return f.read()

def list_directory(path: str) -> list[str]:
    """
    Lists the files in a directory.
    Args:
        path: The path to the directory to list.
    Returns:
        A list of the files in the directory.
    """
    if not os.path.exists(path):
        return "Directory not found"
    entries = os.listdir(path)
    if entries:
        return "\n".join(entries)
    else:
        return f"No files found in directory {path}"
