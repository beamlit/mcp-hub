import asyncio
import os
import tempfile
import shutil
import yaml
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel

from src.agents.metadata_agent import create_metadata_agent
from src.agents.source_agent import create_source_agent
from src.agents.build_agent import create_build_agent
from src.agents.config_agent import create_config_agent
from src.agents.entrypoint_agent import create_entrypoint_agent
from src.agents.env_agent import create_env_agent
from src.agents.assembler_agent import create_assembler_agent
from src.agents.validator import run_mcp_validation

from .static_analyse import extract_repository_info, format_analysis_output
from src.processor.utils import extract_yaml_from_response, post_process_yaml

class Server(BaseModel):
    """Server information."""
    name: str
    tools: Optional[List[Dict[str, Any]]] = None
    repository: Optional[Dict[str, Any]] = None

async def workflow_main(
    servers: List[Server],
    output: str,
) -> str:
    """
    Main workflow entry point for processing MCP servers.
    
    Args:
        server: List of Server objects
        output: Output directory path
        
    Returns:
        Summary of processing results
    """
    
    # Process each server
    results = []
    for server in servers:
        try:
            print(f"Processing {server.name}")
            # Extracting URL properly from repository object
            repo_url = server.repository.url if hasattr(server.repository, "url") else ""
            safe_name, yaml_content = await process_mcp_server(server, repo_url)
            
            if yaml_content:
                # Save the YAML file
                output_file = os.path.join(output, f"{safe_name}.yaml")
                with open(output_file, "w") as f:
                    f.write(yaml_content)
                print(f"Generated <mcp>.yaml for {server.name} in {output_file}")
                results.append(f"Successfully processed {server.name}")
            else:
                print(f"Failed to generate <mcp>.yaml for {server.name}")
                results.append(f"Failed to process {server.name}")
        except Exception as e:
            print(f"Error processing {server.name}: {e}")
            results.append(f"Error processing {server.name}: {e}")
    
    # Generate summary
    summary = f"Processed {len(servers)} MCP servers.\n"
    summary += f"Successful: {len([r for r in results if r.startswith('Successfully')])}\n"
    summary += f"Failed: {len([r for r in results if r.startswith('Failed') or r.startswith('Error')])}\n"
    
    return summary

async def process_mcp_server(
    server: Server,
    repo_url: str,
) -> Tuple[str, str]:
    """
    Process a single MCP server to generate a <mcp>.yaml file.
    
    Args:
        server: Server object containing metadata
        repo_url: URL of the repository to clone and analyze
        
    Returns:
        Tuple of (safe_name, yaml_content)
        
    Note:
        This function internally clones the repository to a temporary directory,
        analyzes it, and passes the repo_path to various agents for thorough analysis.
    """
    # Create a safe name for the file
    safe_name = server.name.lower().replace(" ", "-")
    
    # Create temporary directory for cloning
    temp_dir = tempfile.mkdtemp()
    try:
        # Clone repository
        try:
            print(f"Cloning repository: {repo_url}")
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, temp_dir], 
                check=True, capture_output=True, timeout=60
            )
            print(f"Repository cloned successfully: {repo_url}")
            # Get the branch from the repository
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=temp_dir, capture_output=True, text=True, timeout=30
            ).stdout.strip()
            print(f"Repository branch: {branch}")
            # Store the branch information safely based on repository type
            # Instead of server.repository["branch"] = branch which assumes repository is a dict
            if hasattr(server.repository, "__setattr__"):
                # If it's a Pydantic model or similar object that supports attribute setting
                setattr(server.repository, "branch", branch)
            else:
                # In case it's still a dictionary in some contexts
                print(f"Repository branch {branch} detected but could not be stored in the server object")
        except subprocess.SubprocessError as e:
            print(f"Repository cloning failed completely: {e}")
            return safe_name, ""
        
        # Extract repository info if not provided
        repo_info = extract_repository_info(temp_dir)
        analysis_output = format_analysis_output(repo_info)
        
        # Use multi-agent processing to generate MCP YAML
        yaml_content, _ = await multi_agent_layer(server, repo_url, branch, analysis_output, temp_dir)
        
        # Validate the YAML and fix issues
        validated_yaml = await validate_mcp_server(yaml_content, temp_dir)
        
        return safe_name, validated_yaml
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Failed to clean up temporary directory: {e}")

async def multi_agent_layer(
    server: Server,
    repo_url: str,
    branch: str,
    analysis_output: str,
    repo_path: str = "",
) -> Tuple[str, str]:
    """
    Coordinate multiple agents to generate parts of the MCP YAML.
    
    Args:
        server: Server object containing metadata
        repo_url: URL of the repository
        branch: Branch of the repository
        analysis_output: Static analysis output as string
        repo_path: Path to the cloned repository for direct file analysis
        
    Returns:
        Tuple of (YAML content, tools_output)
    """
    # Helper function to extract YAML regardless of response format
    def extract_agent_output(response):
        """Extracts useful output from an agent response regardless of format."""
        if isinstance(response, dict):
            # Handle {'output': '```yaml...'} format
            if 'output' in response and isinstance(response['output'], str):
                if '```yaml' in response['output']:
                    return extract_yaml_from_response(response['output'])
                return response['output']
            # Return the whole dict if no specific handling is needed
            return response
        elif isinstance(response, str):
            # Handle string with YAML code block
            if '```yaml' in response:
                return extract_yaml_from_response(response)
            return response
        # Default case
        return response
    
    # Create all agents upfront
    metadata_agent = create_metadata_agent()
    source_agent = create_source_agent()
    build_agent = create_build_agent()
    config_agent = create_config_agent()
    entrypoint_agent = create_entrypoint_agent()
    env_agent = create_env_agent()
    
    # Extract tools if repo_path is provided
    tools_output = ""
    known_tools = []
    
    # Initialize results dictionary
    results = {}
    
    if hasattr(server, 'tools') and server.tools:
        known_tools = [t.name for t in server.tools if hasattr(t, 'name')]
        print(f"Known tools from server metadata: {', '.join(known_tools)}")
        results["tools"] = known_tools
    
    # Start independent section generation in parallel
    print("Generating MCP YAML sections in parallel...")
    tasks = {
        "metadata": metadata_agent.ainvoke({
            "name": server.name,
            "repository_url": repo_url,
            "branch": branch,
            "analysis": analysis_output
        }),
        "source": source_agent.ainvoke({
            "repository_url": repo_url,
            "repo_path": repo_path,
            "branch": branch, 
            "analysis": analysis_output
        }),
        "build": build_agent.ainvoke({
            "repository_url": repo_url,
            "repo_path": repo_path,
            "analysis": analysis_output
        }),
        "config": config_agent.ainvoke({
            "repository_url": repo_url,
            "repo_path": repo_path,
            "analysis": analysis_output
        })
    }
    
    # Wait for all independent sections to complete
    for section_name, task in tasks.items():
        try:
            response = await asyncio.wait_for(task, timeout=120)
            results[section_name] = extract_agent_output(response)
            print(f"Generated {section_name} section successfully.")
        except (asyncio.TimeoutError, Exception) as e:
            print(f"Error or timeout generating {section_name} section: {e}")
            results[section_name] = ""
    
    # Generate dependent sections sequentially
    print("Generating dependent sections...")
    try:
        response = await asyncio.wait_for(
            entrypoint_agent.ainvoke({
                "repo_path": repo_path,
                "analysis": analysis_output,
                "config_section": results.get("config", "")
            }), 
            timeout=60
        )
        results["entrypoint"] = extract_agent_output(response)
        print("Generated entrypoint section successfully.")
    except (asyncio.TimeoutError, Exception) as e:
        print(f"Error generating entrypoint section: {e}")
        results["entrypoint"] = ""
    
    try:
        response = await asyncio.wait_for(
            env_agent.ainvoke({
                "repo_path": repo_path,
                "analysis": analysis_output,
                "config_section": results.get("config", ""),
                "entrypoint_section": results.get("entrypoint", "")
            }),
            timeout=60
        )
        results["env"] = extract_agent_output(response)
        print("Generated env section successfully.")
    except (asyncio.TimeoutError, Exception) as e:
        print(f"Error generating env section: {e}")
        results["env"] = ""
    
    # Assemble final YAML
    mcp_yaml = await assemble_mcp_server(
        results.get("metadata", ""),
        results.get("source", ""),
        results.get("build", ""),
        results.get("config", ""),
        results.get("entrypoint", ""),
        results.get("env", ""),
        results.get("tools", [])
    )
    
    return mcp_yaml, tools_output

async def assemble_mcp_server(
    metadata: str,
    source: str,
    build: str,
    config: str,
    entrypoint: str = "",
    env: str = "",
    tools: list = None,
) -> str:
    """
    Assemble the MCP YAML file from the individual sections.
    
    Args:
        metadata: Metadata section
        source: Source section
        build: Build section
        config: Config section
        entrypoint: Entrypoint section (optional)
        env: Env section (optional)
        tools: Tools section (optional) - can be a list or string
        
    Returns:
        Assembled YAML content
    """
    print("Assembling final YAML...")
    assembler_agent = create_assembler_agent()
    
    # Ensure tools is properly formatted
    if tools is None:
        tools = []
    
    # Convert tools to string if it's a list
    tools_section = ""
    if isinstance(tools, list):
        if tools:
            tools_section = "tools:\n  - " + "\n  - ".join(tools)
        else:
            tools_section = "tools: []"
    
    try:
        mcp_yaml = await asyncio.wait_for(
            assembler_agent.ainvoke({
                "metadata_section": metadata,
                "tools_section": tools_section,
                "source_section": source,
                "build_section": build,
                "config_section": config,
                "entrypoint_section": entrypoint,
                "env_section": env
            }),
            timeout=60
        )
        
        # Extract YAML content from the response
        mcp_yaml = extract_yaml_from_response(mcp_yaml)
        if not mcp_yaml.strip():
            print("Generated MCP YAML is empty.")
            return ""
        
        print("MCP YAML assembly complete.")
        return post_process_yaml(mcp_yaml)
    except (asyncio.TimeoutError, Exception) as e:
        print(f"Error during YAML assembly: {e}")
        return ""

async def validate_mcp_server(
    mcp_yaml: str,
    repo_path: str
) -> str:
    """
    Validate and fix issues in the MCP YAML.
    
    Args:
        mcp_yaml: Generated YAML content
        repository_url: URL of the repository
        branch: Branch of the repository
        analysis_output: Static analysis output
        tools_definition: Extracted tools definition
        
    Returns:
        str: Validated and corrected YAML content
    """
    print("Validating MCP YAML...")

    return run_mcp_validation(mcp_yaml, repo_path)