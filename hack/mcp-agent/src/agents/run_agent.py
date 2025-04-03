"""
Run Agent Module

This module provides an agent for generating the run section of MCP YAML files,
including configuration parameters, entrypoint command, and environment variables.
"""

import re
from langchain.tools import Tool
from langchain_community.tools.file_management import ReadFileTool, ListDirectoryTool
from typing import Dict, List, Any, Union, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from .base_agent import BaseAgent

class Property(BaseModel):
    """Property model that matches the Go struct definition."""
    type: str = Field(description="The type of the property (string, number, boolean, etc.)")
    required: bool = Field(description="Whether the property is required")
    default: Optional[Union[str, int, bool, float]] = Field(description="Default value if not provided", default=None)
    enum: Optional[Union[List[str], None]] = Field(description="A list of possible values", default=None)
    hidden: Optional[bool] = Field(description="Whether the property should be hidden in the UI", default=None)
    secret: Optional[bool] = Field(description="Whether the property contains sensitive information", default=None)
    label: Optional[str] = Field(description="A display label for the property", default=None)
    min: Optional[int] = Field(description="Minimum value for numeric properties", default=None)
    max: Optional[int] = Field(description="Maximum value for numeric properties", default=None)
    pattern: Optional[str] = Field(description="A regex pattern for validation", default=None)
    example: Optional[Union[str, int, bool, float]] = Field(description="An example value", default=None)
    env: Optional[str] = Field(description="Environment variable name to map this config property to", default=None)
    arg: Optional[str] = Field(description="Command line argument to pass this config property as", default=None)

class RunResponse(BaseModel):
    """Structured response for run section that matches the Go struct definition."""
    config: Dict[str, Property] = Field(
        description="Configuration parameters that can be set when deploying the module",
        default_factory=dict
    )
    entrypoint: List[str] = Field(
        description="The command to start the module, referencing config parameters",
        default_factory=lambda: ["node", "index.js"]
    )
    env: Dict[str, Property] = Field(
        description="Environment variables to set, typically referencing config parameters",
        default_factory=dict
    )
    
    model_config = {
        "json_schema_extra": {
            "required": []  # Make all fields optional for the OpenAI schema
        }
    }

class RunAgent(BaseAgent):
    """Agent for generating the run section of an MCP YAML file."""
    
    def __init__(self):
        """Initialize the run agent."""
        # Initialize base agent with RunResponse for structured output
        super().__init__(structured_output_class=RunResponse)
        
        # Create tools for the agent to use
        self.tools = [
            Tool(
                name="ReadFile",
                description="Read a file from the repository to analyze its content.",
                func=ReadFileTool().run
            ),
            Tool(
                name="ListDirectory",
                description="List contents of a repository directory to discover important files with run configuration.",
                func=ListDirectoryTool().run
            ),
        ]
        
        # Define system message with properly escaped JSON examples
        self.system_message = """You are an expert at defining run configurations for MCP modules.
Your task is to generate the run section of an MCP YAML file following the specified format.

## PROPERTY STRUCTURE
Each property in config or env sections must have these fields:
- type (string): The data type (string, number, boolean)
- required (boolean): Whether the property is required
- default (any, optional): Default value if not provided
- example (any, optional): An example value
- label (string, optional): User-friendly display label
- secret (boolean, optional): Set to true for sensitive information like API keys
- env (string, optional): Environment variable name to map this config property to
- arg (string, optional): Command line argument to pass this config property as

## FORMAT EXAMPLE
```yaml
run:
  config:
    apiKey:
      type: string
      required: true
      default: none
      example: your_api_key
      label: API Key
      secret: true
      env: API_KEY
    appId:
      type: string
      required: true 
      default: none
      example: your_app_id
      label: Application ID
      secret: true
      arg: --app-id
  entrypoint:
  - node
  - ./dist/index.js
```

## KEY REQUIREMENTS
1. Only 'node' is available in the runtime environment. No npm, pnpm, or other package managers.
2. For config properties:
   - Use 'env' field to map directly to environment variables
   - Use 'arg' field for command line arguments
3. Mark credentials with secret: true (API keys, tokens, passwords)
4. Config parameters should be used in entrypoint or as environment variables

## ANALYSIS METHODOLOGY
1. List the directory structure to understand the project
2. **Start by checking any README.md or similar documentation files for run instructions**
3. Examine package.json, .env files, and main code files
4. Identify configuration parameters and environment variables
5. Determine the main entry point file

## ANALYZE THE REPOSITORY FOR
1. Language and framework (Node.js, Python, etc.)
2. Environment variables used in the code
3. Configuration files and parameters
4. Main entrypoint files
5. Command line arguments
6. **README.md files that explain how to run the application**

Provide a complete run configuration with all necessary parameters based on your analysis."""
        
        # Define human message template (no escaping needed here since we don't have JSON examples)
        self.human_message_template = """Analyze this repository and generate a run configuration:

Repository: {repository_url}
Path: {repo_path}
{name_section}

## FORMAT EXAMPLE
```yaml
run:
  config:
    apiKey:
      type: string
      required: true
      default: none
      example: your_api_key
      label: API Key
      secret: true
      env: API_KEY
    appId:
      type: string
      required: true
      default: none      
      example: your_app_id
      label: Application ID
      secret: true
      arg: --app-id
  entrypoint:
  - node
  - ./dist/index.js
```

## INSTRUCTIONS
1. Explore the repository at {repo_path} using the ListDirectory and ReadFile tools
2. **Start by looking for and reading any README.md or similar documentation files as they often contain crucial setup and run instructions**
3. Focus on discovering:
   - Configuration parameters needed to run the application
   - Environment variables used in the code
   - The main entry point file
   - Command line arguments

Remember:
- Use 'node' directly (no npm/pnpm)
- Include 'env' field to map config properties to environment variables 
- Include 'arg' field for command line arguments
- Mark credentials as secret

Your response must follow the exact format shown above.

## ADDITIONAL CONTEXT
{analysis}"""
        
        # Set up a direct LLM model for post-processing the tool results
        self.post_processing_llm = None
    
    def initialize_agent(self):
        """Initialize the agent with tools and prompt templates."""
        print("Initializing run agent...")
        # Set up the agent executor
        self.agent = self.setup_agent_with_tools(
            self.system_message,
            self.human_message_template,
            self.tools
        )
        
        # Set up a post-processing model with structured output
        self.post_processing_llm = ChatOpenAI(
            model_name=self.model_name,
            temperature=self.temperature
        ).with_structured_output(RunResponse, method="function_calling")
        
        # Validate that the structured_output_class is set correctly
        if not self.structured_output_class or self.structured_output_class != RunResponse:
            print("WARNING: structured_output_class is not set or doesn't match RunResponse, fixing it now")
            self.structured_output_class = RunResponse
        
        print(f"Run agent initialized with tools and structured output class: {self.structured_output_class.__name__}")
    
    def _validate_and_fix_entrypoint(self, response: RunResponse) -> RunResponse:
        """Validate the entrypoint doesn't use npm or pnpm and fix if needed.
        
        Args:
            response: The RunResponse to validate
            
        Returns:
            The validated and potentially fixed RunResponse
        """
        # Exit early if response is None
        if response is None:
            return response
            
        # Check if the entrypoint uses npm or pnpm
        if len(response.entrypoint) > 0:
            first_command = response.entrypoint[0].lower()
            if first_command in ["npm", "pnpm", "yarn"]:
                print(f"WARNING: Entrypoint uses {first_command}, which is not available. Attempting to fix...")
                
                # Try to convert npm/pnpm commands to direct node execution
                if len(response.entrypoint) > 1:
                    npm_command = response.entrypoint[1].lower()
                    
                    # Common mapping of npm commands to direct node execution
                    if npm_command in ["start", "run", "run-script"]:
                        # Try to find the main file from config section if available
                        main_file = "index.js"  # Default guess if not specified
                        
                        # Check if there's a main_file or entry_point in config
                        for key in ["main_file", "entry_point", "main", "entry"]:
                            if key in response.config:
                                main_file = response.config[key].default or main_file
                                break
                        
                        # Replace with direct node execution
                        response.entrypoint = ["node", main_file]
                        print(f"Fixed entrypoint to: {response.entrypoint}")
                
        # Return the response as-is without adding default values
        return response
        
    async def ainvoke(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Asynchronously invoke the run agent.
        
        Args:
            inputs: Dictionary with keys:
                - repository_url: Repository URL
                - repo_path: Path to repository on disk
                - analysis: Repository analysis
                
        Returns:
            The run section as structured output (RunResponse)
        """
        print("Run agent ainvoke called with inputs:", inputs.keys())
        
        # Remove the problematic import attempts
        # Get a local reference to the function
        extract_yaml_func = globals().get('extract_yaml_from_response')
        if not extract_yaml_func:
            # If not available globally, assign it directly from this module
            import sys
            extract_yaml_func = getattr(sys.modules[__name__], 'extract_yaml_from_response')
        
        # Initialize the agent if needed
        if not hasattr(self, 'agent') or self.agent is None:
            print("Agent not initialized, initializing now")
            self.initialize_agent()
            
        try:
            # Debug the inputs to make sure they contain what we expect
            repo_path = inputs.get("repo_path", "")
            repo_url = inputs.get("repository_url", "")
            analysis = inputs.get("analysis", "")
            
            print(f"Repository URL: {repo_url}")
            print(f"Repository Path: {repo_path}")
            print(f"Analysis excerpt: {analysis[:200]}..." if analysis and len(analysis) > 200 else analysis)
            
            # Validate repository path exists and is accessible
            import os
            if not repo_path or not os.path.exists(repo_path):
                print(f"WARNING: Repository path does not exist or is not accessible: {repo_path}")
                if not repo_path:
                    print("Repository path is empty")
                elif not os.path.exists(repo_path):
                    print(f"Path {repo_path} does not exist")
                    # Try to list parent directory
                    parent_dir = os.path.dirname(repo_path)
                    if os.path.exists(parent_dir):
                        print(f"Parent directory {parent_dir} exists, listing contents:")
                        try:
                            print(os.listdir(parent_dir))
                        except Exception as e:
                            print(f"Error listing parent directory: {e}")
                
                # Raise an error instead of using a fallback approach
                raise ValueError(f"Repository path is invalid or inaccessible: {repo_path}")
            else:
                print(f"Repository path exists: {repo_path}")
                try:
                    print(f"Directory contents: {os.listdir(repo_path)[:10]}")
                    
                    # Create custom tools with repo_path as the root dir
                    from langchain_community.tools.file_management import ReadFileTool, ListDirectoryTool
                    
                    try:
                        # First test if we can list the directory with the tools
                        list_tool = ListDirectoryTool(root_dir=repo_path)
                        read_tool = ReadFileTool(root_dir=repo_path)
                        
                        print("Testing directory listing with tool...")
                        try:
                            dir_result = list_tool.run(repo_path)
                            print(f"Directory listing successful: {dir_result[:200]}..." if len(dir_result) > 200 else dir_result)
                        except Exception as e:
                            print(f"Directory listing with tool failed: {e}")
                        
                        # Update tools in the agent
                        self.tools = [
                            Tool(
                                name="ReadFile",
                                description=f"Read file from repository. Provide path relative to {repo_path}.",
                                func=read_tool.run
                            ),
                            Tool(
                                name="ListDirectory",
                                description=f"List directory contents in repository. Provide path relative to {repo_path}.",
                                func=list_tool.run
                            ),
                        ]
                        
                        # Reinitialize the agent with updated tools
                        self.agent = self.setup_agent_with_tools(
                            self.system_message,
                            self.human_message_template,
                            self.tools
                        )
                        
                        print(f"Updated tools to use repository path: {repo_path}")
                    except Exception as tool_error:
                        print(f"Error setting up tools with repository path: {tool_error}")
                        import traceback
                        traceback.print_exc()
                        
                        # Raise the exception instead of falling back to basic tools
                        raise ValueError(f"Unable to set up tools with repository path {repo_path}: {str(tool_error)}")
                except Exception as e:
                    print(f"Error initializing tools: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Calculate an appropriate maximum tokens based on analysis size
            # to prevent exceeding the LLM's token limit
            analysis_tokens = len(analysis) // 4  # rough estimate of tokens
            max_tool_tokens = max(3000, min(8000, 15000 - analysis_tokens))
            print(f"Estimated analysis tokens: {analysis_tokens}, max tool tokens: {max_tool_tokens}")
            
            # We'll generate a simpler response if working with limited tokens
            simplified_mode = analysis_tokens > 10000
            if simplified_mode:
                print("Using simplified mode due to large analysis")
                
            # Create a modified inputs dictionary with added instructions for the agent
            modified_inputs = inputs.copy()
            modified_inputs["explicit_instructions"] = (
                "The repository may be large, so focus on identifying the main entry point and "
                "essential configuration parameters. Look for package.json, .env files, and main code files first. "
                "If you can't access or read files directly, use the analysis to make educated guesses."
            )
            
            # First, get results from the agent using tools
            print("Invoking agent with tools...")
            agent_response = await self.agent.ainvoke(modified_inputs)
            print(f"Run agent received response type: {type(agent_response)}")
            print(f"Response preview: {str(agent_response)[:300]}...")
            
            # If the agent returned a RunResponse directly, validate and return it
            if isinstance(agent_response, RunResponse):
                print("Agent returned a RunResponse directly")
                return self._validate_and_fix_entrypoint(agent_response)
            
            # Otherwise, parse the agent response into a RunResponse using the post-processing LLM
            # First, ensure the post-processing LLM is initialized
            if not self.post_processing_llm:
                print("Initializing post-processing LLM")
                
                        
                # Use either the standard structured output method or create a normalizing parser
                self.post_processing_llm = ChatOpenAI(
                    model_name=self.model_name,
                    temperature=self.temperature
                ).with_structured_output(
                    RunResponse,
                    method="function_calling"
                )
            
            # If agent_response is a dictionary, try to normalize and convert directly first
            if isinstance(agent_response, dict):
                try:
                    print("Agent response is a dictionary, trying to normalize and convert directly")
                    
                    # Check if the agent_response has an 'output' field with YAML content
                    if 'output' in agent_response:
                        print("Agent response contains 'output' field, checking for YAML content")
                        yaml_content = extract_yaml_func(agent_response['output'])
                        if yaml_content:
                            import yaml
                            try:
                                print(f"Found YAML in 'output' field: {yaml_content[:100]}...")
                                yaml_dict = yaml.safe_load(yaml_content)
                                
                                # Check if it's a dictionary with valid sections
                                if isinstance(yaml_dict, dict):
                                    # If it has a "run" key, extract it
                                    if "run" in yaml_dict:
                                        yaml_dict = yaml_dict["run"]
                                        print(f"Extracted 'run' section from YAML")
                                    
                                    # Create response from the YAML dictionary
                                    normalized_data = self.normalize_property_fields(yaml_dict)
                                    
                                    # Ensure all required sections are present
                                    if "config" not in normalized_data:
                                        normalized_data["config"] = {}
                                    if "entrypoint" not in normalized_data:
                                        normalized_data["entrypoint"] = ["node", "index.js"]
                                    if "env" not in normalized_data:
                                        normalized_data["env"] = {}
                                    
                                    # Try to create RunResponse
                                    try:
                                        print("Creating RunResponse from YAML")
                                        run_response = RunResponse(**normalized_data)
                                        print("Successfully created RunResponse from YAML")
                                        return self._validate_and_fix_entrypoint(run_response)
                                    except Exception as e:
                                        print(f"Failed to create RunResponse from YAML: {e}")
                                        raise ValueError(f"Failed to create RunResponse from YAML: {e}")
                            except yaml.YAMLError as e:
                                print(f"Error parsing YAML from output field: {e}")
                                raise ValueError(f"Error parsing YAML from output field: {e}")
                    
                    # If no YAML found in output field, try direct conversion of the dictionary
                    extract_response = agent_response.get("run", agent_response)
                    normalized_data = self.normalize_property_fields(extract_response)
                    
                    # Ensure all required sections are present
                    if "config" not in normalized_data:
                        normalized_data["config"] = {}
                    if "entrypoint" not in normalized_data:
                        normalized_data["entrypoint"] = ["node", "index.js"]
                    if "env" not in normalized_data:
                        normalized_data["env"] = {}
                    
                    # Try to create RunResponse directly
                    try:
                        print("Creating RunResponse from dictionary directly")
                        run_response = RunResponse(**normalized_data)
                        print("Successfully created RunResponse")
                        return self._validate_and_fix_entrypoint(run_response)
                    except Exception as e:
                        print(f"Failed to create RunResponse from dictionary: {e}")
                        raise ValueError(f"Failed to create RunResponse from dictionary: {e}")
                except Exception as e:
                    print(f"Error during dictionary normalization: {e}")
                    raise ValueError(f"Error during dictionary normalization: {e}")
            
            # If agent_response is a string, try to extract YAML
            elif isinstance(agent_response, str):
                yaml_content = extract_yaml_func(agent_response)
                if yaml_content:
                    import yaml
                    try:
                        # Parse the YAML
                        agent_response_dict = yaml.safe_load(yaml_content)
                        
                        if isinstance(agent_response_dict, dict):
                            # If it has a "run" key, extract it
                            if "run" in agent_response_dict:
                                agent_response_dict = agent_response_dict["run"]
                            
                            # Normalize and ensure required sections
                            normalized_data = self.normalize_property_fields(agent_response_dict)
                            if "config" not in normalized_data:
                                normalized_data["config"] = {}
                            if "entrypoint" not in normalized_data:
                                normalized_data["entrypoint"] = ["node", "index.js"]
                            if "env" not in normalized_data:
                                normalized_data["env"] = {}
                            
                            # Try to create RunResponse
                            try:
                                run_response = RunResponse(**normalized_data)
                                return self._validate_and_fix_entrypoint(run_response)
                            except Exception as e:
                                print(f"Failed to create RunResponse from string YAML: {e}")
                                raise ValueError(f"Failed to create RunResponse from string YAML: {e}")
                    except yaml.YAMLError as e:
                        print(f"Error parsing YAML from string: {e}")
                        raise ValueError(f"Error parsing YAML from string: {e}")
            
            # If we get here, we couldn't create a RunResponse
            error_message = "Failed to extract valid YAML or create RunResponse from agent output"
            print(f"Error: {error_message}")
            raise ValueError(error_message)
            
        except Exception as e:
            print(f"Error in run_agent.ainvoke: {e}")
            import traceback
            traceback.print_exc()
            
            # Re-raise the exception instead of creating a fallback
            print("No fallback handling, re-raising exception")
            raise

    def normalize_property_fields(self, data):
        """Normalize property field names to match the expected format in the Pydantic model.
        
        Args:
            data: Dictionary representing the run section
            
        Returns:
            Dictionary with normalized field names
        """
        if not isinstance(data, dict):
            return data
            
        # Create a new dictionary to avoid modifying the input
        result = {}
        
        # Process top-level fields
        for key, value in data.items():
            if key == "config" and isinstance(value, dict):
                # Process config section
                normalized_config = {}
                for config_key, config_value in value.items():
                    if isinstance(config_value, dict):
                        # Normalize property fields
                        normalized_prop = {}
                        for prop_key, prop_value in config_value.items():
                            # Convert keys like 'Type' to 'type'
                            normalized_key = prop_key.lower() if prop_key in ['Type', 'Required', 'Default', 'Secret', 'Label', 'Hidden', 'Min', 'Max', 'Pattern', 'Format', 'Example', 'Env', 'Arg'] else prop_key
                            normalized_prop[normalized_key] = prop_value
                        normalized_config[config_key] = normalized_prop
                    else:
                        normalized_config[config_key] = config_value
                result[key] = normalized_config
            elif key == "env" and isinstance(value, dict):
                # Process env section
                normalized_env = {}
                for env_key, env_value in value.items():
                    if isinstance(env_value, dict):
                        # Normalize property fields
                        normalized_prop = {}
                        for prop_key, prop_value in env_value.items():
                            # Convert keys like 'Type' to 'type'
                            normalized_key = prop_key.lower() if prop_key in ['Type', 'Required', 'Default', 'Secret', 'Label', 'Hidden', 'Min', 'Max', 'Pattern', 'Format', 'Example', 'Env', 'Arg'] else prop_key
                            normalized_prop[normalized_key] = prop_value
                        normalized_env[env_key] = normalized_prop
                    else:
                        normalized_env[env_key] = env_value
                result[key] = normalized_env
            else:
                # Preserve other fields
                result[key] = value
                
        return result
        
    def invoke(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Synchronously invoke the run agent.
        
        Args:
            inputs: Dictionary with keys:
                - repository_url: Repository URL
                - repo_path: Path to repository on disk
                - analysis: Repository analysis
                
        Returns:
            The run section as structured output (RunResponse)
        """
        # For consistency, use the async implementation through an event loop
        import asyncio
        
        # Create an event loop if one doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        # Run the async method
        return loop.run_until_complete(self.ainvoke(inputs))


def extract_yaml_from_response(response_text: str) -> str:
    """Extract YAML content from a string response.
    
    Args:
        response_text: The text response to extract YAML from
        
    Returns:
        The extracted YAML content or an empty string
    """
    # Convert to string if not already
    if not isinstance(response_text, str):
        response_text = str(response_text)
    
    # Look for YAML content between ```yaml and ``` markers - most reliable method
    yaml_pattern = r'```(?:yaml)?\s*([\s\S]*?)```'
    yaml_matches = re.findall(yaml_pattern, response_text)
    
    if yaml_matches:
        yaml_content = yaml_matches[0].strip()
        print(f"Found YAML in code block: {yaml_content[:100]}...")
        return yaml_content
    
    # Look for a run section with proper indentation
    run_pattern = r'(?:^|\n)run:\s*\n((?:\s+.*\n)+)'
    run_matches = re.findall(run_pattern, response_text)
    if run_matches:
        run_yaml = "run:\n" + run_matches[0]
        print(f"Found run section: {run_yaml[:100]}...")
        return run_yaml.strip()
    
    # Last resort: look for any YAML-like structure
    yaml_structure_pattern = r'(?:^|\n)([a-zA-Z_][a-zA-Z0-9_]*:\s*(?:\n\s+[a-zA-Z_][a-zA-Z0-9_]*:[\s\S]*?)+)'
    yaml_matches = re.findall(yaml_structure_pattern, response_text)
    if yaml_matches:
        yaml_content = '\n'.join(yaml_matches).strip()
        print(f"Found YAML-like structure: {yaml_content[:100]}...")
        return yaml_content
    
    return ""


def create_run_agent(model_name: str = "gpt-4o-mini", temperature: float = 0) -> RunAgent:
    """Create a run agent instance.
    
    This function maintains backward compatibility with the original implementation.
    
    Args:
        model_name: The OpenAI model to use
        temperature: Temperature setting for the model
        
    Returns:
        RunAgent instance
    """
    print(f"Creating RunAgent with model: {model_name}, temperature: {temperature}")
    run_agent = RunAgent()
    
    # Set the model name and temperature
    run_agent.model_name = model_name
    run_agent.temperature = temperature
    run_agent.llm = ChatOpenAI(
        model_name=model_name,
        temperature=temperature
    )
    
    # Initialize the agent
    run_agent.initialize_agent()
    
    print("RunAgent initialized successfully")
    return run_agent