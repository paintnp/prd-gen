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
            states = []  # Keep track of all states
            current_node = None
            
            try:
                # More detailed tracking of each state
                node_outputs = {}  # Track outputs from each node
                
                for state in workflow.stream(initial_state):
                    states.append(state)  # Store each state
                    
                    # Extract the run state info (which node just completed)
                    run_state = state.get("__run_state__", {})
                    current_node = run_state.get("current_node")
                    logger.info(f"Completed step: {current_node}")
                    
                    # Keep track of individual node outputs
                    if current_node and current_node in state:
                        node_outputs[current_node] = state[current_node]
                        logger.debug(f"Captured output from node '{current_node}'")
                    
                    # Detailed logging about state structure
                    if "__run_state__" in state:
                        logger.debug(f"State run_state info: {run_state}")
                    
                    logger.debug(f"State contains keys: {list(state.keys())}")
                
                # Find the state after the finalizer node completed
                final_state = None
                
                # First check: Look for a state with finalizer in run_state
                for state in reversed(states):
                    run_state = state.get("__run_state__", {})
                    if run_state.get("current_node") == "finalizer":
                        final_state = state
                        logger.info("Found finalizer state via run_state")
                        break
                
                # Second check: If we didn't find it that way, look for a state with 'finalizer' key
                if final_state is None:
                    for state in reversed(states):
                        if "finalizer" in state:
                            final_state = state
                            logger.info("Found finalizer state via 'finalizer' key")
                            break
                
                # Last resort: Use the last state
                if final_state is None:
                    if states:
                        final_state = states[-1]
                        logger.warning("Couldn't find finalizer node state, using last state")
                    else:
                        raise ValueError("No states were produced by the workflow")
                
                # Enhanced diagnostic info
                logger.debug(f"Final state type: {type(final_state).__name__}")
                logger.debug(f"Final state keys: {list(final_state.keys())}")
                
                # Check for finalizer output
                if "finalizer" in final_state and isinstance(final_state["finalizer"], dict):
                    logger.debug(f"Finalizer output contains: {list(final_state['finalizer'].keys())}")
                
                # If we have finalizer node output directly, use it
                if "finalizer" in node_outputs and isinstance(node_outputs["finalizer"], dict):
                    if "final_prd" in node_outputs["finalizer"]:
                        logger.info("Using final_prd from node_outputs['finalizer']")
                        final_prd = node_outputs["finalizer"]["final_prd"]
                # If we didn't get final_prd from node_outputs
                elif "final_prd" not in final_state:
                    logger.error(f"Final state is missing 'final_prd' key. Available keys: {list(final_state.keys())}")
                     
                    # Check if there's a 'finalizer' key which might contain the node output
                    if "finalizer" in final_state and isinstance(final_state["finalizer"], dict):
                        logger.info("Found 'finalizer' key in state, attempting to extract PRD from it")
                        finalizer_output = final_state["finalizer"]
                        if "final_prd" in finalizer_output:
                            logger.info("Successfully extracted final_prd from finalizer output")
                            final_prd = finalizer_output["final_prd"]
                        else:
                            logger.warning(f"Finalizer output doesn't contain final_prd. Keys: {list(finalizer_output.keys())}")
                            # Continue with regular fallback paths
                     
                    # Regular fallback paths
                    if 'final_prd' not in locals():  # If we didn't set final_prd above
                        if "revised_prd" in final_state and final_state["revised_prd"]:
                            # Use the latest revision as a fallback
                            logger.warning("Using latest revision as fallback for final PRD")
                            final_prd = final_state["revised_prd"][-1]
                        elif "initial_prd" in final_state and final_state["initial_prd"]:
                            # Use the initial PRD as a last-resort fallback
                            logger.warning("Using initial PRD as fallback for final PRD")
                            final_prd = final_state["initial_prd"]
                        else:
                            # Create a minimal fallback if all else fails
                            logger.error("No PRD content found in any state! Creating minimal fallback.")
                            final_prd = f"# PRD for: {config.idea}\n\nThis PRD could not be generated due to workflow errors."
                else:
                    # Get the final PRD normally
                    final_prd = final_state["final_prd"]
                    
                logger.info(f"Workflow completed in {final_state.get('iteration', 1)} iterations")
                logger.info("PRD generation complete")
            
            except Exception as e:
                logger.error(f"Error during workflow execution: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
                # Attempt to recover any PRD content from the states we've collected
                if states:
                    logger.info(f"Attempting to recover PRD content from {len(states)} collected states")
                    final_prd = None
                    
                    # Try to find any state with a revised_prd
                    for state in reversed(states):
                        if "revised_prd" in state and state["revised_prd"]:
                            final_prd = state["revised_prd"][-1]
                            logger.info("Recovered PRD from revised_prd in state")
                            break
                            
                    # If no revised_prd, try initial_prd
                    if not final_prd:
                        for state in states:
                            if "initial_prd" in state and state["initial_prd"]:
                                final_prd = state["initial_prd"]
                                logger.info("Recovered PRD from initial_prd in state")
                                break
                    
                    # If still no PRD, create a minimal fallback
                    if not final_prd:
                        final_prd = f"# PRD for: {config.idea}\n\nThis PRD could not be generated due to workflow errors: {str(e)}"
                        logger.warning("Created minimal fallback PRD")
                else:
                    # If no states were collected, fall back to simple approach
                    logger.info("Falling back to simple approach as no states were collected")
                    prd = create_initial_prd(config.idea, tools, llm)
                    critique = critique_prd(prd, tools, llm)
                    final_prd = revise_prd(prd, critique, tools, llm)

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