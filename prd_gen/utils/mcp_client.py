"""
MCP Client utility module for connecting to MCP servers and retrieving tools.
"""

import asyncio
import logging
from typing import List, Optional, Any, Dict
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool
from prd_gen.utils.debugging import setup_logging

# Set up logging
logger = setup_logging()

class MCPToolProvider:
    """
    Utility class for connecting to MCP servers and retrieving tools.
    """
    
    def __init__(self, server_url: str = "http://localhost:9000/sse", server_name: str = "mcp-server"):
        """
        Initialize the MCP Tool Provider.
        
        Args:
            server_url: URL of the MCP server's SSE endpoint.
            server_name: Name to identify this server connection.
        """
        self.server_url = server_url
        self.server_name = server_name
        self.client = MultiServerMCPClient()
        self.tools = []
        self._connected = False
        
    async def connect(self) -> bool:
        """
        Connect to the MCP server.
        
        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            logger.info(f"Connecting to MCP server at {self.server_url}...")
            await self.client.connect_to_server_via_sse(
                self.server_name,
                url=self.server_url
            )
            logger.info("Successfully connected to MCP server")
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Error connecting to MCP server: {e}")
            self._connected = False
            return False
    
    def get_tools(self) -> List[BaseTool]:
        """
        Get all available tools from the MCP server.
        
        Returns:
            List[BaseTool]: List of LangChain tools from the MCP server.
        """
        if not self._connected:
            logger.warning("Not connected to MCP server. Call connect() first.")
            return []
        
        try:
            tools = self.client.get_tools()
            logger.info(f"Retrieved {len(tools)} tools from MCP server")
            self.tools = tools
            return tools
        except Exception as e:
            logger.error(f"Error retrieving tools from MCP server: {e}")
            return []
    
    def search_tool_available(self) -> bool:
        """
        Check if the search_web tool is available.
        
        Returns:
            bool: True if the search_web tool is available, False otherwise.
        """
        return any(tool.name == "search_web" for tool in self.tools)

# Singleton instance to be used across the application
_mcp_client = None

async def get_mcp_tools() -> List[BaseTool]:
    """
    Get MCP tools for use in the application. Creates and connects the client if needed.
    
    Returns:
        List[BaseTool]: List of tools from the MCP server.
    """
    global _mcp_client
    
    if _mcp_client is None:
        _mcp_client = MCPToolProvider()
        await _mcp_client.connect()
    
    return _mcp_client.get_tools()

def run_async(coro):
    """Helper function to run async code in a synchronous context."""
    return asyncio.get_event_loop().run_until_complete(coro) 