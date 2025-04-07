"""
Configuration utility for the PRD generator.

This module provides functions for loading configuration settings from
environment variables.
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv, find_dotenv
from prd_gen.utils.debugging import setup_logging
import argparse

# Set up logging
logger = logging.getLogger(__name__)

def get_config() -> Dict[str, Any]:
    """
    Get the application configuration.
    
    Returns:
        Dict[str, Any]: The application configuration.
    """
    # Get OpenAI API key from environment
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        logger.warning("OPENAI_API_KEY environment variable not set")
    
    # Configure the model
    model = os.environ.get("OPENAI_MODEL", "gpt-4")
    temperature = float(os.environ.get("OPENAI_TEMPERATURE", "0.7"))
    
    return {
        "openai_api_key": openai_api_key,
        "model": model,
        "temperature": temperature,
    }

class Config:
    """Configuration class for the PRD generator."""
    
    def __init__(self, args: Optional[argparse.Namespace] = None):
        """
        Initialize the configuration.
        
        Args:
            args (Optional[argparse.Namespace]): Command line arguments.
        """
        # Set up basic configuration from environment
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        self.temperature = float(os.environ.get("OPENAI_TEMPERATURE", "0.7"))
        
        # Set up MCP configuration
        self.mcp_server_url = os.environ.get("MCP_SERVER_URL", "http://localhost:9000/sse")
        self.mcp_server_name = os.environ.get("MCP_SERVER_NAME", "mcp-server")
        
        # Set up iteration configuration
        self.max_iterations = int(os.environ.get("MAX_ITERATIONS", "3"))
        
        # Update with command line arguments if provided
        if args:
            self.idea = args.idea
            self.output = args.output
            if hasattr(args, 'max_iterations') and args.max_iterations is not None:
                self.max_iterations = args.max_iterations
        else:
            self.idea = None
            self.output = None
        
        # Log configuration
        logger.debug(f"Configuration: model={self.model}, temperature={self.temperature}, max_iterations={self.max_iterations}")
        if self.idea:
            logger.debug(f"Idea: {self.idea}")
        if self.output:
            logger.debug(f"Output: {self.output}")
        
        # Validate configuration
        self._validate()
    
    def _validate(self):
        """Validate the configuration."""
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        if not self.idea:
            logger.warning("No idea provided")

    def load_from_env(self):
        """
        Load configuration settings from environment variables.
        
        Returns:
            Dict[str, Any]: The configuration dictionary.
        """
        # Load environment variables from the project root
        env_path = find_dotenv(usecwd=True)
        if env_path:
            logger.debug(f"Loading environment from: {env_path}")
            load_dotenv(env_path, override=True)
        else:
            logger.warning("No .env file found for config. Using existing environment variables.")
        
        # LLM configuration
        llm_config = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "4000"))
        }
        
        # Ensure max_tokens is within the model's limit
        if llm_config["max_tokens"] > 8000:
            llm_config["max_tokens"] = 8000
            logger.warning(f"Reduced max_tokens to {llm_config['max_tokens']} to stay within model limits")
        
        # MCP server configuration
        mcp_server_config = {
            "url": self.mcp_server_url,
            "transport": os.environ.get("MCP_SERVER_TRANSPORT", "sse"),
            "timeout": int(os.environ.get("MCP_SERVER_TIMEOUT", "30"))
        }
        
        # PRD generation configuration
        prd_config = {
            "quality_threshold": float(os.environ.get("QUALITY_THRESHOLD", "0.8")),
            "templates_path": os.environ.get("TEMPLATES_PATH", "prd_gen/templates"),
            "max_iterations": self.max_iterations
        }
        
        # Combine all configurations
        config = {
            "llm": llm_config,
            "mcp_server": mcp_server_config,
            "prd": prd_config
        }
        
        logger.debug(f"Loaded configuration: LLM model={llm_config['model']}, temperature={llm_config['temperature']}")
        logger.debug(f"MCP server URL: {mcp_server_config['url']}")
        
        return config 