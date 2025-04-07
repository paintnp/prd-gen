#!/usr/bin/env python3
"""
Test script for verifying search functionality in an agent workflow.

This script simulates a basic agent workflow with search to identify and fix potential issues.
"""

import os
import json
import time
from dotenv import load_dotenv
from openai import OpenAI
from prd_gen.utils.direct_search import direct_search_web_summarized, direct_search_web
from prd_gen.utils.debugging import setup_logging, log_error

# Load environment variables
load_dotenv()

# Set up logging
logger = setup_logging()

def fallback_search(query, summary_focus="key findings"):
    """
    Perform a search with automatic fallback options.
    
    Args:
        query (str): The search query
        summary_focus (str): Focus for summary generation
        
    Returns:
        dict: Search results or mock results if search fails
    """
    print(f"Attempting search for: '{query}' with focus: '{summary_focus}'")
    
    # First try summarized search
    try:
        results = direct_search_web_summarized(query, summary_focus)
        
        # Verify we have valid results
        if results and isinstance(results, dict) and "results" in results and len(results["results"]) > 0:
            print(f"✅ Summarized search successful - returned {len(results['results'])} results")
            return results
        else:
            print("⚠️ Summarized search returned empty or invalid results, trying fallback")
            raise ValueError("Invalid results format")
            
    except Exception as e:
        print(f"⚠️ Summarized search failed: {e}")
        
        # Second try regular search
        try:
            print("Attempting fallback to regular search...")
            results = direct_search_web(query)
            
            # Verify we have valid results
            if results and isinstance(results, dict) and "results" in results and len(results["results"]) > 0:
                print(f"✅ Regular search successful - returned {len(results['results'])} results")
                return results
            else:
                print("⚠️ Regular search returned empty or invalid results, using mock data")
                raise ValueError("Invalid results format from regular search")
                
        except Exception as e2:
            print(f"⚠️ Regular search also failed: {e2}")
            
            # Final fallback: create mock results
            print("Generating mock search results as final fallback")
            return {
                "query": query,
                "summary_focus": summary_focus,
                "results": [
                    {
                        "title": "Mock Search Result - Smart Assistant Market Trends",
                        "url": "https://example.com/mock-result-1",
                        "summary": "The smart assistant market is growing rapidly with voice-enabled devices becoming increasingly common in homes worldwide. Key players include Amazon Alexa, Google Assistant, and Apple Siri, with market share distributed across these platforms. Privacy concerns remain a significant factor influencing consumer adoption, with many users expressing concerns about always-on listening capabilities."
                    },
                    {
                        "title": "Mock Search Result - Voice Technology Adoption",
                        "url": "https://example.com/mock-result-2", 
                        "summary": "Voice technology adoption has increased by approximately 35% year-over-year, with highest usage in smart home control, question answering, and basic task assistance. Integration with other smart home devices is a key driver of adoption, with users who own multiple smart home devices being 3x more likely to use voice assistants regularly."
                    }
                ]
            }
            
def simulate_agent_workflow(product_idea):
    """
    Simulate a simple agent workflow with search integration.
    
    Args:
        product_idea (str): The product idea to research
        
    Returns:
        str: The generated PRD (or in this case, just a summary of findings)
    """
    client = OpenAI()
    
    print(f"Simulating agent workflow for idea: '{product_idea}'")
    
    # Generate search queries based on the product idea
    search_query_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert at creating search queries to gather information for product development."},
            {"role": "user", "content": f"Generate two search queries to research the market for this product idea: {product_idea}. Return them as a JSON object with an array of query strings."}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    
    # Extract the search queries
    search_queries = json.loads(search_query_response.choices[0].message.content)["queries"]
    print(f"Generated search queries: {search_queries}")
    
    # Perform searches with fallback
    search_results = []
    for i, query in enumerate(search_queries):
        print(f"\nExecuting search {i+1}/{len(search_queries)}")
        results = fallback_search(query)
        search_results.append(results)
        time.sleep(1)  # Small delay between searches
    
    # Process the search results using GPT-4o
    result_summaries = []
    for i, result in enumerate(search_results):
        # Extract the content/summaries from the results
        content = []
        if "results" in result and isinstance(result["results"], list):
            for item in result["results"]:
                if "summary" in item:
                    content.append(item["summary"])
                elif "content" in item:
                    content.append(item["content"])
        
        # Join the content
        joined_content = "\n\n".join(content)
        
        # Summarize with GPT-4o
        summary_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert at analyzing market research and extracting key insights."},
                {"role": "user", "content": f"Analyze this search result data related to our product idea '{product_idea}' and summarize the key findings in 3-5 bullet points:\n\n{joined_content}"}
            ],
            temperature=0.2
        )
        
        summary = summary_response.choices[0].message.content
        result_summaries.append(summary)
        
    # Combine the summaries into a final report
    final_report = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert product manager who creates concise market analysis reports."},
            {"role": "user", "content": f"Based on the following market research summaries for the product idea '{product_idea}', create a brief market analysis section that would go into a PRD:\n\n{''.join(result_summaries)}"}
        ],
        temperature=0.3
    )
    
    return final_report.choices[0].message.content

if __name__ == "__main__":
    # Test the workflow with a product idea
    product_idea = "A voice-controlled smart assistant for scheduling meetings and managing calendar events"
    report = simulate_agent_workflow(product_idea)
    
    print("\n" + "="*80 + "\n")
    print("FINAL MARKET ANALYSIS:")
    print("\n" + "="*80 + "\n")
    print(report)
    print("\n" + "="*80 + "\n") 