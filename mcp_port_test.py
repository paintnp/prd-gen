#!/usr/bin/env python3
"""
Comprehensive MCP Server Port Test

This script tests whether an MCP server is available on port 9000
by attempting connections with different server names and configurations.
It also tests if any tools are registered and functioning properly.
"""

import os
import logging
import json
import socket
import subprocess
import time
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_port_test")

def check_port_in_use(port):
    """Check if a port is in use by any process."""
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Set a timeout of 1 second
        s.settimeout(1)
        # Try to connect to the port
        result = s.connect_ex(('localhost', port))
        s.close()
        # If result is 0, the port is open
        return result == 0
    except Exception as e:
        logger.error(f"Error checking port: {e}")
        return False

def find_processes_on_port(port):
    """Find processes listening on a specific port."""
    try:
        # Use lsof command to find processes using the port
        result = subprocess.run(['lsof', '-i', f':{port}'], 
                                capture_output=True, text=True)
        logger.debug(f"Processes on port {port}:\n{result.stdout}")
        return result.stdout
    except Exception as e:
        logger.error(f"Error finding processes on port {port}: {e}")
        return ""

def test_mcp_server(server_name, port=9000):
    """Test connection to an MCP server with specified name and port."""
    logger.info(f"Testing MCP server '{server_name}' on port {port}")
    
    # Configure MCP client
    server_url = f"http://localhost:{port}/sse"
    server_transport = "sse"
    server_timeout = 30
    
    client_config = {
        server_name: {
            "url": server_url,
            "transport": server_transport,
            "timeout": server_timeout
        }
    }
    
    logger.debug(f"Client config: {json.dumps(client_config, indent=2)}")
    
    try:
        # Initialize the MCP client
        client = MultiServerMCPClient(client_config)
        logger.info(f"Successfully connected to MCP client for server '{server_name}'")
        
        # Try to get the available tools
        logger.info("Retrieving available tools...")
        tools = client.get_tools()
        
        # Print tool information
        if tools:
            logger.info(f"Found {len(tools)} tools on server '{server_name}':")
            for i, tool in enumerate(tools):
                logger.info(f"Tool {i+1}: {tool.name}")
                logger.info(f"  Description: {tool.description}")
                
                # Test the tool if it's search_web
                if tool.name == "search_web":
                    logger.info("Testing search_web tool...")
                    try:
                        result = tool.func("stock portfolio analysis")
                        logger.info("Search tool test successful!")
                        if result:
                            logger.debug(f"Result type: {type(result)}")
                            if isinstance(result, dict) and 'results' in result:
                                logger.info(f"Found {len(result['results'])} search results")
                                for i, res in enumerate(result['results'][:2]):  # Show first 2 results
                                    logger.info(f"Result {i+1}: {res.get('title', 'No title')}")
                            else:
                                logger.debug(f"Result preview: {str(result)[:200]}...")
                    except Exception as e:
                        logger.error(f"Error testing search tool: {e}")
            
            return True, tools
        else:
            logger.warning(f"No tools found on MCP server '{server_name}'")
            return True, []
        
    except Exception as e:
        logger.error(f"Error connecting to MCP server '{server_name}': {e}")
        return False, []

def main():
    # Load environment variables
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    exa_api_key = os.environ.get("EXA_API_KEY")
    
    logger.info("Starting MCP port test...")
    logger.info(f"OpenAI API key: {api_key[:5]}...{api_key[-5:] if api_key else 'Not found'}")
    logger.info(f"Exa API key: {exa_api_key[:5]}...{exa_api_key[-5:] if exa_api_key else 'Not found'}")
    
    # Check if port 9000 is in use
    port_in_use = check_port_in_use(9000)
    logger.info(f"Port 9000 is {'in use' if port_in_use else 'not in use'}")
    
    if not port_in_use:
        logger.error("No server detected on port 9000. MCP server may not be running.")
        print("\nMCP Port Test FAILED: No server detected on port 9000")
        return False
    
    # Find processes using port 9000
    processes = find_processes_on_port(9000)
    logger.info(f"Found processes on port 9000:\n{processes}")
    
    # Try different server names that might be used
    server_names = [
        "Exa MCP Server",  # As used in the application
        "TestMCPServer",   # As defined in mcp_server.py
        "MCP Server",      # Generic name
        "EXA_SERVER",      # Another possibility
        ""                 # Empty string as fallback
    ]
    
    success = False
    for name in server_names:
        logger.info(f"Attempting connection with server name: '{name}'")
        connected, tools = test_mcp_server(name)
        
        if connected and tools:
            logger.info(f"Successfully connected to MCP server with name '{name}' and found {len(tools)} tools")
            success = True
            break
        elif connected:
            logger.info(f"Connected to MCP server with name '{name}' but found no tools")
        else:
            logger.info(f"Failed to connect to MCP server with name '{name}'")
    
    if success:
        print("\nMCP Port Test PASSED: Successfully connected and found tools")
        return True
    else:
        print("\nMCP Port Test WARNING: Connected to server but found no tools")
        return False

if __name__ == "__main__":
    main() 