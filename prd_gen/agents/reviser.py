"""
Reviser Agent for PRD generation.

This module defines the Reviser agent, which is responsible for refining
the PRD based on critique from the Critic agent.
"""

from typing import List, Dict, Any, Optional
import json
import os
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import Tool
from prd_gen.utils.debugging import setup_logging, log_error
from prd_gen.utils.openai_logger import setup_openai_logging, log_openai_request, log_openai_response
from prd_gen.utils.agent_logger import log_revision, log_web_search  # Add web search logging
from openai import OpenAI  # Add direct OpenAI client
from prd_gen.utils.mcp_client import run_async, search_web
from prd_gen.utils.direct_search import direct_search_web, create_mock_search_results, direct_search_web_summarized
from prd_gen.prompts.agent_prompts import REVISER_PROMPT

# Set up logging
logger = setup_logging()
openai_logger = setup_openai_logging()

# System prompt comes from the prompts module now

def revise_prd(prd: str, critique: str, tools: List[Any], llm: Any) -> str:
    """
    Revise a PRD based on the critique provided.
    
    Args:
        prd (str): The original PRD to revise.
        critique (str): The critique to use for revision.
        tools (List[Any]): List of tools available for the agent, including MCP tools.
        llm (Any): The language model to use.
        
    Returns:
        str: The revised PRD.
    """
    logger.info("Revising PRD based on critique")
    
    # Check if we have any search tools from MCP server
    search_tools = [tool for tool in tools if tool.name == "search_web_summarized"]
    has_search_tool = len(search_tools) > 0
    
    if has_search_tool:
        logger.info("Found search_web_summarized tool from MCP server, using it for research during revision")
    else:
        logger.info("No search_web_summarized tool found, proceeding without external research")
    
    # Define the system prompt
    system_prompt = REVISER_PROMPT

    if has_search_tool:
        system_prompt += "\nYou can search for additional market information, competitors, technical details, and industry trends using the search_web_summarized tool to enhance the PRD. You can add a summary_focus parameter like 'key findings' or 'main points' to get the most relevant information while avoiding context overflow."
    
    # Define the user prompt
    user_prompt = f"""Here is the original PRD:

{prd}

Here is the critique:

{critique}

Please revise the PRD to address all the issues mentioned in the critique. Provide a complete, revised PRD that is ready for implementation.
"""

    # Try using the direct OpenAI client with fallback to LangChain
    try:
        # Direct OpenAI client call
        logger.info("Using direct OpenAI client for revision")
        client = OpenAI()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # If we have search tools, use them with function calling
        if has_search_tool:
            search_tool = search_tools[0]
            # Define the function for OpenAI
            functions = [{
                "type": "function",
                "function": {
                    "name": "search_web_summarized",
                    "description": search_tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query string"
                            },
                            "summary_focus": {
                                "type": "string",
                                "description": "The summary focus for the search"
                            }
                        },
                        "required": ["query", "summary_focus"]
                    }
                }
            }]
            
            # Log the request with tools
            log_openai_request(messages, "reviser_prd_direct", functions)
            
            # Allow the model to search for additional information
            research_response = client.chat.completions.create(
                model=llm.model_name if hasattr(llm, 'model_name') else "gpt-4o",
                messages=messages,
                tools=functions,
                tool_choice="auto"
            )
        else:
            # Log the request without tools
            log_openai_request(messages, "reviser_prd_direct")
            
            # Without search tool, just generate the revised PRD directly
            response = client.chat.completions.create(
                model=llm.model_name if hasattr(llm, 'model_name') else "gpt-4o",
                messages=messages
            )
            
            revised_prd = response.choices[0].message.content
            
            # Log the response and return early for the no-tools case
            log_openai_response(revised_prd, "reviser_prd_direct")
            return revised_prd

        # Extract and process tool calls
        response_message = research_response.choices[0].message
        
        # If the model wants to use the search tool
        if response_message.tool_calls:
            # Add the assistant message to the conversation
            messages.append(response_message.model_dump())
            
            # Process each tool call
            for tool_call in response_message.tool_calls:
                # Extract the query
                function_name = tool_call.function.name
                if function_name == "search_web_summarized":
                    function_args = json.loads(tool_call.function.arguments)
                    query = function_args.get("query")
                    summary_focus = function_args.get("summary_focus", "key findings")
                    
                    logger.info(f"Searching for: {query} with focus: {summary_focus}")
                    try:
                        # Use the direct search implementation
                        search_result = direct_search_web_summarized(query, summary_focus)
                        logger.info(f"Search completed for: {query}")
                    except Exception as e:
                        error_log = log_error(f"Error during search: {e}", exc_info=True)
                        logger.error(f"Error during search: {e} (see {error_log} for details)")
                        
                        # Return an error result instead of using mock results
                        search_result = {
                            "error": f"Live search failed: {str(e)}",
                            "query": query,
                            "summary_focus": summary_focus,
                            "results": [
                                {
                                    "title": "SEARCH ERROR - Live Search Required",
                                    "url": "N/A",
                                    "content": f"Live search is required but failed: {str(e)}. Please ensure the MCP server is running and properly configured."
                                }
                            ]
                        }
                    
                    # Log the web search in the agent logs
                    try:
                        # Get the current iteration (already calculated below)
                        current_iteration = 1
                        if "revision" in prd.lower():
                            # Estimate iteration from the content
                            revision_markers = prd.lower().count("revision")
                            iteration_markers = prd.lower().count("iteration")
                            version_markers = prd.lower().count("version")
                            current_iteration = max(revision_markers, iteration_markers, version_markers) + 1
                        
                        # Log the search
                        log_web_search(query, "reviser", current_iteration)
                        logger.info(f"Logged web search: {query}")
                    except Exception as e:
                        error_log = log_error(f"Failed to log web search: {e}", exc_info=True)
                        logger.error(f"Failed to log web search: {e} (see {error_log} for details)")
                    
                    # Add the tool response to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps(search_result)
                    })
                else:
                    # Handle other tool types here if needed, or provide a simple response
                    # This ensures ALL tool calls get responses
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps({"error": "Tool not implemented"})
                    })
            
            # Now generate the revised PRD with the added research
            final_response = client.chat.completions.create(
                model=llm.model_name if hasattr(llm, 'model_name') else "gpt-4o",
                messages=messages
            )
            
            revised_prd = final_response.choices[0].message.content
        else:
            # Without search tool, just generate the revised PRD directly
            response = client.chat.completions.create(
                model=llm.model_name if hasattr(llm, 'model_name') else "gpt-4o",
                messages=messages
            )
            
            revised_prd = response.choices[0].message.content
        
        # Log the response
        log_openai_response(revised_prd, "reviser_prd_direct")
        
    except Exception as e:
        error_log = log_error(f"Error with direct OpenAI client: {e}", exc_info=True)
        logger.error(f"Error with direct OpenAI client: {e} (see {error_log} for details)")
        logger.info("Falling back to LangChain implementation")
        
        # Fall back to LangChain
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        # Log the request using LangChain format
        log_openai_request(system_prompt + "\n\n" + user_prompt, "reviser_prd_langchain")
        
        try:
            # Create a prompt template with the messages
            from langchain_core.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages(messages)
            
            # Create the chain
            chain = prompt | llm
            
            # Execute the chain
            response = chain.invoke({})
            revised_prd = response.content
            
            # Log the response
            log_openai_response(revised_prd, "reviser_prd_langchain")
        except Exception as e:
            error_log = log_error(f"Error with LangChain implementation: {e}", exc_info=True)
            logger.error(f"Error with LangChain implementation: {e} (see {error_log} for details)")
            revised_prd = prd
    
    # Get the current iteration from the PRD content if possible
    iteration = 1
    try:
        # Simple heuristic - look for revision markers in the PRD
        revisions = prd.lower().count("revision")
        iterations = prd.lower().count("iteration")
        version_count = prd.lower().count("version")
        
        # Use the highest count as a hint
        revision_markers = max(revisions, iterations, version_count)
        if revision_markers > 0:
            iteration = revision_markers + 1
    except Exception:
        # Default to iteration 1 if we can't determine it
        iteration = 1
    
    # Log the revision using the agent logger
    try:
        log_revision(prd, critique, revised_prd, iteration)
        logger.info(f"Revision for iteration {iteration} logged successfully")
    except Exception as e:
        error_log = log_error(f"Failed to log revision: {e}", exc_info=True)
        logger.error(f"Failed to log revision: {e} (see {error_log} for details)")
    
    return revised_prd

def create_custom_search_tool() -> Optional[Tool]:
    """
    Create a custom search_web tool that works with the Exa MCP Server.
    
    Returns:
        Optional[Tool]: The custom search_web tool, or None if creation fails.
    """
    try:
        # Mock search function
        def mock_search_web(query: str, summary_focus: str = "key findings") -> str:
            """
            Search the web for information related to the query.
            
            Args:
                query (str): The search query.
                summary_focus (str): Focus for the summary generation.
                
            Returns:
                str: The search results as a formatted string.
            """
            print(f"Using mock search_web_summarized tool in reviser with query: {query}, focus: {summary_focus}")
            
            # Mock search results
            mock_results = {
                "query": query,
                "summary_focus": summary_focus,
                "results": [
                    {
                        "title": "No live search available",
                        "url": "N/A",
                        "content": "This is a mock result since live search is not available in the current environment."
                    }
                ]
            }
            
            return mock_results
        
        # Create and return the tool
        return Tool(
            name="search_web_summarized",
            description="Search the web for information related to the query. You can add a summary_focus parameter like 'key findings' or 'main points' to get the most relevant information while avoiding context overflow.",
            func=mock_search_web
        )
    except Exception as e:
        print(f"Error creating custom search tool in reviser: {e}")
        return None 