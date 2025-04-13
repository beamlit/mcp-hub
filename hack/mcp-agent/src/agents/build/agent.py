import json
from typing import Any, Dict, Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from src.models import get_model_small, get_model, get_model_big
from src.shared.format import format_markdown_llm_response
from src.shared.types import MCPState, MCPStateRequestBuild, MCPStateRequestRun, MCPStateResponseBuild
from src.tools.files import read_file, list_directory

with open("src/agents/build/prompt.md", "r") as f:
    PROMPT = f.read()
    PROMPT = PROMPT.format(input=MCPStateRequestBuild.llm_format(), output=MCPStateResponseBuild.llm_format())

with open("src/agents/build/prompt_python.md", "r") as f:
    PROMPT_PYTHON = f.read()

with open("src/agents/build/prompt_typescript.md", "r") as f:
    PROMPT_TYPESCRIPT = f.read()
    PROMPT_TYPESCRIPT = PROMPT_TYPESCRIPT.format(input=MCPStateRequestBuild.llm_format(), output=MCPStateResponseBuild.llm_format())

with open("src/agents/build/prompt_javascript.md", "r") as f:
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
    print(f"{callback_context.state['name']} - Generating build component...")

def before_agent_callback_python(callback_context: CallbackContext) -> Optional[types.Content]:
    print(f"{callback_context.state['name']} - Generating build component for python...")
    mcp_state: MCPState = callback_context.state["mcp_state"]
    mcp_state.errors.append("python language not compatible yet")
    callback_context.state["mcp_build"] = MCPStateResponseBuild(language="python", command="", output="", path="", error="language not compatible yet").model_dump()
    return types.Content(parts=[types.TextPart(text="python language not compatible yet")])

def before_agent_callback_typescript(callback_context: CallbackContext) -> Optional[types.Content]:
    print(f"{callback_context.state['name']} - Generating build component for typescript...")

def before_agent_callback_javascript(callback_context: CallbackContext) -> Optional[types.Content]:
    print(f"{callback_context.state['name']} - Generating build component for javascript...")
    mcp_state: MCPState = callback_context.state["mcp_state"]
    mcp_state.errors.append("javascript language not compatible yet")
    callback_context.state["mcp_build"] = MCPStateResponseBuild(language="javascript", command="", output="", path="", error="language not compatible yet").model_dump()
    return types.Content(parts=[types.TextPart(text="javascript language not compatible yet")])

def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    try:
        callback_context.state["mcp_build"] = json.loads(callback_context.state["mcp_build"])
        if "mcp_build_typescript" in callback_context.state:
            print(f"{callback_context.state['name']} - \n{callback_context.state['mcp_build_typescript']}")
        mcp_state: MCPState = callback_context.state["mcp_state"]
        mcp_build: MCPStateResponseBuild = MCPStateResponseBuild(**callback_context.state["mcp_build"])
        print(f"{callback_context.state['name']} - Build component generated successfully")
        return MCPStateRequestRun(
            name=mcp_state.name,
            language=mcp_build.language,
            repository_path=mcp_state.repository_path,
        )
    except Exception as e:
        print(f"{callback_context.state['name']} - Error generating build component: {e}\nMCP Build state:")
        print(callback_context.state["mcp_build"])
        callback_context.state["mcp_state"].errors.append(f"Error generating build component: {e}")
        return None

python = LlmAgent(
    name="build_python",
    description="Build Agent responsible for building the project in python.",
    instruction=PROMPT_PYTHON,
    model=get_model_small(),
    tools=[read_file, list_directory],
    input_schema=MCPStateRequestBuild,
    before_tool_callback=before_tool_callback,
    before_agent_callback=before_agent_callback_python,
)


typescript = LlmAgent(
    name="build_typescript",
    description="Build Agent responsible for building the project in typescript.",
    instruction=PROMPT_TYPESCRIPT,
    model=get_model(),
    tools=[read_file, list_directory],
    input_schema=MCPStateRequestBuild,
    output_key="mcp_build_typescript",
    before_tool_callback=before_tool_callback,
    before_agent_callback=before_agent_callback_typescript,
    after_model_callback=after_model_callback,
)

javascript = LlmAgent(
    name="build_javascript",
    description="Build Agent responsible for building the project in javascript.",
    instruction=PROMPT_JAVASCRIPT,
    model=get_model_small(),
    tools=[read_file, list_directory],
    input_schema=MCPStateRequestBuild,
    before_tool_callback=before_tool_callback,
    before_agent_callback=before_agent_callback_javascript,
)

build = LlmAgent(
    name="build_coordinator",
    description="Build Agent responsible for building the project.",
    instruction=PROMPT,
    model=get_model_small(),
    tools=[read_file, list_directory],
    input_schema=MCPStateRequestBuild,
    sub_agents=[python, typescript, javascript],
    output_key="mcp_build",
    before_tool_callback=before_tool_callback,
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
    after_model_callback=after_model_callback,
)