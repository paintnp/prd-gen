"""
Utility to test OpenAI API key.

This script can be used to verify that an OpenAI API key is valid.
"""

import os
import sys
import argparse
from dotenv import load_dotenv, find_dotenv
import requests
from prd_gen.utils.debugging import setup_logging

# Set up logging
logger = setup_logging()

def test_openai_api_key(api_key=None):
    """Test if the OpenAI API key is valid."""
    # If no API key is provided, load from environment
    if not api_key:
        # Try to load from .env file
        env_path = find_dotenv(usecwd=True)
        if env_path:
            logger.debug(f"Loading environment from: {env_path}")
            load_dotenv(env_path, override=True)
        else:
            logger.warning("No .env file found!")
        
        # Get API key from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        
        if not api_key:
            print("Error: No OpenAI API key found in environment variables.")
            print("Please set the OPENAI_API_KEY environment variable or provide a key with --api-key.")
            return False
    
    # Create a simple request to test the API key
    url = "https://api.openai.com/v1/models"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print("✅ API Key is valid! Successfully authenticated with OpenAI API.")
            return True
        else:
            error_message = response.json().get("error", {}).get("message", "Unknown error")
            print(f"❌ API Key is invalid: {error_message}")
            if "IP address" in error_message:
                print("  This appears to be an IP restriction issue. Your IP address may not be allowed.")
            elif "expired" in error_message.lower():
                print("  This API key appears to have expired. Please generate a new key.")
            return False
    except Exception as e:
        print(f"❌ Error testing API key: {e}")
        return False

def main():
    """Main entry point for the API key tester."""
    parser = argparse.ArgumentParser(description="Test OpenAI API key")
    parser.add_argument("--api-key", "-k", type=str, help="OpenAI API key to test")
    args = parser.parse_args()
    
    return test_openai_api_key(args.api_key)

if __name__ == "__main__":
    sys.exit(0 if main() else 1) 