# PRD Generator

A framework for generating comprehensive Product Requirement Documents using AI agents and LangGraph.

## Overview

PRD Generator leverages specialized AI agents to create detailed Product Requirement Documents from simple prompts. The system uses LangGraph to orchestrate a team of agents that work together to generate, critique, and refine the PRD to ensure high quality and comprehensive documentation.

The workflow consists of three primary agents:

1. **Creator Agent** - Generates the initial PRD based on the product idea
2. **Critic Agent** - Analyzes the PRD and provides constructive feedback
3. **Reviser Agent** - Refines the PRD based on the feedback from the Critic

These agents collaborate in an iterative process until a quality threshold is met or a maximum number of iterations is reached.

## Features

- Generate comprehensive PRDs from simple product ideas
- Leverage web search via MCP server to gather market research and best practices
- Iterative refinement through AI-powered critique and revision
- Customizable quality thresholds and iteration limits
- Easy-to-use command line interface

## Requirements

- Python 3.8+
- Access to OpenAI API (GPT-4 recommended)
- MCP Server running with search_web tool capability

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/prd-generator.git
   cd prd-generator
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file:
   ```bash
   cp .env.example .env
   ```

4. Edit the `.env` file with your API keys and preferences.

## Usage

### Basic Usage

Generate a PRD with default settings:

```bash
python -m prd_gen.main --idea "A mobile app that helps users track their carbon footprint and suggests ways to reduce it"
```

### Advanced Options

```bash
python -m prd_gen.main --idea "Your product idea" --max_iterations 5 --output "custom_output.md"
```

### Command Line Arguments

- `--idea`, `-i`: Initial product idea or prompt
- `--max_iterations`, `-m`: Maximum number of revision iterations (default: 3)
- `--output`, `-o`: Output file path (default: output/prd.md)

## Architecture

The system uses LangGraph to define a workflow where:

1. The **Creator** agent generates an initial PRD based on the input idea
2. The **Critic** agent reviews the PRD and provides detailed feedback
3. The **Reviser** agent refines the PRD based on the critique
4. The process repeats until either the maximum iterations are reached or the quality threshold is met

Each agent has access to the search_web tool from an MCP (Model Context Protocol) server, allowing them to gather relevant information from the web to improve the PRD's quality.

## MCP Server Integration

This system uses an external MCP server that implements the `search_web` tool. The MCP server should be running on the URL specified in your `.env` file (default: http://localhost:9000/sse).

The MCP server should implement the search_web tool as shown in the example:

```python
@mcp.tool()
def search_web(query: str, use_autoprompt: bool = True, search_type: str = "auto") -> dict:
    """
    Perform a web search using Exa's API.

    :param query: The search query string.
    :param use_autoprompt: Whether to use Exa's autoprompt feature.
    :param search_type: The type of search ('auto', 'neural', or 'keyword').
    :return: Search results as a dictionary.
    """
    results = exa.search_and_contents(query)
    return results
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 