#!/usr/bin/env python3
"""
Test script for the search_web_summarized tool.

This script tests the search_web_summarized tool directly using the direct_search implementation.
"""

import os
import json
from dotenv import load_dotenv
from prd_gen.utils.direct_search import direct_search_web_summarized
from prd_gen.utils.debugging import setup_logging

# Load environment variables
load_dotenv()

# Set up logging
logger = setup_logging()

def test_search_summarized():
    """Test the search_web_summarized tool directly."""
    print("Testing search_web_summarized tool...")
    
    # Search query and summary focus
    query = "What is a Product Requirements Document (PRD)"
    summary_focus = "key findings"
    
    print(f"Query: {query}")
    print(f"Summary focus: {summary_focus}")
    
    try:
        # Call the direct search function
        raw_response = direct_search_web_summarized(query, summary_focus)
        
        print(f"Raw response type: {type(raw_response).__name__}")
        
        # Parse results from the response
        results = None
        
        # If the raw response is a string, try to parse it as JSON
        if isinstance(raw_response, str):
            try:
                results = json.loads(raw_response)
                print("Successfully parsed string response as JSON")
            except json.JSONDecodeError as e:
                print(f"Failed to parse string response as JSON: {e}")
        elif isinstance(raw_response, dict):
            # Check if we have a nested 'content' array typical of MCP server responses
            if 'content' in raw_response and isinstance(raw_response['content'], list):
                print("Found 'content' field in response")
                
                # Look for text field containing JSON
                for item in raw_response['content']:
                    if 'type' in item and item['type'] == 'text' and 'text' in item:
                        try:
                            json_str = item['text']
                            print(f"Found JSON string in text field, length: {len(json_str)}")
                            results = json.loads(json_str)
                            print("Successfully parsed JSON results")
                            break
                        except json.JSONDecodeError as e:
                            print(f"Failed to parse JSON: {e}")
        
        # If results is still None, try using raw_response directly
        if results is None:
            print("No parsed results found, using raw response")
            if isinstance(raw_response, str):
                # If it's a string, make one more attempt to clean and parse it
                try:
                    # Sometimes the string has escaped quotes and other issues
                    cleaned_string = raw_response.replace('\\"', '"').replace('\\n', '\n')
                    results = json.loads(cleaned_string)
                    print("Successfully parsed cleaned string as JSON")
                except json.JSONDecodeError:
                    print("Failed to parse cleaned string, treating as plain text")
                    # Create a simple structure for plain text
                    results = {
                        "results": [{
                            "title": "Search Results",
                            "content": raw_response[:1000] + "..." if len(raw_response) > 1000 else raw_response
                        }]
                    }
            else:
                results = raw_response
        
        # Now check if we have results with a 'results' key
        if isinstance(results, dict) and 'results' in results and isinstance(results['results'], list):
            print(f"\n✅ Found {len(results['results'])} results")
            
            # Print query and other metadata
            query_str = results.get('autoprompt_string', results.get('query', 'N/A'))
            print(f"Response query: {query_str}")
            print(f"Response summary focus: {summary_focus}")
            
            # Print each result
            for i, result in enumerate(results["results"]):
                if i >= 3:  # Only show the first 3 results to avoid too much output
                    print(f"\n... and {len(results['results']) - 3} more results")
                    break
                    
                print(f"\nResult {i+1}:")
                print(f"Title: {result.get('title', 'N/A')}")
                print(f"URL: {result.get('url', 'N/A')}")
                
                # Get the summary if available
                summary = result.get('summary', 'N/A')
                print(f"Summary preview: {summary[:200]}..." if len(summary) > 200 else summary)
            
            # Print brief cost information if available
            if "cost_dollars" in results:
                print(f"\nCost information: {results['cost_dollars']}")
            
            return True
        else:
            print(f"\n❌ No results found or invalid response structure")
            print("Raw response: (first 500 chars)")
            if isinstance(raw_response, str):
                print(raw_response[:500] + "...")
            else:
                print(str(raw_response)[:500] + "...")
            return False
    except Exception as e:
        print(f"\n❌ Error testing search_web_summarized: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_search_summarized() 