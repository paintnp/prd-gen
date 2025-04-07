#!/bin/bash

# Installation script for PRD Generator
# This script sets up the required dependencies and environment

echo "PRD Generator - Installation Script"
echo "==================================="

# Create and activate a virtual environment if it doesn't exist
if [ ! -d "prd-gen-env" ]; then
    echo "Creating virtual environment..."
    python -m venv prd-gen-env
    VENV_CREATED=1
else
    echo "Virtual environment already exists"
    VENV_CREATED=0
fi

# Determine the activation script based on OS
if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # macOS or Linux
    ACTIVATE_SCRIPT="prd-gen-env/bin/activate"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    ACTIVATE_SCRIPT="prd-gen-env\\Scripts\\activate"
else
    echo "Unsupported OS. Please install dependencies manually."
    exit 1
fi

# Source the activation script
echo "Activating virtual environment..."
source "$ACTIVATE_SCRIPT"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies with the --upgrade flag
echo "Installing latest dependencies..."
pip install --upgrade -r requirements.txt

# Set up environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOL
# PRD Generator Environment Configuration

# OpenAI API Key (required)
OPENAI_API_KEY=your_openai_api_key_here

# LLM Configuration
MODEL=gpt-4o
TEMPERATURE=0.7
MAX_TOKENS=4000
EOL
    
    echo ".env file created. Please edit it to add your OpenAI API key."
fi

# Make the main script executable
chmod +x prd_gen/main.py

# Create output directory if it doesn't exist
mkdir -p output

echo ""
echo "Installation complete!"
echo ""

if [ $VENV_CREATED -eq 1 ]; then
    echo "To get started:"
    echo "1. Edit the .env file and add your OpenAI API key"
    echo "2. Activate the virtual environment with: source $ACTIVATE_SCRIPT"
    echo "3. Run the generator: python -m prd_gen.main --idea \"Your product idea\""
else
    echo "To get started:"
    echo "1. Make sure your OpenAI API key is set in the .env file"
    echo "2. Run the generator: python -m prd_gen.main --idea \"Your product idea\""
fi
echo ""
echo "For more options, run: python -m prd_gen.main --help" 