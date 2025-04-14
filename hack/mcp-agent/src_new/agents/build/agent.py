import json
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types

from src_new.models import get_model
from src_new.shared.format import format_markdown_llm_response
from src_new.shared.types import MCPState, MCPStateRequestBuild, MCPStateResponseBuild
from src_new.tools.files import read_file, list_directory

with open("src_new/agents/build/prompt.md", "r") as f:
    PROMPT = f.read()

with open("src_new/agents/build/prompt_python.md", "r") as f:
    PROMPT_PYTHON = f.read()

with open("src_new/agents/build/prompt_typescript.md", "r") as f:
    PROMPT_TYPESCRIPT = f.read()

with open("src_new/agents/build/prompt_javascript.md", "r") as f:
    PROMPT_JAVASCRIPT = f.read()

def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[types.Content]:
    return format_markdown_llm_response(llm_response)


def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    print(f"{callback_context.state['name']} - Generating build component...")

def before_agent_callback_python(callback_context: CallbackContext) -> Optional[types.Content]:
    print(f"{callback_context.state['name']} - Generating build component for python...")
    mcp_state: MCPState = callback_context.state["mcp_state"]
    mcp_state.errors.append("language not compatible yet")
    return MCPStateResponseBuild(language="python", command="", output="", error="language not compatible yet").model_dump_json()

def before_agent_callback_javascript(callback_context: CallbackContext) -> Optional[types.Content]:
    print(f"{callback_context.state['name']} - Generating build component for javascript...")
    mcp_state: MCPState = callback_context.state["mcp_state"]
    mcp_state.errors.append("javascript language not compatible yet")
    return MCPStateResponseBuild(language="javascript", command="", output="", error="language not compatible yet").model_dump_json()

def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    return MCPStateResponseBuild(**json.loads(callback_context.state["mcp_build"]))

python = LlmAgent(
    name="build_python",
    description="Build Agent responsible for building the project in python.",
    instruction=PROMPT_PYTHON,
    model=get_model(),
    tools=[read_file, list_directory],
    input_schema=MCPStateRequestBuild,
    before_agent_callback=before_agent_callback_python,
)


typescript = LlmAgent(
    name="build_typescript",
    description="Build Agent responsible for building the project in typescript.",
    instruction=PROMPT_TYPESCRIPT,
    model=get_model(),
    tools=[read_file, list_directory],
    input_schema=MCPStateRequestBuild,
    after_model_callback=after_model_callback,
)

javascript = LlmAgent(
    name="build_javascript",
    description="Build Agent responsible for building the project in javascript.",
    instruction=PROMPT_JAVASCRIPT,
    model=get_model(),
    tools=[read_file, list_directory],
    input_schema=MCPStateRequestBuild,
    before_agent_callback=before_agent_callback_javascript,
)

build = LlmAgent(
    name="build_coordinator",
    description="Build Agent responsible for building the project.",
    instruction=PROMPT,
    model=get_model(),
    tools=[read_file, list_directory],
    input_schema=MCPStateRequestBuild,
    output_key="mcp_build",
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
    after_model_callback=after_model_callback,
)