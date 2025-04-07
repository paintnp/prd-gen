"""
Agent-specific logging utilities.

This module provides functions for logging detailed agent activities,
particularly focusing on critic's feedback and reviser's changes.
"""

import os
import time
import json
import logging
import re
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime

# Global variables to store the log directory and session ID
AGENT_LOGS_DIR = None
SESSION_ID = None
WEB_SEARCHES = []  # Track all web searches

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

def log_web_search(query: str, agent_type: str, iteration: int = 1) -> None:
    """
    Log a web search performed by an agent.
    
    Args:
        query (str): The search query string.
        agent_type (str): The type of agent making the search (e.g., 'critic', 'reviser').
        iteration (int): The current iteration number.
    """
    global AGENT_LOGS_DIR, SESSION_ID, WEB_SEARCHES
    
    # Ensure the logs directory exists
    if AGENT_LOGS_DIR is None:
        setup_agent_logging()
    
    # Store search info
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    search_info = {
        "timestamp": timestamp,
        "query": query,
        "agent_type": agent_type,
        "iteration": iteration
    }
    
    # Add to global list
    WEB_SEARCHES.append(search_info)
    
    # Create search log file if it doesn't exist
    search_log_file = AGENT_LOGS_DIR / "web_searches.md"
    if not search_log_file.exists():
        with open(search_log_file, "w") as f:
            f.write(f"# Web Searches for Session {SESSION_ID}\n\n")
    
    # Append to search log file
    with open(search_log_file, "a") as f:
        f.write(f"## Search at {timestamp} (Iteration {iteration})\n\n")
        f.write(f"- **Agent**: {agent_type}\n")
        f.write(f"- **Query**: \"{query}\"\n\n")
    
    # Update the session summary with search information
    _update_summary_with_searches()

def _update_summary_with_searches() -> None:
    """Update the session summary file with web search information."""
    global AGENT_LOGS_DIR, WEB_SEARCHES
    
    if not AGENT_LOGS_DIR:
        return
    
    # Get the session summary file
    summary_file = AGENT_LOGS_DIR / "session_summary.md"
    if not summary_file.exists():
        return
    
    # Read the current content
    with open(summary_file, "r") as f:
        content = f.read()
    
    # Check if we already have a web searches section
    search_section_marker = "## Web Searches\n"
    if search_section_marker in content:
        # Remove existing section (everything between the marker and the next major section)
        parts = content.split(search_section_marker)
        pre_content = parts[0]
        post_content = ""
        
        # Find the next major section in the remaining content
        remaining = parts[1]
        next_section_match = re.search(r"^## ", remaining, re.MULTILINE)
        if next_section_match:
            split_index = next_section_match.start()
            post_content = remaining[split_index:]
        else:
            post_content = ""
        
        # Create new content
        content = pre_content + search_section_marker
    else:
        # Find where to insert the searches section (before final section)
        final_section_match = re.search(r"## Generation Complete", content)
        if final_section_match:
            insert_pos = final_section_match.start()
            content = content[:insert_pos] + search_section_marker + "\n" + content[insert_pos:]
        else:
            content += "\n" + search_section_marker + "\n"
    
    # Add the search information
    if WEB_SEARCHES:
        search_content = ""
        # Group searches by iteration
        searches_by_iteration = {}
        for search in WEB_SEARCHES:
            iteration = search["iteration"]
            if iteration not in searches_by_iteration:
                searches_by_iteration[iteration] = []
            searches_by_iteration[iteration].append(search)
        
        # Create content for each iteration
        for iteration in sorted(searches_by_iteration.keys()):
            iteration_searches = searches_by_iteration[iteration]
            search_content += f"### Iteration {iteration}\n\n"
            for i, search in enumerate(iteration_searches):
                search_content += f"- {search['agent_type'].capitalize()} searched for: \"{search['query']}\"\n"
            search_content += "\n"
        
        search_content += f"Total searches: {len(WEB_SEARCHES)}\n\n"
        search_content += "[Detailed search log](web_searches.md)\n\n"
    else:
        search_content = "No web searches performed during this session.\n\n"
    
    # Find where to insert the search content
    search_section_pos = content.find(search_section_marker) + len(search_section_marker)
    content = content[:search_section_pos] + "\n" + search_content + content[search_section_pos:]
    
    # Write updated content back to the file
    with open(summary_file, "w") as f:
        f.write(content)

def log_final_prd(final_prd: str, total_iterations: int) -> None:
    """
    Log the final PRD after all iterations.
    
    Args:
        final_prd (str): The final PRD.
        total_iterations (int): The total number of iterations performed.
    """
    global AGENT_LOGS_DIR, SESSION_ID, WEB_SEARCHES
    
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
        f.write(f"Final PRD length: {len(final_prd)} characters\n")
        f.write(f"Total web searches: {len(WEB_SEARCHES)}\n\n")
        f.write("[View final PRD](final_prd.md)\n\n")
        f.write(f"## Generation Complete\n\n")
        f.write(f"Session completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
    # Make sure the web searches are included in the summary
    _update_summary_with_searches() 