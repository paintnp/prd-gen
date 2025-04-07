#!/usr/bin/env python
"""
MCP Connection Test Script

This script tests MCP server connections, error handling, 
and iteration management in the PRD generator.
"""

import os
import sys
import json
import argparse
import logging
import time
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("mcp_test")

# Valid and invalid URLs for testing
VALID_URL = "http://localhost:9000/sse"
INVALID_URL = "http://localhost:12345/sse"
INVALID_PATH = "http://localhost:9000/invalid-path"

def test_search(url, query="Test query"):
    """
    Test search using the specified MCP URL.
    
    Args:
        url (str): The MCP server URL to test
        query (str): The search query to use
        
    Returns:
        bool: True if search succeeded, False otherwise
    """
    # Set the environment variable for the test
    os.environ["MCP_SERVER_URL"] = url
    
    # Import required modules now that we've set the environment
    try:
        from prd_gen.utils.direct_search import direct_search_web
        from prd_gen.utils.debugging import setup_logging
        
        # Set up logging for the test
        test_logger = setup_logging()
        
        # Log what we're doing
        logger.info(f"Testing search with URL: {url}")
        logger.info(f"Query: {query}")
        
        # Try to search
        result = direct_search_web(query)
        
        # Log the result
        logger.info("Search result:")
        logger.info(json.dumps(result, indent=2))
        
        # Check if we got an error
        if isinstance(result, dict) and "error" in result:
            logger.info("❌ Search returned an error")
            return False
        else:
            logger.info("✅ Search succeeded")
            return True
    except Exception as e:
        logger.error(f"❌ Exception during test: {e}")
        return False

def test_iteration_logs():
    """
    Test the iteration process and log files to understand 
    how iterations are being tracked and executed.
    """
    logger.info("Testing PRD generator iteration process...")
    
    # Check for iteration logs in the logs directory
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logger.error(f"Logs directory not found: {logs_dir}")
        return False
        
    # Look for critique and revision logs
    critique_logs = list(logs_dir.glob("critique_*.json"))
    revision_logs = list(logs_dir.glob("revision_*.json"))
    
    logger.info(f"Found {len(critique_logs)} critique logs and {len(revision_logs)} revision logs")
    
    # Analyze the most recent logs
    critique_logs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    revision_logs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Check the most recent critique log
    if critique_logs:
        newest_critique = critique_logs[0]
        logger.info(f"Newest critique log: {newest_critique.name} (modified: {time.ctime(newest_critique.stat().st_mtime)})")
        
        try:
            with open(newest_critique, 'r') as f:
                critique_data = json.load(f)
                logger.info(f"Critique log contains keys: {list(critique_data.keys())}")
                if 'iteration' in critique_data:
                    logger.info(f"Critique iteration: {critique_data['iteration']}")
        except Exception as e:
            logger.error(f"Error reading critique log: {e}")
    
    # Check the most recent revision log
    if revision_logs:
        newest_revision = revision_logs[0]
        logger.info(f"Newest revision log: {newest_revision.name} (modified: {time.ctime(newest_revision.stat().st_mtime)})")
        
        try:
            with open(newest_revision, 'r') as f:
                revision_data = json.load(f)
                logger.info(f"Revision log contains keys: {list(revision_data.keys())}")
                if 'iteration' in revision_data:
                    logger.info(f"Revision iteration: {revision_data['iteration']}")
        except Exception as e:
            logger.error(f"Error reading revision log: {e}")
    
    # Check any iteration state files
    state_files = list(Path(".").glob("*state*.json"))
    if state_files:
        logger.info(f"Found {len(state_files)} state files")
        for state_file in state_files:
            logger.info(f"State file: {state_file.name} (modified: {time.ctime(state_file.stat().st_mtime)})")
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                    logger.info(f"State file contains keys: {list(state_data.keys())}")
                    if 'iteration' in state_data:
                        logger.info(f"State iteration: {state_data['iteration']}")
                    if 'max_iterations' in state_data:
                        logger.info(f"Max iterations: {state_data['max_iterations']}")
            except Exception as e:
                logger.error(f"Error reading state file: {e}")
    
    # Look for iteration-related DEBUG logs
    debug_log = Path("debug.log")
    if debug_log.exists():
        logger.info(f"Analyzing debug log for iteration information...")
        try:
            with open(debug_log, 'r') as f:
                # Read the last 100 lines of the debug log
                lines = f.readlines()[-100:]
                iteration_lines = [line for line in lines if 'iteration' in line.lower()]
                
                logger.info(f"Found {len(iteration_lines)} iteration-related log lines")
                for line in iteration_lines:
                    logger.info(f"Iteration log: {line.strip()}")
        except Exception as e:
            logger.error(f"Error reading debug log: {e}")
    
    logger.info("Iteration process testing complete")
    return True

def test_custom_scenario(url, query="Test query", iterations=3):
    """
    Test a custom scenario with specific parameters.
    """
    logger.info(f"Testing custom scenario with URL: {url}, query: {query}, iterations: {iterations}")
    
    # Set environment variables for testing
    os.environ["MCP_SERVER_URL"] = url
    os.environ["MAX_ITERATIONS"] = str(iterations)
    
    # Add your custom scenario test code here
    logger.info("Custom scenario not implemented yet")
    return True

def test_cancel_scope_handling():
    """
    Test the client's ability to handle TaskGroup cancel scope errors.
    
    This test simulates the error we were encountering with the SSE client
    by triggering concurrent operations that might lead to cancel scope issues.
    """
    logger.info("Testing TaskGroup cancel scope error handling...")
    
    # Set the environment variable for the test
    os.environ["MCP_SERVER_URL"] = VALID_URL
    
    try:
        # Import required modules
        from prd_gen.utils.direct_search import direct_search_web
        from prd_gen.utils.mcp_client import create_sse_connection, run_async
        import anyio
        
        # Define an async test function
        async def stress_test():
            """Run multiple concurrent operations to try to trigger race conditions"""
            logger.info("Starting stress test of SSE connection...")
            
            async def connect_task():
                client, session_id = await create_sse_connection()
                logger.info(f"Connected with session_id: {session_id}")
                return client, session_id
            
            async def cancel_task(task):
                # Wait a bit then cancel the task to simulate the race condition
                await anyio.sleep(0.1)
                logger.info("Cancelling task...")
                task.cancel()
            
            # Run multiple concurrent operations
            try:
                async with anyio.create_task_group() as tg:
                    for _ in range(3):
                        # Create a connection task
                        task = asyncio.create_task(connect_task())
                        # Create a task to cancel it
                        tg.start_soon(cancel_task, task)
                        # Try to await the connection task
                        try:
                            await task
                        except asyncio.CancelledError:
                            logger.info("Task was cancelled as expected")
            except Exception as e:
                logger.info(f"Task group completed with: {e}")
            
            # Now try a normal connection to verify recovery
            logger.info("Verifying connection works after stress test...")
            try:
                client, session_id = await create_sse_connection()
                logger.info(f"Successfully connected with session_id: {session_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to connect after stress test: {e}")
                return False
        
        # Run the async test
        result = run_async(stress_test())
        
        if result:
            logger.info("✅ Successfully handled TaskGroup cancel scope errors")
        else:
            logger.error("❌ Failed to handle TaskGroup cancel scope errors")
        
        return result
    except Exception as e:
        logger.error(f"❌ Exception during test: {e}")
        return False

def main():
    """Run the MCP connection tests."""
    parser = argparse.ArgumentParser(description="Test MCP server connections and PRD generation")
    parser.add_argument("--url", choices=["valid", "invalid", "bad-path", "custom"], 
                      default="valid", help="Which URL to test")
    parser.add_argument("--custom-url", type=str, help="Custom URL to test")
    parser.add_argument("--query", type=str, default="What's new in AI technology", 
                      help="Search query to use")
    parser.add_argument("--test", choices=["connection", "iterations", "custom", "cancel-scope"],
                      default="connection", help="Which test to run")
    parser.add_argument("--iterations", type=int, default=3,
                      help="Number of iterations for custom scenario test")
    
    args = parser.parse_args()
    
    # Determine the URL to test
    test_url = VALID_URL
    if args.url == "invalid":
        test_url = INVALID_URL
    elif args.url == "bad-path":
        test_url = INVALID_PATH
    elif args.url == "custom" and args.custom_url:
        test_url = args.custom_url
    
    # Run the appropriate test
    if args.test == "connection":
        success = test_search(test_url, args.query)
    elif args.test == "iterations":
        success = test_iteration_logs()
    elif args.test == "custom":
        success = test_custom_scenario(test_url, args.query, args.iterations)
    elif args.test == "cancel-scope":
        success = test_cancel_scope_handling()
    else:
        logger.error(f"Unknown test type: {args.test}")
        success = False
    
    # Return appropriate exit code
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 