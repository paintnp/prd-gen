#!/usr/bin/env python3
"""
PRD Generator - Main Application

This script serves as the entry point for the PRD generator application,
which creates comprehensive Product Requirement Documents from simple prompts
using a team of specialized AI agents and LangGraph for orchestration.
"""

import os
import argparse
import sys
import json
from dotenv import load_dotenv, find_dotenv

from prd_gen.agents.orchestrator import create_prd_workflow
from prd_gen.utils.config import get_config
from prd_gen.utils.debugging import setup_logging
from prd_gen.agents.creator import create_initial_prd
from prd_gen.agents.critic import critique_prd
from prd_gen.agents.reviser import revise_prd
from prd_gen.utils.config import Config
from prd_gen.utils.mcp_client import run_async, get_mcp_tools

# Set up logging
logger = setup_logging()

# Load environment variables - ensure we're looking in the right location
env_path = find_dotenv(usecwd=True)
if env_path:
    logger.debug(f"Loading environment from: {env_path}")
    load_dotenv(env_path, override=True)
else:
    logger.warning("No .env file found!")
    load_dotenv()  # Try loading anyway, in case env vars are set without a file

def check_api_key():
    """Check if the OpenAI API key is set."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable is not set.")
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set your OpenAI API key in the .env file or directly in your environment.")
        sys.exit(1)
    
    # Don't print the actual key, just a masked version for debugging
    masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
    logger.debug(f"Using OpenAI API key: {masked_key}")
    
    # Check if the key is still the placeholder value
    if "your_openai_api_key_here" in api_key.lower():
        logger.error("OpenAI API key appears to be a placeholder value.")
        print("Error: Your OpenAI API key appears to be a placeholder value.")
        print("Please update the .env file with your actual API key.")
        sys.exit(1)
    
    return True

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate a PRD from a product idea prompt")
    parser.add_argument(
        "--idea", "-i", 
        type=str, 
        help="Initial product idea or prompt"
    )
    parser.add_argument(
        "--max_iterations", "-m",
        type=int,
        default=3,
        help="Maximum number of revision iterations (default: 3)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output/prd.md",
        help="Output file path (default: output/prd.md)"
    )
    parser.add_argument(
        "--api-key", "-k",
        type=str,
        help="OpenAI API key (overrides environment variable)"
    )
    return parser.parse_args()

def main():
    """Main function to create a PRD."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate a PRD from a product idea")
    parser.add_argument("--idea", type=str, help="The product idea to create a PRD for", default=None)
    parser.add_argument("--output", type=str, help="The path to the output file", default=None)
    parser.add_argument(
        "--max_iterations", "-m",
        type=int,
        default=3,
        help="Maximum number of revision iterations (default: 3)"
    )
    args = parser.parse_args()

    # Input validation
    config = Config(args)
    if not config.idea:
        logger.error("No product idea provided. Use --idea 'Your idea' to provide one.")
        return

    # Initialize OpenAI model
    try:
        # Initialize the OpenAI model
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            openai_api_key=config.openai_api_key,
            model=config.model,
            temperature=config.temperature,
        )
        logger.info(f"Using model: {config.model}")
    except Exception as e:
        logger.error(f"Error initializing OpenAI model: {e}")
        return

    # Get MCP tools
    tools = run_async(get_mcp_tools())
    logger.info(f"Loaded {len(tools)} tools from MCP server")

    # Generate PRD
    try:
        # Option 1: Use the simple one-iteration approach
        if config.max_iterations <= 1:
            logger.info(f"Using simple approach with single iteration")
            logger.info(f"Creating initial PRD for: {config.idea}")
            prd = create_initial_prd(config.idea, tools, llm)
            logger.info("Initial PRD created")

            logger.info("Critiquing PRD")
            critique = critique_prd(prd, tools, llm)
            logger.info("PRD critique complete")

            logger.info("Revising PRD based on critique")
            final_prd = revise_prd(prd, critique, tools, llm)
            logger.info("PRD revision complete")
        # Option 2: Use the orchestrator for multiple iterations
        else:
            logger.info(f"Using orchestrated approach with up to {config.max_iterations} iterations")
            
            # Load full configuration from environment
            full_config = config.load_from_env()
            
            # Create the PRD workflow
            workflow = create_prd_workflow(full_config)
            
            # Set initial state
            initial_state = {
                "idea": config.idea,
                "max_iterations": config.max_iterations,
                "iteration": 0,
                "done": False,
                "initial_prd": "",
                "critique": "",
                "revised_prd": [],
                "final_prd": ""
            }
            
            # Run the workflow
            logger.info("Starting PRD generation workflow")
            for state in workflow.stream(initial_state):
                current_node = state.get("__run_state__", {}).get("current_node")
                logger.info(f"Completed step: {current_node}")
            
            # Get the final state
            final_state = state
            logger.info(f"Workflow completed in {final_state['iteration']} iterations")
            
            # Get the final PRD
            final_prd = final_state["final_prd"]
            logger.info("PRD generation complete")

        # Save the PRD to a file
        if args.output:
            output_path = args.output
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w") as f:
                f.write(final_prd)
            logger.info(f"PRD saved to: {output_path}")
        else:
            print("\n" + "=" * 50 + "\n")
            print(final_prd)
            print("\n" + "=" * 50 + "\n")

    except Exception as e:
        logger.error(f"Error generating PRD: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return

if __name__ == "__main__":
    main() 