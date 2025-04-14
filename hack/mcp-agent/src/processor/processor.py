import os
import shutil
import subprocess
import tempfile
from typing import Annotated, Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from typing_extensions import Annotated

# Updated imports for our new agent architecture
from src.agents import (create_build_agent, create_metadata_agent,
                        create_run_agent, create_source_agent,
                        run_mcp_validation)
from src.processor.utils import extract_yaml_from_response

from .static_analyse import extract_repository_info, format_analysis_output


def merge_errors(errors_list: List[List[str]]) -> List[str]:
    """Merge multiple error lists into a single list."""
    result = []
    for errors in errors_list:
        if errors:  # Check if errors is not None
            result.extend(errors)
    return result

class MCPState(BaseModel):
    """State for MCP workflow."""
    server: Any  # Server object
    repo_url: str
    branch: str
    repo_path: str
    analysis_output: str
    metadata: Optional[str] = None
    source: Optional[str] = None
    build: Optional[str] = None
    run: Optional[str] = None
    config: Optional[str] = None
    entrypoint: Optional[str] = None
    env: Optional[str] = None
    final_yaml: Optional[str] = None
    errors: List[str] = Field(default_factory=list, annotation=Annotated[List[str], Field(merge_strategy=merge_errors)])
    shared_memory: Dict[str, Any] = Field(default_factory=dict)

class Server(BaseModel):
    """Server information."""
    name: str
    tools: Optional[List[Dict[str, Any]]] = None
    repository: Optional[Dict[str, Any]] = None

def update_memory(state: MCPState, key: str, value: Any) -> None:
    """Update shared memory with new value."""
    state.shared_memory[key] = value

def get_memory(state: MCPState, key: str) -> Any:
    """Get value from shared memory."""
    return state.shared_memory.get(key)

async def metadata_node(state: MCPState) -> Dict:
    """Node for generating metadata section."""
    try:
        print("Creating metadata agent...")
        metadata_agent = create_metadata_agent()

        # Make sure the agent is initialized
        if not hasattr(metadata_agent, 'chain') or metadata_agent.chain is None:
            print("Initializing metadata agent explicitly...")
            metadata_agent.initialize_agent()

        print(f"Invoking metadata agent with server name: {state.server.name}, repo_url: {state.repo_url}")

        # Invoke the agent
        response = await metadata_agent.ainvoke({
            "name": state.server.name,
            "repository_url": state.repo_url,
            "branch": state.branch,
            "analysis": state.analysis_output
        })

        # Debug the response
        print(f"Metadata agent response type: {type(response)}")
        print(response)
        print(f"Metadata agent response preview: {str(response)[:200]}..." if len(str(response)) > 200 else response)

        # Extract YAML from the response
        yaml_content = ""
        if isinstance(response, dict):
            # Convert directly to YAML
            import yaml
            yaml_content = yaml.dump(response, default_flow_style=False, Dumper=yaml.SafeDumper)
        else:
            # Extract from text response
            yaml_content = extract_yaml_from_response(response)

            # Validate and ensure it's proper YAML
            try:
                import yaml
                parsed = yaml.safe_load(yaml_content)
                if parsed:
                    # Re-dump with SafeDumper to avoid Python object tags
                    yaml_content = yaml.dump(parsed, default_flow_style=False, Dumper=yaml.SafeDumper)
            except Exception as yaml_error:
                print(f"Error validating metadata YAML: {yaml_error}")

        print(f"Extracted metadata YAML length: {len(yaml_content)}")

        # Store the metadata in the state
        update_memory(state, "metadata_yaml", yaml_content)
        state.metadata = yaml_content  # Also update state directly

        print("Metadata node completed successfully")
        return {"metadata_yaml": yaml_content}  # Return with consistent key
    except Exception as e:
        error_msg = f"Metadata generation failed: {str(e)}"
        print(f"ERROR in metadata_node: {error_msg}")
        print(f"Exception details: {type(e).__name__}")
        import traceback
        traceback.print_exc()

        update_memory(state, "metadata_error", error_msg)
        state.errors.append(error_msg)  # Add to state errors
        return {"errors": [error_msg]}

async def source_node(state: MCPState) -> Dict:
    """Node for generating source section."""
    try:
        print("Creating source agent...")
        source_agent = create_source_agent()

        # Make sure the agent is initialized
        if not hasattr(source_agent, 'chain') or source_agent.chain is None:
            print("Initializing source agent explicitly...")
            source_agent.initialize_agent()

        print(f"Invoking source agent with repo_url: {state.repo_url}, branch: {state.branch}")

        # Ensure repo_url is not empty
        if not state.repo_url:
            error_msg = "Repository URL is empty or not provided"
            print(f"ERROR in source_node: {error_msg}")
            state.errors.append(error_msg)
            return {"errors": [error_msg]}

        # Get repo information and convert to dictionary if it's a Pydantic object
        repo_info = None
        if hasattr(state.server, 'repository') and state.server.repository:
            if hasattr(state.server.repository, 'model_dump'):
                # Pydantic v2
                repo_info = state.server.repository.model_dump()
            elif hasattr(state.server.repository, 'dict'):
                # Pydantic v1
                repo_info = state.server.repository.dict()
            else:
                # Manual conversion
                repo_info = {
                    "url": getattr(state.server.repository, "url", state.repo_url),
                    "branch": getattr(state.server.repository, "branch", state.branch)
                }

        # Invoke the agent
        response = await source_agent.ainvoke({
            "repository_url": state.repo_url,
            "repo_path": state.repo_path,
            "branch": state.branch,
            "analysis": state.analysis_output
        })

        # Debug the response
        print(f"Source agent response type: {type(response)}")
        print(f"Source agent response preview: {str(response)[:200]}..." if len(str(response)) > 200 else response)

        # Handle different response formats and ensure source structure matches Go struct
        source_yaml = ""
        if isinstance(response, dict):
            # Extract the source section
            if "source" in response:
                import yaml
                source_data = response["source"]

                # Convert from dict to proper format if needed
                if isinstance(source_data, dict):
                    # Check for nested git structure and flatten it
                    if "git" in source_data and isinstance(source_data["git"], dict):
                        git_info = source_data["git"]
                        source_data = {
                            "repo": git_info.get("repository", state.repo_url),
                            "branch": git_info.get("branch", state.branch),
                            "path": git_info.get("path", ".")
                        }
                        response["source"] = source_data

                    # Ensure required fields exist with correct names
                    if "repo" not in source_data:
                        source_data["repo"] = state.repo_url
                    if "repository" in source_data and not source_data.get("repo"):
                        source_data["repo"] = source_data.pop("repository")
                    if "branch" not in source_data:
                        source_data["branch"] = state.branch
                    if "path" not in source_data:
                        source_data["path"] = "."

                    # Remove any fields that don't belong in the Go struct
                    for key in list(source_data.keys()):
                        if key not in ["repo", "branch", "path", "localPath"]:
                            del source_data[key]

                source_yaml = yaml.dump(response, default_flow_style=False, Dumper=yaml.SafeDumper)
            else:
                # Create a proper source section matching Go struct
                import yaml
                source_section = {
                    "source": {
                        "repo": state.repo_url,
                        "branch": state.branch,
                        "path": "."
                    }
                }
                source_yaml = yaml.dump(source_section, default_flow_style=False, Dumper=yaml.SafeDumper)
        else:
            # Extract YAML from the response
            source_yaml = extract_yaml_from_response(response)

            # Verify and fix the extracted YAML to match Go struct
            try:
                import yaml
                yaml_content = yaml.safe_load(source_yaml)

                if not yaml_content or "source" not in yaml_content:
                    # Create a proper source section
                    source_section = {
                        "source": {
                            "repo": state.repo_url,
                            "branch": state.branch,
                            "path": "."
                        }
                    }
                    source_yaml = yaml.dump(source_section, default_flow_style=False, Dumper=yaml.SafeDumper)
                else:
                    source_data = yaml_content["source"]

                    # Check for nested git structure and flatten it
                    if "git" in source_data and isinstance(source_data["git"], dict):
                        git_info = source_data["git"]
                        source_data = {
                            "repo": git_info.get("repository", state.repo_url),
                            "branch": git_info.get("branch", state.branch),
                            "path": git_info.get("path", ".")
                        }
                        yaml_content["source"] = source_data

                    # Ensure required fields exist with correct names
                    if "repo" not in source_data:
                        source_data["repo"] = state.repo_url
                    if "repository" in source_data and not source_data.get("repo"):
                        source_data["repo"] = source_data.pop("repository")
                    if "branch" not in source_data:
                        source_data["branch"] = state.branch
                    if "path" not in source_data:
                        source_data["path"] = "."

                    # Remove any fields that don't belong in the Go struct
                    for key in list(source_data.keys()):
                        if key not in ["repo", "branch", "path", "localPath"]:
                            del source_data[key]

                    source_yaml = yaml.dump(yaml_content, default_flow_style=False, Dumper=yaml.SafeDumper)
            except Exception as yaml_error:
                print(f"Error processing source YAML: {yaml_error}")
                # Create a fallback source section
                source_section = {
                    "source": {
                        "repo": state.repo_url,
                        "branch": state.branch,
                        "path": "."
                    }
                }
                source_yaml = yaml.dump(source_section, default_flow_style=False, Dumper=yaml.SafeDumper)

        print(f"Extracted source YAML length: {len(source_yaml)}")

        # Store the source in the state
        update_memory(state, "source_yaml", source_yaml)
        state.source = source_yaml  # Also update state directly

        print("Source node completed successfully")
        return {"source_yaml": source_yaml}  # Return with consistent key
    except Exception as e:
        error_msg = f"Source generation failed: {str(e)}"
        print(f"ERROR in source_node: {error_msg}")
        print(f"Exception details: {type(e).__name__}")
        import traceback
        traceback.print_exc()

        update_memory(state, "source_error", error_msg)
        state.errors.append(error_msg)  # Add to state errors
        return {"errors": [error_msg]}

async def build_node(state: MCPState) -> Dict:
    """Node for generating build section."""
    try:
        print("Creating build agent...")
        build_agent = create_build_agent()

        # Make sure the agent is initialized
        if not hasattr(build_agent, 'chain') or build_agent.chain is None:
            print("Initializing build agent explicitly...")
            build_agent.initialize_agent()

        print(f"Invoking build agent with repo_url: {state.repo_url}, repo_path: {state.repo_path}")

        # Invoke the agent
        response = await build_agent.ainvoke({
            "repository_url": state.repo_url,
            "repo_path": state.repo_path,
            "analysis": state.analysis_output
        })

        # Debug the response
        print(f"Build agent response type: {type(response)}")
        print(f"Build agent response preview: {str(response)[:200]}..." if len(str(response)) > 200 else response)

        # Extract YAML from the response
        yaml_content = ""
        if isinstance(response, dict):
            # Convert directly to YAML
            import yaml

            # Extract build section
            build_section = {}
            if "build" in response:
                build_section = response["build"]
            else:
                # If no build section, use the whole response if it looks like a build section
                if "language" in response or "command" in response or "output" in response:
                    build_section = response

            # Wrap in build section if not already
            if "build" not in response:
                response = {"build": build_section}

            yaml_content = yaml.dump(response, default_flow_style=False, Dumper=yaml.SafeDumper)
        else:
            # Extract from text response
            yaml_content = extract_yaml_from_response(response)

            # Validate that it's proper YAML
            try:
                import yaml
                parsed = yaml.safe_load(yaml_content)
                if parsed:
                    # Check if build section exists
                    if "build" not in parsed and isinstance(parsed, dict) and ("language" in parsed or "command" in parsed or "output" in parsed):
                        # Wrap in build section if not already
                        parsed = {"build": parsed}

                    # Re-dump with SafeDumper to avoid Python object tags
                    yaml_content = yaml.dump(parsed, default_flow_style=False, Dumper=yaml.SafeDumper)
            except Exception as yaml_error:
                print(f"Error validating build YAML: {yaml_error}")
                # Return error without fallback - BuildAgent should provide valid YAML
                error_msg = f"Build generation produced invalid YAML: {yaml_error}"
                update_memory(state, "build_error", error_msg)
                state.errors.append(error_msg)
                return {"errors": [error_msg]}

        print(f"Extracted build YAML length: {len(yaml_content)}")

        # Store the build in the state
        update_memory(state, "build_yaml", yaml_content)
        state.build = yaml_content  # Also update state directly

        print("Build node completed successfully")
        return {"build_yaml": yaml_content}  # Return with consistent key
    except Exception as e:
        error_msg = f"Build generation failed: {str(e)}"
        print(f"ERROR in build_node: {error_msg}")
        print(f"Exception details: {type(e).__name__}")
        import traceback
        traceback.print_exc()

        update_memory(state, "build_error", error_msg)
        state.errors.append(error_msg)  # Add to state errors
        return {"errors": [error_msg]}

async def run_node(state: MCPState) -> Dict:
    """Node for generating run section (config, entrypoint, env)."""
    try:
        print("Creating run agent...")
        run_agent = create_run_agent()

        # Make sure the agent is initialized
        if not hasattr(run_agent, 'agent') or run_agent.agent is None:
            print("Initializing run agent explicitly...")
            run_agent.initialize_agent()

        print(f"Invoking run agent with repository_url: {state.repo_url}, repo_path: {state.repo_path}")
        print(f"Analysis excerpt: {state.analysis_output[:100]}...")

        # Get server name for the name_section parameter
        name_section = state.server.name if hasattr(state.server, 'name') else "MCP Server"

        response = await run_agent.ainvoke({
            "repository_url": state.repo_url,
            "repo_path": state.repo_path,
            "analysis": state.analysis_output,
            "name_section": name_section  # Add the missing name_section parameter
        })

        # Debug the response
        print(f"Run agent response type: {type(response)}")
        print(f"Run agent response preview: {str(response)[:200]}..." if len(str(response)) > 200 else response)

        # Extract run section from response
        run_section = {}

        # Handle different response types
        from src.agents.run_agent import RunResponse
        if isinstance(response, RunResponse):
            # Handle RunResponse object correctly
            print("Response is a RunResponse object")

            # Convert the Pydantic model to a dictionary
            if hasattr(response, "model_dump"):
                # Pydantic v2
                run_section = response.model_dump()
            else:
                # Pydantic v1
                run_section = response.dict()

            print(f"Converted RunResponse to dictionary: {run_section}")

            # Ensure all config Properties have the required fields
            if "config" in run_section:
                for key, prop in list(run_section["config"].items()):
                    if not isinstance(prop, dict):
                        continue

                    # Ensure required fields are present
                    if "type" not in prop:
                        prop["type"] = "string"
                    if "required" not in prop:
                        prop["required"] = False

                    # Convert numeric and boolean defaults to strings
                    if "default" in prop and not isinstance(prop["default"], str):
                        prop["default"] = str(prop["default"]).lower()

            # Ensure all env Properties have the required fields
            if "env" in run_section:
                for key, prop in list(run_section["env"].items()):
                    if not isinstance(prop, dict):
                        continue

                    # Ensure required fields are present
                    if "type" not in prop:
                        prop["type"] = "string"
                    if "required" not in prop:
                        prop["required"] = False

                    # Check for secrets based on key name
                    if "secret" not in prop:
                        prop["secret"] = key.upper().endswith("_KEY") or key.upper().endswith("_SECRET") or key.upper().endswith("_TOKEN") or key.upper().endswith("_PASSWORD")

                    # Convert numeric and boolean defaults to strings
                    if "default" in prop and not isinstance(prop["default"], str):
                        prop["default"] = str(prop["default"]).lower()

            # Ensure entrypoint is a list of strings
            if "entrypoint" in run_section and not isinstance(run_section["entrypoint"], list):
                if isinstance(run_section["entrypoint"], str):
                    # Try to split by spaces if it's a string
                    run_section["entrypoint"] = run_section["entrypoint"].split()
                else:
                    run_section["entrypoint"] = ["echo", "Invalid entrypoint format"]

        elif isinstance(response, dict):
            # Direct dictionary response
            print("Response is a dictionary")

            # If it has a "run" key, extract the contents
            if "run" in response:
                run_section = response["run"]
            else:
                run_section = response

        elif isinstance(response, str):
            # Try to parse YAML response
            print("Response is a string, attempting to parse as YAML")
            try:
                import yaml
                run_section = yaml.safe_load(response)
                print(f"Parsed YAML into: {type(run_section)}")

                # If it has a "run" key, extract the contents
                if isinstance(run_section, dict) and "run" in run_section:
                    run_section = run_section["run"]
            except Exception as yaml_error:
                print(f"Failed to parse YAML: {yaml_error}")
                error_msg = f"Failed to parse YAML response: {yaml_error}"
                state.errors.append(error_msg)
                return {"errors": [error_msg]}
        else:
            # Try to extract YAML from any other type of response
            print(f"Response is other type: {type(response)}, converting to string")
            yaml_content = extract_yaml_from_response(response)
            try:
                import yaml
                if yaml_content:
                    run_section = yaml.safe_load(yaml_content)
                    print(f"Parsed extracted YAML into: {type(run_section)}")

                    # If it has a "run" key, extract the contents
                    if isinstance(run_section, dict) and "run" in run_section:
                        run_section = run_section["run"]
                else:
                    print("No YAML could be extracted")
                    error_msg = "No YAML could be extracted from response"
                    state.errors.append(error_msg)
                    return {"errors": [error_msg]}
            except Exception as yaml_error:
                print(f"Failed to parse extracted YAML: {yaml_error}")
                error_msg = f"Failed to parse extracted YAML: {yaml_error}"
                state.errors.append(error_msg)
                return {"errors": [error_msg]}

        # Ensure run_section is a dict
        if not isinstance(run_section, dict):
            print(f"run_section is not a dict: {type(run_section)}")
            error_msg = f"run_section is not a dictionary: {type(run_section)}"
            state.errors.append(error_msg)
            return {"errors": [error_msg]}
        else:
            # Define a function to normalize the case of property fields
            # This handles capitalized keys like 'Type' and 'Required' that should be lowercase 'type' and 'required'
            def normalize_property_dict(prop_dict):
                if not isinstance(prop_dict, dict):
                    return prop_dict

                normalized = {}
                for key, value in prop_dict.items():
                    # Convert keys like 'Type' to 'type'
                    normalized_key = key.lower() if key in ['Type', 'Required', 'Default', 'Secret', 'Label'] else key
                    normalized[normalized_key] = value
                return normalized

            # Process config properties to normalize case
            if "config" in run_section and isinstance(run_section["config"], dict):
                for key, prop in list(run_section["config"].items()):
                    if isinstance(prop, dict):
                        run_section["config"][key] = normalize_property_dict(prop)

            # Process env properties to normalize case
            if "env" in run_section and isinstance(run_section["env"], dict):
                for key, prop in list(run_section["env"].items()):
                    if isinstance(prop, dict):
                        run_section["env"][key] = normalize_property_dict(prop)

            # Ensure all required fields exist with defaults
            if "config" not in run_section or not isinstance(run_section["config"], dict):
                print("Missing or invalid 'config'")
                error_msg = "Missing or invalid 'config' in run section"
                state.errors.append(error_msg)
                return {"errors": [error_msg]}

            if "entrypoint" not in run_section or not isinstance(run_section["entrypoint"], list):
                print("Missing or invalid 'entrypoint'")
                error_msg = "Missing or invalid 'entrypoint' in run section"
                state.errors.append(error_msg)
                return {"errors": [error_msg]}

            if "env" not in run_section or not isinstance(run_section["env"], dict):
                print("Missing or invalid 'env'")
                error_msg = "Missing or invalid 'env' in run section"
                state.errors.append(error_msg)
                return {"errors": [error_msg]}

            # Process config properties to ensure they match the Property struct format
            for key, value in list(run_section["config"].items()):
                if not isinstance(value, dict) or "type" not in value:
                    print(f"Config property '{key}' is not in the correct format, fixing")
                    # Convert simple values to properly formatted Property objects
                    if isinstance(value, str):
                        run_section["config"][key] = {
                            "type": "string",
                            "required": False,
                            "default": value,
                            "label": key.replace("_", " ").title()
                        }
                    elif isinstance(value, int):
                        run_section["config"][key] = {
                            "type": "integer",
                            "required": False,
                            "default": str(value),
                            "label": key.replace("_", " ").title()
                        }
                    elif isinstance(value, bool):
                        run_section["config"][key] = {
                            "type": "boolean",
                            "required": False,
                            "default": str(value).lower(),
                            "label": key.replace("_", " ").title()
                        }
                    elif isinstance(value, dict):
                        # Add required fields to existing dict
                        if "type" not in value:
                            value["type"] = "string"
                        if "required" not in value:
                            value["required"] = False
                        if "label" not in value:
                            value["label"] = key.replace("_", " ").title()
                        run_section["config"][key] = value
                    else:
                        # Default case
                        run_section["config"][key] = {
                            "type": "string",
                            "required": False,
                            "label": key.replace("_", " ").title()
                        }

            # Process env properties to ensure they match the Property struct format
            for key, value in list(run_section["env"].items()):
                if not isinstance(value, dict) or "type" not in value:
                    print(f"Env property '{key}' is not in the correct format, fixing")
                    # Convert simple values to properly formatted Property objects
                    if isinstance(value, str):
                        run_section["env"][key] = {
                            "type": "string",
                            "required": False,
                            "default": value,
                            "secret": key.upper().endswith("_KEY") or key.upper().endswith("_SECRET") or key.upper().endswith("_TOKEN") or key.upper().endswith("_PASSWORD")
                        }
                    elif isinstance(value, int):
                        run_section["env"][key] = {
                            "type": "integer",
                            "required": False,
                            "default": str(value)
                        }
                    elif isinstance(value, bool):
                        run_section["env"][key] = {
                            "type": "boolean",
                            "required": False,
                            "default": str(value).lower()
                        }
                    elif isinstance(value, dict):
                        # Add required fields to existing dict
                        if "type" not in value:
                            value["type"] = "string"
                        if "required" not in value:
                            value["required"] = False
                        # Mark as secret if it seems to be a credential
                        if "secret" not in value:
                            value["secret"] = key.upper().endswith("_KEY") or key.upper().endswith("_SECRET") or key.upper().endswith("_TOKEN") or key.upper().endswith("_PASSWORD")
                        run_section["env"][key] = value
                    else:
                        # Default case
                        run_section["env"][key] = {
                            "type": "string",
                            "required": False
                        }
                else:
                    # Already in Property format
                    run_section["env"][key] = value

        print(f"Final run_section: {run_section}")

        # Store the full run section and create the run field
        import yaml
        run_yaml = yaml.dump({"run": run_section}, default_flow_style=False, Dumper=yaml.SafeDumper)
        update_memory(state, "run_yaml", run_yaml)

        # Add the run field to state (this was previously missing)
        state.run = run_yaml

        # Store individual sections as strings
        state.config = yaml.dump({"config": run_section["config"]}, default_flow_style=False, Dumper=yaml.SafeDumper)
        state.entrypoint = yaml.dump({"entrypoint": run_section["entrypoint"]}, default_flow_style=False, Dumper=yaml.SafeDumper)
        state.env = yaml.dump({"env": run_section["env"]}, default_flow_style=False, Dumper=yaml.SafeDumper)

        update_memory(state, "config_yaml", state.config)
        update_memory(state, "entrypoint_yaml", state.entrypoint)
        update_memory(state, "env_yaml", state.env)

        print("Run node completed successfully")
        return {
            "config_yaml": state.config,
            "entrypoint_yaml": state.entrypoint,
            "env_yaml": state.env,
            "run_yaml": run_yaml
        }

    except Exception as e:
        error_msg = f"Run section generation failed: {e}"
        print(f"Exception details: {type(e).__name__}")
        import traceback
        traceback.print_exc()

        state.errors.append(error_msg)
        return {"errors": [error_msg]}

async def assembler_node(state: MCPState) -> Dict:
    """Node for assembling YAML sections without using an agent."""
    try:
        if len(state.errors) > 0:
            print(f"Skipping assembler due to errors: {state.errors}")
            return {"errors": state.errors}

        print("Assembling YAML sections directly...")

        # Debug output to track what's being assembled
        print("Assembling YAML with sections:")
        for section_name in ["metadata_yaml", "source_yaml", "build_yaml", "config_yaml", "entrypoint_yaml", "env_yaml"]:
            section_content = get_memory(state, section_name)
            section_preview = section_content[:100] + "..." if section_content and len(section_content) > 100 else section_content
            print(f"{section_name}: {section_preview}")

        # Get the tools section
        tools_section = state.server.tools if state.server.tools else []
        print(f"Tools section has {len(tools_section)} tools")

        # Convert tools to dictionaries to avoid Python object serialization issues
        converted_tools = []
        for tool in tools_section:
            if hasattr(tool, "model_dump"):
                # Pydantic v2
                converted_tools.append(tool.model_dump())
            elif hasattr(tool, "dict"):
                # Pydantic v1
                converted_tools.append(tool.dict())
            else:
                # Fallback to manual conversion
                tool_dict = {
                    "name": getattr(tool, "name", ""),
                    "description": getattr(tool, "description", ""),
                    "inputSchema": getattr(tool, "inputSchema", {}),
                }
                if hasattr(tool, "outputSchema") and tool.outputSchema:
                    tool_dict["outputSchema"] = tool.outputSchema
                converted_tools.append(tool_dict)

        # Replace the tools section with converted dictionaries
        tools_section = converted_tools
        print(f"Converted {len(tools_section)} tools to dictionaries")

        # Import YAML library for parsing and dumping
        import yaml

        # Parse each YAML section
        metadata_section = yaml.safe_load(get_memory(state, "metadata_yaml") or "{}")
        source_section = yaml.safe_load(get_memory(state, "source_yaml") or "{}")
        build_section = yaml.safe_load(get_memory(state, "build_yaml") or "{}")

        # Load and combine the run section components
        config_yaml = get_memory(state, "config_yaml") or "{}"
        entrypoint_yaml = get_memory(state, "entrypoint_yaml") or "[]"
        env_yaml = get_memory(state, "env_yaml") or "{}"

        print(f"Config YAML: {config_yaml}")
        print(f"Entrypoint YAML: {entrypoint_yaml}")
        print(f"Env YAML: {env_yaml}")

        config_section = yaml.safe_load(config_yaml)
        entrypoint_section = yaml.safe_load(entrypoint_yaml)
        env_section = yaml.safe_load(env_yaml)

        # Extract actual values from potential nested structures
        if isinstance(config_section, dict) and "config" in config_section:
            config_section = config_section["config"]
        if isinstance(entrypoint_section, dict) and "entrypoint" in entrypoint_section:
            entrypoint_section = entrypoint_section["entrypoint"]
        if isinstance(env_section, dict) and "env" in env_section:
            env_section = env_section["env"]

        # Extract source and build from potential nested structures
        if isinstance(source_section, dict) and "source" in source_section:
            source_section = source_section["source"]
        if isinstance(build_section, dict) and "build" in build_section:
            build_section = build_section["build"]

        # Ensure source section follows the Go struct format
        if isinstance(source_section, dict):
            # Check for git nested structure that needs to be flattened
            if "git" in source_section and isinstance(source_section["git"], dict):
                git_info = source_section["git"]
                source_section = {
                    "repo": git_info.get("repository", state.repo_url),
                    "branch": git_info.get("branch", state.branch),
                    "path": git_info.get("path", ".")
                }

            # Ensure required fields exist with correct names
            if "repo" not in source_section:
                source_section["repo"] = state.repo_url
            if "repository" in source_section and not source_section.get("repo"):
                source_section["repo"] = source_section.pop("repository")
            if "branch" not in source_section:
                source_section["branch"] = state.branch
            if "path" not in source_section:
                source_section["path"] = "."

            # Remove any fields that don't belong in the Go struct
            for key in list(source_section.keys()):
                if key not in ["repo", "branch", "path", "localPath"]:
                    del source_section[key]
        else:
            # Fail with error
            error_msg = "Source section is missing or invalid"
            print(f"ERROR: {error_msg}")
            state.errors.append(error_msg)
            return {"errors": [error_msg]}

        # Ensure build section follows the Go struct format
        if isinstance(build_section, dict):
            # Check required fields for build section
            required_build_fields = ["path", "language", "command", "output"]
            missing_build_fields = []

            for field in required_build_fields:
                if field not in build_section:
                    missing_build_fields.append(field)

            # Add any missing fields with default values
            if missing_build_fields:
                print(f"Build section missing fields: {missing_build_fields}")

                # Default values based on analysis or fallbacks
                if "path" not in build_section:
                    build_section["path"] = "."
                if "language" not in build_section:
                    # Try to guess language from analysis
                    if "javascript" in state.analysis_output.lower() or "node" in state.analysis_output.lower():
                        build_section["language"] = "javascript"
                    elif "python" in state.analysis_output.lower():
                        build_section["language"] = "python"
                    else:
                        build_section["language"] = "unknown"
                if "command" not in build_section:
                    if build_section.get("language") == "javascript":
                        build_section["command"] = "npm install"
                    elif build_section.get("language") == "python":
                        build_section["command"] = "pip install -r requirements.txt"
                    else:
                        build_section["command"] = "echo 'No build command specified'"
                if "output" not in build_section:
                    build_section["output"] = "."
        else:
            # Create a default build section
            print("Build section missing or invalid, creating default")
            build_section = {
                "path": ".",
                "language": "javascript" if "javascript" in state.analysis_output.lower() or "node" in state.analysis_output.lower() else "python" if "python" in state.analysis_output.lower() else "unknown",
                "command": "npm install" if "javascript" in state.analysis_output.lower() or "node" in state.analysis_output.lower() else "pip install -r requirements.txt" if "python" in state.analysis_output.lower() else "echo 'No build command specified'",
                "output": "."
            }

        # Construct the run section matching Go struct format
        run_section = {
            "config": {},
            "entrypoint": entrypoint_section,
            "env": {}
        }

        # Ensure config and env properties match the Property struct format
        # Process config section
        if isinstance(config_section, dict):
            for key, value in config_section.items():
                if not isinstance(value, dict) or "type" not in value:
                    # Convert simple values to properly formatted Property objects
                    if isinstance(value, str):
                        run_section["config"][key] = {
                            "type": "string",
                            "required": False,
                            "default": value
                        }
                    elif isinstance(value, int):
                        run_section["config"][key] = {
                            "type": "integer",
                            "required": False,
                            "default": str(value)
                        }
                    elif isinstance(value, bool):
                        run_section["config"][key] = {
                            "type": "boolean",
                            "required": False,
                            "default": str(value).lower()
                        }
                    elif isinstance(value, dict):
                        # Add required fields to existing dict
                        if "type" not in value:
                            value["type"] = "string"
                        if "required" not in value:
                            value["required"] = False
                        run_section["config"][key] = value
                    else:
                        # Default case
                        run_section["config"][key] = {
                            "type": "string",
                            "required": False
                        }
                else:
                    # Already in Property format
                    run_section["config"][key] = value

        # Process env section
        if isinstance(env_section, dict):
            for key, value in env_section.items():
                if not isinstance(value, dict) or "type" not in value:
                    # Convert simple values to properly formatted Property objects
                    if isinstance(value, str):
                        run_section["env"][key] = {
                            "type": "string",
                            "required": False,
                            "default": value,
                            "secret": key.upper().endswith("_KEY") or key.upper().endswith("_SECRET") or key.upper().endswith("_TOKEN") or key.upper().endswith("_PASSWORD")
                        }
                    elif isinstance(value, int):
                        run_section["env"][key] = {
                            "type": "integer",
                            "required": False,
                            "default": str(value)
                        }
                    elif isinstance(value, bool):
                        run_section["env"][key] = {
                            "type": "boolean",
                            "required": False,
                            "default": str(value).lower()
                        }
                    elif isinstance(value, dict):
                        # Add required fields to existing dict
                        if "type" not in value:
                            value["type"] = "string"
                        if "required" not in value:
                            value["required"] = False
                        # Mark as secret if it seems to be a credential
                        if "secret" not in value:
                            value["secret"] = key.upper().endswith("_KEY") or key.upper().endswith("_SECRET") or key.upper().endswith("_TOKEN") or key.upper().endswith("_PASSWORD")
                        run_section["env"][key] = value
                    else:
                        # Default case
                        run_section["env"][key] = {
                            "type": "string",
                            "required": False
                        }
                else:
                    # Already in Property format
                    run_section["env"][key] = value

        # Combine all sections into a single YAML
        # The structure must match the Go struct definitions in hub.go
        assembled_dict = {
            # The metadata fields should be at the top level
            **metadata_section,
            # These should be nested objects matching the Go structs
            "source": source_section,
            "build": build_section,
            "run": run_section
        }

        # Add tools section if it exists
        if tools_section:
            assembled_dict["tools"] = tools_section

        # Ensure all required fields from the Repository struct are present
        required_fields = [
            "name", "displayName", "description", "longDescription",
            "icon", "categories", "version"
        ]

        # Map Go struct field names (camelCase) to YAML keys (potentially snake_case)
        field_mappings = {
            "name": ["name"],
            "displayName": ["displayName", "display_name"],
            "description": ["description"],
            "longDescription": ["longDescription", "long_description"],
            "icon": ["icon"],
            "categories": ["categories"],
            "version": ["version"]
        }

        missing_fields = []
        for field in required_fields:
            found = False
            # Check all possible mappings for this field
            for possible_key in field_mappings.get(field, [field]):
                if possible_key in assembled_dict:
                    found = True
                    break

            if not found:
                missing_fields.append(field)

        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            print(f"ERROR: {error_msg}")
            state.errors.append(error_msg)
            return {"errors": [error_msg]}

        # Convert to YAML string
        assembled_yaml = yaml.dump(assembled_dict, sort_keys=False, default_flow_style=False, Dumper=yaml.SafeDumper)

        # Print the assembled YAML for debugging
        print(f"Assembled YAML (length: {len(assembled_yaml)})")
        if len(assembled_yaml) < 500:
            print(assembled_yaml)
        else:
            print(f"{assembled_yaml[:200]}...")

        # Validate that we have a non-empty YAML
        if not assembled_yaml or len(assembled_yaml.strip()) < 10:
            error_msg = "Assembler produced empty or invalid YAML"
            print(f"ERROR: {error_msg}")
            update_memory(state, "assembler_error", error_msg)
            state.errors.append(error_msg)
            return {"errors": [error_msg]}

        # Make sure to store the assembled_yaml in both state and shared_memory
        update_memory(state, "assembled_yaml", assembled_yaml)
        state.final_yaml = assembled_yaml  # Set the final_yaml in the state directly

        # Store again in shared_memory to ensure it's there
        if not hasattr(state, 'shared_memory'):
            state.shared_memory = {}
        state.shared_memory["assembled_yaml"] = assembled_yaml

        print("Assembler node completed successfully")
        return {"assembled_yaml": assembled_yaml, "final_yaml": assembled_yaml}
    except Exception as e:
        error_msg = f"Assembly failed: {str(e)}"
        print(f"ERROR in assembler_node: {error_msg}")
        print(f"Exception details: {type(e).__name__}")
        import traceback
        traceback.print_exc()

        update_memory(state, "assembler_error", error_msg)
        state.errors.append(error_msg)
        return {"errors": [error_msg]}

async def validator_node(state: MCPState) -> Dict:
    """Node for validating final YAML."""
    try:
        if len(state.errors) > 0:
            print("Validation skipped due to errors")
            return {"errors": state.errors}

        print("Starting validation of assembled YAML")

        # First try to get assembled_yaml from state.final_yaml
        assembled_yaml = None
        if hasattr(state, 'final_yaml') and state.final_yaml:
            print("Using state.final_yaml for validation")
            assembled_yaml = state.final_yaml

        # If not found, try shared_memory
        if not assembled_yaml:
            assembled_yaml = get_memory(state, "assembled_yaml")
            if assembled_yaml:
                print("Using shared_memory[assembled_yaml] for validation")

        # Debug shared memory
        print("Contents of shared_memory:")
        if hasattr(state, 'shared_memory'):
            for key, value in state.shared_memory.items():
                value_preview = str(value)[:50] + "..." if value and len(str(value)) > 50 else value
                print(f"  - {key}: {value_preview}")
        else:
            print("  No shared_memory found on state")

        if not assembled_yaml:
            error_msg = "No assembled YAML available for validation"
            print(f"ERROR: {error_msg}")
            state.errors.append(error_msg)
            return {"errors": [error_msg]}

        print(f"Validating YAML (length: {len(assembled_yaml)})")

        # Check if the YAML structure matches the expected structure in hub.go
        try:
            import yaml

            # Parse using SafeLoader to avoid Python-specific tags
            assembled_dict = yaml.safe_load(assembled_yaml)

            # Check required fields based on the Repository struct in hub.go
            required_fields = [
                "name", "displayName", "description", "longDescription",
                "icon", "categories", "version", "source", "build", "run"
            ]

            missing_fields = []
            for field in required_fields:
                if field not in assembled_dict:
                    missing_fields.append(field)

            if missing_fields:
                error_msg = f"Missing required fields in YAML: {', '.join(missing_fields)}"
                print(f"ERROR: {error_msg}")
                state.errors.append(error_msg)
                return {"errors": [error_msg]}

            # Check nested structures
            if "source" in assembled_dict:
                source = assembled_dict["source"]
                if not isinstance(source, dict):
                    error_msg = "'source' is not a dictionary"
                    print(f"ERROR: {error_msg}")
                    state.errors.append(error_msg)
                    return {"errors": [error_msg]}
                elif "repo" not in source or "branch" not in source:
                    missing = []
                    if "repo" not in source:
                        missing.append("repo")
                    if "branch" not in source:
                        missing.append("branch")
                    error_msg = f"'source' is missing required fields: {', '.join(missing)}"
                    print(f"ERROR: {error_msg}")
                    state.errors.append(error_msg)
                    return {"errors": [error_msg]}

            if "build" in assembled_dict:
                build = assembled_dict["build"]
                if not isinstance(build, dict):
                    error_msg = "'build' is not a dictionary"
                    print(f"ERROR: {error_msg}")
                    state.errors.append(error_msg)
                    return {"errors": [error_msg]}

                required_build_fields = ["path", "language", "command", "output"]
                missing_build_fields = []
                for field in required_build_fields:
                    if field not in build:
                        missing_build_fields.append(field)

                if missing_build_fields:
                    error_msg = f"'build' is missing required fields: {', '.join(missing_build_fields)}"
                    print(f"ERROR: {error_msg}")
                    state.errors.append(error_msg)
                    return {"errors": [error_msg]}

            if "run" in assembled_dict:
                run = assembled_dict["run"]
                if not isinstance(run, dict):
                    error_msg = "'run' is not a dictionary"
                    print(f"ERROR: {error_msg}")
                    state.errors.append(error_msg)
                    return {"errors": [error_msg]}

                required_run_fields = ["config", "entrypoint", "env"]
                missing_run_fields = []
                for field in required_run_fields:
                    if field not in run:
                        missing_run_fields.append(field)

                if missing_run_fields:
                    error_msg = f"'run' is missing required fields: {', '.join(missing_run_fields)}"
                    print(f"ERROR: {error_msg}")
                    state.errors.append(error_msg)
                    return {"errors": [error_msg]}

                # Check config and env are dictionaries
                if not isinstance(run.get("config"), dict):
                    error_msg = "'run.config' is not a dictionary"
                    print(f"ERROR: {error_msg}")
                    state.errors.append(error_msg)
                    return {"errors": [error_msg]}

                if not isinstance(run.get("entrypoint"), list):
                    error_msg = "'run.entrypoint' is not a list"
                    print(f"ERROR: {error_msg}")
                    state.errors.append(error_msg)
                    return {"errors": [error_msg]}

                if not isinstance(run.get("env"), dict):
                    error_msg = "'run.env' is not a dictionary"
                    print(f"ERROR: {error_msg}")
                    state.errors.append(error_msg)
                    return {"errors": [error_msg]}

                # Check config properties
                for key, value in run["config"].items():
                    if not isinstance(value, dict) or "type" not in value:
                        error_msg = f"Config property '{key}' is not in the correct format"
                        print(f"ERROR: {error_msg}")
                        state.errors.append(error_msg)
                        return {"errors": [error_msg]}

                # Check env properties
                for key, value in run["env"].items():
                    if not isinstance(value, dict) or "type" not in value:
                        error_msg = f"Env property '{key}' is not in the correct format"
                        print(f"ERROR: {error_msg}")
                        state.errors.append(error_msg)
                        return {"errors": [error_msg]}

            print("YAML structure validated")

        except Exception as yaml_error:
            error_msg = f"YAML validation error: {str(yaml_error)}"
            print(f"ERROR: {error_msg}")
            state.errors.append(error_msg)
            return {"errors": [error_msg]}

        # try:
        #     # Try validation, but don't fail if it doesn't work
        #     print("Attempting to run validation...")
        #     validation_result = await run_mcp_validation(assembled_yaml, state.repo_path)
        #     if validation_result:
        #         assembled_yaml = validation_result
        #         print(f"Validation complete, result length: {len(validation_result)}")
        #     else:
        #         print("Validation returned no result, using original YAML")
        # except Exception as validation_error:
        #     error_msg = f"Validation error: {str(validation_error)}"
        #     print(f"ERROR: {error_msg}")
        #     state.errors.append(error_msg)
        #     return {"errors": [error_msg]}

        # Store the validated YAML
        update_memory(state, "validated_yaml", assembled_yaml)
        state.final_yaml = assembled_yaml  # Set the final_yaml in the state directly

        # Ensure it's directly accessible in shared_memory too
        if not hasattr(state, 'shared_memory'):
            state.shared_memory = {}
        state.shared_memory["validated_yaml"] = assembled_yaml
        state.shared_memory["final_yaml"] = assembled_yaml  # Add an extra copy with a different key

        print("Updated final_yaml in state and shared_memory")
        return {"final_yaml": assembled_yaml, "validated_yaml": assembled_yaml}
    except Exception as e:
        error_msg = f"Validation failed: {str(e)}"
        print(f"Validation error: {error_msg}")
        update_memory(state, "validator_error", error_msg)
        state.errors.append(error_msg)
        return {"errors": [error_msg]}

async def process_mcp_server(
    server: Server,
    repo_url: str,
) -> Tuple[str, str, List[str]]:
    """Process a single MCP server using the graph-based workflow.

    Returns:
        Tuple of (safe_name, yaml_content, errors)
    """
    # Create temporary directory for cloning
    temp_dir = tempfile.mkdtemp()
    error_messages = []

    try:
        # Clone repository
        try:
            print(f"Cloning repository: {repo_url}")
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, temp_dir],
                check=True, capture_output=True, timeout=60
            )
            print(f"Repository cloned successfully: {repo_url}")

            # Get the branch
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=temp_dir, capture_output=True, text=True, timeout=30
            ).stdout.strip()
            print(f"Repository branch: {branch}")

            if hasattr(server.repository, "__setattr__"):
                setattr(server.repository, "branch", branch)

        except subprocess.SubprocessError as e:
            print(f"Repository cloning failed: {e}")
            return server.name.lower().replace(" ", "-"), "", [f"Repository cloning failed: {e}"]

        # Extract repository info
        repo_info = extract_repository_info(temp_dir)
        analysis_output = format_analysis_output(repo_info)

        try:
            # Create a state object to share data between agent calls
            state = MCPState(
                server=server,
                repo_url=repo_url,
                branch=branch,
                repo_path=temp_dir,
                analysis_output=analysis_output,
                shared_memory={},
                errors=[]
            )

            # Execute each component sequentially with proper error handling
            print("Generating metadata component...")
            metadata_result = await metadata_node(state)
            if "errors" in metadata_result and metadata_result["errors"]:
                error_messages.extend(metadata_result["errors"])
                print(f"Errors in metadata generation: {metadata_result['errors']}")
                return server.name.lower().replace(" ", "-"), "", error_messages

            print("Generating source component...")
            source_result = await source_node(state)
            if "errors" in source_result and source_result["errors"]:
                error_messages.extend(source_result["errors"])
                print(f"Errors in source generation: {source_result['errors']}")
                return server.name.lower().replace(" ", "-"), "", error_messages

            print("Generating build component...")
            build_result = await build_node(state)
            if "errors" in build_result and build_result["errors"]:
                error_messages.extend(build_result["errors"])
                print(f"Errors in build generation: {build_result['errors']}")
                return server.name.lower().replace(" ", "-"), "", error_messages

            print("Generating run component...")
            run_result = await run_node(state)
            if "errors" in run_result and run_result["errors"]:
                error_messages.extend(run_result["errors"])
                print(f"Errors in run generation: {run_result['errors']}")
                return server.name.lower().replace(" ", "-"), "", error_messages

            # Check if all required components are available
            missing_components = []

            if not state.metadata:
                missing_components.append("metadata")
            if not state.source:
                missing_components.append("source")
            if not state.build:
                missing_components.append("build")
            if not hasattr(state, "run") or not state.run:
                if get_memory(state, "run_yaml"):
                    state.run = get_memory(state, "run_yaml")
                else:
                    missing_components.append("run")

            if missing_components:
                error_msg = f"Missing required components: {', '.join(missing_components)}"
                print(error_msg)
                error_messages.append(error_msg)
                return server.name.lower().replace(" ", "-"), "", error_messages

            # Run the assembler to create the complete YAML
            print("Assembling components into complete YAML...")
            assembler_result = await assembler_node(state)

            if "errors" in assembler_result and assembler_result["errors"]:
                error_messages.extend(assembler_result["errors"])
                print(f"Errors in assembler: {assembler_result['errors']}")
                return server.name.lower().replace(" ", "-"), "", error_messages

            # Get the final YAML
            yaml_content = ""
            if "assembled_yaml" in assembler_result:
                yaml_content = assembler_result["assembled_yaml"]
            elif state.final_yaml:
                yaml_content = state.final_yaml
            elif get_memory(state, "assembled_yaml"):
                yaml_content = get_memory(state, "assembled_yaml")

            if not yaml_content:
                error_msg = "Failed to produce YAML output"
                error_messages.append(error_msg)
                print(error_msg)
                return server.name.lower().replace(" ", "-"), "", error_messages

            # # Run validator on the assembled YAML
            # try:
            #     print("Validating assembled YAML...")
            #     validator_result = await validator_node(state)
            #     if "errors" in validator_result and validator_result["errors"]:
            #         error_messages.extend(validator_result["errors"])
            #         print(f"Errors in validator: {validator_result['errors']}")
            #         return server.name.lower().replace(" ", "-"), "", error_messages

            #     if "final_yaml" in validator_result:
            #         yaml_content = validator_result["final_yaml"]
            #         print("Using validated YAML as final output")
            # except Exception as validator_error:
            #     # Fail if validation fails
            #     error_msg = f"Validation error: {validator_error}"
            #     print(f"ERROR: {error_msg}")
            #     error_messages.append(error_msg)
            #     return server.name.lower().replace(" ", "-"), "", error_messages

            print(f"Final YAML length: {len(yaml_content)}")
            return server.name.lower().replace(" ", "-"), yaml_content, error_messages

        except Exception as e:
            print(f"Error processing YAML: {e}")
            error_messages.append(f"Error processing YAML: {str(e)}")
            return server.name.lower().replace(" ", "-"), "", error_messages

    except Exception as e:
        print(f"Unexpected error in process_mcp_server: {e}")
        return server.name.lower().replace(" ", "-"), "", [f"Unexpected error: {str(e)}"]
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Failed to clean up temporary directory: {e}")

async def workflow_main(
    servers: List[Server],
    output: str,
) -> str:
    """Main workflow entry point for processing MCP servers."""
    results = []
    success_count = 0
    failure_count = 0

    for server in servers:
        try:
            print(f"Processing {server.name}")
            repo_url = server.repository.url if hasattr(server.repository, "url") else ""
            if not repo_url:
                error_msg = f"No repository URL for {server.name}"
                print(f"ERROR: {error_msg}")
                results.append(f"Failed to process {server.name}: {error_msg}")
                failure_count += 1
                continue

            print(f"Calling process_mcp_server for {server.name} with repo URL: {repo_url}")

            # Ensure the output directory exists
            os.makedirs(output, exist_ok=True)

            safe_name = server.name.lower().replace(" ", "-")
            output_file = os.path.join(output, f"{safe_name}.yaml")

            try:
                # Call process_mcp_server to get results
                safe_name, yaml_content, errors = await process_mcp_server(server, repo_url)

                print(f"Results for {server.name}:")
                print(f"  - Safe name: {safe_name}")
                print(f"  - YAML content length: {len(yaml_content) if yaml_content else 0}")
                print(f"  - Errors: {errors if errors else 'None'}")

                if yaml_content:
                    with open(output_file, "w") as f:
                        f.write(yaml_content)

                    print(f"Generated <mcp>.yaml for {server.name} in {output_file}")
                    if errors:
                        # If there are errors but we still have YAML content, that's a partial success
                        # but we'll count it as a failure to be strict
                        print(f"WARNING: Generated YAML with errors: {', '.join(errors)}")
                        results.append(f"Partially processed {server.name} with errors: {', '.join(errors)}")
                        failure_count += 1
                    else:
                        # Only count as success if there are no errors
                        results.append(f"Successfully processed {server.name}")
                        success_count += 1
                else:
                    # No YAML content means failure
                    error_msg = f"Failed to generate <mcp>.yaml for {server.name}"
                    if errors:
                        error_msg += f": {', '.join(errors)}"
                    print(f"ERROR: {error_msg}")
                    results.append(error_msg)
                    failure_count += 1

            except Exception as processing_error:
                error_msg = f"Error processing {server.name}: {processing_error}"
                print(f"ERROR: {error_msg}")
                results.append(error_msg)
                failure_count += 1

        except Exception as e:
            error_msg = f"Error processing {server.name}: {e}"
            print(f"ERROR: {error_msg}")
            results.append(error_msg)
            failure_count += 1

    summary = f"Processed {len(servers)} MCP servers.\n"
    summary += f"Successful: {success_count}\n"
    summary += f"Failed: {failure_count}\n\n"
    summary += "Detailed results:\n"
    for result in results:
        summary += f"- {result}\n"

    return summary