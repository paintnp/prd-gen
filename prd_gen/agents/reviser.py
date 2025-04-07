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
from prd_gen.utils.debugging import setup_logging
from prd_gen.utils.openai_logger import setup_openai_logging, log_openai_request, log_openai_response
from prd_gen.utils.agent_logger import log_revision, log_web_search  # Add web search logging
from openai import OpenAI  # Add direct OpenAI client
from prd_gen.utils.mcp_client import run_async

# Set up logging
logger = setup_logging()
openai_logger = setup_openai_logging()

# System prompt for the Reviser agent
PRD_REVISER_PROMPT = """
You are an expert Product Manager specialized in refining Product Requirement Documents (PRDs).

Your task is to improve a PRD based on the critique provided. Follow these guidelines:

1. Address all the critique points thoroughly
   - Do not dismiss or ignore any feedback
   - Prioritize the most critical issues first
   - Maintain the overall structure of the PRD

2. Research and validate
   - Use the search_web tool to gather information needed to address the critique
   - Look for market data, best practices, or technical details to strengthen weak areas
   - Verify facts and assumptions when needed

3. Improve clarity and precision
   - Use clear, unambiguous language
   - Provide concrete examples where helpful
   - Ensure technical terms are properly explained

4. Enhance completeness
   - Add missing information identified in the critique
   - Expand sections that lack detail
   - Make sure all key stakeholder questions are answered

5. Ensure consistency
   - Align goals with features and requirements
   - Ensure the scope is well-defined and coherent
   - Eliminate contradictions or inconsistencies

6. Consider feasibility
   - Make timeline and resource estimates more realistic
   - Acknowledge technical limitations and constraints
   - Add risk mitigation strategies

When making revisions, maintain the document's formatting and structure. Present the complete revised PRD, not just the changes. If the critique contradicts itself, use your best judgment to create the most effective PRD possible.
"""

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
    search_tools = [tool for tool in tools if tool.name == "search_web"]
    has_search_tool = len(search_tools) > 0
    
    if has_search_tool:
        logger.info("Found search_web tool from MCP server, using it for research during revision")
    else:
        logger.info("No search_web tool found, proceeding without external research")
    
    # Define the system prompt
    system_prompt = """You are an expert product manager and technical consultant tasked with revising a Product Requirements Document (PRD) based on critique.

Your job is to improve the PRD by addressing all the feedback in the critique. You must:
1. Maintain the original structure of the PRD
2. Address each issue mentioned in the critique
3. Expand sections that need more detail
4. Add missing sections if needed
5. Ensure technical accuracy and feasibility
6. Keep the document professional and comprehensive

Return the complete revised PRD, not just the changes. The revised document should be well-formatted, comprehensive, and ready for implementation.
"""

    if has_search_tool:
        system_prompt += "\nYou can search for additional market information, competitors, technical details, and industry trends using the search_web tool to enhance the PRD."
    
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
                    "name": "search_web",
                    "description": search_tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query string"
                            }
                        },
                        "required": ["query"]
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
            # Process each tool call
            for tool_call in response_message.tool_calls:
                # Extract the query
                function_name = tool_call.function.name
                if function_name == "search_web":
                    function_args = json.loads(tool_call.function.arguments)
                    query = function_args.get("query")
                    
                    logger.info(f"Searching for: {query}")
                    # Execute the search - use the run_async helper function
                    search_result = run_async(search_tool.ainvoke({"query": query}))
                    
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
                        logger.error(f"Failed to log web search: {e}")
                    
                    # Add the tool response to messages
                    messages.append(response_message.model_dump())
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps(search_result)
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
        logger.error(f"Error with direct OpenAI client: {e}")
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
            logger.error(f"Error with LangChain implementation: {e}")
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
        logger.error(f"Failed to log revision: {e}")
    
    return revised_prd

def create_custom_search_tool() -> Optional[Tool]:
    """
    Create a custom search_web tool that works with the Exa MCP Server.
    
    Returns:
        Optional[Tool]: The custom search_web tool, or None if creation fails.
    """
    try:
        # Create a mock search function
        def search_web(query: str) -> str:
            """
            Search the web for information related to the query.
            
            Args:
                query (str): The search query.
                
            Returns:
                str: The search results as a formatted string.
            """
            print(f"Using mock search_web tool in reviser with query: {query}")
            
            # Mock search results
            mock_results = {
                "query": query,
                "results": [
                    {
                        "title": "Effective PRD Examples in Modern Product Management",
                        "url": "https://example.com/prd-examples",
                        "snippet": "Examples of well-crafted PRDs with clear requirements and user-centered design.",
                        "content": "The most effective PRDs establish a clear connection between business objectives and user needs. They include visual elements like user flow diagrams, wireframes, and competitive analysis charts. Measurable success criteria are defined for each feature, with explicit alignment to strategic goals. Technical requirements are presented in a way that explains the 'why' behind each decision, not just the 'what'."
                    },
                    {
                        "title": "Market Research Methodologies for Product Managers",
                        "url": "https://example.com/market-research-methods",
                        "snippet": "Practical approaches to gathering market data for product requirements.",
                        "content": "Effective market research for PRDs combines both qualitative and quantitative methodologies. User interviews provide deep insights into pain points and needs, while surveys offer broader validation across larger samples. Competitive analysis should categorize competitors into direct, indirect, and potential, with feature comparison matrices. For technical products, beta testing with a representative user group can validate assumptions before full development begins."
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
            func=search_web
        )
    except Exception as e:
        print(f"Error creating custom search tool in reviser: {e}")
        return None 