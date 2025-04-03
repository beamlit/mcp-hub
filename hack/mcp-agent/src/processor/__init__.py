"""
Processor module for MCP agent.

This module contains the main workflow and processing logic for generating MCP YAML files.
"""

from .processor import (
    Server,
    MCPState,
    workflow_main,
    process_mcp_server
)

__all__ = [
    'Server',
    'MCPState',
    'workflow_main',
    'process_mcp_server'
]
