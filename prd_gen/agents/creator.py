"""
Creator Agent for PRD generation.

This module defines the Creator agent, which is responsible for generating
the initial PRD based on the product idea.
"""

from typing import List, Any, Optional
import json
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import Tool
from prd_gen.utils.debugging import setup_logging, log_error
from prd_gen.utils.openai_logger import setup_openai_logging, log_openai_request, log_openai_response
from openai import OpenAI  # Add direct OpenAI client
import os
from prd_gen.utils.mcp_client import run_async, search_web
from prd_gen.utils.direct_search import direct_search_web, create_mock_search_results, direct_search_web_summarized
from prd_gen.prompts.agent_prompts import CREATOR_PROMPT

# Set up logging
logger = setup_logging()
openai_logger = setup_openai_logging()

# System prompt comes from the prompts module now

def create_initial_prd(idea: str, tools: List[Any], llm: Any) -> str:
    """
    Create an initial PRD based on the product idea.
    
    Args:
        idea (str): The product idea to create a PRD for.
        tools (List[Any]): List of tools available for the agent, including MCP tools.
        llm (Any): The language model to use.
        
    Returns:
        str: The generated PRD.
    """
    logger.info(f"Creating initial PRD for: {idea}")
    
    # Check if we have any search tools from MCP server
    search_tools = [tool for tool in tools if tool.name == "search_web_summarized"]
    has_search_tool = len(search_tools) > 0
    
    if has_search_tool:
        logger.info("Found search_web_summarized tool from MCP server, using it for research")
    else:
        logger.info("No search_web_summarized tool found, proceeding without external research")
    
    # Define the system prompt
    system_prompt = CREATOR_PROMPT

    if has_search_tool:
        system_prompt += "\nYou can search for information about the market, competitors, and industry trends using the search_web_summarized tool. You can add a summary_focus parameter like 'key findings' or 'main points' to get the most relevant information while avoiding context overflow."
    
    # Define the user prompt
    user_prompt = f"""Please create a comprehensive PRD for the following product idea:

{idea}

The PRD should be detailed, structured, and cover all aspects of the product from concept to launch.
"""

    # Try using the direct OpenAI client with fallback to LangChain
    try:
        # Direct OpenAI client call
        logger.info("Using direct OpenAI client")
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
            log_openai_request(messages, "creator_prd_direct", functions)
            
            # First, let the model search for information
            research_response = client.chat.completions.create(
                model=llm.model_name if hasattr(llm, 'model_name') else "gpt-4o",
                messages=messages,
                tools=functions,
                tool_choice="auto"
            )
        else:
            # Log the request without tools
            log_openai_request(messages, "creator_prd_direct")
            
            # Without search tool, just generate the PRD directly
            response = client.chat.completions.create(
                model=llm.model_name if hasattr(llm, 'model_name') else "gpt-4o",
                messages=messages
            )
            
            prd = response.choices[0].message.content
            
            # Log the response and return early for the no-tools case
            log_openai_response(prd, "creator_prd_direct")
            return prd
        
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
        
        # Now generate the PRD with the added research
        final_response = client.chat.completions.create(
            model=llm.model_name if hasattr(llm, 'model_name') else "gpt-4o",
            messages=messages
        )
        
        prd = final_response.choices[0].message.content
        
        # Log the response for the case with tools
        log_openai_response(prd, "creator_prd_direct")
        
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
        log_openai_request(system_prompt + "\n\n" + user_prompt, "creator_prd_langchain")
        
        try:
            # Create a prompt template with the messages
            from langchain_core.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages(messages)
            
            # Create the chain
            chain = prompt | llm
            
            # Execute the chain
            response = chain.invoke({})
            prd = response.content
            
            # Log the response
            log_openai_response(prd, "creator_prd_langchain")
        except Exception as e:
            error_log = log_error(f"Error with LangChain implementation: {e}", exc_info=True)
            logger.error(f"Error with LangChain implementation: {e} (see {error_log} for details)")
            prd = f"# Smart Stock Portfolio Analyzer\n\nError generating PRD: {str(e)}"
    
    return prd

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
            logger.debug(f"Using mock search_web tool with query: {query}")
            
            # Mock search results
            mock_results = {
                "query": query,
                "results": [
                    {
                        "title": "2024 Product Management Trends",
                        "url": "https://example.com/pm-trends-2024",
                        "snippet": "AI-driven decision making, remote collaboration tools, and sustainability focus are leading the product management space in 2024.",
                        "content": "In 2024, product managers are increasingly adopting AI tools for market research and decision-making processes. Remote collaboration continues to shape how product teams operate, with new tools enabling asynchronous work across time zones. Sustainability has moved from a nice-to-have to a core product consideration, influencing everything from material choices to supply chain optimization."
                    },
                    {
                        "title": "Product Requirements Document Best Practices",
                        "url": "https://example.com/prd-best-practices",
                        "snippet": "Modern PRDs focus on outcomes rather than specifications, enabling agile teams to innovate while maintaining clear direction.",
                        "content": "The most effective PRDs in today's environment focus on customer outcomes rather than rigid specifications. They clearly articulate the problem being solved and success metrics, while leaving room for implementation details to be determined by the development team. Visual elements like user journey maps and wireframes are increasingly included directly in PRDs to provide clearer context."
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
        logger.error(f"Error creating custom search tool: {e}")
        return None 