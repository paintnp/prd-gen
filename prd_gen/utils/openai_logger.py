"""
OpenAI API logging utilities.

This module provides functions for logging OpenAI API requests and responses.
"""

import os
import time
import json
import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

def setup_openai_logging() -> logging.Logger:
    """
    Set up a logger for OpenAI API requests and responses.
    
    Returns:
        logging.Logger: The configured logger.
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create a timestamp for the log file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"openai_debug_{timestamp}.log"
    
    # Set up logger
    logger = logging.getLogger("openai_debug")
    logger.setLevel(logging.DEBUG)
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    
    print(f"OpenAI API debugging logs will be written to: {log_file}")
    
    return logger

def log_openai_request(messages: Union[List[Dict[str, Any]], List[str], str], model: str = "Unknown", tools: List[Any] = None) -> None:
    """
    Log an OpenAI API request.
    
    Args:
        messages: The messages to log - can be a list of dicts, strings, or a single string
        model: The model name
        tools: Optional list of tools
    """
    logger = logging.getLogger("openai_debug")
    
    # Handle different message formats
    if isinstance(messages, str):
        log_content = {
            "request_type": "OpenAI API Request",
            "model": model,
            "messages": [{"role": "user", "content": messages}],
            "has_tools": tools is not None and len(tools) > 0
        }
    elif isinstance(messages, list) and all(isinstance(msg, str) for msg in messages):
        # Convert list of strings to proper message format
        formatted_messages = []
        for i, msg in enumerate(messages):
            role = "system" if i == 0 else "user" if i % 2 == 1 else "assistant"
            formatted_messages.append({"role": role, "content": msg})
        
        log_content = {
            "request_type": "OpenAI API Request",
            "model": model,
            "messages": formatted_messages,
            "has_tools": tools is not None and len(tools) > 0
        }
    else:
        # Assume it's already in the correct format
        log_content = {
            "request_type": "OpenAI API Request",
            "model": model,
            "messages": messages,
            "has_tools": tools is not None and len(tools) > 0
        }
    
    # Add tool details if available
    if tools is not None and len(tools) > 0:
        # Get basic tool info without the full schema details
        tool_info = []
        for tool in tools:
            # Handle different types of tool objects
            if isinstance(tool, dict) and "function" in tool:
                # OpenAI native tool format
                tool_info.append({
                    "name": tool.get("function", {}).get("name", "unknown"),
                    "type": tool.get("type", "function")
                })
            elif hasattr(tool, "name") and hasattr(tool, "description"):
                # LangChain tool format
                tool_info.append({
                    "name": tool.name,
                    "description": tool.description[:50] + "..." if len(tool.description) > 50 else tool.description
                })
            else:
                # Unknown tool format
                tool_info.append({"name": str(tool)[:30]})
                
        log_content["tools"] = tool_info
    
    try:
        logger.debug(f"REQUEST: {json.dumps(log_content, indent=2)}")
    except Exception as e:
        logger.error(f"Error logging OpenAI request: {e}")

def log_openai_response(response: Any, model: str = "Unknown", success: bool = True) -> None:
    """
    Log an OpenAI API response.
    
    Args:
        response: The response to log
        model: The model name
        success: Whether the call was successful
    """
    logger = logging.getLogger("openai_debug")
    
    try:
        # Convert response to string if it's not already
        if not isinstance(response, str):
            if hasattr(response, "content"):
                response_str = response.content
            else:
                response_str = str(response)
        else:
            response_str = response
            
        # Truncate the response if it's too long
        max_length = 2000
        if len(response_str) > max_length:
            truncated_response = response_str[:max_length] + "... [truncated]"
        else:
            truncated_response = response_str
            
        log_content = {
            "response_type": "OpenAI API Response",
            "model": model,
            "success": success,
            "response": truncated_response
        }
        
        logger.debug(f"RESPONSE: {json.dumps(log_content, indent=2)}")
    except Exception as e:
        logger.error(f"Error logging OpenAI response: {e}") 