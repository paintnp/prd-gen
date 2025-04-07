"""
UI helpers for displaying status messages, errors, and search results.
"""

import sys
import logging
from typing import Dict, Any

# Set up logging
logger = logging.getLogger("prd_gen")

def display_search_status(results: Dict[str, Any]) -> None:
    """
    Display search status or error messages in a user-friendly way.
    
    Args:
        results: The search results dictionary
    """
    # Check if there's a user-friendly message
    if "user_message" in results:
        # Print with a box around it for visibility
        message = results["user_message"]
        width = min(100, max(60, len(max(message.split('\n'), key=len))))
        
        print("\n" + "=" * width)
        print(message)
        print("=" * width + "\n")
        
    # If there was an error but no user message
    elif "error" in results:
        print(f"\n{'=' * 60}\n⚠️ Search issue: {results['error']}\n{'=' * 60}\n")
        
    # If search was successful but results were truncated
    elif "message" in results:
        print(f"\nNote: {results['message']}\n")

def format_search_results_for_display(results: Dict[str, Any], max_results: int = 3) -> str:
    """
    Format search results for display, limiting the number of results shown.
    
    Args:
        results: The search results dictionary
        max_results: Maximum number of results to display
        
    Returns:
        str: Formatted search results ready for display
    """
    if "error" in results:
        # Return the user message if available
        if "user_message" in results:
            return f"Search error: {results['user_message']}"
        return f"Search error: {results['error']}"
    
    # Extract actual results
    result_items = results.get("results", [])
    if not result_items:
        return "No search results found."
    
    # Limit number of results shown
    if len(result_items) > max_results:
        result_items = result_items[:max_results]
    
    # Format the results
    formatted = f"Found {len(results.get('results', []))} results for '{results.get('query', 'unknown query')}':"
    
    for i, item in enumerate(result_items):
        title = item.get("title", "Untitled")
        url = item.get("url", "No URL")
        snippet = item.get("content", "No content available")
        
        # Trim content for display purposes
        if len(snippet) > 300:
            snippet = snippet[:297] + "..."
        
        formatted += f"\n\n{i+1}. {title}\n   {url}\n   {snippet}"
    
    # Add message if there were more results
    if len(results.get("results", [])) > max_results:
        formatted += f"\n\n(Showing {max_results} of {len(results.get('results', []))} results)"
    
    return formatted

def print_friendly_system_error(error_message: str, suggestions: list = None) -> None:
    """
    Print a user-friendly system error with suggestions.
    
    Args:
        error_message: The main error message
        suggestions: List of suggestions to help resolve the issue
    """
    width = 70
    print("\n" + "!" * width)
    print(f"SYSTEM MESSAGE: {error_message}".center(width))
    print("-" * width)
    
    if suggestions:
        print("Suggestions to fix this:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")
    
    print("!" * width + "\n") 