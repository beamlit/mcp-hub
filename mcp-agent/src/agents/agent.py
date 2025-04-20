import json
from typing import Optional

import yaml
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from ..models import get_model_small
from .metadata.agent import MCPStateResponseMetadata, metadata
from .run.agent import MCPStateResponseRun, run
from .types import MCPState


def before_agent_callback_refactor(callback_context: CallbackContext) -> Optional[types.Content]:
    try:
        print(f"{callback_context.state['name']} - Refactoring state...")
        mcp_state: MCPState = callback_context.state["mcp_state"]
        if mcp_state.errors:
            for error in mcp_state.errors:
                print(f"{callback_context.state['name']} - Error: {error}")
            return types.Content(parts=[types.Part(text=f"{callback_context.state['name']} - Server could not be generated")])

        mcp_metadata: MCPStateResponseMetadata = callback_context.state["mcp_metadata"]
        mcp_run: MCPStateResponseRun = callback_context.state["mcp_run"]
        mcp_state.metadata = mcp_metadata
        mcp_state.run = mcp_run

        mcp_state.to_yaml()
        return types.Content(parts=[types.Part(text=f"{callback_context.state['name']} - MCP saved to file output/{mcp_state.name}.yaml")])
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
    sub_agents=[metadata, run, refactor]
)