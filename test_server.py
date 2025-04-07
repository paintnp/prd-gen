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
import requests

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
                
                # If search_web_summarized tool is available, test it
                if any(tool["name"] == "search_web_summarized" for tool in tools):
                    print("\nTesting search_web_summarized tool...")
                    response = requests.post(
                        f"{server_url}/mcp_Exa_MCP_Server_search_web_summarized",
                        json={"query": "What is a Product Requirements Document", "summary_focus": "key points"}
                    )
                    if response.status_code == 200:
                        print("✅ search_web_summarized test successful!")
                        summarized_results = response.json()
                        print(f"Results: {json.dumps(summarized_results, indent=2)[:500]}...")
                    else:
                        print(f"❌ search_web_summarized test failed with status code {response.status_code}")
                        print(response.text)
                else:
                    print("\nWarning: search_web_summarized tool not found!")
                    
                    # Check for search_web as fallback
                    if any(tool["name"] == "search_web" for tool in tools):
                        print("\nTesting search_web tool (fallback)...")
                        response = requests.post(
                            f"{server_url}/mcp_Exa_MCP_Server_search_web",
                            json={"query": "What is a Product Requirements Document"}
                        )
                        if response.status_code == 200:
                            print("✅ search_web test successful!")
                        else:
                            print(f"❌ search_web test failed with status code {response.status_code}")
                            print(response.text)
                    else:
                        print("\nWarning: No search tools found!")
                    
                print("\nTest completed successfully.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_server()) 