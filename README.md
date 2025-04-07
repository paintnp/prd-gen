# PRD Generator

An AI-powered Product Requirements Document (PRD) generator that leverages machine learning to create, critique, and revise professional-grade PRDs with integrated web search capabilities.

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

### Setup

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