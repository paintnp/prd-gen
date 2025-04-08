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
from prd_gen.utils.debugging import setup_logging, log_error
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, create_model, Field

# Set up logging
logger = setup_logging()

class MCPToolProvider:
    """
    MCP Tool Provider
    
    This class is a wrapper for the MCP client to simplify interactions with the MCP server.
    
    Args:
        server_url: The URL of the MCP server. Default: http://localhost:9000/sse
        server_name: The name of the MCP server. Default: Exa MCP Server
    """
    
    def __init__(self, server_url: Optional[str] = None, server_name: Optional[str] = None):
        """Initialize the MCP Tool Provider."""
        self.server_url = server_url or os.environ.get("MCP_SERVER_URL", "http://localhost:9000/sse")
        self.server_name = server_name or os.environ.get("MCP_SERVER_NAME", "Exa MCP Server")
        self.client = None
        self.connected = False
        
    async def connect(self) -> bool:
        """
        Connect to the MCP server.
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            # Create a client
            self.client = MultiServerMCPClient()
            # Connect to the server
            await self.client.connect_to_server_via_sse(self.server_name, url=self.server_url)
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Error connecting to MCP server: {e}")
            return False
            
    async def disconnect(self) -> bool:
        """
        Disconnect from the MCP server.
        
        Returns:
            bool: True if disconnected successfully, False otherwise
        """
        if self.client and self.connected:
            try:
                # Properly close the client connection
                logger.debug("Disconnecting from MCP server")
                await self.client.disconnect_from_server(self.server_name)
                self.connected = False
                return True
            except Exception as e:
                logger.error(f"Error disconnecting from MCP server: {e}")
                return False
        return True  # Already disconnected
        
    def get_tools(self) -> List[BaseTool]:
        """
        Get the list of tools from the MCP server.
        
        Returns:
            List[BaseTool]: The list of tools
        """
        if not self.connected:
            logger.warning("Not connected to MCP server. Call connect() first.")
            return []
        
        # Try to fetch the tools from the client
        try:
            tools = self.client.get_tools()
            
            # Log some diagnostic info if tools is empty
            if not tools:
                logger.warning("No tools retrieved from MCP server")
            
            return tools
        except Exception as e:
            logger.error(f"Error getting tools from MCP server: {e}")
            return []
    
    def search_tool_available(self) -> bool:
        """
        Check if search tools are available.
        
        Returns:
            bool: True if search tools are available, False otherwise.
        """
        # First check for search_web_summarized (preferred)
        if any(tool.name == "search_web_summarized" for tool in self.client.tools):
            return True
            
        # Fall back to search_web if summarized version isn't available
        return any(tool.name == "search_web" for tool in self.client.tools)

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

async def get_mcp_tools(force_new_connection=False):
    """
    Get the list of available tools from the MCP server.
    
    Args:
        force_new_connection (bool): Whether to force a new connection even if cached tools exist
        
    Returns:
        List[Tool]: The list of tools
    """
    global _mcp_tools, _mcp_client, _mcp_session_id
    
    # Return cached tools if they exist and we're not forcing a new connection
    if _mcp_tools and not force_new_connection:
        logger.debug("Using cached MCP tools")
        return _mcp_tools
    
    # Create new MCP client if needed or if forcing a new connection
    if _mcp_client is None or force_new_connection:
        server_url = os.environ.get("MCP_SERVER_URL", "http://localhost:9000/sse")
        server_name = os.environ.get("MCP_SERVER_NAME", "Exa MCP Server")
        
        # If forcing a new connection and client exists, clean up old connection
        if force_new_connection and _mcp_client is not None:
            try:
                # Close and cleanup old client connection
                logger.info("Cleaning up previous MCP client connection")
                await _mcp_client.disconnect()
            except Exception as e:
                # Don't let cleanup errors stop us from creating a new connection
                logger.warning(f"Error cleaning up old MCP client: {e}")
        
        # Create a new client
        _mcp_client = MCPToolProvider(server_url=server_url, server_name=server_name)
        
    # The MAX_RETRIES to connect to the MCP server
    MAX_RETRIES = 3
    
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

async def search_web_summarized(tool, query, summary_focus="key findings"):
    """
    Search the web using the MCP search_web_summarized tool and get summarized results.
    
    Args:
        tool (BaseTool): The search_web_summarized tool from the MCP server.
        query (str): The search query.
        summary_focus (str): Focus for summary generation (e.g., "key findings", "main points")
        
    Returns:
        Dict[str, Any]: The summarized search results.
    """
    try:
        # Add detailed debug logging
        logger.info(f"Searching web with query: '{query}', summary focus: '{summary_focus}'")
        logger.info(f"Using tool: {tool.name} (type: {type(tool).__name__})")
        
        # List available methods on the tool
        methods = [method for method in dir(tool) if not method.startswith('_')]
        logger.info(f"Tool methods: {methods}")
        
        # Create input as a dictionary for JSON schema
        tool_input = {"query": query, "summary_focus": summary_focus}
        logger.info(f"Created tool input: {tool_input}")
        
        # Run the tool
        start_time = time.time()
        logger.info(f"Starting search with tool.ainvoke({tool_input})")
        
        # Use ainvoke instead of run, since the tool requires async
        if hasattr(tool, 'ainvoke'):
            # Most MCP tools support ainvoke
            result = await tool.ainvoke(tool_input)
        elif hasattr(tool, 'arun'):
            # Fallback to arun
            result = await tool.arun(**tool_input)
        else:
            # No async methods available
            raise NotImplementedError(f"Tool {tool.name} does not support async invocation")
        
        # Calculate and log execution time
        execution_time = time.time() - start_time
        logger.info(f"Search completed in {execution_time:.2f} seconds")
        
        return result
    except Exception as e:
        logger.error(f"Error searching web: {e}", exc_info=True)
        error_log = log_error(f"search_web_summarized({query}, {summary_focus}) failed: {e}", exc_info=True)
        logger.error(f"Error log created at: {error_log}")
        
        # Re-raise the exception to be handled by the caller
        raise 