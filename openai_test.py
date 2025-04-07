#!/usr/bin/env python3
"""
Test script to directly call the OpenAI API and verify if the API key is working properly.
"""

import os
import logging
import json
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("openai_direct_test")

def main():
    # Get API key from environment
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment")
        return
    
    logger.info(f"Using API key: {api_key[:5]}...{api_key[-5:]}")
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Simple test prompt
    logger.info("Creating test message")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello and introduce yourself in one sentence."}
    ]
    
    # Log the request
    logger.debug(f"Request: {json.dumps(messages, indent=2)}")
    
    try:
        # Make API call
        logger.info("Calling OpenAI API...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
        )
        
        # Log response information
        logger.debug(f"Response object type: {type(response)}")
        logger.debug(f"Response object dir: {dir(response)}")
        
        # Extract and log content
        choice = response.choices[0]
        content = choice.message.content
        
        logger.info(f"API call successful")
        logger.info(f"Response content: {content}")
        
        return content
        
    except Exception as e:
        logger.error(f"API call failed: {str(e)}")
        logger.exception("Exception details:")
        return None

if __name__ == "__main__":
    main() 