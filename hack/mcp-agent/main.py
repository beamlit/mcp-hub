import argparse
import asyncio
import os
import subprocess
import tempfile

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from src_new.agents.agent import supervisor
from src_new.analyse import extract_repository_info, format_analysis_output
from src_new.servers.glama import fetch_mcp_server, fetch_mcp_servers
from src_new.servers.types import Server
from src_new.shared.types import MCPState


async def get_intial_state(server: Server):
    # Clone repository
    try:
        repo_url = server.repository.url
        temp_dir = tempfile.mkdtemp()
        print(f"Cloning repository: {repo_url}")
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, temp_dir],
            check=True, capture_output=True, timeout=60
        )
        print(f"Repository cloned successfully: {repo_url}")

        # Get the branch
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=temp_dir, capture_output=True, text=True, timeout=30
        ).stdout.strip()
        print(f"Repository branch: {branch}")

        if hasattr(server.repository, "__setattr__"):
            setattr(server.repository, "branch", branch)

    except subprocess.SubprocessError as e:
        raise Exception(f"Repository cloning failed: {e}")

    # Extract repository info
    repo_info = extract_repository_info(temp_dir)
    analysis = format_analysis_output(repo_info)
    # Create a state object to share data between agent calls
    state = MCPState(
        name=server.name,
        server=server,
        repository_url=repo_url,
        branch=branch,
        repository_path=temp_dir,
        analysis=analysis,
        shared_memory={},
        errors=[],
        messages=[]
    )
    return state

async def run_agent(server: Server):
    APP_NAME = "mcp_builder"
    USER_ID = "None"
    SESSION_ID = server.name
    try:
        state = await get_intial_state(server)
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
    parser.add_argument("--server", type=str, help="Server ID")
    parser.add_argument("--count", type=int, help="Number of MCP servers to generate")
    parser.add_argument("--output", type=str, default="output", help="Output directory")
    args = parser.parse_args()
    # Check if the output directory exists
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    if args.server:
        server = await fetch_mcp_server(args.server)
        if server:
            await run_agent(server)
    elif args.count:
        servers = await fetch_mcp_servers(args.count)
        for server in servers:
            await run_agent(server)

if __name__ == "__main__":
    asyncio.run(main())
