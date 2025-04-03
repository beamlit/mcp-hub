import pytest
from src.processor.processor import (
    MCPState,
    Server,
    process_mcp_server,
    workflow_main
)

@pytest.mark.asyncio
async def test_process_mcp_server():
    """Test processing a single MCP server."""
    server = Server(
        name="test-server",
        repository={
            "url": "https://github.com/example/test-repo"
        }
    )
    
    safe_name, yaml_content, errors = await process_mcp_server(server, "https://github.com/example/test-repo")
    assert safe_name == "test-server"
    # Empty content is expected since the repo doesn't exist
    assert yaml_content == ""
    # Errors should be present since repo doesn't exist
    assert len(errors) > 0
    assert "Repository cloning failed" in errors[0]

@pytest.mark.asyncio
async def test_workflow_main():
    """Test the main workflow with multiple servers."""
    servers = [
        Server(
            name="test-server-1",
            repository={
                "url": "https://github.com/example/test-repo-1"
            }
        ),
        Server(
            name="test-server-2",
            repository={
                "url": "https://github.com/example/test-repo-2"
            }
        )
    ]
    
    summary = await workflow_main(servers, "output")
    assert "Processed 2 MCP servers" in summary