#!/usr/bin/env python3
"""
Test script to connect to MCP server on port 9000 and list available tools.
"""

from langchain_mcp_adapters.client import MultiServerMCPClient
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_client_test")

def main():
    # Connect to MCP server on port 9000
    server_url = "http://localhost:9000/sse"
    server_name = "Exa MCP Server"
    logger.info(f"Connecting to MCP server at {server_url}")
    
    try:
        # Create MCP client configuration
        client_config = {
            server_name: {
                "url": server_url,
                "transport": "sse",
                "timeout": 30
            }
        }
        
        # Create MCP client
        client = MultiServerMCPClient(client_config)
        logger.info("Successfully connected to MCP server")
        
        # Get available tools
        tools = client.get_tools()
        
        # Print tool information
        logger.info(f"Found {len(tools)} tools:")
        for i, tool in enumerate(tools):
            logger.info(f"Tool {i+1}: {tool.name}")
            logger.info(f"  Description: {tool.description}")
            if hasattr(tool, 'parameters'):
                logger.info(f"  Parameters: {tool.parameters}")
            print()
            
        return tools
        
    except Exception as e:
        logger.error(f"Error connecting to MCP server: {e}")
        return None

if __name__ == "__main__":
    main() 