import json
import os
import re
import subprocess
from typing import Any, Dict, List


async def clone_repository(repo_url: str, target_dir: str) -> str:
    """Clone a GitHub repository and return its path if successful."""
    repo_name = repo_url.split("/")[-1]
    clone_path = os.path.join(target_dir, repo_name)

    try:
        subprocess.run(["git", "clone", repo_url, clone_path],
                     capture_output=True, text=True, check=False)

        if os.path.exists(clone_path):
            return clone_path
    except Exception as e:
        print(f"Error cloning repository {repo_url}: {e}")

    return ""

def find_python_packages(repo_path: str) -> List[str]:
    """Recursively find Python packages in the repository by looking for __init__.py files."""
    python_packages = []

    for root, dirs, files in os.walk(repo_path):
        # Skip hidden directories and common non-source directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'dist', 'build', '.git', 'tests', 'test', 'docs']]

        if '__init__.py' in files:
            # Get relative path from repo root
            rel_path = os.path.relpath(root, repo_path)
            if rel_path != '.':  # Skip root directory
                python_packages.append(rel_path)

                # Check if this is a potential source directory by looking for other .py files
                py_files = [f for f in files if f.endswith('.py') and f != '__init__.py']
                if py_files:
                    # This is likely a source package
                    python_packages[-1] = (python_packages[-1], len(py_files))

    # Sort by number of .py files (descending) to prioritize main source packages
    python_packages = sorted(python_packages, key=lambda x: x[1] if isinstance(x, tuple) else 0, reverse=True)

    # Convert back to just paths
    python_packages = [p[0] if isinstance(p, tuple) else p for p in python_packages]

    return python_packages

def extract_repository_info(repo_path: str) -> Dict[str, Any]:
    """Extract important information from the repository."""
    info = {}

    # Check for package.json
    package_json_path = os.path.join(repo_path, "package.json")
    if os.path.exists(package_json_path):
        with open(package_json_path, "r") as f:
            package_json_content = f.read()
            info["package_json_content"] = package_json_content
            try:
                package_json = json.loads(package_json_content)
                info["dependencies"] = package_json.get("dependencies", {})
                info["devDependencies"] = package_json.get("devDependencies", {})
                info["scripts"] = package_json.get("scripts", {})
            except Exception as e:
                print(f"Error parsing package.json: {e}")

    # Check for README.md
    readme_path = os.path.join(repo_path, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r") as f:
            info["readme_content"] = f.read()

    # Find Python packages
    python_packages = find_python_packages(repo_path)
    if python_packages:
        info["python_packages"] = python_packages

    # Check for requirements.txt or setup.py
    requirements_path = os.path.join(repo_path, "requirements.txt")
    setup_path = os.path.join(repo_path, "setup.py")
    pyproject_path = os.path.join(repo_path, "pyproject.toml")

    if os.path.exists(requirements_path):
        with open(requirements_path, "r") as f:
            info["requirements_content"] = f.read()
            python_dependencies = []
            for line in info["requirements_content"].splitlines():
                if line.strip() and not line.strip().startswith("#"):
                    python_dependencies.append(line.strip())
            info["python_dependencies"] = python_dependencies

    if os.path.exists(pyproject_path):
        with open(pyproject_path, "r") as f:
            info["pyproject_content"] = f.read()

    if os.path.exists(setup_path):
        with open(setup_path, "r") as f:
            info["setup_content"] = f.read()

    # Find dist directories for JS projects
    js_dist_dirs = []
    if os.path.exists(os.path.join(repo_path, "package.json")):
        for dist_dir in ['dist', 'build', 'out', 'public']:
            if os.path.exists(os.path.join(repo_path, dist_dir)):
                js_dist_dirs.append(dist_dir)

    if js_dist_dirs:
        info["js_dist_dirs"] = js_dist_dirs

    # Check for required files based on project type
    if os.path.exists(os.path.join(repo_path, "package.json")):
        info["is_typescript"] = os.path.exists(os.path.join(repo_path, "tsconfig.json"))
        info["is_javascript"] = not info.get("is_typescript", False)
        info["has_pnpm"] = os.path.exists(os.path.join(repo_path, "pnpm-lock.yaml"))
        info["has_npm"] = os.path.exists(os.path.join(repo_path, "package-lock.json"))
        info["has_yarn"] = os.path.exists(os.path.join(repo_path, "yarn.lock"))

        # Check package.json for build command
        if "scripts" in info:
            scripts = info["scripts"]
            has_build_script = "build" in scripts and scripts["build"]
            info["has_build_script"] = has_build_script
            info["build_script"] = scripts.get("build", "")
            info["start_script"] = scripts.get("start", "")
    else:
        info["is_typescript"] = False
        info["is_javascript"] = False
        info["is_python"] = len(python_packages) > 0 or os.path.exists(setup_path) or os.path.exists(requirements_path)

    return info


def slugify(text: str) -> str:
    """
    Convert a string into a URL-friendly slug.

    Args:
        text: The string to convert to a slug

    Returns:
        A URL-friendly slug string
    """
    # Convert to lowercase
    text = text.lower()

    # Replace spaces and underscores with hyphens
    text = re.sub(r'[\s_]+', '-', text)

    # Remove all non-alphanumeric characters except hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)

    # Replace multiple consecutive hyphens with a single hyphen
    text = re.sub(r'-+', '-', text)

    # Remove leading and trailing hyphens
    text = text.strip('-')

    return text