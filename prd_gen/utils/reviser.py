                    logger.info(f"Searching for: {query}")
                    try:
                        # Use the direct search implementation
                        search_result = direct_search_web(query)
                        logger.info(f"Search completed for: {query}")
                    except Exception as e:
                        logger.error(f"Error during search: {e}")
                        # Return an error result instead of using mock results
                        search_result = {
                            "error": f"Live search failed: {str(e)}",
                            "query": query,
                            "results": [
                                {
                                    "title": "SEARCH ERROR - Live Search Required",
                                    "url": "N/A",
                                    "content": f"Live search is required but failed: {str(e)}. Please ensure the MCP server is running and properly configured."
                                }
                            ]
                        } 