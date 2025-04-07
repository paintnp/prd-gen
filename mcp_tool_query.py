#!/usr/bin/env python3
"""
MCP Server Tool Query Demo

This script demonstrates different approaches to query tools from an MCP server.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("mcp_tool_query")

def main():
    # Load environment variables
    load_dotenv()
    
    # MCP server configuration
    server_port = 9000
    server_url = f"http://localhost:{server_port}/sse"
    server_transport = "sse"
    server_timeout = 30
    
    # Try different approaches to configure the client and query tools
    
    # Approach 1: With server name "Exa MCP Server" (as used in the application)
    logger.info("\n=== Approach 1: Using 'Exa MCP Server' as server name ===")
    client_config_1 = {
        "Exa MCP Server": {
            "url": server_url,
            "transport": server_transport,
            "timeout": server_timeout
        }
    }
    logger.info(f"Client configuration: {json.dumps(client_config_1, indent=2)}")
    
    try:
        client_1 = MultiServerMCPClient(client_config_1)
        logger.info("Successfully created MCP client")
        
        # Get tools using normal get_tools() method
        tools_1 = client_1.get_tools()
        logger.info(f"Found {len(tools_1)} tools using get_tools()")
        for i, tool in enumerate(tools_1):
            logger.info(f"Tool {i+1}: {tool.name}")
        
        # Try alternate ways to get tools if available
        if hasattr(client_1, 'get_tools_for_server'):
            logger.info("Trying get_tools_for_server method...")
            server_tools = client_1.get_tools_for_server("Exa MCP Server")
            logger.info(f"Found {len(server_tools)} tools using get_tools_for_server()")
        
        # Try to access tools through server directly if possible
        if hasattr(client_1, 'servers') and "Exa MCP Server" in client_1.servers:
            logger.info("Trying to access server directly...")
            server = client_1.servers["Exa MCP Server"]
            if hasattr(server, 'get_tools'):
                direct_tools = server.get_tools()
                logger.info(f"Found {len(direct_tools)} tools by accessing server directly")
    
    except Exception as e:
        logger.error(f"Error with Approach 1: {e}")
    
    # Approach 2: With server name "" (empty string)
    logger.info("\n=== Approach 2: Using empty string as server name ===")
    client_config_2 = {
        "": {
            "url": server_url,
            "transport": server_transport,
            "timeout": server_timeout
        }
    }
    logger.info(f"Client configuration: {json.dumps(client_config_2, indent=2)}")
    
    try:
        client_2 = MultiServerMCPClient(client_config_2)
        logger.info("Successfully created MCP client")
        
        tools_2 = client_2.get_tools()
        logger.info(f"Found {len(tools_2)} tools")
        for i, tool in enumerate(tools_2):
            logger.info(f"Tool {i+1}: {tool.name}")
    except Exception as e:
        logger.error(f"Error with Approach 2: {e}")
    
    # Approach 3: Direct connection without server name
    logger.info("\n=== Approach 3: Using client.connect() method ===")
    client_config_3 = {}  # Empty config
    
    try:
        client_3 = MultiServerMCPClient(client_config_3)
        logger.info("Successfully created MCP client with empty config")
        
        # Try to connect directly
        if hasattr(client_3, 'connect'):
            logger.info(f"Connecting directly to {server_url}...")
            client_3.connect(url=server_url, transport=server_transport, timeout=server_timeout)
            
            tools_3 = client_3.get_tools()
            logger.info(f"Found {len(tools_3)} tools after direct connection")
            for i, tool in enumerate(tools_3):
                logger.info(f"Tool {i+1}: {tool.name}")
        else:
            logger.error("Client does not have connect() method")
    except Exception as e:
        logger.error(f"Error with Approach 3: {e}")
    
    # Approach 4: Try with different transports
    logger.info("\n=== Approach 4: Trying different transports ===")
    transports = ["sse", "websocket", "polling"]
    
    for transport in transports:
        logger.info(f"Trying with transport: {transport}")
        client_config_4 = {
            "Exa MCP Server": {
                "url": server_url.replace("/sse", f"/{transport}"),
                "transport": transport,
                "timeout": server_timeout
            }
        }
        
        try:
            client_4 = MultiServerMCPClient(client_config_4)
            tools_4 = client_4.get_tools()
            logger.info(f"Found {len(tools_4)} tools with {transport} transport")
            for i, tool in enumerate(tools_4):
                logger.info(f"Tool {i+1}: {tool.name}")
        except Exception as e:
            logger.error(f"Error with {transport} transport: {e}")

if __name__ == "__main__":
    main() 