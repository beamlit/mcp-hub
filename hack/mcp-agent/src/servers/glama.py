from typing import List

import httpx

from src.servers.types import Server, ServersResponse

ALLOWED_LICENSES = ["MIT", "MIT License", "Apache 2.0", "The Unlicense", "BSD 3-Clause", "ISC License"]
ATTRIBUTES = ["hosting:remote-capable", "hosting:hybrid"]
GLAMA_API_URL = "https://glama.ai/api/mcp/v1"

async def fetch_mcp_servers(limit: int = 100) -> List[Server]:
    """Fetch MCP servers from the Glama API with required attributes."""
    cursor = ""
    has_next_page = True
    number_of_servers_to_have = limit
    servers = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # response = await client.get("https://glama.ai/mcp/servers?attributes=language%3Atypescript%2Cauthor%3Aofficial&sort=github-stargazers%3Adesc")
            # print(response.text)

            while len(servers) < number_of_servers_to_have and has_next_page:
                response = await client.get(GLAMA_API_URL + "/servers", params={"after": cursor, "first": 20})
                if response.status_code != 200:
                    print(f"Error fetching servers: {response.text}")
                    return []

                # Parse the JSON response first
                response_data = response.json()

                # Fix any None descriptions in tools
                for server in response_data.get("servers", []):
                    if server.get("tools"):
                        for tool in server.get("tools", []):
                            if tool.get("description") is None:
                                tool["description"] = ""

                # Now validate with Pydantic
                data = ServersResponse.model_validate(response_data)
                cursor = data.pageInfo.endCursor
                has_next_page = data.pageInfo.hasNextPage

                for server in data.servers:
                    # Skip servers that don't meet criteria
                    if (server.spdxLicense and server.spdxLicense.get("name") not in ALLOWED_LICENSES) or \
                    not any(attribute in server.attributes for attribute in ATTRIBUTES) or \
                    not server.repository:
                        continue

                    # TODO: Support Python servers
                    package_url = server.repository.url.replace("github.com", "raw.githubusercontent.com") + "/refs/heads/main/package.json"
                    res = await client.get(package_url)
                    if res.status_code != 200:
                        continue

                    servers.append(Server(
                        name=server.name,
                        description=server.description,
                        spdxLicense=server.spdxLicense,
                        repository=server.repository,
                        id=server.id,
                        url=server.url,
                        tools=server.tools,
                        attributes=server.attributes,
                    ))

        except Exception as e:
            print(f"Error during API call: {e}")
    return servers

async def fetch_mcp_server_by_id(server_id: str, **kwargs) -> Server:
    """Fetch a single MCP server from the Glama API."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(GLAMA_API_URL + f"/servers/{server_id}")
            if response.status_code != 200:
                print(f"Error fetching server: {response.text}")
                return None

            # Parse the JSON response first
            response_data = response.json()

            # Fix any None descriptions in tools
            if response_data.get("tools"):
                for tool in response_data.get("tools", []):
                    if tool.get("description") is None:
                        tool["description"] = ""

            # Now validate with Pydantic
            server = Server.model_validate(response_data)
            for key in kwargs.keys():
                if hasattr(server, key):
                    setattr(server, key, kwargs[key])
            return server
        except Exception as e:
            print(f"Error fetching server: {e}")
            return None


async def fetch_mcp_server_by_name(server_name: str, **kwargs) -> Server:
    """Fetch a single MCP server from the Glama API."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(GLAMA_API_URL + f"/servers", params={"query": server_name})
            if response.status_code != 200:
                print(f"Error fetching server: {response.text}")
                return None

            # Parse the JSON response first
            response_data = response.json()

            servers = response_data["servers"]
            if len(servers) == 0:
                print(f"No server found for {server_name}")
                return None
            if len(servers) > 1:
                print(f"Multiple servers found for {server_name}, choose one by starting uv run main.py --server-id <server-id>")
                print(f"Available servers: \n{'\n'.join([server['name'] + "->" + server['id'] for server in servers])}")
                return None

            server = servers[0]
            # Fix any None descriptions in tools
            if server.get("tools"):
                for tool in server.get("tools", []):
                    if tool.get("description") is None:
                        tool["description"] = ""

            # Now validate with Pydantic
            server = Server.model_validate(server)
            for key in kwargs.keys():
                if hasattr(server, key):
                    setattr(server, key, kwargs[key])
            return server
        except Exception as e:
            print(f"Error fetching server: {e}")
            return None