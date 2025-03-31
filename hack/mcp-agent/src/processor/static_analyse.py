import os
import json
import subprocess
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

class StaticAnalysisResult(BaseModel):
    """Results of static analysis."""
    language: Optional[str] = None
    package_name: Optional[str] = None
    package_version: Optional[str] = None
    package_description: Optional[str] = None
    build_command: Optional[str] = None
    start_command: Optional[str] = None
    test_command: Optional[str] = None
    dependencies: Optional[str] = None
    has_readme: bool = False
    readme_snippet: Optional[str] = None
    build_output_dir: Optional[str] = None
    has_setup_py: bool = False
    repo_url: Optional[str] = None
    branch: Optional[str] = None

def extract_repository_info(repo_path: str) -> StaticAnalysisResult:
    """
    Extract key information about a repository using static analysis.
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        StaticAnalysisResult object with extracted information
    """
    info = StaticAnalysisResult()
    
    # Check for package.json (Node.js projects)
    package_json_path = os.path.join(repo_path, "package.json")
    if os.path.exists(package_json_path):
        try:
            with open(package_json_path, 'r') as f:
                package_json = json.loads(f.read())
                info.package_name = package_json.get("name", "")
                info.package_version = package_json.get("version", "")
                info.package_description = package_json.get("description", "")
                info.language = "javascript/typescript"
                
                # Extract scripts
                scripts = package_json.get("scripts", {})
                if scripts:
                    if "build" in scripts:
                        info.build_command = "npm run build"
                    if "start" in scripts:
                        info.start_command = "npm run start"
                    if "test" in scripts:
                        info.test_command = "npm run test"
                
                # Extract dependencies
                deps = package_json.get("dependencies", {})
                if deps:
                    info.dependencies = ", ".join(deps.keys())
        except Exception as e:
            print(f"Error parsing package.json: {e}")
    
    # Check for requirements.txt (Python projects)
    requirements_path = os.path.join(repo_path, "requirements.txt")
    if os.path.exists(requirements_path):
        try:
            with open(requirements_path, 'r') as f:
                requirements = f.read()
                info.language = "python"
                info.dependencies = requirements
        except Exception as e:
            print(f"Error reading requirements.txt: {e}")
       
    # Check for README
    for readme_name in ["README.md", "README", "readme.md", "readme"]:
        readme_path = os.path.join(repo_path, readme_name)
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r') as f:
                    readme = f.read()
                    info.has_readme = True
                    # Extract a brief snippet (first 200 chars)
                    info.readme_snippet = readme[:200] + "..." if len(readme) > 200 else readme
                    break
            except Exception as e:
                print(f"Error reading README: {e}")
    
    # Check for common build artifacts directories
    build_dirs = ["dist", "build", "out", "target"]
    for build_dir in build_dirs:
        if os.path.exists(os.path.join(repo_path, build_dir)):
            info.build_output_dir = build_dir
            break
    
    # Extract git repository info
    try:
        repo_url = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=repo_path, check=True, capture_output=True, text=True, timeout=30
        ).stdout.strip()
        info.repo_url = repo_url
        
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path, check=True, capture_output=True, text=True, timeout=30
        ).stdout.strip()
        info.branch = branch
    except subprocess.SubprocessError as e:
        print(f"Error extracting git info: {e}")
    
    return info

def format_analysis_output(analysis: StaticAnalysisResult) -> str:
    """
    Format the analysis result as a string for agent consumption.
    
    Args:
        analysis: StaticAnalysisResult object
        
    Returns:
        Formatted string with analysis information
    """
    lines = []
    
    if analysis.repo_url:
        lines.append(f"Repository: {analysis.repo_url}")
    if analysis.branch:
        lines.append(f"Branch: {analysis.branch}")
    if analysis.language:
        lines.append(f"Language: {analysis.language}")
    if analysis.package_name:
        lines.append(f"Package Name: {analysis.package_name}")
    if analysis.package_version:
        lines.append(f"Version: {analysis.package_version}")
    if analysis.package_description:
        lines.append(f"Description: {analysis.package_description}")
    if analysis.build_command:
        lines.append(f"Build Command: {analysis.build_command}")
    if analysis.start_command:
        lines.append(f"Start Command: {analysis.start_command}")
    if analysis.dependencies:
        lines.append(f"Dependencies: {analysis.dependencies}")
    if analysis.has_readme:
        lines.append(f"README snippet: {analysis.readme_snippet}")
    if analysis.build_output_dir:
        lines.append(f"Build Output Directory: {analysis.build_output_dir}")
    
    return "\n".join(lines)
