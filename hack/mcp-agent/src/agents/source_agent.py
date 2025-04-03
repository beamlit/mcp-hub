"""
Source Agent Module

This module provides an agent for generating the source section of MCP YAML files.
"""

from typing import Dict, Any, Union
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from .base_agent import BaseAgent

class SourceInfo(BaseModel):
    """Source repository information according to Go struct."""
    repo: str = Field(description="The full URL to the git repository")
    branch: str = Field(description="The specific branch to use", default="main")
    path: str = Field(description="Path to the project root directory", default=".")

class SourceResponse(BaseModel):
    """Structured response for source section."""
    source: SourceInfo = Field(
        description="Source section containing repository information",
        default_factory=lambda: SourceInfo(repo="", branch="main", path=".")
    )


class SourceAgent(BaseAgent):
    """Agent for generating the source section of an MCP YAML file."""
    
    def __init__(self):
        """Initialize the source agent."""
        super().__init__(structured_output_class=SourceResponse)
        
        # Define the system and human messages for the agent
        self.system_message = """You are an expert at defining source repositories for MCP modules.
        Your task is to extract repository information from the provided analysis and generate the source section of an MCP YAML file.
        
        Focus ONLY on generating the source section with these fields:
        - source.repo: The full URL to the git repository
        - source.branch: The specific branch to use (typically "main" or "master" if not specified)
        - source.path: The path to the project root directory (e.g. "."). Where the package.json is located, where I should run the build command.
        
        Base your source section on the provided analysis and repository URL, making sure it's properly formatted according to YAML standards.
        
        The output should be a valid YAML object for the source section, looking like this:
        
        source:
          repo: <repo_url>
          branch: <branch>
          path: <path>
        """
        
        self.human_message_template = """Generate the source section for an MCP module based on this analysis:

        Repository: {repository_url}
        Repo Path: {repo_path}
        Branch: {branch}

        Analysis:
        {analysis}

        Please generate ONLY the source section of the YAML file with proper formatting, ensuring the repository URL is correctly included in the 'repo' field."""
        
    def initialize_agent(self):
        """Initialize the agent with the chain."""
        # Set up the chain using the base class method
        self.chain = self.setup_chain(self.system_message, self.human_message_template)

    async def ainvoke(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Asynchronously invoke the source agent.
        
        Args:
            inputs: Dictionary with keys:
                - repository_url: Repository URL
                - repo_path: Path to repository on disk
                - branch: Repository branch
                - analysis: Repository analysis
                
        Returns:
            The source section as structured output (SourceResponse)
        """
        # Ensure the repository_url is available and not empty
        if not inputs.get("repository_url"):
            # Create a more informative error or provide a default
            print("Warning: repository_url is empty or not provided in inputs")
        
        # Call the chain directly to get the structured output
        response = await self.chain.ainvoke(inputs)
        
        # If we got a dict response directly, make sure it has the proper structure
        if isinstance(response, dict):
            if "source" not in response:
                # Create a properly structured response
                response = {
                    "source": {
                        "repo": inputs.get("repository_url", ""),
                        "branch": inputs.get("branch", "main"),
                        "path": "."
                    }
                }
            elif isinstance(response["source"], dict):
                # Make sure 'source' has the correct fields
                source = response["source"]
                # Check if there's a nested 'git' that needs to be flattened
                if "git" in source and isinstance(source["git"], dict):
                    git_info = source["git"]
                    source = {
                        "repo": git_info.get("repository", inputs.get("repository_url", "")),
                        "branch": git_info.get("branch", inputs.get("branch", "main")),
                        "path": git_info.get("path", ".")
                    }
                    response["source"] = source
                
                # Ensure required fields exist
                if "repo" not in source:
                    source["repo"] = inputs.get("repository_url", "")
                if "branch" not in source:
                    source["branch"] = inputs.get("branch", "main")
                if "path" not in source:
                    source["path"] = "."
                
                # Remove any other fields that shouldn't be there
                for key in list(source.keys()):
                    if key not in ["repo", "branch", "path"]:
                        del source[key]
        
        # Return the response directly - it's already structured
        return response
    
    def invoke(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Synchronously invoke the source agent.
        
        Args:
            inputs: Dictionary with keys:
                - repository_url: Repository URL
                - repo_path: Path to repository on disk
                - branch: Repository branch
                - analysis: Repository analysis
                
        Returns:
            The source section as structured output (SourceResponse)
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


def create_source_agent(model_name: str = "gpt-4o-mini", temperature: float = 0) -> SourceAgent:
    """Create a source agent instance.
    
    This function maintains backward compatibility with the original implementation.
    
    Args:
        model_name: The OpenAI model to use
        temperature: Temperature setting for the model
        
    Returns:
        SourceAgent instance
    """
    source_agent = SourceAgent()
    
    # Set the model name and temperature
    source_agent.llm = ChatOpenAI(
        model_name=model_name,
        temperature=temperature
    )
    
    # Initialize the agent
    source_agent.initialize_agent()
    
    return source_agent 