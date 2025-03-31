"""
Processor module for MCP agent.

This module contains functions for processing MCP servers, including:
- Static analysis of repositories
- Multi-agent processing of MCP YAML generation
- Assembly of YAML sections
- Validation of YAML files
"""

from .processor import (
    workflow_main,
    process_mcp_server,
    multi_agent_layer,
    assemble_mcp_server,
    validate_mcp_server,
)

from .static_analyse import (
    extract_repository_info,
    format_analysis_output,
)

__all__ = [
    'workflow_main',
    'process_mcp_server',
    'multi_agent_layer',
    'assemble_mcp_server',
    'validate_mcp_server',
    'extract_repository_info',
    'format_analysis_output',
    'StaticAnalysisResult',
]
