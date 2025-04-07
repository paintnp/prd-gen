#!/usr/bin/env python
"""
Simple test for error handling in the direct_search_web function.
"""

import sys
import os
import logging

# Add the parent directory to the path so we can import the prd_gen modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prd_gen.utils.debugging import setup_logging
from prd_gen.utils.direct_search import direct_search_web

# Set up logging
logger = setup_logging()

def main():
    """Run the test."""
    # Set an invalid MCP server URL
    os.environ["MCP_SERVER_URL"] = "http://localhost:12345/sse"
    
    # Try to search, which should gracefully handle the error
    logger.info("Testing search with invalid MCP server URL...")
    result = direct_search_web("test query")
    
    # Log the result
    logger.info("Search result:")
    import json
    logger.info(json.dumps(result, indent=2))
    
    # Check if we got an error response
    if isinstance(result, dict) and "error" in result:
        logger.info("✅ Got expected error response")
        return 0
    else:
        logger.error("❌ Did not get expected error response")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 