from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain.tools import Tool
from langchain_community.tools.file_management import ReadFileTool, ListDirectoryTool
from langchain.agents import AgentExecutor, create_openai_functions_agent
import os
import re
from typing import Dict, List, Any

def extract_config_parameters(repo_path: str) -> List[Dict[str, Any]]:
    """Extract configuration parameters from repository code."""
    config_params = []
    
    # Search for environment variables in common files
    env_patterns = [
        r'process\.env\.([A-Z0-9_]+)',  # Node.js
        r'os\.environ\[["\'](.*?)["\']\]',  # Python
        r'env\(["\']([A-Z0-9_]+)["\']\)',  # Various frameworks
        r'getenv\(["\']([A-Z0-9_]+)["\']\)'  # PHP/Python
    ]
    
    # Check for .env.example or similar files
    env_files = ['.env.example', '.env.sample', '.env.template', '.env.defaults']
    for env_file in env_files:
        env_path = os.path.join(repo_path, env_file)
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split('=', 1)
                            if len(parts) == 2:
                                param_name = parts[0].strip()
                                param_value = parts[1].strip()
                                
                                param_type = 'string'
                                if param_value.lower() in ('true', 'false'):
                                    param_type = 'boolean'
                                elif param_value.isdigit():
                                    param_type = 'number'
                                
                                config_params.append({
                                    'name': param_name,
                                    'type': param_type,
                                    'description': f"Configuration parameter from {env_file}",
                                    'default': param_value if param_value else None,
                                    'required': False
                                })
            except Exception as e:
                print(f"Error parsing {env_file}: {e}")
    
    # Check for config files
    config_files = ['config.js', 'config.ts', 'config.json', 'config.py', 'settings.py']
    for config_file in config_files:
        for root, _, files in os.walk(repo_path):
            if config_file in files:
                config_path = os.path.join(root, config_file)
                try:
                    with open(config_path, 'r') as f:
                        content = f.read()
                        for pattern in env_patterns:
                            for match in re.finditer(pattern, content):
                                param_name = match.group(1)
                                if not any(p['name'] == param_name for p in config_params):
                                    config_params.append({
                                        'name': param_name,
                                        'type': 'string',  # Default to string
                                        'description': f"Environment variable found in {os.path.relpath(config_path, repo_path)}",
                                        'required': False
                                    })
                except Exception as e:
                    print(f"Error parsing {config_path}: {e}")
    
    # Check for command line arguments
    cli_files = ['main.py', 'cli.py', 'index.js', 'server.js', 'app.js']
    cli_patterns = [
        r'parser\.add_argument\(["\']--([a-zA-Z0-9_-]+)["\']',  # Python argparse
        r'yargs\.option\(["\']([a-zA-Z0-9_-]+)["\']',  # Node.js yargs
        r'program\.option\(["\']--([a-zA-Z0-9_-]+)',  # Commander.js
    ]
    
    for cli_file in cli_files:
        for root, _, files in os.walk(repo_path):
            if cli_file in files:
                cli_path = os.path.join(root, cli_file)
                try:
                    with open(cli_path, 'r') as f:
                        content = f.read()
                        for pattern in cli_patterns:
                            for match in re.finditer(pattern, content):
                                param_name = match.group(1)
                                if not any(p['name'] == param_name for p in config_params):
                                    config_params.append({
                                        'name': param_name.replace('-', '_'),
                                        'type': 'string',  # Default to string
                                        'description': f"Command line argument found in {os.path.relpath(cli_path, repo_path)}",
                                        'required': False
                                    })
                except Exception as e:
                    print(f"Error parsing {cli_path}: {e}")
    
    return config_params

def create_config_agent():
    """Create an agent to generate the config section of the run part of the MCP YAML file."""
    tools = [
        Tool(
            name="ReadFile",
            description="Read a file from the repository to analyze its content.",
            func=ReadFileTool().run
        ),
        Tool(
            name="ListDirectory",
            description="List contents of a repository directory to discover configuration files.",
            func=ListDirectoryTool().run
        ),
        Tool(
            name="ExtractConfigParameters",
            description="Extract configuration parameters from repository code.",
            func=lambda repo_path: extract_config_parameters(repo_path)
        )
    ]
    
    system_message = """You are an expert at identifying configuration parameters for MCP modules.
    Your task is to generate a properly formatted config section for the run part of an MCP YAML file.
    
    Focus ONLY on the config section, which defines all configurable options for the module.
    Each parameter should follow this format:
      parameterName:
        type: string|number|boolean|object|array  # Required, data type of this parameter
        description: "Clear explanation of what this parameter does"  # Required
        default: value  # Optional, default value if not explicitly configured
        required: true|false  # Optional, whether this parameter must be provided
        secret: true|false  # Optional, whether this contains sensitive data
        enum: [value1, value2]  # Optional, list of allowed values if applicable
    
    IMPORTANT - Config Parameter Guidelines:
    - ONLY include config parameters that are ACTUALLY USED by the application
    - Parameters MUST be verifiably referenced in environment variables or entrypoint files
    - ALWAYS verify that each parameter has a clear reference in the code before including it
    - Derive parameters from actual command-line arguments or environment variables found in the repository
    - DO NOT add generic parameters like "apiEndpoint", "port", or "logLevel" unless you find evidence they are actually used
    - If uncertain whether a parameter exists, DO NOT include it
    - An empty config object is better than one with made-up parameters
    
    Analyze the repository carefully to identify genuine configuration parameters from:
    - Environment variables referenced in code
    - Command line arguments specifically defined in entrypoint files
    - Configuration files with clear usage patterns
    
    Use the tools provided to:
    1. List directories to find key configuration files
    2. Read files to extract configurable parameters
    3. Use the extraction tool to automatically discover common configuration patterns
    4. Cross-reference discovered parameters with actual usage in code
    """
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "Generate the config section for the run part of an MCP module based on this analysis:\n\n"
                "Repository URL: {repository_url}\n"
                "Repository Path: {repo_path}\n"
                "Analysis:\n{analysis}\n\n"
                "Please generate ONLY the config section with proper formatting.\n"
                "If no clear configuration parameters are found, return an empty config object: config: {{}}"),
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