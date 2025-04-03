"""
MCP Validator Module

This module provides agent-based validation functionality for MCP (Model Control Protocol) YAML files.
It uses an LLM agent with tools to validate and correct MCP YAML,
including testing the build and run functionality.
"""

from typing import Dict, Any, Union, Optional
from langchain_core.tools import Tool, StructuredTool
from langchain_community.tools.file_management import ReadFileTool, ListDirectoryTool
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish, LLMResult
from pathlib import Path
import re
import yaml
import uuid
import json
from datetime import datetime
from langchain_openai import ChatOpenAI

from .base_agent import BaseAgent
from src.tools.run_mcps import test_server


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
        # Re-raise the exception instead of returning a fallback response
        print("No fallback handling in run_mcps_wrapper, re-raising exception")
        raise


class ValidatorAgent(BaseAgent):
    """Agent that validates and corrects MCP YAML files."""
    
    def __init__(self):
        """Initialize the validator agent."""
        # No structured output class for validator
        super().__init__()
        
        # Create tools for the agent to use
        self.tools = [
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
        
        # Define system message with properly escaped JSON/config references
        self.system_message = """You are an expert for MCP module functional validation.
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
           - Fix format of config references in entrypoint: ${{{{config.parameterName}}}}
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
        
        # Define human message template
        self.human_message_template = """Please build and run this MCP module definition:

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

{input}"""
    
    def initialize_agent(self):
        """Initialize the agent with tools and prompt templates."""
        # Use the updated base class method which correctly includes agent_scratchpad
        # And now uses tools_llm to avoid conflicts
        self.agent = self.setup_agent_with_tools(
            self.system_message,
            self.human_message_template,
            self.tools
        )
    
    async def ainvoke(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Asynchronously invoke the validator agent.
        
        Args:
            inputs: Dictionary with keys:
                - mcp_yaml: The MCP YAML content to validate
                - input: Additional input for the agent (optional)
                
        Returns:
            The validated and corrected MCP YAML content
        """
        result = await self.agent.ainvoke(inputs)
        
        # The validator often returns a complex object with both text and YAML
        # Extract the YAML content if possible
        if isinstance(result, dict) and "output" in result:
            # Try to extract YAML from the output
            yaml_content = self._extract_yaml_from_text(result["output"])
            if yaml_content:
                return yaml_content
                
        # If it's a string, it might already be YAML or contain YAML
        if isinstance(result, str):
            yaml_content = self._extract_yaml_from_text(result)
            if yaml_content:
                return yaml_content
                
        # Return the original result if we couldn't extract YAML
        return result
    
    def invoke(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Synchronously invoke the validator agent.
        
        Args:
            inputs: Dictionary with keys:
                - mcp_yaml: The MCP YAML content to validate
                - input: Additional input for the agent (optional)
                
        Returns:
            The validated and corrected MCP YAML content
        """
        result = self.agent.invoke(inputs)
        
        # The validator often returns a complex object with both text and YAML
        # Extract the YAML content if possible
        if isinstance(result, dict) and "output" in result:
            # Try to extract YAML from the output
            yaml_content = self._extract_yaml_from_text(result["output"])
            if yaml_content:
                return yaml_content
                
        # If it's a string, it might already be YAML or contain YAML
        if isinstance(result, str):
            yaml_content = self._extract_yaml_from_text(result)
            if yaml_content:
                return yaml_content
                
        # Return the original result if we couldn't extract YAML
        return result
        
    def _extract_yaml_from_text(self, text: str) -> Optional[str]:
        """Extract YAML content from text.
        
        Args:
            text: Text that may contain YAML
            
        Returns:
            The extracted YAML content or None if not found
        """
        if not isinstance(text, str):
            return None
            
        # Try to find YAML content between triple backticks
        yaml_pattern = r"```(?:yaml)?\s*([\s\S]*?)```"
        yaml_matches = re.findall(yaml_pattern, text)
        
        if yaml_matches:
            # Return the first match
            return yaml_matches[0].strip()
            
        # If no YAML blocks found, check if the entire text is valid YAML
        try:
            # Try to parse the text as YAML
            yaml.safe_load(text)
            # If it parses without error, return the text
            return text.strip()
        except:
            # Not valid YAML
            pass
            
        return None


class YAMLTrackingCallbackHandler(BaseCallbackHandler):
    """Callback handler to track changes to YAML throughout agent execution."""
    
    def __init__(self, initial_yaml: str, base_dir: str = "/tmp/mcp_validation", max_iterations=5):
        """Initialize the YAML tracking callback handler.
        
        Args:
            initial_yaml: The initial MCP YAML content
            base_dir: Base directory for storing YAML files
            max_iterations: Maximum number of iterations to track
        """
        super().__init__()
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a session ID
        self.session_id = str(uuid.uuid4())[:8]
        self.session_dir = self.base_dir / f"session_{self.session_id}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Store initial YAML
        self.current_yaml = initial_yaml
        self._write_current_yaml("initial")
        
        # Setup tracking
        self.iterations = 0
        self.max_iterations = max_iterations
        self.changes = []
        self.final_yaml = None
        
        print(f"YAML Tracking initialized for session {self.session_id}")
        
    def _write_current_yaml(self, stage: str) -> str:
        """Write the current YAML to a file with stage information.
        
        Args:
            stage: The stage in the validation process
            
        Returns:
            str: The path to the written file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.session_dir / f"{timestamp}_{stage}.yaml"
        
        try:
            file_path.write_text(self.current_yaml)
            print(f"Saved {stage} YAML to {file_path}")
            
            # Also write to standard validation path
            current_path = self.base_dir / "current_mcp.yaml"
            current_path.write_text(self.current_yaml)
            
            return str(file_path)
        except Exception as e:
            print(f"Error writing YAML: {e}")
            return ""
    
    def on_agent_start(self, serialized: Dict[str, Any], **kwargs: Any) -> None:
        """Handle agent start event."""
        print(f"Validation agent started - session {self.session_id}")
        self._write_current_yaml("agent_start")
    
    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Handle agent finish event."""
        print(f"Validation agent finished - session {self.session_id}")
        
        # Try to extract YAML from the agent's final output
        yaml_content = self._extract_yaml_from_text(finish.return_values.get("output", ""))
        if yaml_content:
            self.current_yaml = yaml_content
            self.final_yaml = yaml_content
            self._write_current_yaml("agent_finish")
            print(f"Final YAML extracted and saved")
    
    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        """Handle agent action event."""
        self.iterations += 1
        print(f"Validation iteration {self.iterations}/{self.max_iterations}: {action.tool}")
        
        # Extract and update YAML if the agent output contains YAML
        yaml_content = self._extract_yaml_from_text(action.log)
        if yaml_content:
            self.current_yaml = yaml_content
            self._write_current_yaml(f"iteration_{self.iterations}")
            print(f"Updated YAML at iteration {self.iterations}")
        
        # Track this change
        self.changes.append({
            "iteration": self.iterations,
            "tool": action.tool,
            "tool_input": action.tool_input,
            "yaml_updated": bool(yaml_content)
        })
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Handle tool end event."""
        # If the tool was run_mcp, log the results
        tool_name = kwargs.get("name", "")
        if tool_name == "run_mcp":
            try:
                result = json.loads(output) if isinstance(output, str) else output
                success = result.get("success", False)
                
                status = "SUCCESS" if success else "FAILED"
                print(f"Run result: {status}")
                
                # Log errors if any
                if not success and "errors" in result:
                    for error in result["errors"]:
                        print(f"Error: {error}")
                        
                # After a run, save the current state with run result
                self._write_current_yaml(f"after_run_{self.iterations}_{status.lower()}")
                
            except Exception as e:
                print(f"Error processing run result: {e}")
    
    def _extract_yaml_from_text(self, text: str) -> str:
        """Extract YAML content from text.
        
        Args:
            text: Text that might contain YAML
            
        Returns:
            str: Extracted YAML content or empty string if none found
        """
        if not text:
            return ""
        
        # Look for YAML content in code blocks
        yaml_blocks = re.findall(r'```(?:yaml)?\s*([\s\S]*?)```', text)
        if yaml_blocks:
            return yaml_blocks[0].strip()
        
        # If no code blocks found, try to extract a yaml structure
        # by looking for lines that start with typical YAML patterns
        lines = text.split('\n')
        yaml_lines = []
        in_yaml_section = False
        
        for line in lines:
            # Check for YAML section headers or list items
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*:', line) or re.match(r'^\s*-\s+', line):
                in_yaml_section = True
                yaml_lines.append(line)
            # Include indented lines that might be part of YAML structure
            elif in_yaml_section and (line.startswith('  ') or not line.strip()):
                yaml_lines.append(line)
            # Break if we encounter non-YAML text after YAML section
            elif in_yaml_section and line.strip() and not line.startswith('  '):
                break
        
        if yaml_lines:
            print(f"Extracted {len(yaml_lines)} lines of YAML from text")
            return '\n'.join(yaml_lines)
        
        return ""
    
    def get_final_yaml(self) -> str:
        """Get the final YAML content.
        
        Returns:
            str: The final validated YAML content
        """
        return self.final_yaml or self.current_yaml


class YAMLExtractingCallbackHandler(BaseCallbackHandler):
    """Callback handler to extract YAML from LLM responses."""
    
    def __init__(self):
        """Initialize the YAML extracting callback handler."""
        super().__init__()
        self.yaml_content = None
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Handle LLM end event to extract YAML content.
        
        Args:
            response: The LLM result object
        """
        if not response.generations:
            return
        
        text = response.generations[0][0].text
        if not text:
            return
        
        # Extract YAML from code blocks
        yaml_match = re.search(r'```(?:yaml)?\s*([\s\S]*?)```', text)
        if yaml_match:
            self.yaml_content = yaml_match.group(1).strip()
            return
        
        # If no code blocks, try to find YAML-like content (key: value pairs)
        yaml_lines = []
        in_yaml = False
        
        for line in text.split('\n'):
            if re.match(r'^[\w-]+:\s*', line.strip()):
                in_yaml = True
                yaml_lines.append(line)
            elif in_yaml and (line.strip().startswith('-') or line.strip().startswith(' ')):
                yaml_lines.append(line)
            elif in_yaml and line.strip() == '':
                yaml_lines.append(line)
            elif in_yaml:
                in_yaml = False
        
        if yaml_lines:
            self.yaml_content = '\n'.join(yaml_lines)


def create_validator_agent(model_name: str = "gpt-4o", temperature: float = 0) -> ValidatorAgent:
    """Create a validator agent instance.
    
    This function maintains backward compatibility with the original implementation.
    
    Args:
        model_name: The OpenAI model to use
        temperature: Temperature setting for the model
        
    Returns:
        ValidatorAgent instance
    """
    validator = ValidatorAgent()
    
    # Set the model name and temperature
    validator.llm = ChatOpenAI(
        model_name=model_name,
        temperature=temperature
    )
    
    # Initialize the agent
    validator.initialize_agent()
    
    return validator


async def run_mcp_validation(mcp_yaml: str, repo_path: str, max_iterations: int = 5) -> Optional[str]:
    """Run MCP validation using the validator agent.
    
    This function validates the provided MCP YAML content and returns
    the corrected version if validation succeeds.
    
    Args:
        mcp_yaml: The MCP YAML content to validate
        repo_path: Path to the repository
        max_iterations: Maximum number of iterations before considering validation failed
        
    Returns:
        Optional[str]: The validated YAML content if successful, None otherwise
    """
    try:
        # Create the validator agent
        validator = create_validator_agent()
        
        # Create a callback handler to track YAML changes
        yaml_tracker = YAMLTrackingCallbackHandler(
            initial_yaml=mcp_yaml,
            base_dir="/tmp/mcp_validation",
            max_iterations=max_iterations
        )
        
        # Write initial YAML to file for validation
        base_dir = Path("/tmp/mcp_validation")
        base_dir.mkdir(parents=True, exist_ok=True)
        yaml_file = base_dir / "current_mcp.yaml"
        yaml_file.write_text(mcp_yaml)
        print(f"Initial YAML written to {yaml_file}")
        
        # Invoke the validator agent with tracking
        try:
            # Create inputs for the validator
            inputs = {
                "mcp_yaml": mcp_yaml,
                "input": f"Repository path: {repo_path}"
            }
            
            print(f"Running validator with parameters: {inputs.keys()}")
            
            # Run the validator with callbacks
            result = await validator.agent.acall(
                inputs, 
                callbacks=[yaml_tracker],
                return_only_outputs=True
            )
            
            print(f"Validator completed with result: {result}")
            
            # Get the final validated YAML
            validated_yaml = yaml_tracker.get_final_yaml()
            if not validated_yaml:
                print("Validation failed to produce valid YAML")
                return None
                
            print(f"Validation complete - YAML length: {len(validated_yaml)}")
            return validated_yaml
            
        except Exception as agent_error:
            print(f"Agent execution error: {agent_error}")
            # If agent execution fails, return the latest YAML from tracker
            return yaml_tracker.get_final_yaml()
        
    except Exception as e:
        print(f"Validation failed: {e}")
        return None
