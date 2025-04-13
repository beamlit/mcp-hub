import json
from typing import Any, Dict, Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from src.models import get_model_big, get_model_small
from src.shared.format import format_markdown_llm_response
from src.shared.types import MCPState, MCPStateRequestRun, MCPStateResponseRun
from src.tools.files import list_directory, read_file

with open("src/agents/run/prompt.md", "r") as f:
    PROMPT = f.read()
    PROMPT = PROMPT.format(input=MCPStateRequestRun.llm_format(), output=MCPStateResponseRun.llm_format())

with open("src/agents/run/prompt_python.md", "r") as f:
    PROMPT_PYTHON = f.read()

with open("src/agents/run/prompt_typescript.md", "r") as f:
    PROMPT_TYPESCRIPT = f.read()
    PROMPT_TYPESCRIPT = PROMPT_TYPESCRIPT.format(input=MCPStateRequestRun.llm_format(), output=MCPStateResponseRun.llm_format())

with open("src/agents/run/prompt_javascript.md", "r") as f:
    PROMPT_JAVASCRIPT = f.read()

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
    mcp_state: MCPState = callback_context.state["mcp_state"]
    mcp_state.errors.append("run - language not compatible yet")
    return MCPStateResponseRun(language="python", command="", output="", error="language not compatible yet").model_dump_json()

def before_agent_callback_javascript(callback_context: CallbackContext) -> Optional[types.Content]:
    print(f"{callback_context.state['name']} - Generating run component for javascript...")
    mcp_state: MCPState = callback_context.state["mcp_state"]
    mcp_state.errors.append("run - javascript language not compatible yet")
    return MCPStateResponseRun(language="javascript", command="", output="", error="language not compatible yet").model_dump_json()

def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    try:
        mcp_run = MCPStateResponseRun(**json.loads(callback_context.state["mcp_run"]))
        # When the LLM did not find any config in files it tends to return sample data from llm_format
        for key in json.loads(MCPStateResponseRun.llm_format())["config"].keys():
            if key in mcp_run.config:
                del mcp_run.config[key]
        callback_context.state["mcp_run"] = mcp_run.model_dump()
        print(f"{callback_context.state['name']} - Run component generated successfully")
        return types.Content(parts=[types.Part(text="Run component generated successfully")])
    except Exception as e:
        print(f"{callback_context.state['name']} - Error generating run component: {e}\nMCP Run state:")
        print(callback_context.state["mcp_run"])
        callback_context.state["mcp_state"].errors.append(f"Error generating run component: {e}")
        return None

python = LlmAgent(
    name="run_python",
    description="Run Agent responsible for runing the project in python.",
    instruction=PROMPT_PYTHON,
    model=get_model_big(),
    tools=[read_file, list_directory],
    input_schema=MCPStateRequestRun,
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
    before_tool_callback=before_tool_callback,
    after_model_callback=after_model_callback,
    before_agent_callback=before_agent_callback_typescript,
)

javascript = LlmAgent(
    name="run_javascript",
    description="Run Agent responsible for runing the project in javascript.",
    instruction=PROMPT_JAVASCRIPT,
    model=get_model_big(),
    tools=[read_file, list_directory],
    input_schema=MCPStateRequestRun,
    before_tool_callback=before_tool_callback,
    after_model_callback=after_model_callback,
    before_agent_callback=before_agent_callback_javascript,
)

run = LlmAgent(
    name="run_coordinator",
    description="Run Agent responsible for runing the project.",
    instruction=PROMPT,
    model=get_model_small(),
    tools=[read_file, list_directory],
    sub_agents=[python, typescript, javascript],
    input_schema=MCPStateRequestRun,
    output_key="mcp_run",
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
    after_model_callback=after_model_callback,
)