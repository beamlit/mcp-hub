import json
import os
from typing import Annotated, Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from ..libs.mcppulse import Server


def merge_errors(errors_list: List[List[str]]) -> List[str]:
    """Merge multiple error lists into a single list."""
    result = []
    for errors in errors_list:
        if errors:  # Check if errors is not None
            result.extend(errors)
    return result

class MCPStateRequestMetadata(BaseModel):
    name: str = Field(description="The name of the MCP module")
    repository: str = Field(description="The URL to the repository")
    directory: str = Field(description="Directory where the MCP module has been cloned")
    path: str = Field(description="The path to the directory inside the repository cloned")

    @classmethod
    def llm_format(cls):
        return json.dumps({
            "name": "my-module",
            "repository": "https://example.com/repository",
            "directory": "directory/respotiory/clone/path",
            "path": "path/inside/repository/cloned"
        })

class MCPStateResponseMetadata(BaseModel):
    """Structured response for metadata section."""
    site: str = Field(description="The URL to the product's official page")
    icon: str = Field(description="The URL to the product's logo")
    categories: List[str] = Field(description="The categories of the MCP module")

    @classmethod
    def llm_format(cls):
        return json.dumps({
            "site": "https://example.com",
            "icon": "https://example.com/icon.png",
            "categories": ["example", "example2"]
        })


class MCPStateRequestRun(BaseModel):
    name: str = Field(description="The name of the MCP module")
    repository: str = Field(description="The path to the repository")
    path: str = Field(description="The path to the directory")
    directory: str = Field(description="The path to the directory")
    language: str = Field(description="The language of the repository")

    @classmethod
    def llm_format(cls):
        return json.dumps({
            "name": "my-module",
            "repository": "https://example.com/repository",
            "directory": "src/modules/my-module",
            "path": "src/modules/my-module",
            "language": "typescript"
        })

class RunConfigField(BaseModel):
    """Model for a configuration field."""
    required: bool = Field(description="Whether the field is required")
    label: str = Field(description="The human-readable label for the field")
    secret: bool = Field(description="Whether the field contains sensitive information")
    arg: Optional[str] = Field(description="The command line argument name for this field")
    env: Optional[str] = Field(description="The environment variable name for this field, snake case in uppercase")

class MCPStateResponseRun(BaseModel):
    """Complete module configuration model."""
    config: dict[str, RunConfigField] = Field(description="The configuration of the module")

    @classmethod
    def llm_format(cls):
        return json.dumps({
            "config": {
                "nameArgsSecret1": {
                    "label": "Example Arg 1",
                    "arg": "--name-args-secret-1",
                    "env": "NAME_ARGS_SECRET_1",
                    "required": True,
                    "secret": True,
                },
                "nameArgs2": {
                    "label": "Example Arg 2",
                    "arg": "--name-args-2",
                    "env": "NAME_ARGS_2",
                    "required": False,
                    "secret": False,
                }
            },
        })

class MCPTool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]
    outputSchema: Optional[Dict[str, Any]] = None

class MCPState(Server):
    """State for MCP workflow."""
    name: str = Field(description="The name of the MCP module")
    repository: str
    path: str
    directory: str
    language: str
    icon: Optional[str] = None
    metadata: Optional["MCPStateResponseMetadata"] = None
    run: Optional["MCPStateResponseRun"] = None
    errors: List[str] = Field(default_factory=list, annotation=Annotated[List[str], Field(merge_strategy=merge_errors)])

    def to_yaml(self):
        with open(os.path.join("output", f"{self.name}.yaml"), "w") as f:
            result = {
                "name": self.name,
                "displayName": self.display_name,
                "repository": self.repository,
                "path": self.path,
                "description": self.short_description,
                "longDescription": self.EXPERIMENTAL_ai_generated_description,
                "language": self.language,
                "githubStars": self.github_stars,
                "packageRegistry": self.package_registry,
                "packageName": self.package_name,
                "packageDownloadCount": self.package_download_count,
                "icon": self.metadata.icon,
                "site": self.metadata.site,
                "categories": self.metadata.categories,
                "config": self.run.model_dump()["config"],
            }
            yaml.dump(result, f, sort_keys=False, default_flow_style=False, Dumper=yaml.SafeDumper)