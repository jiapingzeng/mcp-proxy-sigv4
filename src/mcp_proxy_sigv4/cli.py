"""CLI entry point for mcp-proxy-sigv4."""

import asyncio
import os
import sys
from urllib.parse import urlparse

import click

from .proxy import ProxyServer


@click.command()
@click.option(
    "--endpoint",
    required=True,
    help="Remote MCP server endpoint URL (e.g., https://example.com/mcp)",
)
@click.option(
    "--aws-region",
    default="us-east-1",
    help="AWS region for SigV4 authentication (default: us-east-1)",
)
@click.option(
    "--aws-service",
    default="execute-api",
    help="AWS service name for SigV4 authentication (default: execute-api)",
)
@click.option(
    "--aws-profile",
    help="AWS profile to use for credentials (optional)",
)
@click.option(
    "--bearer-token",
    help="OAuth JWT bearer token for authentication. Can also use BEARER_TOKEN environment variable.",
)
@click.option(
    "--no-auth",
    is_flag=True,
    help="Disable authentication (connect without signing requests or bearer token)",
)
@click.option(
    "--timeout",
    default=30.0,
    type=float,
    help="Request timeout in seconds (default: 30.0)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def main(
    endpoint: str,
    aws_region: str,
    aws_service: str,
    aws_profile: str | None,
    bearer_token: str | None,
    no_auth: bool,
    timeout: float,
    verbose: bool,
):
    """
    MCP proxy server with AWS SigV4 and OAuth JWT authentication support.

    This tool creates a local MCP server that acts as a proxy to a remote MCP server,
    supporting AWS SigV4 signing, OAuth JWT bearer tokens, or no authentication.

    Examples:
        # Connect to a remote MCP server with SigV4 auth (uses AWS credentials from provider chain)
        uvx mcp-proxy-sigv4 --endpoint https://api.example.com/mcp

        # Connect with OAuth JWT bearer token (CLI)
        uvx mcp-proxy-sigv4 --endpoint https://api.example.com/mcp --bearer-token "your-jwt-token"

        # Connect with OAuth JWT bearer token (environment variable)
        export BEARER_TOKEN="your-jwt-token"
        uvx mcp-proxy-sigv4 --endpoint https://api.example.com/mcp

        # Connect without authentication
        uvx mcp-proxy-sigv4 --endpoint http://localhost:8000/mcp --no-auth

        # Use specific AWS profile and region
        uvx mcp-proxy-sigv4 --endpoint https://api.example.com/mcp \\
            --aws-profile my-profile --aws-region us-west-2
    """
    # Validate endpoint URL
    try:
        parsed_url = urlparse(endpoint)
        if not parsed_url.scheme or not parsed_url.netloc:
            click.echo("Error: Invalid endpoint URL", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: Failed to parse endpoint URL: {e}", err=True)
        sys.exit(1)

    # Check for BEARER_TOKEN environment variable if not provided via CLI
    if not bearer_token:
        bearer_token = os.getenv("BEARER_TOKEN")

    # Validate authentication options
    if bearer_token and no_auth:
        click.echo("Error: Cannot specify both bearer token and --no-auth", err=True)
        sys.exit(1)

    # Configure logging level based on verbose flag
    import logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if verbose:
        click.echo("Starting MCP proxy server...")
        click.echo(f"Remote endpoint: {endpoint}")
        if bearer_token:
            click.echo("Authentication: OAuth JWT Bearer Token")
        elif no_auth:
            click.echo("Authentication: Disabled")
        else:
            click.echo("Authentication: AWS SigV4")
            click.echo(f"AWS region: {aws_region}")
            click.echo(f"AWS service: {aws_service}")
            if aws_profile:
                click.echo(f"AWS profile: {aws_profile}")

    try:
        proxy = ProxyServer(
            server_endpoint=endpoint,
            aws_region=aws_region,
            aws_service=aws_service,
            aws_profile=aws_profile,
            bearer_token=bearer_token,
            enable_auth=not no_auth,
            timeout=timeout,
            verbose=verbose,
        )

        asyncio.run(proxy.run_stdio())

    except KeyboardInterrupt:
        if verbose:
            click.echo("\\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
