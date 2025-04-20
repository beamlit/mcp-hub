import json
import os
from typing import Any, Dict, Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from ...agents.run.agent import MCPStateRequestRun
from ...agents.types import (MCPState, MCPStateRequestMetadata,
                             MCPStateResponseMetadata)
from ...libs.fetch import fetch_url
from ...libs.files import list_directory, read_file
from ...libs.format import format_markdown_llm_response
from ...models import get_model

current_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(current_dir, "prompt.md"), "r") as f:
    PROMPT = f.read()
    PROMPT = PROMPT.format(
        input=MCPStateRequestMetadata.llm_format(),
        output=MCPStateResponseMetadata.llm_format()
    )


def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    mcp_state = MCPState(**json.loads(callback_context.user_content.parts[0].text))
    callback_context.state["name"] = mcp_state.name
    callback_context.state["mcp_state"] = mcp_state
    callback_context.state["icon_url"] = f"https://github.com/{mcp_state.repository.split('/')[-2]}"
    print(f"{callback_context.state['name']} - Generating metadata component...")

def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[types.Content]:
    return format_markdown_llm_response(llm_response)

def before_tool_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """Inspects/modifies tool args or skips the tool call."""
    tool_name = tool.name
    print(f"{tool_context.state['name']} - Before tool call for tool '{tool_name}' args '{args}'")

def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    try:
        mcp_state: MCPState = callback_context.state["mcp_state"]
        mcp_metadata = MCPStateResponseMetadata(**json.loads(callback_context.state["mcp_metadata_result"]))
        callback_context.state["mcp_metadata"] = mcp_metadata
        mcp_state.metadata = mcp_metadata
        print(f"{callback_context.state['name']} - Metadata component generated successfully")
        return MCPStateRequestRun(
            name=mcp_state.name,
            repository=mcp_state.repository,
            directory=mcp_state.directory,
            language=mcp_state.language,
            path=mcp_state.path,
        )
    except Exception as e:
        mcp_state: MCPState = callback_context.state["mcp_state"]
        mcp_state.errors.append(f"Error generating metadata: {e}")
        return None

metadata = LlmAgent(
    name="metadata",
    description="Metadata Agent responsible for extracting metadata from the repository.",
    instruction=PROMPT,
    model=get_model(),
    tools=[read_file, list_directory, fetch_url],
    input_schema=MCPState,
    output_key="mcp_metadata_result",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    before_tool_callback=before_tool_callback,
    after_model_callback=after_model_callback,
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback
)