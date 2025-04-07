#!/usr/bin/env python3
"""
MCP Server for PRD Generator

This script implements a Model Context Protocol (MCP) server that
provides the search_web tool for the PRD generator application.
"""

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os
import json
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mcp_server.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("mcp_server")

# Load environment variables
load_dotenv()

# Create a mock Exa search results function for testing
def mock_search_and_contents(query):
    """
    Mock implementation of search_and_contents for testing without an Exa API key.
    """
    logger.debug(f"Searching web for query: {query}")
    
    results = {
        "query": query,
        "results": [
            {
                "title": "Product Management Trends in 2024",
                "url": "https://example.com/trends-2024",
                "snippet": "AI-powered product development, customer-centric design, and data-driven decision making are leading trends in 2024.",
                "content": "In 2024, product management is evolving rapidly with several key trends: 1) AI Integration - Using AI for feature prioritization and customer insights. 2) Customer-Centric Approaches - Deeper focus on user research and feedback loops. 3) Data-Driven Decision Making - Advanced analytics to guide product decisions. 4) Remote Collaboration Tools - Enhanced platforms for distributed product teams. 5) Sustainability - Growing emphasis on environmentally sustainable product development."
            },
            {
                "title": "The Future of Product Requirements Documents",
                "url": "https://example.com/prd-future",
                "snippet": "Modern PRDs are becoming more visual, collaborative, and integrated with agile methodologies.",
                "content": "Product Requirements Documents (PRDs) have evolved significantly in recent years. The most effective PRDs now incorporate visual elements like wireframes and user flows, enable real-time collaboration between stakeholders, integrate directly with agile project management tools, and focus on outcomes rather than specifications. This allows product teams to maintain clarity while preserving the flexibility needed in modern development environments."
            }
        ]
    }
    
    logger.debug(f"Search results: {json.dumps(results, indent=2)}")
    return results

# Create MCP server instance with a different port
server_name = "TestMCPServer"
server_port = 9001

# Create MCP server instance
mcp = FastMCP(server_name, port=server_port)

@mcp.tool()
def search_web(query: str, use_autoprompt: bool = True, search_type: str = "auto") -> dict:
    """
    Perform a web search using Exa's API.

    :param query: The search query string.
    :param use_autoprompt: Whether to use Exa's autoprompt feature.
    :param search_type: The type of search ('auto', 'neural', or 'keyword').
    :return: Search results as a dictionary.
    """
    logger.debug(f"search_web tool called with query: {query}")
    
    # For testing purposes, use the mock implementation
    # In production, you would use the actual Exa API
    results = mock_search_and_contents(query)
    return results

# List all registered tools
tools = mcp.get_tools()
logger.debug(f"Registered tools: {[t.name for t in tools]}")
for i, tool in enumerate(tools):
    logger.debug(f"Tool {i+1}: {tool.name}")
    logger.debug(f"  Description: {tool.description}")
    if hasattr(tool, 'args_schema'):
        logger.debug(f"  Args Schema: {tool.args_schema}")

if __name__ == "__main__":
    logger.info(f"Starting MCP Server on port {server_port}...")
    logger.info(f"Server name: {server_name}")
    logger.info(f"Available tools: {[t.name for t in tools]}")
    print(f"Starting MCP Server on port {server_port}...")
    print(f"Server name: {server_name}")
    print(f"Available tools: {[t.name for t in tools]}")
    print("Press Ctrl+C to stop the server")
    
    try:
        mcp.run(transport="sse")
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        print(f"Error running MCP server: {e}") 