"""
Agents Package

This package provides a structured set of agents for different parts of MCP YAML generation,
all built on a common BaseAgent class.
"""

# Import the base agent class
from .base_agent import BaseAgent

# Import all agent implementations
from .metadata_agent import MetadataAgent, create_metadata_agent, MetadataResponse
from .source_agent import SourceAgent, create_source_agent, SourceResponse
from .build_agent import BuildAgent, create_build_agent, BuildResponse
from .run_agent import RunAgent, create_run_agent, RunResponse
from .validator_agent import ValidatorAgent, create_validator_agent, run_mcp_validation

__all__ = [
    # Base class
    'BaseAgent',
    
    # Agent factories (for backward compatibility)
    'create_validator_agent',
    'create_metadata_agent',
    'create_source_agent',
    'create_build_agent',
    'create_run_agent',
    
    # Agent classes
    'ValidatorAgent',
    'MetadataAgent',
    'SourceAgent',
    'BuildAgent',
    'RunAgent',
    
    # Response models
    'MetadataResponse',
    'SourceResponse',
    'BuildResponse',
    'RunResponse',
    
    # Utility functions
    'run_mcp_validation'
]
