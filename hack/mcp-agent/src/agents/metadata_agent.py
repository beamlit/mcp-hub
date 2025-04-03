"""
Metadata Agent Module

This module provides an agent for generating the metadata section of MCP YAML files.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Union
from langchain_openai import ChatOpenAI

from .base_agent import BaseAgent

class MetadataResponse(BaseModel):
    """Structured response for metadata section."""
    name: str = Field(description="The name of the MCP module")
    displayName: str = Field(description="The human-readable name of the MCP module")
    description: str = Field(description="A concise explanation of the MCP module")
    longDescription: str = Field(description="A detailed explanation of the MCP module's purpose and functionality")
    siteUrl: str = Field(description="The URL to the product's official page")
    icon: str = Field(description="The URL to the product's logo")
    categories: List[str] = Field(description="The categories of the MCP module")
    version: str = Field(description="The semantic version of the MCP module")


class MetadataAgent(BaseAgent):
    """Agent for generating the metadata section of an MCP YAML file."""
    
    def __init__(self):
        """Initialize the metadata agent."""
        super().__init__(structured_output_class=MetadataResponse)
        
        # Define the system and human messages for the agent
        self.system_message = """You are an expert at creating metadata for MCP modules.
        Your task is to extract basic metadata information from repository analysis and generate the metadata section of an MCP YAML file.

        When saying the company domain, use the company website or documentation referenced by the MCP module.
        
        Focus ONLY on generating these basic metadata fields:
        - name (technical identifier without spaces)
        - displayName (human-readable name)
        - description (concise explanation, 1-2 sentences maximum)
        - longDescription (detailed explanation about the module's purpose and functionality)
        - siteUrl: URL to the product's official page (e.g. https://product.com) e.g google-mcp-server -> https://google.com
        - icon: URL to the product's logo (e.g. https://img.logo.dev/product.domain) e.g google-mcp-server -> https://img.logo.dev/google.com
        - categories (list of relevant categories for the module)
        - version (semantic version, usually 1.0.0)
        
        Base your metadata on the provided analysis and make sure all fields are properly formatted according to YAML standards.

        The output should be a valid YAML object, looking like this:
        name: <n>
        displayName: <displayName>
        description: <description>
        longDescription: <longDescription>
        siteUrl: <siteUrl>
        icon: <icon>
        categories: <categories>
        version: <version>
        """
        
        self.human_message_template = """Generate the metadata section for an MCP module based on this analysis:

        Module name: {name}
        Repository: {repository_url}
        Branch: {branch}

        Analysis:
        {analysis}

        Please generate ONLY the metadata section of the YAML file with proper formatting."""
    
    def initialize_agent(self):
        """Initialize the agent with the chain."""
        # Set up the chain using the base class method
        self.chain = self.setup_chain(self.system_message, self.human_message_template)

    async def ainvoke(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Asynchronously invoke the metadata agent.
        
        Args:
            inputs: Dictionary with keys:
                - name: Module name
                - repository_url: Repository URL
                - branch: Repository branch
                - analysis: Repository analysis
                
        Returns:
            The metadata section as structured output (MetadataResponse)
        """
        # Call the chain directly to get the structured output
        response = await self.chain.ainvoke(inputs)
        
        # Return the response directly - it's already structured
        return response
    
    def invoke(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Synchronously invoke the metadata agent.
        
        Args:
            inputs: Dictionary with keys:
                - name: Module name
                - repository_url: Repository URL
                - branch: Repository branch
                - analysis: Repository analysis
                
        Returns:
            The metadata section as structured output (MetadataResponse)
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


def create_metadata_agent(model_name: str = "gpt-4o-mini", temperature: float = 0) -> MetadataAgent:
    """Create a metadata agent instance.
    
    This function maintains backward compatibility with the original implementation.
    
    Args:
        model_name: The OpenAI model to use
        temperature: Temperature setting for the model
        
    Returns:
        MetadataAgent instance
    """
    metadata_agent = MetadataAgent()
    
    # Set the model name and temperature
    metadata_agent.llm = ChatOpenAI(
        model_name=model_name,
        temperature=temperature
    )
    
    # Initialize the agent
    metadata_agent.initialize_agent()
    
    return metadata_agent 