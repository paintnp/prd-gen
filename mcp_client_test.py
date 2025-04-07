#!/usr/bin/env python3

"""
Comprehensive test script for the MCP client that powers the PRD generator.
Tests direct connection, tool retrieval, and search tool availability.
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our MCP client implementation
from prd_gen.utils.mcp_client import MCPToolProvider, run_async, get_mcp_tools

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_client_test")

# Load environment variables
load_dotenv()

async def test_direct_connection():
    """Test direct connection to MCP server using our MCPToolProvider"""
    logger.info("Testing direct connection to MCP server...")
    
    # Get server URL from environment or use default
    server_url = os.environ.get("MCP_SERVER_URL", "http://localhost:9000/sse")
    
    # Create our MCPToolProvider instance
    client = MCPToolProvider(server_url=server_url)
    
    # Connect to the server
    connected = await client.connect()
    if not connected:
        logger.error("Failed to connect to MCP server")
        return False
    
    # Get available tools
    tools = client.get_tools()
    
    # Log information about tools
    if not tools:
        logger.warning("No tools found on MCP server")
        return False
    
    logger.info(f"Successfully retrieved {len(tools)} tools:")
    for i, tool in enumerate(tools):
        logger.info(f"  Tool {i+1}: {tool.name} - {tool.description}")
    
    # Check for search_web tool
    has_search = client.search_tool_available()
    if has_search:
        logger.info("✅ search_web tool is available")
    else:
        logger.warning("⚠️ search_web tool is NOT available")
    
    return True

async def run_test():
    """Run the MCP client test"""
    logger.info("Starting MCP client test")
    
    # Test direct connection
    success = await test_direct_connection()
    
    if success:
        logger.info("✅ MCP client test passed - search_web tool available")
        return True
    else:
        logger.error("❌ MCP client test failed - couldn't retrieve tools")
        return False

if __name__ == "__main__":
    # Process command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Test MCP client connection")
    parser.add_argument("--method", choices=["direct", "get_tools"], default="direct",
                        help="Test method to use: direct connection or get_mcp_tools()")
    args = parser.parse_args()
    
    logger.info(f"MCP Client Test - Testing connectivity to MCP server using {args.method} method")
    
    if args.method == "direct":
        # Test direct connection 
        success = run_async(run_test())
    else:
        # Test get_mcp_tools function
        try:
            tools = run_async(get_mcp_tools())
            has_search = any(tool.name == "search_web" for tool in tools)
            
            if has_search:
                logger.info(f"✅ Successfully retrieved {len(tools)} tools using get_mcp_tools()")
                logger.info("✅ search_web tool is available")
                success = True
            else:
                logger.warning(f"⚠️ Retrieved {len(tools)} tools but search_web is NOT available")
                success = False
        except Exception as e:
            logger.error(f"❌ Error using get_mcp_tools(): {e}")
            success = False
    
    if success:
        logger.info("✅ MCP client test passed")
        sys.exit(0)
    else:
        logger.error("❌ MCP client test failed")
        sys.exit(1) 