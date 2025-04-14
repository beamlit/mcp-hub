from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, Field
from typing_extensions import Annotated


def merge_errors(errors_list: List[List[str]]) -> List[str]:
    """Merge multiple error lists into a single list."""
    result = []
    for errors in errors_list:
        if errors:  # Check if errors is not None
            result.extend(errors)
    return result

class MCPState(BaseModel):
    """State for MCP workflow."""
    name: str = Field(description="The name of the MCP module")
    server: Any  # Server object
    branch: str
    repository_url: str
    repository_path: str
    analysis: str
    build: Optional[str] = None
    run: Optional[str] = None
    config: Optional[str] = None
    entrypoint: Optional[str] = None
    env: Optional[str] = None
    errors: List[str] = Field(default_factory=list, annotation=Annotated[List[str], Field(merge_strategy=merge_errors)])

class MCPStateRequestMetadata(BaseModel):
    name: str = Field(description="The name of the MCP module")
    repository_url: str = Field(description="The URL to the repository")
    branch: str = Field(description="The branch to use", default="main")
    analysis: str = Field(description="The analysis of the repository")

class MCPStateResponseMetadata(BaseModel):
    """Structured response for metadata section."""
    name: str = Field(description="The name of the MCP module")
    displayName: str = Field(description="The human-readable name of the MCP module")
    description: str = Field(description="A concise explanation of the MCP module")
    longDescription: str = Field(description="A detailed explanation of the MCP module's purpose and functionality")
    siteUrl: str = Field(description="The URL to the product's official page")
    icon: str = Field(description="The URL to the product's logo")
    categories: List[str] = Field(description="The categories of the MCP module")
    version: str = Field(description="The semantic version of the MCP module")
    error: Optional[str] = Field(default=None, description="The error message to use")

class MCPStateRequestSource(BaseModel):
    name: str = Field(description="The name of the MCP module")
    branch: str = Field(description="The branch to use", default="main")
    repository_path: str = Field(description="The path to the repository")
    analysis: str = Field(description="The analysis of the repository")

class MCPStateResponseSource(BaseModel):
    repository: str = Field(description="The full URL to the git repository")
    branch: str = Field(description="The specific branch to use", default="main")
    path: str = Field(description="Path to the project root directory", default=".")
    error: Optional[str] = Field(default=None, description="The error message to use")

class MCPStateRequestBuild(BaseModel):
    name: str = Field(description="The name of the MCP module")
    branch: str = Field(description="The branch to use", default="main")
    repository_url: str = Field(description="The URL to the repository")
    repository_path: str = Field(description="The path to the repository")
    analysis: str = Field(description="The analysis of the repository")

class MCPStateResponseBuild(BaseModel):
    language: str = Field(description="The language of the repository")
    command: str = Field(description="The build command to use")
    output: str = Field(description="The output of the build command")
    error: Optional[str] = Field(default=None, description="The error message to use")

class MCPFile(BaseModel):
    name: str = Field(description="The name of the MCP module")
    displayName: str = Field(description="The human-readable name of the MCP module")
    description: str = Field(description="A concise explanation of the MCP module")
    longDescription: str = Field(description="A detailed explanation of the MCP module's purpose and functionality")
    siteUrl: str = Field(description="The URL to the product's official page")
    icon: str = Field(description="The URL to the product's logo")
    categories: List[str] = Field(description="The categories of the MCP module")
    version: str = Field(description="The semantic version of the MCP module")
    source: MCPStateResponseSource = Field(description="The source of the MCP module")
    build: MCPStateResponseBuild = Field(description="The build of the MCP module")
    # run: MCPStateResponseRun = Field(description="The run of the MCP module")