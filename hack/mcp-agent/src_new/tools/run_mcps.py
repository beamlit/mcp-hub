#!/usr/bin/env python
"""Tool for running tests on MCP servers based on the logic in test-run.sh."""

import os
import subprocess
from typing import Dict, Any, Tuple
from langchain_core.tools import Tool

def _run_command(command: str) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, and stderr."""
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr

def test_server(server_path: str) -> Dict[str, Any]:
    """
    Test a single MCP server according to the logic in test-run.sh.
    
    Args:
        server_path: The path to the server YAML file to test
    
    Returns:
        Dictionary with test results information
    """
    current_dir = os.getcwd()
    os.chdir("/Users/mjoffre/Documents/beamlit/mcp-store")
    print(f"Testing {server_path}")
    result = {
        "server": server_path,
        "success": False,
        "errors": [],
        "logs": [],
    }

    catalog_path = "/".join(server_path.split("/")[0:-1])
    mcp_name = server_path.split("/")[-1].replace(".yaml", "")
    
    # If server_file is an absolute path with .yaml extension, extract just the file name
    if os.path.isabs(server_path) and server_path.endswith(".yaml"):
        # Check if the file exists
        if not os.path.exists(server_path):
            result["errors"].append(f"File not found: {server_path}")
            os.chdir(current_dir)
            return result
    else:
        # Extract file name without extension
        mcp_name = server_path.replace(".yaml", "")
    
    result["logs"].append(f"Testing {mcp_name}")
    
    # Run the server test
    result["logs"].append(f"Testing {mcp_name}")
    test_command = f"go run /Users/mjoffre/Documents/beamlit/mcp-store/main.go test -c {catalog_path} -m {mcp_name} --debug"
    
    exit_code, stdout, stderr = _run_command(test_command)
    os.chdir(current_dir)
    result["logs"].append(stdout)
    
    if exit_code != 0:
        result["errors"].append(f"Error: go run command failed with exit code {exit_code}")
        result["logs"].append(stderr)
        
        # Clean up docker containers and images
        _run_command(f"docker ps -a | grep {mcp_name} | awk '{{print $1}}' | xargs docker stop")
        _run_command(f"docker ps -a | grep {mcp_name} | awk '{{print $1}}' | xargs docker rm")
        _run_command(f"docker image rm docker.io/library/{mcp_name}:latest")
        
        return result
    
    # Run the web-search client test
    os.chdir("/Users/mjoffre/Documents/beamlit/mcp-store/web-search")
    npmx_command = "npx tsx --tsconfig=/Users/mjoffre/Documents/beamlit/mcp-store/web-search/tsconfig.json /Users/mjoffre/Documents/beamlit/mcp-store/web-search/client.ts"
    exit_code, stdout, stderr = _run_command(npmx_command)
    os.chdir(current_dir)
    result["logs"].append(stdout)
    
    if exit_code != 0:
        result["errors"].append(f"Error: npx tsx command failed with exit code {exit_code}")
        result["logs"].append(stderr)
        
        # Clean up docker containers and images
        _run_command(f"docker ps -a | grep {mcp_name} | awk '{{print $1}}' | xargs docker stop")
        _run_command(f"docker image rm docker.io/library/{mcp_name}:latest")
        
        return result
    
    # Clean up docker containers and images
    _run_command(f"docker ps -a | grep {mcp_name} | awk '{{print $1}}' | xargs docker stop")
    
    image_remove_command = f"docker image rm docker.io/library/{mcp_name}:latest"
    exit_code, stdout, stderr = _run_command(image_remove_command)
    
    if exit_code != 0:
        result["logs"].append(f"Warning: Failed to remove docker image for {server_path}")
    
    result["success"] = True
    return result


# Create the LangChain tool
run_mcps = Tool(
    name="run_mcp",
    func=test_server,
    description="""
    Test MCP server and retrieve tool list.
    
    Parameters:
    - server_path: The path to the server YAML file to test
    """,
)
