import copy
import json
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types

from src.models import get_model_small
from src.shared.format import format_markdown_llm_response
from src.shared.types import (MCPState, MCPStateRequestSource,
                              MCPStateResponseMetadata)

with open("src/agents/metadata/prompt.md", "r") as f:
    PROMPT = f.read()

def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[types.Content]:
    return format_markdown_llm_response(llm_response)

def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    mcp_state = MCPState(**json.loads(callback_context.user_content.parts[0].text))
    callback_context.state["name"] = mcp_state.name
    callback_context.state["mcp_state"] = mcp_state
    print(f"{callback_context.state['name']} - Generating metadata component...")

def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    mcp_state: MCPState = callback_context.state["mcp_state"]
    return MCPStateRequestSource(
        name=mcp_state.name,
        repository_path=mcp_state.repository_path,
        branch=mcp_state.branch,
        analysis=mcp_state.analysis,
    )

metadata = LlmAgent(
    name="metadata",
    description="Metadata Agent responsible for extracting metadata from the repository.",
    instruction=PROMPT,
    model=get_model_small(),
    input_schema=MCPState,
    output_schema=MCPStateResponseMetadata,
    output_key="mcp_metadata",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    after_model_callback=after_model_callback,
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback
)