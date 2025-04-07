#!/usr/bin/env python3
"""
Test script to verify agent integration with the enhanced search functionality.

This script tests a direct call to the creator agent using a simple product idea
to ensure search works correctly in the agent workflow.
"""

import os
import json
import time
from dotenv import load_dotenv
from openai import OpenAI
from prd_gen.utils.debugging import setup_logging
from prd_gen.agents.creator import create_initial_prd
from prd_gen.utils.mcp_client import run_async, get_mcp_tools
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# Set up logging
logger = setup_logging()

def run_agent_test(product_idea):
    """
    Run a test of the creator agent with the given product idea.
    
    Args:
        product_idea (str): The product idea to test with
    
    Returns:
        str: The generated PRD
    """
    print(f"Testing Creator agent with idea: '{product_idea}'")
    
    # Initialize the model
    try:
        # Initialize the OpenAI model
        model_name = os.environ.get("LLM_MODEL", "gpt-4o")
        temperature = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
        
        print(f"Using model: {model_name} with temperature {temperature}")
        
        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
        )
    except Exception as e:
        print(f"Error initializing model: {e}")
        return None
    
    # Get MCP tools
    try:
        # First try to get tools using the get_mcp_tools function
        tools = run_async(get_mcp_tools())
        
        if tools:
            print(f"✅ Successfully loaded {len(tools)} tools from MCP server")
            
            # Check if search tools are available
            search_summarized = any(tool.name == "search_web_summarized" for tool in tools)
            search_regular = any(tool.name == "search_web" for tool in tools)
            
            if search_summarized:
                print("✅ Found search_web_summarized tool")
            else:
                print("⚠️ search_web_summarized tool not found")
                
            if search_regular:
                print("✅ Found search_web tool")
            else:
                print("⚠️ search_web tool not found")
                
            if not search_summarized and not search_regular:
                print("⚠️ No search tools found! Creator will run without search capability")
        else:
            print("⚠️ No tools found from MCP server")
            tools = []
    except Exception as e:
        print(f"Error getting MCP tools: {e}")
        tools = []
    
    # Run the creator agent
    try:
        print("Running creator agent...")
        prd = create_initial_prd(product_idea, tools, llm)
        print("✅ Creator agent completed successfully!")
        return prd
    except Exception as e:
        print(f"❌ Error running creator agent: {e}")
        import traceback
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    # Use a simple product idea for testing
    product_idea = "A mobile app for tracking daily water intake with gamification elements"
    
    # Run the test
    prd = run_agent_test(product_idea)
    
    # Save the results
    if prd:
        output_file = "test_agent_output.md"
        with open(output_file, "w") as f:
            f.write(prd)
        print(f"\nPRD successfully saved to {output_file}")
        
        # Print the first few lines
        print("\nFirst 10 lines of the PRD:")
        for line in prd.split("\n")[:10]:
            print(line) 