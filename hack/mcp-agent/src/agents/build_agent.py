from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain_community.tools.file_management import ReadFileTool, ListDirectoryTool
from langchain.agents import AgentExecutor, create_openai_functions_agent

def create_build_agent():
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
        )
    ]

    """Create an agent to generate the build section of the MCP YAML file."""
    system_message = """You are an expert at defining build information for MCP modules.
    Your task is to generate a properly formatted build section for an MCP YAML file.
    
    Focus ONLY on the build section which must include:
    - language: Primary programming language used (typescript, javascript, python, etc.)
    - command: The full command to build the project (e.g. npm run build or python setup.py build ...)
    - output: Where the built files will be stored (relative path to built files). Only include the directory name, not the full path.
    
    IMPORTANT NOTES:
    1. The command should be the simplest form that identifies the build script (e.g. npm run build or python setup.py build ...)
    2. This value will later be used by the build system which knows how to execute the appropriate script
    3. When examining package.json, look for scripts like "build", "compile", or similar build-related script names
    4. CRITICAL: The command must ONLY be the script invocation (like "npm run build") and NOT the actual script content/implementation
    5. For example, if package.json contains: "scripts": {{"build": "tsc && webpack"}}, you should specify just "npm run build" as the command
    
    Base your build section on the repository structure and files.
    Make realistic assumptions based on the repository's structure, but don't include information that isn't evident.
    
    Use the tools provided to:
    1. List directories to find key configuration files
    2. Read files to extract build commands and configuration
    3. Extract detailed build information directly from the repository
    """
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "Generate the build section for an MCP module based on this analysis:\n\n"
                "Repository URL: {repository_url}\n"
                "Repository Path: {repo_path}\n"
                "Analysis: {analysis}\n"
                "Please generate ONLY the build section of the YAML file with proper formatting."),
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