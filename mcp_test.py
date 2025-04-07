#!/usr/bin/env python3

"""
Simple test script to verify connection to MCP server on port 9000
"""

import asyncio
import logging
from langchain_mcp_adapters.client import MultiServerMCPClient

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_test")

async def test_mcp_connection():
    """Test connection to MCP server on port 9000"""
    logger.info("Testing connection to MCP server on port 9000...")
    
    # Create a MultiServerMCPClient instance
    client = MultiServerMCPClient()
    
    try:
        # Connect to the MCP server on port 9000 via SSE
        logger.info("Attempting to connect to MCP server on port 9000...")
        await client.connect_to_server_via_sse(
            'test-connection',
            url='http://localhost:9000/sse'
        )
        
        # Try to get the available tools
        logger.info("Getting available tools...")
        tools = client.get_tools()
        
        # Print the available tools
        logger.info(f"Found {len(tools)} tools:")
        for i, tool in enumerate(tools):
            logger.info(f"  Tool {i+1}: {tool.name} - {tool.description}")
        
        logger.info("Connection test successful!")
        return True
        
    except Exception as e:
        logger.error(f"Error connecting to MCP server: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting MCP server connection test")
    result = asyncio.run(test_mcp_connection())
    
    if result:
        logger.info("✅ MCP server on port 9000 is accessible and working")
    else:
        logger.error("❌ Failed to connect to MCP server on port 9000") 