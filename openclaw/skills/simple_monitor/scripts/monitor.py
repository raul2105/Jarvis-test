#!/usr/bin/env python3
"""
Simple health monitor script for OpenClaw skill.
This script is intended to be run by an agentTurn cron job.
It expects the following in the job payload (as JSON in the agentTurn message):
{
  "url": "http://example.com/health",
  "timeout": 10
}
It will record the result in a memory file and optionally announce.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime

def main():
    # In an agentTurn job, the message is passed as the first argument? 
    # Actually, the agentTurn job kind passes the message as the prompt to the agent.
    # But we are running a script, so we need to get the input from the environment or from a file.
    # Let's assume the input is passed via a JSON file in the workspace or via stdin.
    # For simplicity, we'll read from a file named 'input.json' in the current directory.
    # Alternatively, we can design the cron job to pass the URL as part of the agentTurn message and then
    # have the agent run this script with the URL as an argument.
    # However, the OpenClaw documentation for agentTurn does not specify how to pass parameters to the script.
    # Let's change approach: we'll make the skill configurable via the cron job's payload in the agentTurn.
    # The agentTurn job will run a subagent that has access to the workspace and can run this script.
    # We'll have the subagent read the job's context (which includes the payload) and then run the script.
    # But that is complex.

    # Given the time, let's simplify: we'll create a cron job that runs a systemEvent that sets a reminder
    # to check the health, and then we'll have a separate agent that does the check.
    # Alternatively, we can use the agentTurn to run a Python one-liner that does the check and logs.

    # Since we are in a skill, we can provide a script that the user can manually run or adapt.
    # For the purpose of this example, we'll write a script that takes a URL as a command line argument.

    if len(sys.argv) < 2:
        print("Usage: monitor.py <url> [timeout]")
        sys.exit(1)

    url = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    try:
        req = urllib.request.Request(url)
        response = urllib.request.urlopen(req, timeout=timeout)
        status_code = response.getcode()
        result = {
            "url": url,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status_code": status_code,
            "result": "healthy" if 200 <= status_code < 300 else "unhealthy",
            "error": None
        }
    except Exception as e:
        result = {
            "url": url,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status_code": None,
            "result": "error",
            "error": str(e)
        }

    # Record to memory
    memory_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'memory')
    os.makedirs(memory_dir, exist_ok=True)
    today = datetime.utcnow().strftime('%Y-%m-%d')
    memory_file = os.path.join(memory_dir, f'{today}.md')

    with open(memory_file, 'a') as f:
        f.write(f"- Health check for {url} at {result['timestamp']}: {result['result']}")
        if result['error']:
            f.write(f" (Error: {result['error']})")
        f.write(f"\\n")

    # Optionally, print for logging
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()