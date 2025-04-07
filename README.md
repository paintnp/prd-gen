# PRD Generator

An AI-powered Product Requirements Document (PRD) generator that leverages machine learning to create, critique, and revise professional-grade PRDs with integrated web search capabilities.

## Recent Improvements

- **Enhanced Search Tool**: Implemented `search_web_summarized` to reduce token usage and avoid context overflow by focusing on key findings
- **Centralized Prompts**: Created a dedicated prompts module for easier maintenance and customization of agent instructions
- **Improved Context Management**: Better handling of search results to maintain quality while reducing token consumption

## Features

- **Create PRDs**: Generate comprehensive PRDs from simple product ideas
- **Critique PRDs**: Analyze PRDs and provide detailed feedback
- **Revise PRDs**: Automatically improve PRDs based on feedback through configurable iteration cycles
- **Web Search Integration**: Enhance PRDs with real-time market data using MCP (Multi-agent Conversational Pipeline)
- **Customizable Templates**: Tailor the PRD format to your needs
- **High-Quality Output**: Produce professional documentation ready for stakeholder review
- **Configurable Iterations**: Control the quality-speed tradeoff by setting the number of revision cycles

## Installation

### Prerequisites

- Python 3.8+
- OpenAI API key
- MCP server (optional, for web search capabilities)

### Easy Setup

We provide automated installation scripts for easy setup:

**For macOS/Linux:**
```bash
# Make the script executable (if needed)
chmod +x install.sh

# Run the installation script
./install.sh
```

**For Windows (PowerShell):**
```powershell
# Run the installation script
.\install.ps1
```

The installation scripts will:
- Create a virtual environment
- Install and upgrade all dependencies to the latest compatible versions
- Create a template .env file for you to add your API keys
- Set up the necessary directories

### Manual Setup

If you prefer to install manually:

1. Clone the repository
   ```bash
   git clone https://github.com/paintnp/prd-gen.git
   cd prd-gen
   ```

2. Create a virtual environment
   ```bash
   python -m venv prd-gen-env
   source prd-gen-env/bin/activate  # On Windows: prd-gen-env\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables
   ```bash
   cp .env.example .env
   ```
   
5. Edit the `.env` file and add your OpenAI API key
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

### Generating a PRD

To generate a new PRD, use the `main.py` script:

```bash
python -m prd_gen.main --idea "Your product idea here" --output output/prd.md
```

**Parameters:**
- `--idea`: Description of your product idea (required)
- `--output`: Path to save the generated PRD (default: `output/prd.md`)
- `--max_iterations`, `-m`: Maximum number of revision iterations (default: 3)

### Example

```bash
python -m prd_gen.main --idea "Smart stock portfolio analyzer" --output output/stock_analyzer_prd.md --max_iterations 5
```

### How It Works

The PRD generation process follows these steps:

1. **Creation**: The system generates an initial PRD based on your product idea
2. **Critique**: The initial PRD is analyzed and feedback is provided on areas of improvement
3. **Revision**: The PRD is revised based on the critique
4. **Iteration**: Steps 2-3 repeat for the number of iterations specified (default: 3)
5. **Finalization**: The final improved PRD is saved to the specified output file

Increasing the number of iterations typically improves PRD quality at the cost of longer processing time.

## Environment Variables

The following environment variables can be set in your `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | None (Required) |
| `LLM_MODEL` | The language model to use | `gpt-4o` |
| `LLM_TEMPERATURE` | Temperature for model outputs | `0.2` |
| `LLM_MAX_TOKENS` | Maximum tokens for model responses | `100000` |
| `MCP_SERVER_URL` | URL for the MCP server | `http://localhost:9000/sse` |
| `MCP_TIMEOUT` | Timeout for MCP server requests | `30` |
| `TEMPLATES_PATH` | Path to PRD templates | `prd_gen/templates` |
| `QUALITY_THRESHOLD` | Minimum quality threshold for PRDs | `0.8` |
| `MAX_ITERATIONS` | Maximum number of revision iterations | `3` |

## Project Structure

```
prd-gen/
├── prd_gen/                 # Main package
│   ├── agents/              # Agent modules
│   │   ├── creator.py       # PRD creation agent
│   │   ├── critic.py        # PRD critique agent
│   │   ├── reviser.py       # PRD revision agent
│   │   └── orchestrator.py  # Agent orchestration
│   ├── utils/               # Utility modules
│   │   ├── config.py        # Configuration utilities
│   │   ├── debugging.py     # Debugging helpers
│   │   ├── mcp_client.py    # MCP client for web search
│   │   └── openai_logger.py # OpenAI API logging
│   └── main.py              # Main entry point
├── output/                  # Output directory for PRDs
├── .env.example             # Example environment variables
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## MCP Integration

The PRD Generator optionally integrates with the Multi-agent Conversational Pipeline (MCP) server for web search capabilities. This enhances PRDs with real-time market information, competitor analysis, and technical details.

To use MCP:
1. Ensure the MCP server is running
2. Set the `MCP_SERVER_URL` environment variable to point to your server
3. Web search will be automatically used to enhance PRDs when available

## MCP Server Connection & Error Handling

The PRD Generator includes robust error handling for connections to the MCP (Model Control Protocol) server:

### Connection Features:

- Automatic retries (up to 3 attempts) for failed connections
- Detailed error diagnostics for various error types
- Special handling for TaskGroup cancel scope errors that can occur with SSE connections
- Path correction suggestions (e.g., if `/sse` is missing from the URL)
- Graceful recovery mechanisms to ensure consistent search operation

### Error Types Detected:

1. **Connection Errors**: When the server is unreachable or the connection times out
2. **Not Found Errors (404)**: When the server endpoint doesn't exist
3. **TaskGroup/Cancellation Errors**: Related to the async SSE connection implementation
4. **Authentication Errors**: When credentials are invalid
5. **Server Errors**: When the server is running but encounters internal issues

### Testing:

You can test the error handling with the `mcp_connect_test.py` script:

```bash
# Test with a valid server URL (default)
python mcp_connect_test.py --url valid

# Test with an invalid server URL (wrong port)
python mcp_connect_test.py --url invalid

# Test with an invalid path
python mcp_connect_test.py --url bad-path

# Test TaskGroup cancel scope error handling
python mcp_connect_test.py --test=cancel-scope
```

The error handling ensures that even when connections fail, the application provides clear, actionable error messages rather than cryptic exceptions.

## Advanced Features

### Detailed Agent Logging

The system now provides detailed logging of agent activities in a dedicated directory structure:

```
logs/
├── agent_logs_YYYYMMDD_HHMMSS/   # Session-specific logs
│   ├── session_summary.md        # Overview of all iterations
│   ├── iteration_1_critique.md   # Detailed critique for iteration 1
│   ├── iteration_1_revision.md   # Detailed revision for iteration 1
│   ├── iteration_2_critique.md   # Detailed critique for iteration 2
│   ├── ...                       # Additional iteration logs
│   └── final_prd.md              # The final PRD output
└── openai_debug_YYYYMMDD_HHMMSS.log  # OpenAI API logs
```

These logs allow you to:
- See detailed critiques provided for each iteration
- Track changes made during each revision
- Understand how the PRD evolved over multiple iterations
- Identify areas of improvement in the initial vs. final PRD

This is especially useful for:
- Learning how to write better PRDs
- Understanding the thought process of the agents
- Debugging issues with PRD generation
- Improving your initial product ideas

### Auto-Upgrading Dependencies

The installation scripts now automatically upgrade all dependencies to the latest compatible versions, ensuring:
- Security patches and bug fixes are applied
- Latest features from dependencies are available
- Version compatibility is maintained through upper bounds

## Advanced Usage

### Running the MCP Server

If you want to use the web search capabilities, you'll need to run the MCP server:

```bash
python mcp_server.py
```

This will start the server on the default port (9000) and enable web search integration.

### Customizing Output

You can modify the templates in the `prd_gen/templates` directory to customize the format of generated PRDs.

### Optimizing Iterations

- **Single Iteration** (`--max_iterations 1`): Fastest generation, good for drafts or simple ideas
- **Default (3 Iterations)**: Balanced approach suitable for most use cases
- **5+ Iterations**: More thorough refinement for complex products or when higher quality is essential

## Troubleshooting

**Issue: Error with OpenAI API key**
- Ensure your API key is correctly set in the `.env` file
- Check that your OpenAI account has sufficient credits

**Issue: MCP integration not working**
- Verify that the MCP server is running
- Check the server URL in your `.env` file
- Ensure that the required dependencies are installed

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## User-Friendly Error Handling

The PRD Generator is designed to be accessible to users without extensive programming backgrounds. It includes:

### Clear Error Messages

- **Non-Technical Language**: Errors are explained in plain language without technical jargon
- **Visual Formatting**: Important messages are highlighted with visual borders
- **Actionable Suggestions**: Each error includes specific steps to resolve the issue

### Smart Search Result Management

- **Automatic Truncation**: Large search results are automatically shortened to prevent token limits
- **Content Summarization**: Individual search results are trimmed to manageable sizes
- **Result Limiting**: The number of results is capped to prevent information overload

### Examples of User-Friendly Error Messages:

```
=======================================================================
⚠️ Your search returned too much data.

Your search for 'artificial intelligence trends 2025' returned a very large 
amount of information that exceeds what the system can process. Try:
1. Using a more specific search query
2. Breaking your search into smaller, focused queries
3. Adding specific keywords to narrow the results
=======================================================================
```

```
=======================================================================
⚠️ Search unavailable: Unable to connect to the search service.

This could be because:
1. The search service is not running
2. Your internet connection is down
3. The service address is incorrect

You can continue working without search, or try again later.
=======================================================================
```

These improvements ensure that even users without technical backgrounds can:
- Understand what went wrong when errors occur
- Know exactly how to fix common issues
- Get helpful guidance on how to make better search queries 