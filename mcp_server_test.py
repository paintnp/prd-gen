#!/usr/bin/env python3
"""
Test script to verify the MCP server on port 9000 is functioning correctly.
This script uses the same API as the main application to test connectivity.
"""

import os
import logging
import json
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_server_test")

def main():
    # Load environment variables
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    exa_api_key = os.environ.get("EXA_API_KEY")
    
    logger.info(f"OpenAI API key: {api_key[:5]}...{api_key[-5:] if api_key else 'Not found'}")
    logger.info(f"Exa API key: {exa_api_key[:5]}...{exa_api_key[-5:] if exa_api_key else 'Not found'}")
    
    # MCP server configuration - same as used in the application
    server_name = "Exa MCP Server"
    server_url = "http://localhost:9000/sse"
    server_transport = "sse"
    server_timeout = 30
    
    # Configure MCP client
    client_config = {
        server_name: {
            "url": server_url,
            "transport": server_transport,
            "timeout": server_timeout
        }
    }
    
    logger.info(f"Connecting to MCP server at {server_url}")
    logger.debug(f"Client config: {json.dumps(client_config, indent=2)}")
    
    try:
        # Initialize the MCP client - same as in the application
        client = MultiServerMCPClient(client_config)
        logger.info("Successfully connected to MCP client")
        
        # Try to get the available tools
        logger.info("Retrieving available tools...")
        tools = client.get_tools()
        
        # Print tool information
        if tools:
            logger.info(f"Successfully retrieved {len(tools)} tools:")
            for i, tool in enumerate(tools):
                logger.info(f"Tool {i+1}: {tool.name}")
                logger.info(f"  Description: {tool.description}")
                if hasattr(tool, 'schema'):
                    logger.info(f"  Schema: {tool.schema}")
                logger.info("")
                
            # Test the search_web tool if available
            search_tool = next((t for t in tools if t.name == "search_web"), None)
            if search_tool:
                logger.info("Testing search_web tool...")
                try:
                    result = search_tool.func("stock portfolio analysis best practices")
                    logger.info("Search tool test successful!")
                    logger.debug(f"Search result preview: {result[:200]}...")
                except Exception as e:
                    logger.error(f"Error testing search tool: {e}")
            else:
                logger.warning("search_web tool not found in available tools")
        else:
            logger.warning("No tools found on the MCP server")
            
        return True
    
    except Exception as e:
        logger.error(f"Error connecting to MCP server: {e}")
        logger.exception("Exception details:")
        return False

if __name__ == "__main__":
    success = main()
    print(f"\nMCP Server Test {'PASSED' if success else 'FAILED'}") 