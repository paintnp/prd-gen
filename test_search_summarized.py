#!/usr/bin/env python3
"""
Test script to verify search_web_summarized functionality.
"""

import os
import json
from dotenv import load_dotenv
from prd_gen.utils.direct_search import direct_search_web_summarized

# Load environment variables
load_dotenv()

def test_search_summarized():
    """Test the search_web_summarized function with a simple query"""
    query = "artificial intelligence applications in healthcare"
    print(f"Testing search_web_summarized with query: '{query}'")
    
    try:
        results = direct_search_web_summarized(query)
        
        # Check if we got valid results
        if results and isinstance(results, dict):
            # Check if we have a summary
            if "summary" in results and results["summary"]:
                print("\n✅ SUCCESS: Got summary from search_web_summarized")
                print("\nSummary excerpt:")
                print(results["summary"][:300] + "...")
            else:
                print("\n❌ ISSUE: No summary in results")
                
            # Check if we have results
            if "results" in results and results["results"]:
                print(f"\n✅ SUCCESS: Got {len(results['results'])} search results")
            else:
                print("\n❌ ISSUE: No search results returned")
                
            # Print the full structure
            print("\nFull results structure:")
            print(json.dumps(results, indent=2)[:1000] + "...")
            
            return True
        else:
            print("\n❌ ISSUE: Invalid results format")
            print(f"Results: {results}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    test_search_summarized() 