import argparse
import asyncio
import os
import shutil
import subprocess

import yaml
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.agents.agent import supervisor
from src.analyse import extract_repository_info, format_analysis_output
from src.servers.glama import (fetch_mcp_server_by_id,
                               fetch_mcp_server_by_name, fetch_mcp_servers)
from src.servers.types import Server
from src.shared.types import MCPState


async def get_initial_state(server: Server):
    # Clone repository
    try:
        repo_url = server.repository.url
        # Create a temporary directory for the repository
        # tmp_dir = tempfile.mkdtemp()

        tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp", server.name)
        # Remove directory if it already exists
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir, exist_ok=True)
        print(f"Cloning repository: {repo_url}")
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, tmp_dir],
            check=True, capture_output=True, timeout=60
        )
        print(f"Repository cloned successfully: {repo_url}")

        # Get the branch
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=tmp_dir, capture_output=True, text=True, timeout=30
        ).stdout.strip()
        print(f"Repository branch: {branch}")

        if hasattr(server.repository, "__setattr__"):
            setattr(server.repository, "branch", branch)

    except subprocess.SubprocessError as e:
        raise Exception(f"Repository cloning failed: {e}")

    # Extract repository info
    repo_info = extract_repository_info(tmp_dir)
    analysis = format_analysis_output(repo_info)

    directory = tmp_dir
    if server.path:
        directory += f"/{server.path}"

    # Create a state object to share data between agent calls
    state = MCPState(
        name=server.name,
        server=server.model_dump(),
        repository_url=repo_url,
        branch=branch,
        repository_path=directory,
        analysis=analysis,
        shared_memory={},
        errors=[],
        messages=[]
    )
    print(state)
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

async def main():
    parser = argparse.ArgumentParser(description="Process MCP servers")
    parser.add_argument("--server-id", type=str, help="Server ID")
    parser.add_argument("--server-name", type=str, help="Server Name")
    parser.add_argument("--count", type=int, help="Number of MCP servers to generate")
    parser.add_argument("--output", type=str, default="output", help="Output directory")
    args = parser.parse_args()
    # Check if the output directory exists
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    servers = []
    if args.server_id:
        server = await fetch_mcp_server_by_id(args.server_id)
        if server:
            servers.append(server)

    elif args.server_name:
        server = await fetch_mcp_server_by_name(args.server_name)
        if server:
            servers.append(server)
    elif args.count:
        servers = await fetch_mcp_servers(args.count)

    else:
        with open("servers.yaml") as f:
            _servers = yaml.safe_load(f)
            tasks = []
            for _server in _servers:
                if _server.get("id"):
                    tasks.append((fetch_mcp_server_by_id, _server["id"], _server))
                else:
                    tasks.append((fetch_mcp_server_by_name, _server["name"], _server))

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

if __name__ == "__main__":
    asyncio.run(main())
