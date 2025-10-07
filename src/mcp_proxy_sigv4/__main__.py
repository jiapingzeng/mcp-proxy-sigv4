"""Allow mcp_proxy_sigv4 to be executable from `python -m mcp_proxy_sigv4`."""

from .cli import main

if __name__ == "__main__":
    main()
