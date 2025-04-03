#!/usr/bin/env python3
"""
Test script for the validator agent implementation.

This script instantiates the validator agent and tests its functionality
with a simple MCP YAML configuration.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Import the agent
from src.agents import ValidatorAgent, run_mcp_validation


async def main():
    """Run the validator agent test."""
    # Simple test YAML
    test_yaml = """apiVersion: v1
kind: MCP
metadata:
  name: test-mcp
  description: A test MCP module
spec:
  build:
    entrypoint: python server.py
  runtime:
    environment:
      - name: PORT
        value: "8080"
  config:
    - name: port
      description: The port to run the server on
      type: number
      default: 8080
"""

    print("Testing validator agent:")
    print("=======================")
    
    # Create validator agent
    print("Creating validator agent...")
    validator = ValidatorAgent()
    validator.llm = ChatOpenAI(model_name="gpt-4o", temperature=0)
    validator.initialize_agent()
    
    # Test the agent
    print("Testing validator implementation...")
    result = await validator.ainvoke({
        "mcp_yaml": test_yaml,
        "input": "Repository path: /tmp/test_repo"
    })
    
    print("\nValidator result:")
    print("================")
    print(result)
    
    # Test the run_mcp_validation function
    print("\nTesting run_mcp_validation function...")
    validated_yaml = await run_mcp_validation(
        mcp_yaml=test_yaml,
        repo_path="/tmp/test_repo",
        max_iterations=3
    )
    
    print("\nValidation result:")
    print("================")
    if validated_yaml:
        print(f"Validation successful, YAML length: {len(validated_yaml)}")
    else:
        print("Validation failed")


if __name__ == "__main__":
    # Import ChatOpenAI here to avoid circular imports
    from langchain_openai import ChatOpenAI
    
    # Run the async main function
    asyncio.run(main()) 