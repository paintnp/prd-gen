"""
MCP Client utility module for connecting to MCP servers and retrieving tools.
"""

import asyncio
import logging
import time
import os
import json
import inspect
from typing import List, Optional, Any, Dict, Union
from functools import partial
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool, tool
from prd_gen.utils.debugging import setup_logging
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, create_model, Field

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

# Cached tools for efficiency
_mcp_tools = None  # Cache for tools
_mcp_client = None  # Cached MCP client
_mcp_session_id = None  # Cached session ID

def args_schema_from_openapi(schema: Dict[str, Any]) -> type[BaseModel]:
    """
    Create a Pydantic model from an OpenAPI schema.
    
    Args:
        schema (Dict[str, Any]): The OpenAPI schema.
        
    Returns:
        type[BaseModel]: The Pydantic model.
    """
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    
    # Create field definitions
    fields = {}
    for name, prop in properties.items():
        field_type = str  # Default type
        if prop.get("type") == "boolean":
            field_type = bool
        elif prop.get("type") == "integer":
            field_type = int
        elif prop.get("type") == "number":
            field_type = float
        
        # Set default if available, otherwise None
        default = prop.get("default", ... if name in required else None)
        
        # Add field with type and default
        fields[name] = (field_type, Field(default=default, description=prop.get("description", "")))
    
    # Create the model
    model_name = schema.get("title", "ArgsSchema")
    return create_model(model_name, **fields)

async def create_sse_connection(url=None):
    """
    Create a connection to the MCP server.
    
    Args:
        url (str, optional): The SSE server URL. If None, uses the default URL.
        
    Returns:
        Tuple[MultiServerMCPClient, str]: The MCP client and session ID
    """
    url = url or os.environ.get("MCP_SERVER_URL", "http://localhost:9000/sse")
    logger.info(f"Connecting to MCP server at {url}...")
    
    try:
        # Create the client without any initial connections
        client = MultiServerMCPClient()
        
        # Connect to the server via SSE with proper error handling
        connection_id = "default"
        
        # Use a try/except with specific handling for TaskGroup cancellation
        for attempt in range(1, 4):  # Try up to 3 times
            try:
                await client.connect_to_server_via_sse(connection_id, url=url)
                logger.info(f"Successfully connected to MCP server on attempt {attempt}")
                return client, connection_id
            except Exception as e:
                # Check for TaskGroup cancellation errors
                error_msg = str(e).lower()
                is_cancel_scope_error = (
                    "cancel scope" in error_msg or 
                    "cancelled by cancel scope" in error_msg or
                    "runtime error: unhandled errors in a taskgroup" in error_msg
                )
                
                # Check if it's a 404 error
                is_404 = "404" in error_msg or "not found" in error_msg
                
                if is_cancel_scope_error:
                    logger.error(f"TaskGroup cancellation error: {e}")
                    # Create a fresh client and retry immediately
                    client = MultiServerMCPClient()
                    continue
                    
                if is_404 and "/sse" not in url and attempt == 1:
                    suggested_url = url
                    if suggested_url.endswith("/"):
                        suggested_url = suggested_url[:-1]
                    suggested_url += "/sse"
                    logger.error(f"404 Not Found error - endpoint may be incorrect. Try {suggested_url} instead.")
                    
                if attempt < 3:  # Don't log on the last attempt
                    logger.warning(f"Connection attempt {attempt} failed: {e}. Retrying...")
                    await asyncio.sleep(1)
                else:
                    # Last attempt failed
                    logger.error(f"Error connecting to MCP server: {e}")
                    raise Exception(f"Failed to connect to MCP server at {url} after {attempt} attempts.") from e
    except Exception as e:
        logger.error(f"Error creating MCP client: {e}")
        raise Exception(f"Error creating MCP client: {e}") from e

async def get_mcp_tools():
    """
    Get tools from the MCP server. Uses caching to avoid redundant connections.
    
    Returns:
        List[BaseTool]: The tools available from the MCP server
    """
    global _mcp_tools, _mcp_client, _mcp_session_id
    
    # Check if we should use a fresh connection
    force_new = os.environ.get("MCP_FORCE_NEW_CONNECTION", "").lower() in ("true", "1", "yes")
    
    # If we already have cached tools and we're not forcing a new connection, return them
    if _mcp_tools is not None and len(_mcp_tools) > 0 and not force_new:
        logger.debug(f"Using cached MCP tools ({len(_mcp_tools)} tools)")
        return _mcp_tools
    
    try:
        # Try to use the connection function
        client, connection_id = await create_sse_connection()
        _mcp_client = client
        _mcp_session_id = connection_id
        
        # Get the tools
        try:
            # Get tools from the MCP server
            tools = client.get_tools()
            
            # Log the number of tools found
            if tools:
                logger.info(f"Retrieved {len(tools)} tools from MCP server: {[t.name for t in tools]}")
                # Cache the tools for future use
                _mcp_tools = tools
            else:
                logger.warning("No tools found on the MCP server")
            
            return tools
        except Exception as e:
            logger.error(f"Error processing tools: {e}")
            return []
    except Exception as e:
        logger.error(f"Error connecting to MCP server: {e}")
        logger.warning("Failed to retrieve tools from MCP server")
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
    Run an async coroutine in a synchronous context.
    
    Args:
        coro: The coroutine to run
        
    Returns:
        The result of the coroutine
    """
    try:
        # Create a new event loop if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        # Check if the loop is running
        if loop.is_running():
            # Already in an async context, return a future
            return coro
        else:
            # Run the coroutine in the event loop
            return loop.run_until_complete(coro)
    except Exception as e:
        logger.error(f"Error in run_async: {e}")
        raise

async def search_web(tool, query):
    """
    Search the web using the MCP search_web tool.
    
    Args:
        tool (BaseTool): The search_web tool from the MCP server.
        query (str): The search query.
        
    Returns:
        Dict[str, Any]: The search results.
    """
    try:
        # Add detailed debug logging
        logger.info(f"Searching web with query: '{query}'")
        logger.info(f"Using tool: {tool.name} (type: {type(tool).__name__})")
        
        # List available methods on the tool
        methods = [method for method in dir(tool) if not method.startswith('_')]
        logger.info(f"Tool methods: {methods}")
        
        # Create input as a dictionary for JSON schema
        tool_input = {"query": query}
        logger.info(f"Created tool input: {tool_input}")
        
        # Try to use the most appropriate method
        if hasattr(tool, 'ainvoke'):
            logger.info("Using ainvoke method")
            result = await tool.ainvoke(tool_input)
            logger.info(f"Result type: {type(result).__name__}")
            if isinstance(result, str):
                logger.info(f"Result is a string of length {len(result)}")
                # If result is a string, try to parse it as JSON
                if result.strip().startswith('{'):
                    import json
                    try:
                        return json.loads(result)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse result as JSON")
                # Return a properly formatted dict
                return {
                    "query": query,
                    "results": [
                        {
                            "title": "Search Result",
                            "url": "https://example.com",
                            "content": result[:50000] if len(result) > 50000 else result
                        }
                    ]
                }
            return result
        elif hasattr(tool, 'arun'):
            logger.info("Using arun method")
            result = await tool.arun(tool_input)
            logger.info(f"Result type: {type(result).__name__}")
            if isinstance(result, str):
                logger.info(f"Result is a string of length {len(result)}")
                # Return a properly formatted dict
                return {
                    "query": query,
                    "results": [
                        {
                            "title": "Search Result",
                            "url": "https://example.com",
                            "content": result[:50000] if len(result) > 50000 else result
                        }
                    ]
                }
            return result
        elif hasattr(tool, 'invoke'):
            logger.info("Using invoke method")
            result = tool.invoke(tool_input)
            logger.info(f"Result type: {type(result).__name__}")
            if isinstance(result, str):
                logger.info(f"Result is a string of length {len(result)}")
                # Return a properly formatted dict
                return {
                    "query": query,
                    "results": [
                        {
                            "title": "Search Result",
                            "url": "https://example.com",
                            "content": result[:50000] if len(result) > 50000 else result
                        }
                    ]
                }
            return result
        elif hasattr(tool, 'run'):
            logger.info("Using run method")
            result = tool.run(tool_input)
            logger.info(f"Result type: {type(result).__name__}")
            if isinstance(result, str):
                logger.info(f"Result is a string of length {len(result)}")
                # Return a properly formatted dict
                return {
                    "query": query,
                    "results": [
                        {
                            "title": "Search Result",
                            "url": "https://example.com",
                            "content": result[:50000] if len(result) > 50000 else result
                        }
                    ]
                }
            return result
        else:
            logger.error(f"No compatible method found on tool {tool.name}")
            raise Exception(f"Invalid tool object: {tool} - missing run methods")
    except Exception as e:
        logger.error(f"Error in search_web: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return {
            "error": f"Error searching: {str(e)}",
            "query": query,
            "results": []
        } 