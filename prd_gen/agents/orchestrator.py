"""
Orchestrator module for the PRD generator.

This module defines the LangGraph workflow that orchestrates the agents
involved in generating a PRD.
"""

from typing import Dict, List, Any, Annotated, Literal
from typing_extensions import TypedDict
import operator
import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain_mcp_adapters.client import MultiServerMCPClient

from prd_gen.agents.creator import create_initial_prd, PRD_CREATOR_PROMPT
from prd_gen.agents.critic import critique_prd, PRD_CRITIC_PROMPT
from prd_gen.agents.reviser import revise_prd, PRD_REVISER_PROMPT
from prd_gen.utils.debugging import setup_logging, log_mcp_client_config, log_mcp_tools

# Set up logging
logger = setup_logging()

# Define the state of our PRD generation workflow
class PRDState(TypedDict):
    # Input
    idea: str
    max_iterations: int
    iteration: int
    done: bool
    
    # Working data
    initial_prd: str
    critique: str
    revised_prd: Annotated[List[str], operator.add]
    
    # Output
    final_prd: str

def create_prd_workflow(config: Dict[str, Any]) -> StateGraph:
    """
    Create the LangGraph workflow for PRD generation.
    
    Args:
        config (Dict[str, Any]): The configuration dictionary.
        
    Returns:
        StateGraph: The compiled LangGraph workflow.
    """
    # Get the API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment. This will cause authentication errors.")
    
    # Initialize the LLM with explicit API key
    llm = ChatOpenAI(
        api_key=api_key,
        model=config["llm"]["model"],
        temperature=config["llm"]["temperature"],
        max_tokens=config["llm"]["max_tokens"]
    )
    
    # Create the state graph
    workflow = StateGraph(PRDState)
    
    # MCP server configuration - use the working server on port 9000
    server_name = "Exa MCP Server"
    server_url = "http://localhost:9000/sse"
    server_transport = "sse"
    server_timeout = 30
    
    # Define nodes
    
    # Node 1: Create the initial PRD
    def creator_node(state: PRDState) -> Dict[str, Any]:
        # Initialize the MCP client without using it as a context manager
        logger.debug("Creating MCP client for creator_node")
        client_config = {
            server_name: {
                "url": server_url,
                "transport": server_transport,
                "timeout": server_timeout
            }
        }
        log_mcp_client_config(client_config)
        
        client = MultiServerMCPClient(client_config)
        
        # Get tools and create the PRD
        logger.debug("Getting tools from MCP client")
        tools = client.get_tools()
        log_mcp_tools(tools)
        
        logger.debug(f"Creating initial PRD for idea: {state['idea']}")
        result = create_initial_prd(state["idea"], tools, llm)
        logger.debug(f"Initial PRD created successfully. Length: {len(result)}")
        
        if not result:
            logger.error("Generated PRD is empty! This will cause issues in later stages.")
            # Create a simple placeholder PRD for debugging
            result = f"# Smart Stock Portfolio Analyzer - Product Requirements Document\n\n(This is a placeholder PRD for debugging purposes.)\n\n## Executive Summary\nA smart tool to analyze and optimize stock portfolios."
            logger.debug(f"Using placeholder PRD: {result[:100]}...")
        
        # Print the first 500 characters of the PRD for debugging
        logger.debug(f"PRD preview: {result[:500]}...")
        
        return {"initial_prd": result, "revised_prd": [result]}
    
    # Node 2: Critique the PRD
    def critic_node(state: PRDState) -> Dict[str, Any]:
        # Initialize the MCP client without using it as a context manager
        logger.debug("Creating MCP client for critic_node")
        client_config = {
            server_name: {
                "url": server_url,
                "transport": server_transport,
                "timeout": server_timeout
            }
        }
        log_mcp_client_config(client_config)
        
        client = MultiServerMCPClient(client_config)
        
        # Get tools and critique the PRD
        logger.debug("Getting tools from MCP client")
        tools = client.get_tools()
        log_mcp_tools(tools)
        
        current_prd = state["revised_prd"][-1] if state["revised_prd"] else state["initial_prd"]
        
        # Check if current_prd is empty
        if not current_prd:
            logger.error("Current PRD is empty, cannot critique.")
            current_prd = "# Smart Stock Portfolio Analyzer\n\n(Empty PRD - nothing to critique)"
        
        logger.debug(f"Critiquing PRD (iteration {state['iteration']})")
        logger.debug(f"Current PRD length: {len(current_prd)}")
        logger.debug(f"Current PRD preview: {current_prd[:500]}...")
        
        result = critique_prd(current_prd, tools, llm)
        logger.debug("Critique completed successfully")
        logger.debug(f"Critique length: {len(result)}")
        logger.debug(f"Critique preview: {result[:500]}...")
        
        # Increment the iteration counter
        iteration = state["iteration"] + 1
        return {"critique": result, "iteration": iteration}
    
    # Node 3: Revise the PRD based on critique
    def reviser_node(state: PRDState) -> Dict[str, Any]:
        # Initialize the MCP client without using it as a context manager
        logger.debug("Creating MCP client for reviser_node")
        client_config = {
            server_name: {
                "url": server_url,
                "transport": server_transport,
                "timeout": server_timeout
            }
        }
        log_mcp_client_config(client_config)
        
        client = MultiServerMCPClient(client_config)
        
        # Get tools and revise the PRD
        logger.debug("Getting tools from MCP client")
        tools = client.get_tools()
        log_mcp_tools(tools)
        
        current_prd = state["revised_prd"][-1] if state["revised_prd"] else state["initial_prd"]
        critique = state["critique"]
        
        # Check if current_prd is empty
        if not current_prd:
            logger.error("Current PRD is empty, cannot revise.")
            current_prd = "# Smart Stock Portfolio Analyzer\n\n(Empty PRD - nothing to revise)"
        
        logger.debug(f"Revising PRD based on critique (iteration {state['iteration']})")
        result = revise_prd(current_prd, critique, tools, llm)
        logger.debug("Revision completed successfully")
        
        return {"revised_prd": [result]}
    
    # Node 4: Finalize the PRD
    def finalizer_node(state: PRDState) -> Dict[str, Any]:
        logger.debug("Finalizing PRD")
        
        try:
            # Get the latest revision or initial PRD with careful error handling
            if "revised_prd" in state and state["revised_prd"] and len(state["revised_prd"]) > 0:
                latest_revision = state["revised_prd"][-1]
                logger.debug(f"Using latest revision from {len(state['revised_prd'])} revisions")
            elif "initial_prd" in state and state["initial_prd"]:
                latest_revision = state["initial_prd"]
                logger.debug("No revisions available, using initial PRD")
            else:
                logger.error("No PRD content found in state! Creating minimal content.")
                # Create a placeholder if nothing is available
                latest_revision = f"# Smart Stock Portfolio Analyzer\n\n(This PRD could not be generated properly - no content found in state)"
        
            # Check if latest_revision is empty
            if not latest_revision or len(latest_revision.strip()) < 10:  # Ensure we have at least some content
                logger.error("Latest revision is empty or too short, creating placeholder")
                # Fall back to initial PRD if available
                if "initial_prd" in state and state["initial_prd"] and len(state["initial_prd"].strip()) >= 10:
                    latest_revision = state["initial_prd"]
                    logger.debug("Using initial PRD as fallback")
                else:
                    # Create a placeholder if nothing is available
                    latest_revision = "# Smart Stock Portfolio Analyzer\n\n(This PRD could not be generated properly - content was empty)"
                    logger.debug("Created placeholder PRD")
            
            # Log detailed info for debugging
            logger.debug(f"Final PRD length: {len(latest_revision)}")
            logger.debug(f"Final PRD preview: {latest_revision[:500]}...")
            logger.debug("PRD finalized successfully")
            
            # Make sure to preserve the iteration count and include all necessary keys
            return {
                "final_prd": latest_revision, 
                "done": True,
                "iteration": state.get("iteration", 1),  # Ensure iteration count is preserved
                # Include other keys to ensure no state is lost
                "initial_prd": state.get("initial_prd", ""),
                "critique": state.get("critique", ""),
                # Include revised_prd if it exists, otherwise use an empty list
                "revised_prd": state.get("revised_prd", [])
            }
            
        except Exception as e:
            logger.error(f"Error in finalizer node: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Create a placeholder PRD
            emergency_prd = "# Smart Stock Portfolio Analyzer\n\n(This PRD could not be generated properly due to an error in finalization)"
            
            # Return a valid state with the emergency PRD
            return {
                "final_prd": emergency_prd,
                "done": True,
                "iteration": state.get("iteration", 1),
                "initial_prd": state.get("initial_prd", ""),
                "critique": state.get("critique", ""),
                "revised_prd": state.get("revised_prd", [])
            }
    
    # Add nodes to the graph
    workflow.add_node("creator", creator_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("reviser", reviser_node)
    workflow.add_node("finalizer", finalizer_node)
    
    # Define conditional edge routing logic
    def should_continue(state: PRDState) -> Literal["continue", "finalize"]:
        """
        Determine if we should continue with more revisions or finalize the PRD.
        """
        try:
            # Check if state contains required keys
            if "iteration" not in state:
                logger.error("State missing 'iteration' key, defaulting to finalize")
                return "finalize"
                
            if "max_iterations" not in state:
                logger.error("State missing 'max_iterations' key, using default of 3")
                max_iterations = 3
            else:
                max_iterations = state["max_iterations"]
            
            current_iteration = state["iteration"]
            
            # Validate that we have the necessary data to continue
            if "revised_prd" not in state or not state["revised_prd"]:
                logger.warning("No revised PRD available, may need to finalize")
                # If we haven't even done one iteration, try to continue
                if current_iteration < 1:
                    logger.info("First iteration incomplete, continuing anyway")
                    return "continue"
                return "finalize"
                
            # Check if we've reached max iterations
            if current_iteration >= max_iterations:
                logger.debug(f"Max iterations reached ({current_iteration}/{max_iterations}), finalizing PRD")
                return "finalize"
                
            logger.debug(f"Continuing with iteration {current_iteration + 1}/{max_iterations}")
            return "continue"
            
        except Exception as e:
            logger.error(f"Error in should_continue function: {e}")
            logger.error(f"State contents: {state.keys()}")
            # Default to finalizing in case of any error
            return "finalize"
    
    # Add edges to connect the nodes
    workflow.add_edge("creator", "critic")
    workflow.add_conditional_edges(
        "critic",
        should_continue,
        {
            "continue": "reviser",
            "finalize": "finalizer"
        }
    )
    workflow.add_edge("reviser", "critic")
    workflow.add_edge("finalizer", END)
    
    # Set the entry point
    workflow.set_entry_point("creator")
    
    logger.debug("Workflow created successfully")
    
    # Compile the workflow
    return workflow.compile() 