from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_community.tools.file_management import ReadFileTool, ListDirectoryTool
import os
import subprocess
from typing import Dict, Any

def extract_source_info(repo_path: str) -> Dict[str, Any]:
    """Extract source information from a repository."""
    source_info = {
        "repo": None,
        "branch": None,
        "path": "."  # Default to root path
    }
    
    # Try to get repository information using git
    try:
        # Get remote URL
        remote_url = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            timeout=30
        ).stdout.strip()
        
        # Format the URL to remove any authentication info
        if remote_url:
            # Convert SSH urls to HTTPS
            if remote_url.startswith("git@"):
                parts = remote_url.split(":")
                if len(parts) > 1:
                    domain = parts[0].replace("git@", "")
                    repo_path = parts[1]
                    if repo_path.endswith(".git"):
                        repo_path = repo_path[:-4]
                    remote_url = f"https://{domain}/{repo_path}"
            
            # Remove .git suffix if present
            if remote_url.endswith(".git"):
                remote_url = remote_url[:-4]
                
            source_info["repo"] = remote_url
        
        # Get current branch
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            timeout=30
        ).stdout.strip()
        
        if branch:
            source_info["branch"] = branch
            
        # Check if the code is in a subdirectory
        # This is a heuristic - look for key files that might indicate the main code path
        project_indicators = [
            "package.json",
            "setup.py",
            "requirements.txt",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
            "Gemfile"
        ]
        
        # First check if any of these files exist in the root
        root_has_indicator = any(os.path.exists(os.path.join(repo_path, indicator)) 
                              for indicator in project_indicators)
        
        # If not, try to find them in subdirectories
        if not root_has_indicator:
            for root, dirs, files in os.walk(repo_path):
                rel_path = os.path.relpath(root, repo_path)
                if rel_path == ".":
                    continue
                    
                # Skip hidden directories and common non-code directories
                if any(part.startswith(".") for part in rel_path.split(os.sep)) or \
                   any(excluded in rel_path.split(os.sep) for excluded in ["node_modules", "venv", "dist", "build"]):
                    continue
                
                if any(indicator in files for indicator in project_indicators):
                    source_info["path"] = rel_path
                    break
            
    except subprocess.SubprocessError as e:
        print(f"Error extracting git information: {e}")
        
    return source_info

def create_source_agent():
    """Create an agent to generate the source section of the MCP YAML file."""
    tools = [
        Tool(
            name="ReadFile",
            description="Read a file from the repository to analyze its content.",
            func=ReadFileTool().run
        ),
        Tool(
            name="ListDirectory",
            description="List contents of a repository directory to discover important files with tool definitions.",
            func=ListDirectoryTool().run
        ),
        Tool(
            name="ExtractSourceInfo",
            description="Extract source information from the repository.",
            func=lambda repo_path: extract_source_info(repo_path)
        )
    ]
    
    system_message = """You are an expert at defining source information for MCP modules.
    Your task is to generate a properly formatted source section for an MCP YAML file.
    
    Focus ONLY on the source section which must include:
    - repo: URL to the source code repository
    - branch: Branch to use (typically main or master)
    - path: Path to the module code within the repository. Should be relative to the root of the repository e.g. src/mypkg or .
    
    Ensure all fields are properly formatted and accurate based on the provided repository information.
    Use the tools provided to extract detailed source information directly from the repository.
    """
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "Generate the source section for an MCP module based on this information:\n\n"
                "Repository URL: {repository_url}\n"
                "Repository Path: {repo_path}\n"
                "Branch: {branch}\n"
                "Analysis:\n{analysis}\n\n"
                "Please generate ONLY the source section of the YAML file with proper formatting."),
        ("placeholder", "{agent_scratchpad}")
    ])
    
    agent = create_openai_functions_agent(llm, tools, prompt)
    
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=15
    ) 