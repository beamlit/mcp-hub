# MCP Agent

A multi-agent system for automatically generating `<mcp>.yaml` files from repository analysis.

## Overview

The MCP Agent is a tool that analyzes repositories to automatically generate MCP module definition files (`<mcp>.yaml`). It uses a combination of specialized LLM-powered agents to:

1. Analyze repository structure and code
2. Extract tool definitions
3. Generate a properly formatted `<mcp>.yaml` file
4. Validate and correct the YAML output

## Installation

1. Clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate the virtual environment: `source .venv/bin/activate`
4. Install dependencies: `pip install -e .`
5. Set up the OpenAI API key in your environment: `export OPENAI_API_KEY=your_api_key_here`

## Usage

The MCP Agent offers both a monolithic agent approach (original) and a specialized agents approach (new) for generating MCP YAML files. The specialized approach often produces higher quality results by focusing on each section separately.

### Process a Local Repository

To process a local repository:

```bash
python main.py --local /path/to/repo [--specialized]
```

The generated YAML file will be saved in the `output` directory.

### Process an MCP Server by ID

To process a server by ID:

```bash
python main.py --server your-server-id [--specialized]
```

### Process Multiple MCP Servers

To process multiple MCP servers:

```bash
python main.py --count 5 [--specialized]
```

### Options

- `--specialized`: Use specialized agents for each part of the YAML generation (recommended for better quality)
  - Without this flag, the default monolithic agent approach is used

## Architecture

### Monolithic Agent Approach

The original approach uses a single agent that takes the repository analysis and generates the complete MCP YAML file in one step.

### Specialized Agents Approach

The new approach breaks down the YAML generation into specialized agents:

1. **Metadata Agent**: Generates the basic metadata section (name, displayName, description, etc.)
2. **Tools Agent**: Analyzes and generates the tools section
3. **Source Agent**: Handles the source section
4. **Build Agent**: Creates the build section
5. **Config Agent**: Identifies and structures configuration parameters
6. **Entrypoint Agent**: Creates the command entrypoint based on config
7. **Environment Agent**: Creates environment variables referencing config values
8. **Assembler Agent**: Takes outputs from all agents and assembles the final YAML

This approach offers several benefits:
- Each agent can focus on a specific part of the YAML
- Better quality and more accurate outputs
- Parallel processing of independent sections
- Easier to update or improve specific sections

## License

[MIT License](LICENSE) 