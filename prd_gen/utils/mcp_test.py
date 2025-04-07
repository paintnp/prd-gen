"""
Utility to test MCP server connection.

This script can be used to test the connection to the MCP server.
"""

import os
import json
import inspect
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Load environment variables
load_dotenv()

def test_mcp_connection():
    """Test the connection to the MCP server."""
    
    # Use the correct server configuration
    server_name = "Exa MCP Server"
    server_url = "http://localhost:9000/sse"
    server_transport = "sse"
    server_timeout = 30
    
    print(f"Testing MCP server connection at {server_url}...")
    print(f"Server name: {server_name}")
    print(f"Server transport: {server_transport}")
    
    # Create the MCP client with the correct server name
    client_config = {
        server_name: {
            "url": server_url,
            "transport": server_transport,
            "timeout": server_timeout
        }
    }
    
    print(f"Client configuration: {json.dumps(client_config, indent=2)}")
    
    client = MultiServerMCPClient(client_config)
    
    # Get available tools
    try:
        tools = client.get_tools()
        print(f"Successfully connected to MCP server!")
        
        if tools:
            print(f"Found {len(tools)} tools:")
            for i, tool in enumerate(tools):
                print(f"  {i+1}. {tool.name}: {tool.description}")
                if hasattr(tool, 'args_schema'):
                    print(f"     Parameters: {tool.args_schema}")
        else:
            print("No tools found on the MCP server via discovery.")
            
        # Inspect the client object to see available methods
        print("\nAvailable methods in MultiServerMCPClient:")
        for name, method in inspect.getmembers(client, predicate=inspect.ismethod):
            if not name.startswith('_'):
                print(f"  {name}")
                
        # Inspect private methods too
        print("\nPrivate methods in MultiServerMCPClient:")
        for name, method in inspect.getmembers(client, predicate=inspect.ismethod):
            if name.startswith('_') and not name.startswith('__'):
                print(f"  {name}")
            
        # Try to manually create a search_web tool
        print("\nCreating manual search_web tool...")
        try:
            # Try to create a manual search tool
            search_tool = Tool(
                name="search_web",
                description="Search the web for information",
                func=lambda query: client._call_tool(server_name, "search_web", {"query": query})
            )
            
            # Try using the tool
            query = "Product management trends 2024"
            print(f"Testing search with query: '{query}'")
            result = search_tool.invoke(query)
            print(f"Search result: {json.dumps(result, indent=2) if result else 'No result'}")
        except Exception as e:
            print(f"Error creating or using manual tool: {e}")
            
        return True
    except Exception as e:
        print(f"Error connecting to MCP server: {e}")
        return False

if __name__ == "__main__":
    test_mcp_connection() 