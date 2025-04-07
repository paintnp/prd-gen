#!/usr/bin/env python
"""
MCP Server Failure Test

This script tests how the system handles connection failures to the MCP server.
It intentionally tries to connect to invalid servers to verify error handling.
"""

import os
import sys
import logging
import time
from typing import Optional, Dict, Any

# Add the parent directory to the path so we can import the prd_gen modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prd_gen.utils.debugging import setup_logging, log_error
from prd_gen.utils.direct_search import DirectSearchClient
from prd_gen.utils.mcp_client import run_async, get_mcp_tools

# Set up logging
logger = setup_logging()

def test_invalid_port() -> bool:
    """Test connection to localhost on an invalid port."""
    logger.info("Testing connection to localhost on an invalid port (12345)...")
    
    # Set environment variable to override the default MCP server URL
    os.environ["MCP_SERVER_URL"] = "http://localhost:12345/sse"
    
    try:
        # Create a new client with the invalid URL
        client = DirectSearchClient()
        
        # Try to search for something
        logger.info("Attempting to search using an invalid port...")
        result = client.search_web("test query")
        
        # We expect a result with an error message, not an exception
        if isinstance(result, dict) and "error" in result:
            logger.info("✅ Got expected error response from invalid port")
            logger.info(f"Error message: {result['error']}")
            
            # Display the full diagnostic information
            logger.info("\n=== DETAILED ERROR DIAGNOSTIC INFORMATION ===")
            import json
            logger.info(json.dumps(result, indent=2))
            logger.info("=== END DIAGNOSTIC INFORMATION ===\n")
            
            return True
        else:
            logger.error("❌ Test failed: Did not get expected error format from invalid port")
            logger.info(f"Result: {result}")
            return False
    except Exception as e:
        # We don't expect an uncaught exception
        logger.error("❌ Test failed: Uncaught exception when connecting to invalid port")
        logger.error(f"Exception: {str(e)}")
        return False

def test_nonexistent_host() -> bool:
    """Test connection to a non-existent host."""
    logger.info("Testing connection to a non-existent host...")
    
    # Set environment variable to override the default MCP server URL
    os.environ["MCP_SERVER_URL"] = "http://non-existent-host.invalid/sse"
    
    try:
        # Create a new client with the invalid URL
        client = DirectSearchClient()
        
        # Try to search for something
        logger.info("Attempting to search using a non-existent host...")
        result = client.search_web("test query")
        
        # We expect a result with an error message, not an exception
        if isinstance(result, dict) and "error" in result:
            logger.info("✅ Got expected error response from non-existent host")
            logger.info(f"Error message: {result['error']}")
            return True
        else:
            logger.error("❌ Test failed: Did not get expected error format from non-existent host")
            logger.info(f"Result: {result}")
            return False
    except Exception as e:
        # We don't expect an uncaught exception
        logger.error("❌ Test failed: Uncaught exception when connecting to non-existent host")
        logger.error(f"Exception: {str(e)}")
        return False

def test_invalid_path() -> bool:
    """Test connection to a valid host but invalid path."""
    logger.info("Testing connection to localhost with invalid path...")
    
    # Set environment variable to override the default MCP server URL
    os.environ["MCP_SERVER_URL"] = "http://localhost:9000/invalid-path"
    
    try:
        # Create a new client with the invalid URL
        client = DirectSearchClient()
        
        # Try to search for something
        logger.info("Attempting to search using an invalid path...")
        result = client.search_web("test query")
        
        # We expect a result with an error message, not an exception
        if isinstance(result, dict) and "error" in result:
            logger.info("✅ Got expected error response from invalid path")
            logger.info(f"Error message: {result['error']}")
            
            # Display the full diagnostic information
            logger.info("\n=== DETAILED ERROR DIAGNOSTIC INFORMATION ===")
            import json
            logger.info(json.dumps(result, indent=2))
            logger.info("=== END DIAGNOSTIC INFORMATION ===\n")
            
            return True
        else:
            logger.error("❌ Test failed: Did not get expected error format from invalid path")
            logger.info(f"Result: {result}")
            return False
    except Exception as e:
        # We don't expect an uncaught exception
        logger.error("❌ Test failed: Uncaught exception when connecting with invalid path")
        logger.error(f"Exception: {str(e)}")
        return False

def test_graceful_error_handling() -> bool:
    """Test that errors are handled gracefully in the search function."""
    logger.info("Testing graceful error handling in search function...")
    
    # Set environment variable to override the default MCP server URL
    os.environ["MCP_SERVER_URL"] = "http://localhost:12345/sse"
    
    try:
        # Use the direct search function which should handle errors gracefully
        from prd_gen.utils.direct_search import direct_search_web
        
        logger.info("Calling direct_search_web function which should handle errors gracefully...")
        result = direct_search_web("test query")
        
        # We expect a result with an error message, not an exception
        if isinstance(result, dict) and "error" in result:
            logger.info("✅ Got expected error response in search result")
            logger.info(f"Error message: {result['error']}")
            return True
        else:
            logger.error("❌ Test failed: Did not get expected error format")
            logger.info(f"Result: {result}")
            return False
    except Exception as e:
        # We don't expect an exception to be thrown, it should be handled
        logger.error("❌ Test failed: Exception was thrown instead of returning error object")
        logger.error(f"Exception: {str(e)}")
        return False

def reset_environment():
    """Reset the environment variables after testing."""
    # Remove the custom MCP server URL if it exists
    if "MCP_SERVER_URL" in os.environ:
        del os.environ["MCP_SERVER_URL"]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test MCP server failure handling")
    parser.add_argument("--test", choices=["all", "port", "host", "path", "graceful"], default="all",
                        help="Which test to run")
    args = parser.parse_args()
    
    try:
        # Track overall success
        overall_success = True
        
        if args.test in ["all", "port"]:
            overall_success = test_invalid_port() and overall_success
            
        if args.test in ["all", "host"]:
            overall_success = test_nonexistent_host() and overall_success
            
        if args.test in ["all", "path"]:
            overall_success = test_invalid_path() and overall_success
            
        if args.test in ["all", "graceful"]:
            overall_success = test_graceful_error_handling() and overall_success
        
        # Reset environment
        reset_environment()
        
        # Report overall result
        if overall_success:
            logger.info("✅ All tests passed! Error handling is working correctly.")
            exit(0)
        else:
            logger.error("❌ Some tests failed. Error handling needs improvement.")
            exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error during testing: {e}")
        # Log to error file
        log_error(f"Unexpected error during failure testing: {e}", exc_info=True)
        exit(1)
    finally:
        # Make sure environment is reset even if an error occurs
        reset_environment() 