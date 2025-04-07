"""
Debugging utilities for the PRD generator.
"""

import json
import logging
import sys
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("prd_gen")

def setup_logging():
    """Set up logging for the application."""
    return logger

def log_mcp_client_config(client_config: Dict[str, Any]):
    """Log the MCP client configuration."""
    logger.debug(f"MCP Client Configuration: {json.dumps(client_config, indent=2)}")

def log_mcp_tools(tools):
    """Log the MCP tools."""
    tool_names = [tool.name for tool in tools] if tools else []
    logger.debug(f"MCP Tools: {tool_names}")
    
    if tools:
        for i, tool in enumerate(tools):
            logger.debug(f"Tool {i+1}: {tool.name}")
            logger.debug(f"  Description: {tool.description}")
            if hasattr(tool, 'args_schema'):
                logger.debug(f"  Args Schema: {tool.args_schema}")
    else:
        logger.debug("No tools found on the MCP server.") 