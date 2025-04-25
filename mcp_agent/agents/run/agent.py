import json
import os
from typing import Any, Dict, Optional, Union

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from pydantic import BaseModel, Field

from ...agents.types import MCPState, MCPStateRequestRun, MCPStateResponseRun
from ...libs.files import list_directory, read_file
from ...libs.format import format_markdown_llm_response
from ...models import get_model_big, get_model_small

# Get the directory of the current file
current_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(current_dir, "prompt.md"), "r") as f:
    PROMPT = f.read()
    PROMPT = PROMPT.format(input=MCPStateRequestRun.llm_format(), output=MCPStateResponseRun.llm_format())

with open(os.path.join(current_dir, "prompt_python.md"), "r") as f:
    PROMPT_PYTHON = f.read()
    PROMPT_PYTHON = PROMPT_PYTHON.format(input=MCPStateRequestRun.llm_format(), output=MCPStateResponseRun.llm_format())

with open(os.path.join(current_dir, "prompt_typescript.md"), "r") as f:
    PROMPT_TYPESCRIPT = f.read()
    PROMPT_TYPESCRIPT = PROMPT_TYPESCRIPT.format(input=MCPStateRequestRun.llm_format(), output=MCPStateResponseRun.llm_format())


def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[types.Content]:
    return format_markdown_llm_response(llm_response)

def before_tool_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """Inspects/modifies tool args or skips the tool call."""
    tool_name = tool.name
    print(f"{tool_context.state['name']} - Before tool call for tool '{tool_name}' args '{args}'")

def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    print(f"{callback_context.state['name']} - Generating run component...")

def before_agent_callback_typescript(callback_context: CallbackContext) -> Optional[types.Content]:
    print(f"{callback_context.state['name']} - Generating run component for typescript...")

def before_agent_callback_python(callback_context: CallbackContext) -> Optional[types.Content]:
    print(f"{callback_context.state['name']} - Generating run component for python...")

def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    try:
        mcp_state: MCPState = callback_context.state["mcp_state"]
        mcp_run = MCPStateResponseRun(**json.loads(callback_context.state["mcp_run_result"]))
        # When the LLM did not find any config in files it tends to return sample data from llm_format
        for key in json.loads(MCPStateResponseRun.llm_format())["config"].keys():
            if key in mcp_run.config:
                del mcp_run.config[key]
        callback_context.state["mcp_run"] = mcp_run
        mcp_state.run = mcp_run
        print(f"{callback_context.state['name']} - Run component generated successfully")
        return types.Content(parts=[types.Part(text="Run component generated successfully")])
    except Exception as e:
        print(f"{callback_context.state['name']} - Error generating run component: {e}\nMCP Run state:")
        print(callback_context.state["mcp_run_result"])
        callback_context.state["mcp_state"].errors.append(f"Error generating run component: {e}")
        return None

python = LlmAgent(
    name="run_python",
    description="Run Agent responsible for runing the project in python.",
    instruction=PROMPT_PYTHON,
    model=get_model_big(),
    tools=[read_file, list_directory],
    input_schema=MCPStateRequestRun,
    output_key="mcp_run_result",
    before_tool_callback=before_tool_callback,
    after_model_callback=after_model_callback,
    before_agent_callback=before_agent_callback_python,
)


typescript = LlmAgent(
    name="run_typescript",
    description="Run Agent responsible for runing the project in typescript.",
    instruction=PROMPT_TYPESCRIPT,
    model=get_model_big(),
    tools=[read_file, list_directory],
    input_schema=MCPStateRequestRun,
    output_key="mcp_run_result",
    before_tool_callback=before_tool_callback,
    after_model_callback=after_model_callback,
    before_agent_callback=before_agent_callback_typescript,
)

run = LlmAgent(
    name="run_coordinator",
    description="Run Agent responsible for runing the project.",
    instruction=PROMPT,
    model=get_model_small(),
    tools=[read_file, list_directory],
    sub_agents=[python, typescript],
    input_schema=MCPStateRequestRun,
    output_key="mcp_run_result",
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
    after_model_callback=after_model_callback,
)