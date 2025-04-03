# MCP Agent

> NOTE: In tools, you'll need to update the path used to match your local path.

A multi-agent system for automatically generating `<mcp>.yaml` files from repository analysis.

## Overview

The MCP Agent is a tool that analyzes repositories to automatically generate MCP module definition files (`<mcp>.yaml`). It uses a combination of specialized LLM-powered agents to:

1. Analyze repository structure and code
2. Extract tool definitions
3. Generate a properly formatted `<mcp>.yaml` file
4. Validate and correct the YAML output

## Installation

1. Clone the repository
2. Activate the virtual environment: `uv sync`
3. Set up the OpenAI API key in your environment: `export OPENAI_API_KEY=your_api_key_here`

## Usage

The MCP Agent offers both a monolithic agent approach (original) and a specialized agents approach (new) for generating MCP YAML files. The specialized approach often produces higher quality results by focusing on each section separately.

The generated YAML file will be saved in the `output` directory.

### Process an MCP Server by ID

To process a server by ID:

```bash
uv run main.py --server your-server-id [--output folder-name]
```

### Process Multiple MCP Servers

To process multiple MCP servers:

```bash
uv run main.py --count 5 [--output folder-name]
```
## Architecture

### Monolithic Agent Approach

The original approach uses a single agent that takes the repository analysis and generates the complete MCP YAML file in one step.

### Specialized Agents Approach

The new approach breaks down the YAML generation into specialized agents:

1. **Metadata Agent**: Generates the basic metadata section (name, displayName, description, etc.)
2. **Source Agent**: Handles the source section
3. **Build Agent**: Creates the build section 
4. **Run Agent**: Creates the run section
5. **Assembler Agent**: Takes outputs from all agents and assembles the final YAML
6. **Validator Agent**: Validates the final YAML by running the MCP Server and updating the YAML file if necessary

This approach offers several benefits:
- Each agent can focus on a specific part of the YAML
- Better quality and more accurate outputs
- Parallel processing of independent sections
- Easier to update or improve specific sections
