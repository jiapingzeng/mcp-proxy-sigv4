# MCP Proxy SigV4

A Model Context Protocol (MCP) proxy server with AWS SigV4 and OAuth JWT authentication support, allowing you to connect to remote MCP servers.

## Example MCP configuration

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "remote-sigv4-mcp-server": {
      "command": "uvx",
      "args": [
        "mcp-proxy-sigv4",
        "--endpoint",
        "https://sigv4-mcp.example.com/mcp",
        "--aws-service",
        "bedrock-agentcore",
        "--aws-region",
        "us-east-1"
      ]
    },
    "oauth-mcp-server": {
      "command": "uvx",
      "args": [
        "mcp-proxy-sigv4",
        "--endpoint",
        "https://oauth-mcp.example.com/mcp",
        "--bearer-token",
        "your-token-here"
      ]
    }
  }
}
```

## Architecture

```
MCP Client (e.g., Claude Desktop)
            ↓ (stdio)
    mcp-proxy-sigv4 (Local Proxy)
            ↓ (HTTPS + SigV4 / OAuth)
    Remote MCP Server (Bedrock AgentCore, Lambda, etc.)
```

## Installation

### Using uvx (Recommended)

```bash
uvx mcp-proxy-sigv4 --endpoint https://api.example.com/mcp
```

### Using pip

```bash
pip install mcp-proxy-sigv4
mcp-proxy-sigv4 --endpoint https://api.example.com/mcp
```

### Development Installation

```bash
# Create venv and install dependencies
git clone https://github.com/jiapingzeng/mcp-proxy-sigv4
uv venv
source .venv/bin/activate
uv sync

# Run proxy
cd src
uv run python -m src.mcp_proxy_sigv4 --help
```

## Usage

### Basic Usage

Connect to a remote MCP server with default AWS SigV4 authentication (using Bedrock AgentCore as an example):

```bash
uvx mcp-proxy-sigv4 \\
    --endpoint https://api.example.com/mcp \\
    --aws-region us-east-1 \\
    --aws-service bedrock-agentcore
```

### OAuth JWT Bearer Token Authentication

Connect using a JWT bearer token via CLI option:

```bash
uvx mcp-proxy-sigv4 \\
    --endpoint https://api.example.com/mcp \\
    --bearer-token "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

Or use the `BEARER_TOKEN` environment variable:

```bash
export BEARER_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
uvx mcp-proxy-sigv4 --endpoint https://api.example.com/mcp
```

### Without Authentication

For testing with servers that don't require authentication:

```bash
uvx mcp-proxy-sigv4 \\
    --endpoint http://localhost:8000/mcp \\
    --no-auth
```

### Verbose Logging

Enable detailed logging for debugging:

```bash
uvx mcp-proxy-sigv4 \\
    --endpoint https://api.example.com/mcp \\
    --verbose
```

## Command Line Options

- `--endpoint` (required): Remote MCP server endpoint URL
- `--bearer-token`: OAuth JWT bearer token for authentication (alternative to AWS SigV4)
- `--aws-region`: AWS region for SigV4 authentication (default: us-east-1)
- `--aws-service`: AWS service name for SigV4 authentication (default: execute-api)
- `--aws-profile`: AWS profile to use for credentials (optional)
- `--no-auth`: Disable authentication (no signing or bearer token)
- `--timeout`: Request timeout in seconds (default: 30.0)
- `--verbose`: Enable verbose logging
