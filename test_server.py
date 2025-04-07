#!/usr/bin/env python3
"""
Test script for the MCP server.

This script tests the MCP server directly using the MCP client library.
"""

import os
import json
import asyncio
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client

# Load environment variables
load_dotenv()

async def test_mcp_server():
    """Test the MCP server directly."""
    # Server details
    server_name = "TestMCPServer"
    server_url = "http://localhost:9001/sse"
    
    print(f"Connecting to MCP server at {server_url}...")
    
    try:
        # Connect to the server using SSE
        async with sse_client(server_url) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                
                # List available tools
                tools = await session.list_tools()
                print(f"Available tools: {json.dumps(tools, indent=2)}")
                
                # If search_web tool is available, test it
                if any(tool["name"] == "search_web" for tool in tools):
                    print("\nTesting search_web tool...")
                    result = await session.invoke_tool(
                        "search_web", 
                        {"query": "What are the current trends in product management?"}
                    )
                    print(f"Search results: {json.dumps(result, indent=2)}")
                else:
                    print("\nWarning: search_web tool not found!")
                    
                print("\nTest completed successfully.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_server()) 