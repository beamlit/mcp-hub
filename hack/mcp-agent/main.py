import asyncio
from src.processor.processor import workflow_main
from src.servers.glama import fetch_mcp_server, fetch_mcp_servers
import argparse
import os

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process MCP servers")
    parser.add_argument("--server", type=str, help="Server ID")
    parser.add_argument("--count", type=int, help="Number of MCP servers to generate")
    parser.add_argument("--output", type=str, default="output", help="Output directory")
    args = parser.parse_args()

    # Check if the output directory exists
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    if args.server:
        server = asyncio.run(fetch_mcp_server(args.server))
        if server:
            asyncio.run(workflow_main([server], args.output))
    elif args.count:
        servers = asyncio.run(fetch_mcp_servers(args.count))
        asyncio.run(workflow_main(servers, args.output))

   