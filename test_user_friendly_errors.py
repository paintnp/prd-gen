#!/usr/bin/env python
"""
Test script for user-friendly error handling.

This script tests the various error scenarios and the user-friendly
messages that are displayed for each one.
"""

import os
import sys
import logging
from pathlib import Path

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("error_test")

def test_search_too_large():
    """Test the behavior when search results are too large"""
    from prd_gen.utils.direct_search import direct_search_web
    from prd_gen.utils.ui_helpers import display_search_status
    import json
    
    print("\n" + "=" * 80)
    print("TESTING: Very large search results (token limit handling)")
    print("=" * 80)
    
    # Use a query likely to return large results
    query = "comprehensive history of artificial intelligence from 1950 to present day"
    print(f"Query: '{query}'")
    
    # Run the search
    results = direct_search_web(query)
    
    # Display the user-friendly error/status
    display_search_status(results)
    
    # Check if we received results and they were processed
    if "results" in results and len(results["results"]) > 0:
        total_chars = sum(len(r.get("content", "")) for r in results["results"])
        print(f"Got {len(results['results'])} results with {total_chars} total characters")
        
        # Check if results were truncated
        if "message" in results and "truncated" in results["message"].lower():
            print("✅ Test PASSED: Results were properly truncated and user notified")
        elif total_chars < 100000 and "user_message" in results:
            print("✅ Test PASSED: Results size was managed and user interface is friendly")
        else:
            print("❌ Test FAILED: Results were not properly truncated or user not notified")
    elif "user_message" in results and "too much data" in results["user_message"].lower():
        print("✅ Test PASSED: Token limit error was caught and user-friendly message shown")
    else:
        print("❌ Test FAILED: Results handling not working properly")
    
    return results

def test_connection_error():
    """Test the behavior when the MCP server is not available"""
    from prd_gen.utils.direct_search import direct_search_web
    from prd_gen.utils.ui_helpers import display_search_status
    import os
    
    print("\n" + "=" * 80)
    print("TESTING: Connection error (MCP server not available)")
    print("=" * 80)
    
    # Save the original URL
    original_url = os.environ.get("MCP_SERVER_URL", "")
    
    try:
        # Set an invalid URL to force a connection error
        os.environ["MCP_SERVER_URL"] = "http://localhost:12345/sse"
        print(f"Using invalid server URL: {os.environ['MCP_SERVER_URL']}")
        
        # Tell MCPClient to use a fresh connection (not cached)
        os.environ["MCP_FORCE_NEW_CONNECTION"] = "true"
        
        # Try to search
        query = "test query"
        print(f"Query: '{query}' with invalid server URL")
        
        # Run the search with the invalid URL
        results = direct_search_web(query)
        
        # Display the user-friendly error
        display_search_status(results)
        
        # Check for connection error message
        if "user_message" in results and ("Unable to connect" in results["user_message"] or "unavailable" in results["user_message"].lower()):
            print("✅ Test PASSED: Connection error was caught with user-friendly message")
        else:
            print("❌ Test FAILED: Connection error was not handled properly")
        
        return results
    finally:
        # Restore the original URL
        if original_url:
            os.environ["MCP_SERVER_URL"] = original_url
        else:
            os.environ.pop("MCP_SERVER_URL", None)
        # Remove the force new connection flag
        os.environ.pop("MCP_FORCE_NEW_CONNECTION", None)

def test_not_found_error():
    """Test the behavior when the MCP server URL path is incorrect"""
    from prd_gen.utils.direct_search import direct_search_web
    from prd_gen.utils.ui_helpers import display_search_status
    import os
    
    print("\n" + "=" * 80)
    print("TESTING: Not Found error (incorrect server path)")
    print("=" * 80)
    
    # Save the original URL
    original_url = os.environ.get("MCP_SERVER_URL", "")
    
    try:
        # Set a URL with an incorrect path to force a 404 error
        os.environ["MCP_SERVER_URL"] = "http://localhost:9000/wrong-path"
        print(f"Using incorrect server path: {os.environ['MCP_SERVER_URL']}")
        
        # Tell MCPClient to use a fresh connection (not cached)
        os.environ["MCP_FORCE_NEW_CONNECTION"] = "true"
        
        # Try to search
        query = "test query"
        print(f"Query: '{query}' with incorrect server path")
        
        # Run the search
        results = direct_search_web(query)
        
        # Display the user-friendly error
        display_search_status(results)
        
        # Check for not found error message
        if "user_message" in results and ("endpoint not found" in results["user_message"].lower() or "not found" in results["user_message"].lower()):
            print("✅ Test PASSED: Not Found error was caught with user-friendly message")
        else:
            print("❌ Test FAILED: Not Found error was not handled properly")
        
        return results
    finally:
        # Restore the original URL
        if original_url:
            os.environ["MCP_SERVER_URL"] = original_url
        else:
            os.environ.pop("MCP_SERVER_URL", None)
        # Remove the force new connection flag
        os.environ.pop("MCP_FORCE_NEW_CONNECTION", None)

def test_general_system_error():
    """Test the display of general system errors"""
    from prd_gen.utils.ui_helpers import print_friendly_system_error
    
    print("\n" + "=" * 80)
    print("TESTING: General system error display")
    print("=" * 80)
    
    # Display a test error message
    print_friendly_system_error(
        "This is a test system error message",
        [
            "This is the first suggestion",
            "This is the second suggestion",
            "This is the third suggestion"
        ]
    )
    
    print("✅ Test PASSED: System error message displayed")
    return True

def main():
    """Run all the error handling tests"""
    print("Starting user-friendly error handling tests...")
    
    # Run the tests
    test_search_too_large()
    test_connection_error()
    test_not_found_error()
    test_general_system_error()
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    main() 