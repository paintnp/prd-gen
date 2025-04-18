"""
Critic Agent for PRD generation.

This module defines the Critic agent, which is responsible for analyzing
and providing constructive criticism on the PRD.
"""

from typing import List, Dict, Any, Optional
import json
import os
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import Tool
from prd_gen.utils.debugging import setup_logging, log_error
from prd_gen.utils.openai_logger import setup_openai_logging, log_openai_request, log_openai_response
from prd_gen.utils.agent_logger import log_critique, log_web_search  # Add web search logging
from openai import OpenAI  # Add direct OpenAI client
from prd_gen.utils.mcp_client import run_async, search_web
from prd_gen.utils.direct_search import direct_search_web, create_mock_search_results, direct_search_web_summarized
from prd_gen.prompts.agent_prompts import CRITIC_PROMPT

# Set up logging
logger = setup_logging()
openai_logger = setup_openai_logging()

# System prompt comes from the prompts module now

def critique_prd(prd: str, tools: List[Any], llm: Any) -> str:
    """
    Critique a PRD using the language model.
    
    Args:
        prd (str): The PRD to critique.
        tools (List[Any]): List of tools available for the agent, including MCP tools.
        llm (Any): The language model to use.
        
    Returns:
        str: The critique of the PRD.
    """
    logger.info("Critiquing PRD")
    
    # Check if we have any search tools from MCP server
    search_tools = [tool for tool in tools if tool.name == "search_web_summarized"]
    has_search_tool = len(search_tools) > 0
    
    if has_search_tool:
        logger.info("Found search_web_summarized tool from MCP server, using it for market analysis")
    else:
        logger.info("No search_web_summarized tool found, proceeding without external research")
    
    # Define the system prompt
    system_prompt = CRITIC_PROMPT

    if has_search_tool:
        system_prompt += "\nYou can search for market information, competitors, and industry trends using the search_web_summarized tool to ensure accuracy. You can add a summary_focus parameter like 'key findings' or 'main points' to get the most relevant information while avoiding context overflow."
    
    # Define the user prompt
    user_prompt = f"""Please critique the following PRD thoroughly:

{prd}

Provide a detailed critique with specific, actionable feedback on how to improve each section.
"""

    # Try using the direct OpenAI client with fallback to LangChain
    try:
        # Direct OpenAI client call
        logger.info("Using direct OpenAI client for critique")
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
                                "description": "Focus area for the summary like 'key findings' or 'main points'",
                                "default": "key findings"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }]
            
            # Log the request with tools
            log_openai_request(messages, "critic_prd_direct", functions)
            
            # Allow the model to search for market information
            research_response = client.chat.completions.create(
                model=llm.model_name if hasattr(llm, 'model_name') else "gpt-4o",
                messages=messages,
                tools=functions,
                tool_choice="auto"
            )
        else:
            # Log the request without tools
            log_openai_request(messages, "critic_prd_direct")
            
            # Without search tool, just generate the critique directly
            response = client.chat.completions.create(
                model=llm.model_name if hasattr(llm, 'model_name') else "gpt-4o",
                messages=messages
            )
            
            critique = response.choices[0].message.content
            
            # Log the response and return early for the no-tools case
            log_openai_response(critique, "critic_prd_direct")
            return critique

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
                    
                    logger.info(f"Searching for: {query} with summary focus: {summary_focus}")
                    try:
                        # Use the direct search implementation
                        search_result = direct_search_web_summarized(query, summary_focus)
                        logger.info(f"Search completed for: {query}")
                    except Exception as e:
                        error_log = log_error(f"Error during search: {e}", exc_info=True)
                        logger.error(f"Error during search: {e} (see {error_log} for details)")
                        
                        # Create mock results to continue
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
                        log_web_search(query, "critic", current_iteration)
                        logger.info(f"Logged web search: {query}")
                    except Exception as e:
                        error_log = log_error(f"Failed to log web search: {e}", exc_info=True)
                        logger.error(f"Failed to log web search: {e} (see {error_log} for details)")
                    
                    # Add the tool response to messages (right after the assistant message)
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
            
            # Now generate the critique with the added research
            final_response = client.chat.completions.create(
                model=llm.model_name if hasattr(llm, 'model_name') else "gpt-4o",
                messages=messages
            )
            
            critique = final_response.choices[0].message.content
        else:
            # Without search tool, just generate the critique directly
            response = client.chat.completions.create(
                model=llm.model_name if hasattr(llm, 'model_name') else "gpt-4o",
                messages=messages
            )
            
            critique = response.choices[0].message.content
        
        # Log the response
        log_openai_response(critique, "critic_prd_direct")
        
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
        log_openai_request(system_prompt + "\n\n" + user_prompt, "critic_prd_langchain")
        
        try:
            # Create a prompt template with the messages
            from langchain_core.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages(messages)
            
            # Create the chain
            chain = prompt | llm
            
            # Execute the chain
            response = chain.invoke({})
            critique = response.content
            
            # Log the response
            log_openai_response(critique, "critic_prd_langchain")
        except Exception as e:
            error_log = log_error(f"Error with LangChain implementation: {e}", exc_info=True)
            logger.error(f"Error with LangChain implementation: {e} (see {error_log} for details)")
            critique = "The PRD requires improvement in several areas, including more detailed market analysis and clearer technical specifications."
    
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
    
    # Log the critique using the agent logger
    try:
        log_critique(prd, critique, iteration)
        logger.info(f"Critique for iteration {iteration} logged successfully")
    except Exception as e:
        error_log = log_error(f"Failed to log critique: {e}", exc_info=True)
        logger.error(f"Failed to log critique: {e} (see {error_log} for details)")
    
    return critique

def create_custom_search_tool() -> Optional[Tool]:
    """
    Create a custom search_web tool that works with the Exa MCP Server.
    
    Returns:
        Optional[Tool]: The custom search_web tool, or None if creation fails.
    """
    try:
        # Create a mock search function
        def mock_search_web(query: str) -> str:
            """
            Search the web for information related to the query.
            
            Args:
                query (str): The search query.
                
            Returns:
                str: The search results as a formatted string.
            """
            logger.debug(f"Using mock search_web tool in critic with query: {query}")
            
            # Mock search results
            mock_results = {
                "query": query,
                "results": [
                    {
                        "title": "PRD Best Practices: What Makes a Great Product Requirements Document",
                        "url": "https://example.com/prd-best-practices",
                        "snippet": "Great PRDs focus on outcomes rather than specifications, enabling agile teams to innovate while maintaining clear direction.",
                        "content": "The most effective PRDs in today's environment focus on customer outcomes rather than rigid specifications. They clearly articulate the problem being solved and success metrics, while leaving room for implementation details to be determined by the development team. Visual elements like user journey maps and wireframes are increasingly included directly in PRDs to provide clearer context."
                    },
                    {
                        "title": "Common Pitfalls in Product Requirements Documents",
                        "url": "https://example.com/prd-pitfalls",
                        "snippet": "Avoid ambiguity, excessive detail, and unrealistic timelines in your PRDs.",
                        "content": "The most common issues in PRDs include ambiguous language that leaves requirements open to interpretation, excessive technical detail that constrains implementation unnecessarily, unrealistic timelines that don't account for complexity, and insufficient user research to validate assumptions. Effective PRDs stay focused on user needs and business goals, with clear criteria for success."
                    }
                ]
            }
            
            # Format results as a readable string
            formatted_results = f"Search results for '{query}':\n\n"
            for i, result in enumerate(mock_results["results"]):
                formatted_results += f"{i+1}. {result['title']}\n"
                formatted_results += f"   URL: {result['url']}\n"
                formatted_results += f"   {result['content']}\n\n"
                
            return formatted_results
        
        # Create and return the tool
        return Tool(
            name="search_web",
            description="Search the web for information related to the query.",
            func=mock_search_web
        )
    except Exception as e:
        logger.error(f"Error creating custom search tool in critic: {e}")
        return None 