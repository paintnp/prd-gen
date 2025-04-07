"""
Direct Search Implementation

This module provides a direct HTTP implementation of the search_web functionality
without relying on the MCP client's complex async structure.
"""

import requests
import json
import logging
import os
import time
from typing import Dict, Any, List, Optional, Union
from prd_gen.utils.mcp_client import get_mcp_tools, search_web, run_async, search_web_summarized
from prd_gen.utils.debugging import setup_logging, log_error

# Set up logging
logger = setup_logging()

# Configure max content size to prevent token limit issues
MAX_RESULT_CHARS = 8000  # Limit characters per search result
MAX_TOTAL_CHARS = 20000  # Limit total characters for all results combined
MAX_RESULTS = 2  # Limit number of results returned

class DirectSearchClient:
    """
    A direct client for interacting with the MCP server's search functionality
    that leverages the working MCP client implementation.
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the DirectSearchClient.
        
        Args:
            base_url: The base URL of the MCP server (default: http://localhost:9000/sse)
        """
        # Store the server URL for logging purposes
        self.server_url = base_url or os.environ.get("MCP_SERVER_URL", "http://localhost:9000/sse")
        self.mcp_tools = None
        
    def search_web(self, query: str) -> Dict[str, Any]:
        """
        Perform a web search using the MCP server by leveraging the existing MCP client.
        
        Args:
            query: The search query
            
        Returns:
            Dict[str, Any]: The search results
        """
        try:
            # Log what we're doing
            logger.info(f"Searching for '{query}' using MCP client")
            
            # Try to get tools from MCP (uses cached tools if available)
            tools = run_async(get_mcp_tools())
            
            # If we didn't get any tools, return an error
            if not tools:
                error_msg = f"Failed to retrieve tools from MCP server. Please ensure the server is running at {self.server_url}"
                error_log = log_error(error_msg)
                return self._create_error_response(
                    query, 
                    error_msg,
                    {
                        "error_type": "connection_error",
                        "server_url": self.server_url,
                        "connection_attempts": 3,
                        "failure_reason": "No tools were returned from the MCP server"
                    }
                )
            
            # Find the search tool
            search_tool = next((tool for tool in tools if tool.name == "search_web"), None)
            
            # If we don't have a search tool, return an error
            if not search_tool:
                error_msg = "The search_web tool is not available from the MCP server. Please ensure your MCP server has this tool enabled."
                error_log = log_error(error_msg)
                return self._create_error_response(
                    query, 
                    error_msg,
                    {
                        "error_type": "tool_not_available",
                        "server_url": self.server_url,
                        "available_tools": [t.name for t in tools],
                        "required_tool": "search_web",
                        "failure_reason": "The required search_web tool was not found in the available tools"
                    }
                )
            
            # Use the search tool
            logger.info(f"Using search_web tool to search for: {query}")
            result = run_async(search_web(search_tool, query))
            
            # Check if the result is valid
            if not result:
                logger.warning(f"Search returned empty result for: {query}")
                return self._create_empty_response(query)
            elif isinstance(result, str):
                # The result might be a JSON string
                try:
                    parsed_result = json.loads(result)
                    return parsed_result
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse JSON response: {e}"
                    error_log = log_error(error_msg, exc_info=True)
                    # If it's not valid JSON, return it as content in our standard format
                    return {
                        "query": query,
                        "results": [
                            {
                                "title": "Search Results",
                                "url": "N/A",
                                "content": result
                            }
                        ]
                    }
            elif isinstance(result, dict) and "error" in result:
                error_msg = f"Search returned error: {result['error']}"
                error_log = log_error(error_msg)
                return self._create_error_response(
                    query, 
                    result["error"],
                    {
                        "error_type": "search_api_error",
                        "server_url": self.server_url,
                        "original_error": result,
                        "failure_reason": "The search API returned an error response"
                    }
                )
            
            # Return the successful result
            logger.info(f"Search completed successfully for: {query}")
            return result
            
        except Exception as e:
            error_msg = f"Exception during search: {str(e)}"
            error_log = log_error(error_msg, exc_info=True)
            logger.error(f"Error in search_web: {e} (see {error_log} for details)")
            
            # Attempt to categorize the error
            error_details = {
                "exception_type": type(e).__name__,
                "exception_message": str(e),
                "server_url": self.server_url
            }
            
            # Determine error type based on exception and message
            error_message = str(e).lower()
            
            # Check for common HTTP status codes in the error message
            if "404" in error_message or "not found" in error_message:
                error_details["error_type"] = "not_found_error"
                # Try to extract path information
                if self.server_url:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(self.server_url)
                    error_details["path"] = parsed_url.path
                    error_details["host"] = parsed_url.netloc
                    error_details["failure_reason"] = f"Endpoint {parsed_url.path} not found on server {parsed_url.netloc}"
                    # Suggest the correct path if it's not already /sse
                    if parsed_url.path != "/sse":
                        error_details["suggested_path"] = "/sse"
            elif "401" in error_message or "unauthorized" in error_message:
                error_details["error_type"] = "authentication_error"
                error_details["failure_reason"] = "Authentication failed - invalid credentials or token"
            elif "403" in error_message or "forbidden" in error_message:
                error_details["error_type"] = "authorization_error"
                error_details["failure_reason"] = "Authorization failed - insufficient permissions"
            elif "timeout" in error_message or "timed out" in error_message:
                error_details["error_type"] = "timeout_error"
                error_details["failure_reason"] = "Request timed out - server may be overloaded or unreachable"
            elif "connection" in error_message or "connect" in error_message or "failed to establish" in error_message:
                error_details["error_type"] = "connection_error"
                error_details["failure_reason"] = "Failed to establish connection - server may be down or unreachable"
            else:
                error_details["error_type"] = "unknown_error"
                error_details["failure_reason"] = f"Unrecognized error: {error_message}"
            
            # Add HTTP status code if available
            if "HTTPStatusError" in error_details["exception_type"] or any(code in error_message for code in ["404", "401", "403", "500", "502", "503", "504"]):
                # Try to extract status code
                import re
                status_match = re.search(r'(\d{3})', error_message)
                if status_match:
                    error_details["http_status_code"] = status_match.group(1)
            
            return self._create_error_response(
                query, 
                f"Exception during search: {str(e)}. Please verify the MCP server is running at {self.server_url}",
                error_details
            )
            
    def _create_error_response(self, query: str, error_message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a standardized error response.
        
        Args:
            query: The original search query
            error_message: The main error message
            details: Additional error details and diagnostic information
            
        Returns:
            Dict[str, Any]: A structured error response
        """
        # Create basic error content
        error_content = f"An error occurred during search: {error_message}. "
        error_content += f"Please ensure the MCP server is running and properly configured at {self.server_url}"
        
        # Check if error contains 404 Not Found
        if details and "exception_message" in details:
            error_msg = details["exception_message"].lower()
            if "404" in error_msg or "not found" in error_msg:
                details["error_type"] = "not_found_error"
                if "server_url" in details:
                    from urllib.parse import urlparse
                    url = urlparse(details["server_url"])
                    details["path"] = url.path
                    details["host"] = url.netloc
                    details["failure_reason"] = f"Endpoint {url.path} not found on server {url.netloc}"
        
        # Initialize the error response
        error_response = {
            "error": error_message,
            "query": query,
            "error_type": "connection_error" if details is None else details.get("error_type", "unknown_error"),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "server_url": self.server_url,
            "results": [
                {
                    "title": "Search Error",
                    "url": "N/A",
                    "content": error_content
                }
            ]
        }
        
        # Add diagnostic details if available
        if details:
            error_response["diagnostic_info"] = details
            
            # Add suggested actions based on error type
            error_type = details.get("error_type", "unknown_error")
            if error_type == "connection_error":
                error_response["suggested_action"] = [
                    "Verify the MCP server is running",
                    "Check network connectivity",
                    "Confirm the server URL is correct",
                    f"Try accessing {self.server_url} directly in a browser"
                ]
            elif error_type == "authentication_error":
                error_response["suggested_action"] = [
                    "Verify API credentials",
                    "Check if authentication token has expired",
                    "Ensure you have the correct permissions"
                ]
            elif error_type == "timeout_error":
                error_response["suggested_action"] = [
                    "The server may be overloaded - try again later",
                    "Check if the query is too complex",
                    "Verify network stability"
                ]
            elif error_type == "not_found_error":
                path = details.get("path", "unknown")
                host = details.get("host", "unknown")
                error_response["suggested_action"] = [
                    f"The endpoint '{path}' was not found on server {host}",
                    "Verify the endpoint path is correct",
                    "Check server documentation for correct API endpoints",
                    f"The correct endpoint may be '/sse' instead of '{path}'"
                ]
            elif error_type == "unknown_error":
                error_response["suggested_action"] = [
                    "Check server logs for more details",
                    "Verify server configuration",
                    "Check network connectivity"
                ]
        
        # Log the error for troubleshooting
        logger.warning(f"Search error for query '{query}': {error_message}")
        if details and "exception_message" in details:
            logger.debug(f"Error details: {details['exception_message']}")
        
        return error_response
        
    def _create_empty_response(self, query: str) -> Dict[str, Any]:
        """
        Create an empty response for when no results are found.
        
        Args:
            query: The original query
            
        Returns:
            Dict[str, Any]: A formatted empty response
        """
        return {
            "query": query,
            "results": []
        }

# Global client instance
_direct_search_client = None

def get_direct_search_client() -> DirectSearchClient:
    """
    Get a DirectSearchClient instance.
    
    Returns:
        DirectSearchClient: A client instance
    """
    global _direct_search_client
    if _direct_search_client is None:
        _direct_search_client = DirectSearchClient()
    return _direct_search_client

def direct_search_web(query: str) -> Dict[str, Any]:
    """
    Perform a web search using the MCP search tool.
    
    Args:
        query (str): The search query
        
    Returns:
        Dict[str, Any]: The search results or error information
    """
    try:
        # Log the search attempt with a user-friendly message
        logger.info(f"Searching for: {query}")
        
        # Get the tools from the MCP server
        tools = run_async(get_mcp_tools())
        
        # Look for the search_web tool
        search_tool = None
        for tool in tools:
            if tool.name == "search_web":
                search_tool = tool
                break
                
        if not search_tool:
            # User-friendly error message when search tool isn't available
            error_message = (
                "Search unavailable: The search tool couldn't be found.\n"
                "Please check that:\n"
                "1. The MCP server is running (usually on port 9000)\n"
                "2. Your connection to the server is working\n"
                "3. The server has the search_web tool enabled"
            )
            logger.error(error_message)
            return {
                "error": "Search tool not available", 
                "user_message": error_message,
                "query": query,
                "results": []
            }
        
        # Perform the search
        raw_results = run_async(search_web(search_tool, query))
        
        # If the result is a string (raw JSON or text), convert it to proper format
        if isinstance(raw_results, str):
            logger.info(f"Converting string result of {len(raw_results)} chars to structured format")
            # Try to parse as JSON first
            try:
                import json
                parsed = json.loads(raw_results)
                if isinstance(parsed, dict):
                    raw_results = parsed
                else:
                    # Create a properly formatted result
                    raw_results = {
                        "query": query,
                        "results": [
                            {
                                "title": "Search Results",
                                "url": "https://example.com/search",
                                "content": raw_results[:100000] if len(raw_results) > 100000 else raw_results
                            }
                        ]
                    }
            except json.JSONDecodeError:
                # Not valid JSON, create a single result with the text content
                raw_results = {
                    "query": query,
                    "results": [
                        {
                            "title": "Search Results",
                            "url": "https://example.com/search",
                            "content": raw_results[:100000] if len(raw_results) > 100000 else raw_results
                        }
                    ]
                }
        
        # Process and truncate results to prevent token limit errors
        processed_results = _process_search_results(raw_results, query)
        
        return processed_results
        
    except Exception as e:
        # Create a user-friendly error message
        error_type = type(e).__name__
        error_message = str(e)
        
        user_message = _create_user_friendly_error(error_type, error_message, query)
        
        logger.error(f"Error searching web: {error_type}: {error_message}")
        
        return {
            "error": f"{error_type}: {error_message}",
            "user_message": user_message,
            "query": query,
            "results": []
        }

def _process_search_results(results: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Process and truncate search results to prevent token limit errors.
    
    Args:
        results: The raw search results
        query: The original search query
        
    Returns:
        Dict[str, Any]: The processed search results
    """
    # If results already have an error, just return them
    if "error" in results:
        # Add a user-friendly message if not present
        if "user_message" not in results:
            results["user_message"] = _create_user_friendly_error(
                "SearchError", results["error"], query
            )
        return results
    
    # Check if we have valid results
    if not isinstance(results, dict):
        logger.error(f"Invalid results type: {type(results).__name__}")
        return {
            "error": "Invalid search results format",
            "user_message": "The search service returned data in an unexpected format. Please try again with a different query.",
            "query": query,
            "results": []
        }
    
    # Get the results list, properly handling different formats
    result_items = []
    if "results" in results and isinstance(results["results"], list):
        result_items = results["results"]
    else:
        # Try to extract content from a string or other structure
        logger.warning(f"Results doesn't have a proper 'results' list: {list(results.keys())}")
        # Try to create a single result item from whatever we have
        content = ""
        if isinstance(results, str):
            content = results
        elif isinstance(results, dict):
            # Try to find content in common fields
            for key in ["content", "text", "snippet", "raw", "response"]:
                if key in results and isinstance(results[key], str):
                    content = results[key]
                    break
        
        if content:
            result_items = [
                {
                    "title": "Search Results",
                    "url": "https://example.com/search",
                    "content": content[:100000] if len(content) > 100000 else content
                }
            ]
    
    # Log the structure
    logger.info(f"Processing {len(result_items)} result items")
    
    # If no results, return as is with a user-friendly message
    if not result_items:
        results["user_message"] = f"No search results found for '{query}'. Please try a different search term."
        results["results"] = []
        return results
    
    # Ensure each result has basic fields
    for i, item in enumerate(result_items):
        if not isinstance(item, dict):
            logger.warning(f"Result item {i} is not a dict, converting")
            result_items[i] = {
                "title": "Search Result",
                "url": "https://example.com/search",
                "content": str(item)[:MAX_RESULT_CHARS]
            }
        else:
            # Ensure each item has the required fields
            if "title" not in item:
                item["title"] = "Search Result"
            if "url" not in item:
                item["url"] = "https://example.com/search"
            if "content" not in item:
                # Try to get content from another field
                for key in ["text", "snippet", "summary", "description"]:
                    if key in item and isinstance(item[key], str):
                        item["content"] = item[key]
                        break
                # If still no content, use a placeholder
                if "content" not in item:
                    item["content"] = "No content available"
    
    # Truncate the number of results if needed
    if len(result_items) > MAX_RESULTS:
        logger.info(f"Truncating search results from {len(result_items)} to {MAX_RESULTS}")
        result_items = result_items[:MAX_RESULTS]
    
    # Track total content size
    total_chars = 0
    truncated = False
    
    # Process each result
    for i, result in enumerate(result_items):
        if "content" in result:
            # Make sure content is a string
            if not isinstance(result["content"], str):
                result["content"] = str(result["content"])
                
            # Truncate individual result if too large
            if len(result["content"]) > MAX_RESULT_CHARS:
                logger.info(f"Truncating content for result {i+1} from {len(result['content'])} to {MAX_RESULT_CHARS} chars")
                result["content"] = result["content"][:MAX_RESULT_CHARS] + "... [Content truncated]"
                truncated = True
            
            # Track total size
            total_chars += len(result["content"])
            logger.info(f"Result {i+1} content size: {len(result['content'])} chars, total so far: {total_chars}")
            
            # If we exceed total limit, truncate remaining results
            if total_chars > MAX_TOTAL_CHARS:
                logger.info(f"Total content exceeds limit ({total_chars} > {MAX_TOTAL_CHARS}), keeping first {i+1} results")
                result_items = result_items[:i+1]
                truncated = True
                break
    
    # Update the results with truncated data
    results["results"] = result_items
    results["query"] = query
    
    # Add a message if we truncated
    if truncated:
        results["message"] = "Search results were truncated due to size limits."
        results["user_message"] = (
            "Your search returned a large amount of data. Some results have been shortened "
            "to stay within system limits. For better results, try a more specific search query."
        )
    
    # Log the final size
    final_size = sum(len(r.get("content", "")) for r in results["results"])
    logger.info(f"Final results: {len(results['results'])} items with total size {final_size} chars")
    
    return results

def _create_user_friendly_error(error_type: str, error_message: str, query: str) -> str:
    """
    Create a user-friendly error message from a technical error.
    
    Args:
        error_type: The type of error
        error_message: The technical error message
        query: The search query
        
    Returns:
        str: A user-friendly error message
    """
    # Look for specific error patterns and provide helpful messages
    
    # Connection errors
    if "connection" in error_message.lower() or "connect" in error_message.lower():
        return (
            "⚠️ Search unavailable: Unable to connect to the search service.\n\n"
            "This could be because:\n"
            "1. The search service is not running\n"
            "2. Your internet connection is down\n"
            "3. The service address is incorrect\n\n"
            "You can continue working without search, or try again later."
        )
    
    # Token limit errors
    if "token" in error_message.lower() and "limit" in error_message.lower():
        return (
            "⚠️ Your search returned too much data.\n\n"
            f"Your search for '{query}' returned a very large amount of information "
            "that exceeds what the system can process. Try:\n"
            "1. Using a more specific search query\n"
            "2. Breaking your search into smaller, focused queries\n"
            "3. Adding specific keywords to narrow the results"
        )
    
    # Not found errors
    if "404" in error_message or "not found" in error_message.lower():
        return (
            "⚠️ Search service endpoint not found.\n\n"
            "The search service is running, but the correct endpoint wasn't found. "
            "This is typically a configuration issue. Please check:\n"
            "1. That you're using the correct server URL\n"
            "2. The URL includes '/sse' at the end\n"
            "3. The search service is properly configured"
        )
    
    # Default friendly message
    return (
        "⚠️ Search unavailable right now.\n\n"
        f"There was a problem with your search for '{query}'. "
        "You can continue working without search results, "
        "or try a different search query later."
    )

def create_mock_search_results(query: str) -> Dict[str, Any]:
    """
    Create mock search results for when the real search fails.
    
    Args:
        query: The search query
        
    Returns:
        Dict[str, Any]: Mock search results
    """
    return {
        "query": query,
        "results": [
            {
                "title": "Language Learning Market Trends 2023",
                "url": "https://example.com/language-learning-trends-2023",
                "content": "The language learning app market is projected to grow at a CAGR of 18.7% from 2023 to 2028. Key trends include AI-powered personalization, immersive learning through AR/VR, integration of speech recognition for pronunciation feedback, and gamification elements to increase user engagement and retention."
            },
            {
                "title": "Top Language Learning Apps Comparison",
                "url": "https://example.com/language-app-comparison",
                "content": "Leading apps like Duolingo, Babbel, and Rosetta Stone dominate the market with different approaches. Duolingo focuses on gamification, Babbel on conversation-based learning, and Rosetta Stone on immersive learning. Newer entrants are differentiating through specialized offerings like business language or regional dialect support."
            }
        ]
    }

def direct_search_web_summarized(query: str, summary_focus: str = "key findings") -> Dict[str, Any]:
    """
    Perform a web search and get summarized results using the MCP search_web_summarized tool.
    
    Args:
        query (str): The search query
        summary_focus (str): Focus for the summary generation (e.g., "key findings", "main points")
        
    Returns:
        Dict[str, Any]: The search results or error information
    """
    try:
        # Log the search attempt with a user-friendly message
        logger.info(f"Searching for: {query} with summary focus: {summary_focus}")
        
        # Get the tools from the MCP server
        tools = run_async(get_mcp_tools())
        
        # Look for the search_web_summarized tool
        search_tool = None
        for tool in tools:
            if tool.name == "search_web_summarized":
                search_tool = tool
                break
                
        if not search_tool:
            # User-friendly error message when search tool isn't available
            error_message = (
                "Summarized search unavailable: The search_web_summarized tool couldn't be found.\n"
                "Please check that:\n"
                "1. The MCP server is running (usually on port 9000)\n"
                "2. Your connection to the server is working\n"
                "3. The server has the search_web_summarized tool enabled"
            )
            logger.error(error_message)
            return {
                "error": "Summarized search tool not available", 
                "user_message": error_message,
                "query": query,
                "summary_focus": summary_focus,
                "results": []
            }
        
        # Perform the search
        raw_response = run_async(search_web_summarized(search_tool, query, summary_focus))
        
        # Parse the response properly
        results = None
        
        # If the raw response is a string, try to parse it as JSON
        if isinstance(raw_response, str):
            try:
                results = json.loads(raw_response)
                logger.info("Successfully parsed string response as JSON")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse string response as JSON: {e}")
        elif isinstance(raw_response, dict):
            # Handle nested MCP server response format with 'content' array
            if 'content' in raw_response and isinstance(raw_response['content'], list):
                logger.info("Found 'content' field in response, extracting data")
                
                # Look for text field containing JSON
                for item in raw_response['content']:
                    if 'type' in item and item['type'] == 'text' and 'text' in item:
                        try:
                            json_str = item['text']
                            logger.info(f"Found JSON string in text field, length: {len(json_str)}")
                            results = json.loads(json_str)
                            logger.info("Successfully parsed JSON results from text field")
                            break
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse JSON from content field: {e}")
            
            # If we couldn't extract from content, use raw response
            if not results:
                logger.info("No JSON data found in content field, using raw response")
                results = raw_response
        
        # If no structured data was found, but we have a string, make one last attempt
        if results is None and isinstance(raw_response, str):
            # Try to clean the string and parse again
            try:
                cleaned_string = raw_response.replace('\\"', '"').replace('\\n', '\n')
                results = json.loads(cleaned_string)
                logger.info("Successfully parsed cleaned string as JSON")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse cleaned string as JSON: {e}")
                # Create a minimal result structure
                results = {
                    "query": query,
                    "summary_focus": summary_focus,
                    "results": [{
                        "title": "Search Results",
                        "content": raw_response[:8000] + "..." if len(raw_response) > 8000 else raw_response
                    }]
                }
        
        # If we have results, return them
        if results:
            return results
        else:
            error_message = "No results were returned from the summarized search"
            logger.error(error_message)
            return {
                "error": "No results", 
                "user_message": error_message,
                "query": query,
                "summary_focus": summary_focus,
                "results": []
            }
            
    except Exception as e:
        # Log the error
        error_log_path = log_error(
            f"Error performing summarized web search for '{query}': {e}", 
            exc_info=True
        )
        
        # User-friendly error message
        error_message = (
            f"Search error: {str(e)}\n"
            "The search could not be completed. This could be due to:\n"
            "1. Connection issues with the MCP server\n"
            "2. An internal error in the search service\n"
            "See the error log for more details."
        )
        
        logger.error(f"Error in summarized search: {e} (see {error_log_path} for details)")
        
        # Return error information
        return {
            "error": str(e),
            "user_message": error_message,
            "query": query,
            "summary_focus": summary_focus,
            "results": []
        } 