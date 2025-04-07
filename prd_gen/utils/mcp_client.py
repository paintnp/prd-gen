"""
MCP Client utility module for connecting to MCP servers and retrieving tools.
"""

import asyncio
import logging
import time
import os
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
    
    def __init__(self, server_url: str = None, server_name: str = "mcp-server"):
        """
        Initialize the MCP Tool Provider.
        
        Args:
            server_url: URL of the MCP server's SSE endpoint.
            server_name: Name to identify this server connection.
        """
        if server_url is None:
            # Get URL from environment or use default
            server_url = os.environ.get("MCP_SERVER_URL", "http://localhost:9000/sse")
        
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
            
            # Try connecting multiple times in case of timing issues
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    await self.client.connect_to_server_via_sse(
                        self.server_name,
                        url=self.server_url
                    )
                    logger.info(f"Successfully connected to MCP server on attempt {attempt}")
                    self._connected = True
                    
                    # Immediately fetch tools after successful connection
                    self.tools = self.client.get_tools()
                    logger.info(f"Retrieved {len(self.tools)} tools from MCP server: {[tool.name for tool in self.tools]}")
                    
                    return True
                except Exception as e:
                    if attempt < max_retries:
                        logger.warning(f"Connection attempt {attempt} failed: {e}. Retrying...")
                        # Wait a bit before retrying
                        await asyncio.sleep(1)
                    else:
                        raise
            
            return False
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
        
        # If we already have tools from connect() method, return them
        if self.tools:
            return self.tools
        
        # Otherwise try to fetch them
        try:
            tools = self.client.get_tools()
            
            # Log each tool for better debugging
            tool_names = [tool.name for tool in tools]
            logger.info(f"Retrieved {len(tools)} tools from MCP server: {tool_names}")
            
            if tool_names:
                for i, tool in enumerate(tools):
                    logger.debug(f"Tool {i+1}: {tool.name} - {tool.description}")
            else:
                logger.warning("No tools retrieved from MCP server")
            
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
_mcp_tools = None  # Cache for tools

async def get_mcp_tools() -> List[BaseTool]:
    """
    Get MCP tools for use in the application. Creates and connects the client if needed.
    
    Returns:
        List[BaseTool]: List of tools from the MCP server.
    """
    global _mcp_client, _mcp_tools
    
    # If we already have cached tools, return them
    if _mcp_tools is not None and len(_mcp_tools) > 0:
        logger.debug(f"Using cached MCP tools ({len(_mcp_tools)} tools)")
        return _mcp_tools
    
    try:
        # Create a fresh client for each call to avoid connection conflicts
        client = MCPToolProvider()
        connected = await client.connect()
        
        if connected:
            tools = client.get_tools()
            if tools:
                # Cache the tools for future use
                _mcp_tools = tools
                # Update singleton instance
                _mcp_client = client
                return tools
        
        # If we couldn't get tools this way, try to use the existing singleton
        if _mcp_client is not None:
            logger.info("Using existing MCP client")
            tools = _mcp_client.get_tools()
            if tools:
                _mcp_tools = tools
                return tools
        
        logger.warning("Failed to retrieve tools from MCP server")
        return []
    except Exception as e:
        logger.error(f"Error in get_mcp_tools: {e}")
        # Return empty list if we get an exception
        return []

async def _safe_invoke_search_tool(search_tool, query):
    """
    Safely invoke a search tool with proper handling of async context.
    
    Args:
        search_tool: The search tool to invoke
        query: The search query string
        
    Returns:
        The search results
    """
    try:
        # Create a clean isolated task for the search operation
        if hasattr(search_tool, 'ainvoke'):
            # For aiohttp-based MCP client tools
            result = await search_tool.ainvoke({"query": query})
            return result
        elif hasattr(search_tool, 'invoke'):
            # For synchronous tools
            return search_tool.invoke({"query": query})
        else:
            # Try direct function call
            return search_tool(query=query)
    except Exception as e:
        logger.error(f"Error invoking search tool: {e}")
        # Return a minimally formatted error result
        return {
            "error": f"Search failed: {str(e)}",
            "results": [
                {
                    "title": "Search Error",
                    "url": "N/A",
                    "content": f"An error occurred during search: {str(e)}. Please try a different query or proceed without search results."
                }
            ]
        }

def run_async(coro):
    """
    Helper function to run async code in a synchronous context.
    
    Args:
        coro: A coroutine or coroutine function to run
        
    Returns:
        The result of running the coroutine
    """
    try:
        # Get or create an event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop in this thread, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Special handling for search tool invocation
        if isinstance(coro, object) and hasattr(coro, '__await__'):
            # This is already a coroutine object
            return loop.run_until_complete(coro)
        elif callable(coro):
            # This is a coroutine function, call it first
            return loop.run_until_complete(coro())
        else:
            logger.warning(f"Unknown object passed to run_async: {type(coro)}")
            return None
    except Exception as e:
        logger.error(f"Error in run_async: {e}")
        # Return None instead of raising to avoid stopping the process
        return None

def search_web(search_tool, query):
    """
    A syncronous wrapper for search tool invocation that properly handles async context.
    
    Args:
        search_tool: The search tool to use
        query: The search query string
        
    Returns:
        The search results
    """
    try:
        result = run_async(_safe_invoke_search_tool(search_tool, query))
        if result is None:
            # If we got None due to an error, return a fallback
            logger.warning(f"Search failed for query: {query}, using fallback")
            return {
                "warning": "Search could not be completed",
                "query": query,
                "results": []
            }
        return result
    except Exception as e:
        logger.error(f"Error in search_web: {e}")
        # Return a minimal result on error
        return {
            "error": str(e),
            "query": query,
            "results": []
        } 