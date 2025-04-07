"""
Debugging utilities for the PRD generator.
"""

import json
import logging
import sys
import os
from typing import Dict, Any
from datetime import datetime

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

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

# Setup error logging handler
error_log_file = os.path.join("logs", f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
error_handler = logging.FileHandler(error_log_file)
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
error_handler.setFormatter(error_formatter)
logger.addHandler(error_handler)

def setup_logging():
    """Set up logging for the application."""
    return logger

def setup_error_logging():
    """Set up error-specific logging that captures only errors in a separate file."""
    return error_handler

def log_error(error_message: str, exc_info=None):
    """
    Log an error message to both the main log and the dedicated error log.
    
    Args:
        error_message: The error message to log
        exc_info: Exception information (from an except block) if available
    """
    if exc_info:
        logger.error(f"ERROR: {error_message}", exc_info=exc_info)
    else:
        logger.error(f"ERROR: {error_message}")
    
    # Return the path to the error log for reference
    return error_log_file

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