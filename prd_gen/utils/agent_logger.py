"""
Agent-specific logging utilities.

This module provides functions for logging detailed agent activities,
particularly focusing on critic's feedback and reviser's changes.
"""

import os
import time
import json
import logging
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime

# Global variables to store the log directory and session ID
AGENT_LOGS_DIR = None
SESSION_ID = None

def setup_agent_logging() -> Path:
    """
    Set up a dedicated logging directory for agent activities.
    
    Returns:
        Path: The path to the agent logs directory.
    """
    global AGENT_LOGS_DIR, SESSION_ID
    
    # Create a unique session ID based on timestamp
    SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create a session-specific directory
    agent_logs_dir = logs_dir / f"agent_logs_{SESSION_ID}"
    agent_logs_dir.mkdir(exist_ok=True)
    
    # Store the directory path globally
    AGENT_LOGS_DIR = agent_logs_dir
    
    print(f"Agent activity logs will be written to: {agent_logs_dir}")
    
    return agent_logs_dir

def log_critique(prd: str, critique: str, iteration: int = 1) -> None:
    """
    Log the critic agent's critique.
    
    Args:
        prd (str): The PRD that was critiqued.
        critique (str): The critique provided by the critic agent.
        iteration (int): The current iteration number.
    """
    global AGENT_LOGS_DIR, SESSION_ID
    
    # Ensure the logs directory exists
    if AGENT_LOGS_DIR is None:
        setup_agent_logging()
    
    # Create log files
    critique_file = AGENT_LOGS_DIR / f"iteration_{iteration}_critique.md"
    
    # Create a formatted critique log
    log_content = f"""# Critique for Iteration {iteration}

## Timestamp
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Original PRD
```markdown
{prd}
```

## Critique
```markdown
{critique}
```
"""
    
    # Write to file
    with open(critique_file, "w") as f:
        f.write(log_content)
    
    # Create a session summary file if it doesn't exist
    summary_file = AGENT_LOGS_DIR / "session_summary.md"
    if not summary_file.exists():
        with open(summary_file, "w") as f:
            f.write(f"# PRD Generation Session {SESSION_ID}\n\n")
            f.write(f"## Summary of Iterations\n\n")
    
    # Append to the summary file
    with open(summary_file, "a") as f:
        f.write(f"### Iteration {iteration} Critique\n\n")
        f.write(f"Critique length: {len(critique)} characters\n\n")
        f.write(f"Key points from critique:\n")
        
        # Extract the first few lines as key points
        critique_lines = critique.split('\n')
        key_points = [line for line in critique_lines if line.strip() and not line.startswith('#')][:5]
        for point in key_points:
            f.write(f"- {point}\n")
        f.write("\n[Full critique](iteration_{}_critique.md)\n\n".format(iteration))

def log_revision(original_prd: str, critique: str, revised_prd: str, iteration: int = 1) -> None:
    """
    Log the reviser agent's revision.
    
    Args:
        original_prd (str): The original PRD.
        critique (str): The critique that led to the revision.
        revised_prd (str): The revised PRD.
        iteration (int): The current iteration number.
    """
    global AGENT_LOGS_DIR, SESSION_ID
    
    # Ensure the logs directory exists
    if AGENT_LOGS_DIR is None:
        setup_agent_logging()
    
    # Create log files
    revision_file = AGENT_LOGS_DIR / f"iteration_{iteration}_revision.md"
    
    # Create a formatted revision log
    log_content = f"""# Revision for Iteration {iteration}

## Timestamp
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Original PRD
```markdown
{original_prd}
```

## Critique
```markdown
{critique}
```

## Revised PRD
```markdown
{revised_prd}
```
"""
    
    # Write to file
    with open(revision_file, "w") as f:
        f.write(log_content)
    
    # Append to the summary file
    summary_file = AGENT_LOGS_DIR / "session_summary.md"
    with open(summary_file, "a") as f:
        f.write(f"### Iteration {iteration} Revision\n\n")
        f.write(f"Original PRD length: {len(original_prd)} characters\n")
        f.write(f"Revised PRD length: {len(revised_prd)} characters\n")
        f.write(f"Change: {len(revised_prd) - len(original_prd)} characters\n\n")
        f.write("[Full revision](iteration_{}_revision.md)\n\n".format(iteration))

def log_final_prd(final_prd: str, total_iterations: int) -> None:
    """
    Log the final PRD after all iterations.
    
    Args:
        final_prd (str): The final PRD.
        total_iterations (int): The total number of iterations performed.
    """
    global AGENT_LOGS_DIR, SESSION_ID
    
    # Ensure the logs directory exists
    if AGENT_LOGS_DIR is None:
        setup_agent_logging()
    
    # Create log file
    final_file = AGENT_LOGS_DIR / "final_prd.md"
    
    # Create a formatted final log
    log_content = f"""# Final PRD

## Timestamp
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Final PRD after {total_iterations} iterations
```markdown
{final_prd}
```
"""
    
    # Write to file
    with open(final_file, "w") as f:
        f.write(log_content)
    
    # Append to the summary file
    summary_file = AGENT_LOGS_DIR / "session_summary.md"
    with open(summary_file, "a") as f:
        f.write(f"## Final PRD\n\n")
        f.write(f"Total iterations: {total_iterations}\n")
        f.write(f"Final PRD length: {len(final_prd)} characters\n\n")
        f.write("[View final PRD](final_prd.md)\n\n")
        f.write(f"## Generation Complete\n\n")
        f.write(f"Session completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n") 