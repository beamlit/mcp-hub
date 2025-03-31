from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain_community.tools.file_management import ReadFileTool, ListDirectoryTool
from langchain.agents import AgentExecutor, create_openai_functions_agent


def create_entrypoint_agent():
    """Create an agent to generate the entrypoint section of the run part of the MCP YAML file."""
    tools = [
        Tool(
            name="ReadFile",
            description="Read a file from the repository to analyze its content.",
            func=ReadFileTool().run
        ),
        Tool(
            name="ListDirectory",
            description="List contents of a repository directory to discover startup scripts.",
            func=ListDirectoryTool().run
        )
    ]
    
    system_message = """You are an expert at defining entrypoint commands for MCP modules.
    Your task is to generate a properly formatted entrypoint array for the run part of an MCP YAML file.
    
    Focus ONLY on the entrypoint array, which specifies the command to run the module:
    - entrypoint: Array of command elements that references config values using the format: ["command", "arg1", "--flag=${{config.parameterName}}"]
    
    IMPORTANT - Entrypoint Guidelines:
    - ONLY reference config parameters that actually exist in the config section provided
    - Base the entrypoint command on the actual startup command found in the repository
    - If you're unsure how the application starts, use a simple command without config references
    - Format the array correctly as a YAML sequence with proper string escaping
    
    Analyze the repository to determine the correct startup command, typically found in:
    - package.json scripts (for Node.js)
    - Dockerfile CMD or ENTRYPOINT
    - Shell scripts or Makefiles
    - Main application file (e.g., if using a framework with conventions)
    
    Use the tools provided to:
    1. List directories to find key startup scripts
    2. Read files to extract startup commands
    3. Use the extraction tool to automatically discover entrypoint commands
    """
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "Generate the entrypoint section for the run part of an MCP module based on this information:\n\n"
                "Repository Path: {repo_path}\n"
                "Please generate ONLY the entrypoint array with proper formatting."),
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