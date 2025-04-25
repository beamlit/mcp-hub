from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

API_BASE_URL = "https://api.pulsemcp.com/v0beta"

class Integration(BaseModel):
    name: str
    slug: str
    url: str

class Server(BaseModel):
    name: str
    display_name: str
    url: str
    external_url: Optional[str] = None
    short_description: Optional[str] = None
    source_code_url: Optional[str] = None
    repository: Optional[str] = None
    path: Optional[str] = None
    github_stars: Optional[int] = None
    package_registry: Optional[str] = None
    package_name: Optional[str] = None
    package_download_count: Optional[int] = None
    EXPERIMENTAL_ai_generated_description: Optional[str] = Field(None, alias="EXPERIMENTAL_ai_generated_description")
    integrations: Optional[List[Integration]] = None

class ListIntegrationsResponse(BaseModel):
    integrations: List[Integration]

class PulseMcpClient:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def list_servers(
        self,
        query: Optional[str] = None,
        count_per_page: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Server]:
        """
        List MCP servers with optional filtering

        Args:
            query: Search term to filter servers
            count_per_page: Number of results per page (maximum: 5000)
            offset: Number of results to skip for pagination

        Returns:
            ListServersResponse containing servers and pagination info
        """
        params = {}
        if query:
            params["query"] = query
        if count_per_page:
            params["count_per_page"] = count_per_page
        if offset:
            params["offset"] = offset

        response = await self.client.get("/servers", params=params)
        response.raise_for_status()
        servers = []
        for server in response.json()["servers"]:
            server["display_name"] = server["name"]
            server["name"] = server["url"].split("/")[-1]
            servers.append(Server(**server))
        return servers

    async def list_integrations(self) -> ListIntegrationsResponse:
        """
        List all available integrations

        Returns:
            ListIntegrationsResponse containing list of integrations
        """
        response = await self.client.get("/integrations")
        response.raise_for_status()
        return ListIntegrationsResponse.model_validate(response.json())

# Example usage:
async def main():
    try:
        async with PulseMcpClient() as client:
            # List servers example
            servers = await client.list_servers(
                query="fetch",
            )
            print("Servers:", servers.model_dump_json(indent=2))

            # List integrations example
            integrations = await client.list_integrations()
            print("Integrations:", integrations.model_dump_json(indent=2))
    except httpx.HTTPStatusError as e:
        print("\nHTTP Error Details:")
        print(f"Status Code: {e.response.status_code}")
        print(f"URL: {e.request.url}")
        print(f"Method: {e.request.method}")
        print("\nResponse Headers:")
        for header, value in e.response.headers.items():
            print(f"  {header}: {value}")
        print("\nResponse Body:")
        try:
            print(e.response.json())
        except:
            print(e.response.text)
    except httpx.RequestError as e:
        print("\nRequest Error:")
        print(f"Error: {str(e)}")
        if hasattr(e, 'request'):
            print(f"URL: {e.request.url}")
            print(f"Method: {e.request.method}")
    except Exception as e:
        print("\nUnexpected Error:")
        print(f"Error: {str(e)}")
        print(f"Type: {type(e).__name__}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
