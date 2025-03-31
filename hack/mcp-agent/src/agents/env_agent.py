from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain.tools import Tool
from langchain_community.tools.file_management import ReadFileTool, ListDirectoryTool
from langchain.agents import AgentExecutor, create_openai_functions_agent
import os
import re
from typing import Dict, List, Any

def extract_env_variables(repo_path: str) -> List[Dict[str, Any]]:
    """Extract environment variables from repository code."""
    potential_env_vars = []
    verified_env_vars = []
    
    # Common patterns for env variable usage
    env_patterns = [
        (r'process\.env\.([A-Z0-9_]+)', 'JavaScript/TypeScript'),
        (r'os\.environ\[["\'](.*?)["\']\]', 'Python'),
        (r'getenv\(["\']([A-Z0-9_]+)["\']\)', 'PHP/Python'),
        (r'ENV\s+([A-Z0-9_]+)', 'Docker')
    ]
    
    # Define entrypoint files for tracking which vars are automatically verified
    entrypoint_files = ['Dockerfile', 'docker-entrypoint.sh', 'entrypoint.sh', 'run.sh', 'start.sh']
    
    # Check for .env.example or similar files
    env_files = ['.env.example', '.env.sample', '.env.template', '.env.defaults', '.env']
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
                                var_name = parts[0].strip()
                                var_value = parts[1].strip() if len(parts) > 1 else ""
                                
                                # Determine if variable is sensitive
                                is_secret = any(sensitive in var_name.lower() for sensitive in 
                                              ["token", "secret", "password", "key", "auth", "credential"])
                                
                                if not any(v['name'] == var_name for v in potential_env_vars):
                                    potential_env_vars.append({
                                        'name': var_name,
                                        'description': f"Environment variable from {env_file}",
                                        'value': var_value,
                                        'required': False,
                                        'secret': is_secret,
                                        'source': env_path
                                    })
            except Exception as e:
                print(f"Error parsing {env_file}: {e}")
    
    # Search through code files for environment variable usage
    file_extensions = ['.js', '.ts', '.py', '.php', '.java', '.go', '.rb', '.sh']
    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_name = os.path.basename(file_path)
            
            # Check if this is an entrypoint file (special handling)
            is_entrypoint = file_name in entrypoint_files
            
            if is_entrypoint or any(file.endswith(ext) for ext in file_extensions):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        # For entrypoint files, use patterns to find env vars in shell scripts
                        if is_entrypoint:
                            shell_patterns = [
                                r'\$\{?([A-Z0-9_]+)\}?',  # ${VAR} or $VAR format in shell scripts
                                r'ENV\s+([A-Z0-9_]+)',    # ENV VAR in Dockerfile
                                r'ARG\s+([A-Z0-9_]+)',    # ARG VAR in Dockerfile
                                r'--env\s+([A-Z0-9_]+)',  # --env VAR in docker run
                                r'-e\s+([A-Z0-9_]+)',     # -e VAR in docker run
                            ]
                            
                            for pattern in shell_patterns:
                                for match in re.finditer(pattern, content):
                                    var_name = match.group(1)
                                    
                                    # Skip if already found
                                    if any(v['name'] == var_name for v in potential_env_vars):
                                        continue
                                    
                                    # Determine if variable is sensitive
                                    is_secret = any(sensitive in var_name.lower() for sensitive in 
                                                  ["token", "secret", "password", "key", "auth", "credential"])
                                    
                                    potential_env_vars.append({
                                        'name': var_name,
                                        'description': f"Environment variable used in {os.path.relpath(file_path, repo_path)}",
                                        'required': False,
                                        'secret': is_secret,
                                        'source': file_path,
                                        'entrypoint': True  # Mark as used in entrypoint
                                    })
                        
                        # Regular code file patterns
                        for pattern, language in env_patterns:
                            for match in re.finditer(pattern, content):
                                var_name = match.group(1)
                                
                                # Skip if already found
                                if any(v['name'] == var_name for v in potential_env_vars):
                                    continue
                                
                                # Determine if variable is sensitive
                                is_secret = any(sensitive in var_name.lower() for sensitive in 
                                              ["token", "secret", "password", "key", "auth", "credential"])
                                
                                potential_env_vars.append({
                                    'name': var_name,
                                    'description': f"Environment variable used in {os.path.relpath(file_path, repo_path)} ({language})",
                                    'required': False,
                                    'secret': is_secret,
                                    'source': file_path,
                                    'entrypoint': is_entrypoint  # Mark as used in entrypoint if this is an entrypoint file
                                })
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    # Check Dockerfile for ENV instructions
    dockerfile_path = os.path.join(repo_path, "Dockerfile")
    if os.path.exists(dockerfile_path):
        try:
            with open(dockerfile_path, 'r') as f:
                content = f.read()
                env_pattern = r'ENV\s+([A-Z0-9_]+)[\s=]'
                for match in re.finditer(env_pattern, content):
                    var_name = match.group(1)
                    
                    # Skip if already found
                    if any(v['name'] == var_name for v in potential_env_vars):
                        continue
                    
                    potential_env_vars.append({
                        'name': var_name,
                        'description': f"Environment variable defined in Dockerfile",
                        'required': False,
                        'secret': False,
                        'source': dockerfile_path,
                        'entrypoint': True  # Mark as used in entrypoint
                    })
        except Exception as e:
            print(f"Error parsing Dockerfile: {e}")
    
    # Verify environment variables by checking if they are used in code or entrypoint files
    for env_var in potential_env_vars:
        # Variables found in entrypoint files are automatically verified
        if env_var.get('entrypoint', False):
            # Clean up temporary fields
            if 'entrypoint' in env_var:
                del env_var['entrypoint']
            if 'source' in env_var:
                del env_var['source']
            verified_env_vars.append(env_var)
            continue
        
        # For variables not in entrypoint files, we need to verify they're used in the code
        var_name = env_var['name']
        source_file = env_var.get('source', '')
        
        # Check for usage in code files
        usages_found = False
        for root, _, files in os.walk(repo_path):
            if usages_found:
                break
                
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip the source file itself if it's an .env file
                if file_path == source_file and any(env_file in source_file for env_file in env_files):
                    continue
                
                if any(file.endswith(ext) for ext in file_extensions):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                            # Look for patterns specific to file type
                            if file.endswith('.py'):
                                patterns = [
                                    f"os.environ\\[\"{var_name}\"\\]",
                                    f"os.environ\\['{var_name}'\\]",
                                    f"getenv\\(\"{var_name}\"\\)",
                                    f"getenv\\('{var_name}'\\)"
                                ]
                            elif file.endswith(('.js', '.ts')):
                                patterns = [
                                    f"process.env.{var_name}",
                                    f"env\\(\"{var_name}\"\\)",
                                    f"env\\('{var_name}'\\)"
                                ]
                            elif file.endswith('.sh') or file in entrypoint_files:
                                patterns = [
                                    f"\\${var_name}",
                                    f"\\${{var_name}}"
                                ]
                            else:
                                patterns = [var_name]
                                
                            for pattern in patterns:
                                if re.search(pattern, content):
                                    usages_found = True
                                    break
                                    
                            if usages_found:
                                break
                                
                    except Exception as e:
                        print(f"Error checking usage in {file_path}: {e}")
                        
                if usages_found:
                    break
        
        if usages_found:
            # Clean up temporary fields
            if 'entrypoint' in env_var:
                del env_var['entrypoint']
            if 'source' in env_var:
                del env_var['source']
            verified_env_vars.append(env_var)
    
    return verified_env_vars

def create_env_agent():
    """Create an agent to generate the env section of the run part of the MCP YAML file."""
    tools = [
        Tool(
            name="ReadFile",
            description="Read a file from the repository to analyze its content.",
            func=ReadFileTool().run
        ),
        Tool(
            name="ListDirectory",
            description="List contents of a repository directory to discover files that might use environment variables.",
            func=ListDirectoryTool().run
        ),
        Tool(
            name="ExtractEnvVariables",
            description="Extract environment variables from repository code.",
            func=lambda repo_path: extract_env_variables(repo_path)
        )
    ]
    
    system_message = """You are an expert at defining environment variables for MCP modules.
    Your task is to generate a properly formatted env section for the run part of an MCP YAML file.
    
    Focus ONLY on the env section, which specifies environment variables to set when running the module.
    Each entry should be either:
    - A direct string reference to a config parameter:
        ENV_VAR: ${{config.parameterName}}
    - Or an object with more details:
        ENV_VAR:
          value: ${{config.parameterName}}
          description: "Explanation of what this env var is used for"
          required: true|false
    
    IMPORTANT - Environment Variable Guidelines:
    - ONLY include environment variables that are ACTUALLY USED by the application
    - Environment variables MUST be verifiably referenced in code or entrypoint files
    - ALWAYS verify that each environment variable has a clear reference in the code before including it
    - DO NOT create environment variables for parameters already passed as command line arguments
    - ONLY reference config parameters that exist in the config section provided
    - If uncertain whether an environment variable exists, DO NOT include it
    - An empty env object is better than one with made-up variables
    
    Analyze the repository to identify genuine environment variables from:
    - Code that explicitly references process.env, os.environ, etc.
    - Docker or container configuration and entrypoint scripts
    - Example .env files or documentation with evidence of actual usage
    
    Use the tools provided to:
    1. List directories to find key files that might use environment variables
    2. Read files to identify environment variable usage
    3. Use the extraction tool to automatically discover environment variables
    4. Cross-reference discovered environment variables with actual usage in code
    """
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "Generate the env section for the run part of an MCP module based on this information:\n\n"
                "Repository Path: {repo_path}\n"
                "Analysis:\n{analysis}\n"
                "Config section:\n{config_section}\n"
                "Entrypoint:\n{entrypoint_section}\n\n"
                "Please generate ONLY the env section with proper formatting.\n"
                "If no clear environment variables are found, return an empty env object: env: {{}}"),
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