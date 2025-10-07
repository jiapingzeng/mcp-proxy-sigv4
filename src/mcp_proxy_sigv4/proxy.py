"""MCP proxy server with AWS SigV4 authentication support."""

import logging
from urllib.parse import urlparse

from fastmcp import FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server.proxy import ProxyClient

from .sigv4_auth import SigV4Auth, SigV4StreamableHttpTransport

logger = logging.getLogger(__name__)


class ProxyServer:
    """MCP proxy server with AWS SigV4, OAuth JWT, and no-auth support."""

    def __init__(
        self,
        server_endpoint: str,
        aws_region: str = "us-east-1",
        aws_service: str = "execute-api",
        aws_profile: str | None = None,
        bearer_token: str | None = None,
        enable_auth: bool = True,
        timeout: float = 30.0,
        verbose: bool = False,
    ):
        self.server_endpoint = server_endpoint
        self.aws_region = aws_region
        self.aws_service = aws_service
        self.aws_profile = aws_profile
        self.bearer_token = bearer_token
        self.enable_auth = enable_auth
        self.timeout = timeout
        self.verbose = verbose

        if verbose:
            logging.getLogger("mcp_proxy_sigv4").setLevel(logging.DEBUG)
            logging.getLogger("fastmcp").setLevel(logging.DEBUG)

        parsed_url = urlparse(server_endpoint)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid server endpoint URL: {server_endpoint}")

        self._sigv4_auth = None
        self._bearer_auth = None

        if not enable_auth:
            logger.info("Authentication disabled, connecting without signing requests")
        elif bearer_token:
            self._bearer_auth = bearer_token
            logger.info("Bearer token authentication configured")
        else:
            try:
                self._sigv4_auth = SigV4Auth(
                    region=aws_region,
                    service=aws_service,
                    profile=aws_profile,
                )
                logger.info(
                    f"SigV4 authentication initialized for region {aws_region}, service {aws_service}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize SigV4 authentication: {e}")
                raise

    def _create_transport(self):
        """Create transport based on authentication method."""
        if self._bearer_auth:
            return StreamableHttpTransport(
                url=self.server_endpoint,
                auth=self._bearer_auth,
                sse_read_timeout=self.timeout,
            )
        elif self._sigv4_auth:
            return SigV4StreamableHttpTransport(
                url=self.server_endpoint,
                sigv4_auth=self._sigv4_auth,
                timeout=self.timeout,
            )
        else:
            return StreamableHttpTransport(
                url=self.server_endpoint,
                sse_read_timeout=self.timeout,
            )

    async def run_stdio(self) -> None:
        """Run the proxy server using stdio transport."""
        logger.info("Starting MCP proxy server with stdio transport")

        logger.info(f"Testing connection to: {self.server_endpoint}")
        if not await self.test_connection():
            raise ConnectionError(
                f"Failed to connect to remote MCP server: {self.server_endpoint}"
            )

        try:
            transport = self._create_transport()
            proxy_client = ProxyClient(transport)
            proxy_server = FastMCP.as_proxy(proxy_client, name="mcp-proxy-sigv4")

            logger.info(
                f"Connection verified, starting proxy server for: {self.server_endpoint}"
            )
            await proxy_server.run_async("stdio")

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            raise
        except Exception as e:
            logger.error(f"Proxy server error: {e}")
            if self.verbose:
                logger.exception("Full traceback:")
            raise

    async def test_connection(self) -> bool:
        """Test connection to the remote MCP server."""
        try:
            transport = self._create_transport()
            proxy_client = ProxyClient(transport)

            async with proxy_client:
                logger.info("Connection test successful")
                return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            if self.verbose:
                logger.exception("Full traceback:")
            return False
