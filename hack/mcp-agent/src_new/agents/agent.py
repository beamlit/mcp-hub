import json
from typing import Optional

import yaml
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from src_new.agents.build.agent import build
from src_new.agents.metadata.agent import metadata
from src_new.agents.source.agent import source
from src_new.models import get_model
from src_new.shared.types import (MCPFile, MCPState, MCPStateResponseBuild,
                                  MCPStateResponseMetadata,
                                  MCPStateResponseSource)


def before_agent_callback_refactor(callback_context: CallbackContext) -> Optional[types.Content]:
    print(f"{callback_context.state['name']} - Refactoring state...")
    mcp_state: MCPState = callback_context.state["mcp_state"]
    mcp_metadata: MCPStateResponseMetadata = MCPStateResponseMetadata(**json.loads(callback_context.state["mcp_metadata"]))
    mcp_source: MCPStateResponseSource = MCPStateResponseSource(**json.loads(callback_context.state["mcp_source"]))
    mcp_build: MCPStateResponseBuild = MCPStateResponseBuild(**json.loads(callback_context.state["mcp_build"]))
    mcp_file = MCPFile(
        name=mcp_state.name,
        displayName=mcp_metadata.displayName,
        description=mcp_metadata.description,
        longDescription=mcp_metadata.longDescription,
        siteUrl=mcp_metadata.siteUrl,
        icon=mcp_metadata.icon,
        categories=mcp_metadata.categories,
        version=mcp_metadata.version,
        source=mcp_source,
        build=mcp_build,
    )
    with open(f"output/{mcp_metadata.name}.yaml", "w") as f:
        yaml.dump(mcp_file.model_dump(), f, sort_keys=False, default_flow_style=False, Dumper=yaml.SafeDumper)
        print(f"{callback_context.state['name']} - MCP saved to file")
    return types.Content(parts=[types.Part(text=f"{callback_context.state['name']} - MCP saved to file")])

refactor = LlmAgent(
    name="refactor",
    description="Refactor Agent responsible for refactoring the MCP state.",
    model=get_model(),
    before_agent_callback=before_agent_callback_refactor,
)

supervisor = SequentialAgent(
    name="mcp_builder",
    description="MCP Supervisor Agent responsible for orchestrating the generation of MCP configuration files by coordinating specialized agents.",
    sub_agents=[metadata, source, build, refactor]
)