#!/usr/bin/env python3

"""
Comprehensive test script for the MCP client that powers the PRD generator.
Tests direct connection, tool retrieval, and search tool availability.
"""

import asyncio
import logging
import os
import sys
import json
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our MCP client implementation
from prd_gen.utils.mcp_client import MCPToolProvider, run_async, get_mcp_tools
from prd_gen.utils.direct_search import direct_search_web, create_mock_search_results

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_client_test")

# Load environment variables
load_dotenv()

async def test_direct_connection():
    """Test direct connection to MCP server using our MCPToolProvider"""
    logger.info("Testing direct connection to MCP server...")
    
    # Get server URL from environment or use default
    server_url = os.environ.get("MCP_SERVER_URL", "http://localhost:9000/sse")
    
    # Create our MCPToolProvider instance
    client = MCPToolProvider(server_url=server_url)
    
    # Connect to the server
    connected = await client.connect()
    if not connected:
        logger.error("Failed to connect to MCP server")
        return False
    
    # Get available tools
    tools = client.get_tools()
    
    # Log information about tools
    if not tools:
        logger.warning("No tools found on MCP server")
        return False
    
    logger.info(f"Successfully retrieved {len(tools)} tools:")
    for i, tool in enumerate(tools):
        logger.info(f"  Tool {i+1}: {tool.name} - {tool.description}")
    
    # Check for search_web tool
    has_search = client.search_tool_available()
    if has_search:
        logger.info("✅ search_web tool is available")
    else:
        logger.warning("⚠️ search_web tool is NOT available")
    
    return True

def test_search_query():
    """Test executing a sample search query using direct_search_web"""
    logger.info("Testing live search functionality with a sample query...")
    
    # Sample search query
    query = "latest trends in language learning apps"
    logger.info(f"Executing live search for: '{query}'")
    
    try:
        # Execute the search
        result = direct_search_web(query)
        
        # Log the result structure
        logger.info(f"Search result type: {type(result)}")
        logger.info(f"Search result keys: {list(result.keys() if isinstance(result, dict) else [])}")
        
        # Check if we got results
        if isinstance(result, dict) and "results" in result:
            results = result["results"]
            logger.info(f"✅ Received {len(results)} LIVE search results")
            
            # Print the first result
            if results:
                first_result = results[0]
                logger.info("First result:")
                logger.info(f"  Title: {first_result.get('title', 'N/A')}")
                logger.info(f"  URL: {first_result.get('url', 'N/A')}")
                content = first_result.get('content', '')
                logger.info(f"  Content: {content[:100]}..." if len(content) > 100 else content)
                return True
            else:
                logger.error("❌ Live search returned zero results")
                return False
        elif isinstance(result, dict) and "error" in result:
            logger.error(f"❌ LIVE SEARCH ERROR: {result['error']}")
            logger.error("Live search is required - please ensure the MCP server is running and properly configured")
            return False
        else:
            logger.error(f"❌ Unexpected result format from live search: {json.dumps(result)[:200]}")
            return False
    except Exception as e:
        logger.error(f"❌ Error executing live search: {e}")
        logger.error("Live search is required - please ensure the MCP server is running and properly configured")
        return False

async def run_test():
    """Run the MCP client test"""
    logger.info("Starting MCP client test")
    
    # Test direct connection
    connection_success = await test_direct_connection()
    
    if not connection_success:
        logger.error("❌ MCP client connection test failed - couldn't retrieve tools")
        return False
        
    logger.info("✅ MCP client connection test passed - search_web tool available")
    
    # Test search functionality
    search_success = test_search_query()
    
    return connection_success and search_success

if __name__ == "__main__":
    # Process command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Test MCP client connection")
    parser.add_argument("--method", choices=["direct", "get_tools", "search", "errors", "test_error_logging"], default="direct",
                        help="Test method to use: direct connection, get_mcp_tools(), search, display recent errors, or test error logging")
    parser.add_argument("--query", type=str, default="latest trends in language learning apps",
                        help="Search query to test (only used with --method=search)")
    parser.add_argument("--count", type=int, default=10,
                        help="Number of recent errors to display (only used with --method=errors)")
    parser.add_argument("--error_message", type=str, default="Test error message",
                        help="Error message to log (only used with --method=test_error_logging)")
    args = parser.parse_args()
    
    logger.info(f"MCP Client Test - Testing using {args.method} method")
    
    success = False
    
    if args.method == "direct":
        # Test direct connection 
        success = run_async(run_test())
    elif args.method == "get_tools":
        # Test get_mcp_tools function
        try:
            tools = run_async(get_mcp_tools())
            has_search = any(tool.name == "search_web" for tool in tools)
            
            if has_search:
                logger.info(f"✅ Successfully retrieved {len(tools)} tools using get_mcp_tools()")
                logger.info("✅ search_web tool is available")
                success = True
            else:
                logger.warning(f"⚠️ Retrieved {len(tools)} tools but search_web is NOT available")
                success = False
        except Exception as e:
            logger.error(f"❌ Error using get_mcp_tools(): {e}")
            success = False
    elif args.method == "search":
        # Test search functionality directly
        try:
            logger.info(f"Testing search for query: '{args.query}'")
            result = direct_search_web(args.query)
            
            # Log basic info about result
            if isinstance(result, dict):
                if "error" in result:
                    logger.error(f"❌ LIVE SEARCH ERROR: {result['error']}")
                    logger.error("Live search is required - please ensure the MCP server is running and properly configured")
                    success = False
                elif "results" in result:
                    results = result["results"]
                    logger.info(f"✅ Received {len(results)} LIVE search results")
                    
                    # Print each result
                    for i, res in enumerate(results):
                        logger.info(f"Result {i+1}:")
                        logger.info(f"  Title: {res.get('title', 'N/A')}")
                        logger.info(f"  URL: {res.get('url', 'N/A')}")
                        content = res.get('content', '')
                        logger.info(f"  Content: {content[:100]}..." if len(content) > 100 else content)
                    
                    success = len(results) > 0
                    if not success:
                        logger.error("❌ Live search returned zero results")
                else:
                    logger.error(f"❌ Unexpected result format from live search: {list(result.keys())}")
                    success = False
            else:
                logger.error(f"❌ Unexpected result type from live search: {type(result)}")
                success = False
        except Exception as e:
            logger.error(f"❌ Error testing live search: {e}")
            logger.error("Live search is required - please ensure the MCP server is running and properly configured")
            success = False
    elif args.method == "errors":
        # Display recent errors from error log files
        import glob
        import os
        from datetime import datetime
        
        # Get all error log files
        error_logs = glob.glob(os.path.join("logs", "error_*.log"))
        
        # Sort by modification time (newest first)
        error_logs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        if not error_logs:
            logger.info("No error logs found.")
            success = True
        else:
            # Display the content of the most recent error logs
            count = min(args.count, len(error_logs))
            logger.info(f"Displaying the {count} most recent error logs:")
            
            for i, log_file in enumerate(error_logs[:count]):
                modified_time = datetime.fromtimestamp(os.path.getmtime(log_file))
                logger.info(f"\nError Log {i+1}: {os.path.basename(log_file)} - {modified_time}")
                
                # Display the log content
                try:
                    with open(log_file, 'r') as f:
                        # Read the last 20 lines to avoid overwhelming output
                        lines = f.readlines()
                        if len(lines) > 20:
                            logger.info(f"...Showing last 20 of {len(lines)} lines...")
                            lines = lines[-20:]
                        
                        for line in lines:
                            print(line.strip())
                except Exception as e:
                    logger.error(f"Error reading log file {log_file}: {e}")
            
            success = True
    elif args.method == "test_error_logging":
        # Test error logging functionality
        from prd_gen.utils.debugging import log_error
        
        try:
            logger.info(f"Testing error logging with message: '{args.error_message}'")
            
            # Generate different types of errors to test logging
            # 1. Simple error
            simple_error_log = log_error(f"{args.error_message} - Simple Test")
            
            # 2. Error with exception
            try:
                # Deliberately cause an exception
                result = 1 / 0
            except Exception as e:
                exception_error_log = log_error(f"{args.error_message} - Exception Test", exc_info=e)
            
            # 3. Error with custom exception
            custom_error_log = log_error(f"{args.error_message} - Custom Exception Test", 
                                       Exception("This is a custom test exception"))
            
            logger.info("✅ Successfully logged test errors. Check these files for error details:")
            logger.info(f"  - {simple_error_log}")
            logger.info(f"  - {exception_error_log}")
            logger.info(f"  - {custom_error_log}")
            
            # Display most recent error log
            import os
            from datetime import datetime
            
            if os.path.exists(custom_error_log):
                modified_time = datetime.fromtimestamp(os.path.getmtime(custom_error_log))
                logger.info(f"\nMost recent error log: {os.path.basename(custom_error_log)} - {modified_time}")
                
                with open(custom_error_log, 'r') as f:
                    content = f.read()
                    print("\n" + content.strip())
            
            success = True
        except Exception as e:
            logger.error(f"❌ Error testing error logging: {e}")
            success = False
    
    if success:
        logger.info("✅ MCP client test passed")
        exit(0)
    else:
        logger.error("❌ MCP client test failed")
        exit(1) 