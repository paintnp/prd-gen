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
from typing import Dict, Any, List, Optional

# Set up logging
from prd_gen.utils.debugging import setup_logging
logger = setup_logging()

class DirectSearchClient:
    """
    A direct HTTP client for interacting with the MCP server's search functionality
    without using the async MCP client.
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the DirectSearchClient.
        
        Args:
            base_url: The base URL of the MCP server (default: http://localhost:9000)
        """
        self.base_url = base_url or os.environ.get("MCP_SERVER_URL", "http://localhost:9000").replace("/sse", "")
        self.session = requests.Session()
        self.session_id = None
        
    def _create_session(self) -> bool:
        """
        Create a new session with the MCP server.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Create a new session
            url = f"{self.base_url}/session"
            response = self.session.post(url)
            response.raise_for_status()
            
            # Extract the session ID
            data = response.json()
            self.session_id = data.get("session_id")
            if not self.session_id:
                logger.error("Failed to get session ID from server response")
                return False
                
            logger.info(f"Created new MCP session with ID: {self.session_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating MCP session: {e}")
            return False
            
    def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a request to the MCP server.
        
        Args:
            method: The JSON-RPC method to call
            params: Parameters for the method
            
        Returns:
            Dict[str, Any]: The response from the server
        """
        try:
            # Create the request payload
            payload = {
                "jsonrpc": "2.0",
                "id": int(time.time() * 1000),  # Use timestamp as ID
                "method": method,
                "params": params or {}
            }
            
            # Send the request
            url = f"{self.base_url}/messages"
            if self.session_id:
                url += f"?session_id={self.session_id}"
                
            logger.debug(f"Sending request to {url}: {json.dumps(payload)}")
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            logger.debug(f"Received response: {json.dumps(data)}")
            return data
        except Exception as e:
            logger.error(f"Error sending request to MCP server: {e}")
            return {"error": str(e)}
            
    def search_web(self, query: str) -> Dict[str, Any]:
        """
        Perform a web search using the MCP server.
        
        Args:
            query: The search query
            
        Returns:
            Dict[str, Any]: The search results
        """
        try:
            # Create a session if we don't have one
            if not self.session_id and not self._create_session():
                return self._create_error_response(query, "Failed to create MCP session")
                
            # Send the search request
            params = {
                "tool": "search_web",
                "args": {
                    "query": query
                }
            }
            
            response = self._send_request("tools/invoke", params)
            
            # Check for errors
            if "error" in response:
                return self._create_error_response(query, f"MCP server error: {response['error']}")
                
            # Extract the result
            if "result" in response:
                return response["result"]
                
            # Fallback
            return self._create_empty_response(query)
        except Exception as e:
            logger.error(f"Error in search_web: {e}")
            return self._create_error_response(query, str(e))
            
    def _create_error_response(self, query: str, error_message: str) -> Dict[str, Any]:
        """
        Create a formatted error response.
        
        Args:
            query: The original query
            error_message: The error message
            
        Returns:
            Dict[str, Any]: A formatted error response
        """
        logger.warning(f"Search error for query '{query}': {error_message}")
        return {
            "error": error_message,
            "query": query,
            "results": [
                {
                    "title": "Search Error",
                    "url": "N/A",
                    "content": f"An error occurred during search: {error_message}. Please try a different query or proceed without search results."
                }
            ]
        }
        
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
    Perform a web search using a direct HTTP implementation.
    
    Args:
        query: The search query
        
    Returns:
        Dict[str, Any]: The search results
    """
    client = get_direct_search_client()
    return client.search_web(query)

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