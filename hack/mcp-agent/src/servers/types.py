from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator

from src.servers.utils import (clone_repository, extract_repository_info,
                               find_python_packages, slugify)


class Repository(BaseModel):
    url: str
    branch: Optional[str] = None

class MCPTool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]
    outputSchema: Optional[Dict[str, Any]] = None

class Server(BaseModel):
    attributes: List[str]
    description: str
    id: str
    name: str
    repository: Optional[Repository] = None
    spdxLicense: Optional[Dict[str, str]] = None
    tools: List[MCPTool]
    url: str
    path: Optional[str] = None

    async def clone(self):
        if self.repository:
            return await clone_repository(self.repository.url, ".")
        return None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return slugify(v)

    def find_python_packages(self, repo_path):
        return find_python_packages(repo_path)

    def extract_repository_info(self, repo_path):
        """Extract repository info for the given repo path."""
        return extract_repository_info(repo_path)

class PageInfo(BaseModel):
    endCursor: str
    hasNextPage: bool
    hasPreviousPage: bool
    startCursor: str

class ServersResponse(BaseModel):
    pageInfo: PageInfo
    servers: List[Server]