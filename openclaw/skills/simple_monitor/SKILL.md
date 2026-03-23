# simple_monitor - Health monitoring skill

## Description
Simple health monitoring skill that checks a service endpoint and records results.

## When to use
Use when you want to periodically check the health of a web service and log the results.

## Inputs
- `url`: The URL to check (required)
- `interval`: How often to check in seconds (optional, default 60)
- `timeout`: Request timeout in seconds (optional, default 10)

## Outputs
Records check results to memory files and can announce status.

## Example usage
See scripts/monitor.py for implementation.

## References
- None
