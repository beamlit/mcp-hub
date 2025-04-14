import json
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types

from src_new.models import get_model
from src_new.shared.format import format_markdown_llm_response
from src_new.shared.types import (MCPState, MCPStateRequestBuild,
                                  MCPStateRequestSource,
                                  MCPStateResponseSource)

with open("src_new/agents/source/prompt.md", "r") as f:
    PROMPT = f.read()

def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[types.Content]:
    return format_markdown_llm_response(llm_response)

def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    print(f"{callback_context.state['name']} - Generating source component...")

def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    mcp_state: MCPState = callback_context.state["mcp_state"]
    return MCPStateRequestBuild(
        name=mcp_state.name,
        branch=mcp_state.branch,
        repository_url=mcp_state.repository_url,
        repository_path=mcp_state.repository_path,
        analysis=mcp_state.analysis,
    )


source = LlmAgent(
    name="source",
    description="Source Agent responsible for extracting source from the repository.",
    instruction=PROMPT,
    model=get_model(),
    input_schema=MCPStateRequestSource,
    output_schema=MCPStateResponseSource,
    output_key="mcp_source",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    after_model_callback=after_model_callback,
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
)