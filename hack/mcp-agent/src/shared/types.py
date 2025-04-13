import json
from typing import Annotated, Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from src.servers.types import MCPTool, Server


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
    server: Server  # Server object
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

    @classmethod
    def llm_format(cls):
        return json.dumps({
            "name": "my-module",
            "repository_url": "https://github.com/my-org/my-module",
            "repository_path": "/path/to/repo",
            "analysis": "The analysis of the repository"
        })

class MCPStateResponseBuild(BaseModel):
    language: str = Field(description="The language of the repository")
    command: str = Field(description="The build command to use")
    output: str = Field(description="The output of the build command")
    path: str = Field(description="The path to the build directory")
    error: Optional[str] = Field(default=None, description="The error message to use")

    @classmethod
    def llm_format(cls):
        return json.dumps({
            "language": "<language of the repository>",
            "command": "<command to run the build>",
            "output": "<path to the output of the build>",
            "path": "<path inside the repository to start the build from>",
            "error": "<error message if an error happened>"
        })

class MCPStateRequestRun(BaseModel):
    name: str = Field(description="The name of the MCP module")
    repository_path: str = Field(description="The path to the repository")
    language: str = Field(description="The language of the repository")

    @classmethod
    def llm_format(cls):
        return json.dumps({
            "name": "my-module",
            "repository_path": "/path/to/repo",
            "language": "typescript"
        })

class RunConfigField(BaseModel):
    """Model for a configuration field."""
    type: str = Field(description="The type of the configuration field")
    required: bool = Field(description="Whether the field is required")
    default: Optional[Union[str, int, None]] = Field(description="The default value of the field")
    example: Union[str, int] = Field(description="An example value for the field")
    label: str = Field(description="The human-readable label for the field")
    secret: bool = Field(description="Whether the field contains sensitive information")
    arg: Optional[str] = Field(description="The command line argument name for this field")
    env: Optional[str] = Field(description="The environment variable name for this field, snake case in uppercase")

class MCPStateResponseRun(BaseModel):
    """Complete module configuration model."""
    config: dict[str, RunConfigField] = Field(description="The configuration of the module")
    entrypoint: list[str] = Field(description="The command and arguments to run the module, do not include arguments from the config")
    language: str = Field(description="The language of the repository")
    error: Optional[str] = Field(default=None, description="The error message to use")

    @classmethod
    def llm_format(cls):
        return json.dumps({
            "config": {
                "nameArgs1": {
                    "type": "integer",
                    "required": True,
                    "default": 3000,
                    "example": 8080,
                    "label": "Example Arg 1",
                    "secret": False,
                    "arg": "--name-args-1",
                    "env": "NAME_ARGS_1"
                },
                "nameArgs2": {
                    "type": "string",
                    "required": True,
                    "default": None,
                    "example": "example-arg-2",
                    "label": "Example Arg 2",
                    "secret": True,
                    "arg": "--name-args-2",
                    "env": "NAME_ARGS_2"
                }
            },
            "entrypoint": ["npm", "start"],
            "language": "typescript",
            "error": None
        })

class MCPFile(MCPStateResponseMetadata):
    id: str = Field(description="The id of the MCP module")
    source: MCPStateResponseSource = Field(description="The source of the MCP module")
    build: MCPStateResponseBuild = Field(description="The build of the MCP module")
    tools: List[MCPTool] = Field(description="The tools of the MCP module")
    run: MCPStateResponseRun = Field(description="The run of the MCP module")