"""
MCP Validator Module - Simplified Agent Version

This module provides agent-based validation functionality for MCP (Model Control Protocol) YAML files.
It uses an LLM agent with tools to validate and correct MCP YAML,
including testing the build and run functionality.

Note: The module still maintains backward-compatible functions for direct validation
used by other parts of the codebase, but the recommended approach is to use the agent-based
validation via run_mcp_validation().
"""

from langchain_core.tools import Tool, StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_community.tools.file_management import ReadFileTool, ListDirectoryTool
from src.tools.run_mcps import test_server
import re
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Union, Optional, List
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish, LLMResult
import uuid
import json
from datetime import datetime

def write_yaml_to_file(content: Optional[str] = None, file_path: Optional[str] = None) -> str:
    """Write YAML content to a file and return the file path.
    
    Args:
        content: The YAML content to write to the file
        file_path: The path where the file should be written
        
    Returns:
        str: The file path on success or an error message on failure
    """
    if content is None or file_path is None:
        return "Error: Both content and file_path must be provided"
    
    try:
        # Validate the YAML content
        try:
            yaml_obj = yaml.safe_load(content)
            if yaml_obj is None:
                return "Error: Empty or invalid YAML content"
        except yaml.YAMLError as e:
            return f"Error validating YAML: {str(e)}"
        
        # Use pathlib for better path handling
        file_path_obj = Path(file_path)
        file_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content to file
        file_path_obj.write_text(content)
        
        print(f"Successfully wrote YAML to {file_path}")
        return str(file_path_obj)
    except Exception as e:
        error_msg = f"Error writing YAML to {file_path}: {str(e)}"
        print(error_msg)
        return error_msg


def run_mcps_wrapper(server_file: str) -> Dict[str, Any]:
    """Test an MCP module and validate it works."""
    try:
        # Call the implementation function directly
        print(f"Running MCP from {server_file}")
        result = test_server(server_file)
        print(f"Run result: {result.get('success', False)}")
        return result
    except Exception as e:
        error_msg = f"Error in run_mcps_wrapper: {str(e)}"
        print(error_msg)
        return {"server": server_file, "success": False, "errors": [error_msg], "logs": []}

def create_validator_agent():
    """Create an agent that validates and corrects the outputs from analysis, MCP generation, and tools extraction agents."""
    tools = [
        Tool(name="ReadFile", func=ReadFileTool().run, 
             description="Read a file from the repository to validate its content."),
        Tool(name="ListDirectory", func=ListDirectoryTool().run, 
             description="List contents of a repository directory."),
        StructuredTool.from_function(
            func=run_mcps_wrapper,
            name="run_mcp",
            description="Test an MCP module and validate it works. Requires server_file parameter pointing to a valid YAML file path."
        ),
    ]
    
    system_message = """You are an expert for MCP module functional validation.
    Your sole focus is to ensure the MCP server builds successfully and runs correctly.
    
    YOU MUST PERFORM THESE STEPS IN EXACT SEQUENCE - DO NOT SKIP OR REPEAT STEPS:
    
    1. First - Analyze the initial YAML structure:
       - Review the provided YAML for obvious structural issues
       - Check for configuration parameter references to ensure they're correctly formatted
       
    2. Next - Run the MCP server:
       - Call run_mcp with the server_file parameter set to "/tmp/mcp_validation/current_mcp.yaml"
       - The system will automatically write the YAML before running
       - Analyze any runtime errors carefully
    
    3. Then - Fix configuration issues ONLY if run fails:
       - If the run fails, identify issues with configuration parameters
       - Fix format of config references in entrypoint: ${{config.parameterName}}
       - Update environment variables to reference existing config parameters
       - After suggesting corrections, call run_mcp again (the system will automatically apply your changes)
    
    4. If the run fails again, make additional corrections:
       - Focus on structural issues with the YAML
       - Check for missing or incorrect sections
       - After suggesting corrections, call run_mcp again
       
    5. Finally - Add any discovered tools to the MCP YAML if needed.
    
    IMPORTANT RULES:
    - You don't need to write the YAML to a file, that happens automatically
    - ALWAYS use named parameters exactly as shown in the examples
    - DO NOT repeat the same step multiple times without progressing
    - If a step fails, fix the issues and then continue with the next step
    
    Return the corrected <mcp>.yaml content after successful build and run, along with a brief report.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
        ("human", """Please build and run this MCP module definition:

Generated MCP YAML:
{mcp_yaml}

YOUR TASK IS TO VALIDATE AND FIX THIS YAML:

1. First analyze the YAML structure:
   - Look for any obvious errors or issues
   - The system will track your changes automatically

2. Then run the MCP server:
   ```
   run_mcp(
       server_file="/tmp/mcp_validation/current_mcp.yaml"
   )
   ```
   - The system will automatically write the current YAML before running
   - Examine the result to determine if the server ran successfully

3. If it failed, fix issues and run again:
   - Make corrections to the YAML
   - After each correction, call run_mcp to test again
   - Repeat until successful

4. Return the final YAML:
   - When the MCP server runs successfully, provide the corrected YAML
   - Include a brief report on what changes were made

IMPORTANT NOTES:
- You DO NOT need to write the file yourself - this happens automatically
- Just suggest the corrected YAML content and call run_mcp when ready to test
- Focus on fixing the YAML, not on file operations

{input}""")
    ])
    
    # Use gpt-4o instead of gpt-4o-mini for better step following
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent = create_openai_functions_agent(llm, tools, prompt)
    
    # Return both the agent and tools to use in the executor
    return agent, tools

def run_mcp_validation(mcp_yaml, repo_path, max_iterations=5):
    """Run MCP validation using either direct validation or agent-based validation.
    
    This function is the main entry point for MCP validation. It provides a unified
    interface for both direct validation and agent-based validation.
    
    Args:
        mcp_yaml (str): The MCP YAML content to validate
        repo_path (str): Path to the repository
        max_iterations (int, optional): Maximum number of iterations before considering validation failed. Defaults to 5.
        
    Returns:
        str: The final validated YAML content
    """
    # Create the agent and get the tools
    agent, tools = create_validator_agent()
    
    # Create a callback handler to track YAML changes throughout execution
    yaml_tracker = YAMLTrackingCallbackHandler(
        initial_yaml=mcp_yaml,
        base_dir="/tmp/mcp_validation",
        max_iterations=max_iterations
    )
    
    # Create the agent executor with the callback handler and explicit tools
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools,  # Use the tools returned from create_validator_agent
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=max_iterations,  # Limit to specified number of iterations
        max_execution_time=None,
        callbacks=[yaml_tracker],  # Add the YAML tracking callback
    )
    
    # Custom callback to process intermediate responses and extract YAML updates
    class YAMLExtractingCallbackHandler(BaseCallbackHandler):
        def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
            """Extract YAML from LLM responses when present."""
            try:
                # Try to extract YAML from the response
                if hasattr(response, 'generations') and response.generations:
                    for gen in response.generations[0]:
                        if hasattr(gen, 'text'):
                            yaml_blocks = re.findall(r'```(?:yaml)?\s*([\s\S]*?)```', gen.text)
                            if yaml_blocks:
                                # Use the last YAML block found
                                yaml_tracker.current_yaml = yaml_blocks[-1]
                                yaml_tracker._write_current_yaml("llm_correction")
                                print("Extracted and updated YAML from LLM response")
            except Exception as e:
                print(f"Error extracting YAML from LLM response: {e}")
    
    # Add the YAML extracting callback
    agent_executor.callbacks.append(YAMLExtractingCallbackHandler())
    
    # Run the agent
    result = agent_executor.invoke({
        "mcp_yaml": mcp_yaml,
        "repo_path": repo_path,
        "input": "Please analyze and fix this MCP YAML. You don't need to write files."
    })
    
    # Get the final YAML from the tracker (more reliable than parsing from output)
    final_yaml = yaml_tracker.get_final_yaml()
    
    # Report tracking information
    tracking_dir = yaml_tracker.tracking_dir
    print(f"YAML tracking history saved to: {tracking_dir}")
    print(f"Total iterations tracked: {yaml_tracker.iteration}")
    
    # Check if validation was successful and handle accordingly
    if not yaml_tracker.validation_success:
        # Create fail folder if it doesn't exist
        fail_dir = Path("/tmp/mcp_validation/failed_validations")
        fail_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate fail filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fail_filename = f"{timestamp}_failed_validation.yaml"
        fail_path = fail_dir / fail_filename
        
        # Write the final unsuccessful YAML
        fail_path.write_text(final_yaml)
        
        # Write debug information
        debug_info = {
            "timestamp": timestamp,
            "iterations": yaml_tracker.iteration,
            "validation_success": False,
            "history_path": str(yaml_tracker.tracking_dir),
            "final_yaml_path": str(fail_path)
        }
        
        debug_path = fail_dir / f"{timestamp}_debug_info.json"
        debug_path.write_text(json.dumps(debug_info, indent=2))
        
        print(f"Validation failed after {yaml_tracker.iteration} iterations. Debug info saved to {debug_path}")
    
    return final_yaml

class YAMLTrackingCallbackHandler(BaseCallbackHandler):
    """Callback handler that writes YAML content to file at the start and during each iteration."""
    
    def __init__(self, initial_yaml: str, base_dir: str = "/tmp/mcp_validation", max_iterations=5):
        """Initialize the callback handler with initial YAML.
        
        Args:
            initial_yaml: The initial YAML content to track
            base_dir: Base directory to store tracking files
            max_iterations: Maximum number of iterations before considering validation failed
        """
        self.current_yaml = initial_yaml
        self.run_id = str(uuid.uuid4())[:8]
        self.iteration = 0
        self.base_dir = Path(base_dir)
        self.tracking_dir = self.base_dir / f"tracking_{self.run_id}"
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
        self.history = []
        self.max_iterations = max_iterations
        self.validation_success = True
        
        # Write initial YAML
        self._write_current_yaml("initial")
        
    def _write_current_yaml(self, stage: str) -> str:
        """Write current YAML to a file with timestamp and stage info.
        
        Args:
            stage: Stage identifier (initial, action, etc.)
            
        Returns:
            str: Path to the written file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{stage}_iteration_{self.iteration}.yaml"
        file_path = self.tracking_dir / filename
        
        # Write the YAML content
        file_path.write_text(self.current_yaml)
        
        # Update history
        self.history.append({
            "timestamp": timestamp,
            "iteration": self.iteration,
            "stage": stage,
            "file_path": str(file_path)
        })
        
        # Write history to JSON
        history_path = self.tracking_dir / "history.json"
        history_path.write_text(json.dumps(self.history, indent=2))
        
        return str(file_path)
    
    def on_agent_start(self, serialized: Dict[str, Any], **kwargs: Any) -> None:
        """Called when agent starts."""
        # Already handled in __init__
        pass
        
    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Called when agent finishes."""
        # Extract YAML from output if possible
        yaml_blocks = re.findall(r'```(?:yaml)?\s*([\s\S]*?)```', finish.return_values.get("output", ""))
        if yaml_blocks:
            self.current_yaml = yaml_blocks[-1]  # Take the last YAML block
            self._write_current_yaml("final")
            
        # If we've reached the end without a successful run, mark as failed
        if self.iteration >= self.max_iterations and not self.validation_success:
            print(f"Agent finished after {self.iteration} iterations without successful validation")
    
    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        """Called when agent takes an action."""
        self.iteration += 1
        
        # Check if we've reached max iterations
        if self.iteration > self.max_iterations:
            print(f"Reached maximum iterations ({self.max_iterations})")
            self.validation_success = False
        
        # If the agent is about to run MCP, ensure we write the latest YAML to the standard location
        if action.tool == "run_mcp":
            # Write the current YAML to a standard location for run_mcp
            standard_file_path = self.base_dir / "current_mcp.yaml"
            standard_file_path.write_text(self.current_yaml)
            print(f"Automatically wrote current YAML to {standard_file_path} before running MCP")
            
            # Also track this auto-write in our history
            self._write_current_yaml("pre_run")
        
        # Write current state for every action
        self._write_current_yaml("action")
        
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when a tool finishes execution."""
        # For run_mcp tool, write the current state with result info
        tool_name = kwargs.get("name")
        if tool_name == "run_mcp":
            try:
                # Try to parse output as JSON
                result = json.loads(output) if isinstance(output, str) else output
                success = result.get("success", False)
                
                # Update validation success status
                if success:
                    self.validation_success = True
                    
                stage = "run_success" if success else "run_failure"
                self._write_current_yaml(stage)
                
                # Check if we've reached max iterations without success
                if not success and self.iteration >= self.max_iterations:
                    print(f"Reached maximum iterations ({self.max_iterations}) without successful validation")
                    self.validation_success = False
            except:
                self._write_current_yaml("run_unknown")
                
    def get_final_yaml(self) -> str:
        """Get the final YAML content after processing.
        
        Returns:
            str: Final YAML content
        """
        return self.current_yaml
