import json
from typing import Optional

import yaml
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from src.agents.build.agent import build
from src.agents.metadata.agent import metadata
from src.agents.run.agent import run
from src.agents.source.agent import source
from src.models import get_model_small
from src.shared.types import (MCPFile, MCPState, MCPStateResponseBuild,
                              MCPStateResponseMetadata, MCPStateResponseRun,
                              MCPStateResponseSource)


def before_agent_callback_refactor(callback_context: CallbackContext) -> Optional[types.Content]:
    try:
        print(f"{callback_context.state['name']} - Refactoring state...")
        mcp_state: MCPState = callback_context.state["mcp_state"]
        mcp_metadata: MCPStateResponseMetadata = MCPStateResponseMetadata(**callback_context.state["mcp_metadata"])
        mcp_source: MCPStateResponseSource = MCPStateResponseSource(**callback_context.state["mcp_source"])
        mcp_build: MCPStateResponseBuild = MCPStateResponseBuild(**callback_context.state["mcp_build"])
        mcp_run: MCPStateResponseRun = MCPStateResponseRun(**callback_context.state["mcp_run"])

        mcp_file = MCPFile(
            name=mcp_state.name,
            id=mcp_state.server.id,
            displayName=mcp_metadata.displayName,
            description=mcp_metadata.description,
            longDescription=mcp_metadata.longDescription,
            siteUrl=mcp_metadata.siteUrl,
            icon=mcp_metadata.icon,
            categories=mcp_metadata.categories,
            version=mcp_metadata.version,
            source=mcp_source,
            build=mcp_build,
            run=mcp_run,
            tools=mcp_state.server.tools,
        )
        with open(f"output/{mcp_metadata.name}.yaml", "w") as f:
            result = mcp_file.model_dump()
            del result["error"]
            del result["source"]["error"]
            del result["build"]["error"]
            yaml.dump(result, f, sort_keys=False, default_flow_style=False, Dumper=yaml.SafeDumper)
        return types.Content(parts=[types.Part(text=f"{callback_context.state['name']} - MCP saved to file output/{mcp_metadata.name}.yaml")])
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"{callback_context.state['name']} - Error refactoring state: {e}")
        print(f"Error occurred at: {error_traceback}")
        return types.Content(parts=[types.Part(text=f"{callback_context.state['name']} - Error refactoring state: {e}\nError occurred at: {error_traceback}")])

refactor = LlmAgent(
    name="refactor",
    description="Refactor Agent responsible for refactoring the MCP state.",
    model=get_model_small(),
    before_agent_callback=before_agent_callback_refactor,
)

supervisor = SequentialAgent(
    name="mcp_builder",
    description="MCP Supervisor Agent responsible for orchestrating the generation of MCP configuration files by coordinating specialized agents.",
    sub_agents=[metadata, source, build, run, refactor]
)