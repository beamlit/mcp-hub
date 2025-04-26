import argparse
import asyncio
import os
import shutil
import subprocess

import yaml
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agents.agent import supervisor
from .agents.types import MCPState
from .libs.mcppulse import PulseMcpClient, Server


async def get_initial_state(server: Server):
    # Clone repository
    try:
        # Create a temporary directory for the repository
        # tmp_dir = tempfile.mkdtemp()
        tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp", server.url.split("/")[-1])
        # Remove directory if it already exists
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir, exist_ok=True)
        print(f"Cloning repository: {server.repository}")
        subprocess.run(
            ["git", "clone", "--depth", "1", server.repository, tmp_dir],
            check=True, capture_output=True, timeout=60
        )
        print(f"Repository cloned successfully: {server.repository}")

        # Get the branch
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=tmp_dir, capture_output=True, text=True, timeout=30
        ).stdout.strip()
        print(f"Repository branch: {branch}")

    except subprocess.SubprocessError as e:
        raise Exception(f"Repository cloning failed: {e}")

    if server.path != ".":
        server.path = f"{tmp_dir}/{server.path}"
    else:
        server.path = tmp_dir

    def get_language() -> str:
        if "npm" in server.package_registry:
            return "typescript"
        elif "pypi" in server.package_registry:
            return "python"
        return "typescript"

    # Create a state object to share data between agent calls
    state = MCPState(
        **server.model_dump(),
        branch=branch,
        directory=tmp_dir,
        language=get_language(),
        errors=[],
        messages=[]
    )
    return state

async def run_agent(server: Server):
    APP_NAME = "mcp_builder"
    USER_ID = "None"
    SESSION_ID = server.name
    try:
        state = await get_initial_state(server)
    except Exception as e:
        print(f"{server.name} - {e}")
        return

    # Create the specific session where the conversation will happen
    session_service = InMemorySessionService()
    session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")
    runner = Runner(
        agent=supervisor,
        app_name=APP_NAME,
        session_service=session_service,
    )


    content = types.Content(role="user", parts=[types.Part(text=state.model_dump_json())])
    async for event in runner.run_async(new_message=content, user_id=USER_ID, session_id=SESSION_ID):
        # Key Concept: is_final_response() marks the concluding message for the turn.
        if event.is_final_response():
            if event.content and event.content.parts:
                # Assuming text response in the first part
                final_response_text = event.content.parts[0].text
        elif event.actions and event.actions.escalate: # Handle potential errors/escalations
            final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"

    print(final_response_text)

async def fetch_mcp_server(repository: str, path: str = ".", query: str = None):
    async with PulseMcpClient() as client:
        pulse_query = repository.split("/")[-1]
        if path != ".":
            pulse_query = path.split("/")[-1]
        if query:
            pulse_query = query
        servers = await client.list_servers(query=pulse_query)
        for server in servers:
            if server.source_code_url and repository.replace(".git", "") in server.source_code_url:
                server.repository = repository
                server.path = path
                return server
    print(f"WARNING: No server found for repository={repository} path={path}")
    return None

async def main():
    parser = argparse.ArgumentParser(description="Process MCP servers")
    parser.add_argument("--repository", type=str, help="Repository")
    parser.add_argument("--path", type=str, default=".", help="Path in the repository")
    parser.add_argument("--query", type=str, help="Query to search for", default=None)
    args = parser.parse_args()
    # Check if the output directory exists
    if not os.path.exists("agent-output"):
        os.makedirs("agent-output")

    servers = []
    if args.repository:
        server = await fetch_mcp_server(args.repository, path=args.path, name=args.query)
        if server:
            servers.append(server)
    else:
        with open(f"{os.path.dirname(os.path.abspath(__file__))}/servers.yaml") as f:
            _servers = yaml.safe_load(f)
            tasks = []
            for _server in _servers:
                if "repository" not in _server:
                    raise Exception(f"Repository not found for {_server['name']}")
                if _server.get("repository"):
                    tasks.append((fetch_mcp_server, _server["repository"], {"path": _server.get("path", "."), "query": _server.get("query", None)}))

            servers = await asyncio.gather(
                *[func(arg, **kwargs) for (func, arg, kwargs) in tasks]
            )
            servers = [server for server in servers if server]

    # Process servers in batches of 5
    batch_size = 5
    for i in range(0, len(servers), batch_size):
        batch = servers[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1} of {(len(servers) + batch_size - 1)//batch_size}")
        await asyncio.gather(*(run_agent(server) for server in batch))
        print(f"Completed batch {i//batch_size + 1}")
