"""Tests for the proxy server."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_proxy_sigv4.proxy import ProxyServer


class TestProxyServer:
    """Test ProxyServer functionality."""

    def test_init_with_defaults(self, mock_boto3_session, mock_aws_credentials):
        """Test ProxyServer initialization with default parameters."""
        server = ProxyServer("https://example.com/mcp")

        assert server.server_endpoint == "https://example.com/mcp"
        assert server.aws_region == "us-east-1"
        assert server.aws_service == "execute-api"
        assert server.aws_profile is None
        assert server.bearer_token is None
        assert server.enable_auth is True
        assert server.timeout == 30.0
        assert server.verbose is False

    def test_init_with_custom_params(self):
        """Test ProxyServer initialization with custom parameters."""
        server = ProxyServer(
            server_endpoint="https://api.test.com/mcp",
            aws_region="eu-west-1",
            aws_service="lambda",
            aws_profile="test-profile",
            bearer_token="test-token",
            enable_auth=False,
            timeout=60.0,
            verbose=True,
        )

        assert server.server_endpoint == "https://api.test.com/mcp"
        assert server.aws_region == "eu-west-1"
        assert server.aws_service == "lambda"
        assert server.aws_profile == "test-profile"
        assert server.bearer_token == "test-token"
        assert server.enable_auth is False
        assert server.timeout == 60.0
        assert server.verbose is True

    def test_invalid_url_raises_error(self):
        """Test that invalid URLs raise ValueError."""
        with pytest.raises(ValueError, match="Invalid server endpoint URL"):
            ProxyServer("invalid-url")

    @patch("mcp_proxy_sigv4.proxy.SigV4Auth")
    def test_sigv4_auth_initialization(self, mock_sigv4_auth):
        """Test SigV4 authentication initialization."""
        mock_auth_instance = Mock()
        mock_sigv4_auth.return_value = mock_auth_instance

        server = ProxyServer("https://example.com/mcp", aws_region="us-west-2")

        mock_sigv4_auth.assert_called_once_with(
            region="us-west-2", service="execute-api", profile=None
        )
        assert server._sigv4_auth == mock_auth_instance

    def test_bearer_token_auth_initialization(self):
        """Test bearer token authentication initialization."""
        server = ProxyServer("https://example.com/mcp", bearer_token="test-token")

        assert server._bearer_auth == "test-token"
        assert server._sigv4_auth is None

    def test_no_auth_initialization(self):
        """Test no authentication initialization."""
        server = ProxyServer("https://example.com/mcp", enable_auth=False)

        assert server._bearer_auth is None
        assert server._sigv4_auth is None

    @patch("mcp_proxy_sigv4.proxy.SigV4Auth")
    def test_sigv4_auth_failure_raises_error(self, mock_sigv4_auth):
        """Test that SigV4 auth initialization failure raises error."""
        mock_sigv4_auth.side_effect = Exception("No credentials")

        with pytest.raises(Exception, match="No credentials"):
            ProxyServer("https://example.com/mcp")

    def test_create_transport_with_bearer_token(self):
        """Test transport creation with bearer token."""
        server = ProxyServer("https://example.com/mcp", bearer_token="test-token")

        with patch("mcp_proxy_sigv4.proxy.StreamableHttpTransport") as mock_transport:
            mock_transport_instance = Mock()
            mock_transport.return_value = mock_transport_instance

            transport = server._create_transport()

            mock_transport.assert_called_once_with(
                url="https://example.com/mcp", auth="test-token", sse_read_timeout=30.0
            )
            assert transport == mock_transport_instance

    @patch("mcp_proxy_sigv4.proxy.SigV4Auth")
    def test_create_transport_with_sigv4(self, mock_sigv4_auth):
        """Test transport creation with SigV4 auth."""
        mock_auth_instance = Mock()
        mock_sigv4_auth.return_value = mock_auth_instance

        server = ProxyServer("https://example.com/mcp")

        with patch(
            "mcp_proxy_sigv4.proxy.SigV4StreamableHttpTransport"
        ) as mock_transport:
            mock_transport_instance = Mock()
            mock_transport.return_value = mock_transport_instance

            transport = server._create_transport()

            mock_transport.assert_called_once_with(
                url="https://example.com/mcp",
                sigv4_auth=mock_auth_instance,
                timeout=30.0,
            )
            assert transport == mock_transport_instance

    def test_create_transport_no_auth(self):
        """Test transport creation without authentication."""
        server = ProxyServer("https://example.com/mcp", enable_auth=False)

        with patch("mcp_proxy_sigv4.proxy.StreamableHttpTransport") as mock_transport:
            mock_transport_instance = Mock()
            mock_transport.return_value = mock_transport_instance

            transport = server._create_transport()

            mock_transport.assert_called_once_with(
                url="https://example.com/mcp", sse_read_timeout=30.0
            )
            assert transport == mock_transport_instance

    @pytest.mark.asyncio
    @patch("mcp_proxy_sigv4.proxy.FastMCP")
    @patch("mcp_proxy_sigv4.proxy.ProxyClient")
    async def test_run_stdio_success(self, mock_proxy_client, mock_fastmcp):
        """Test successful stdio server run."""
        server = ProxyServer("https://example.com/mcp", enable_auth=False)

        # Mock transport
        mock_transport = Mock()
        server._create_transport = Mock(return_value=mock_transport)

        # Mock ProxyClient
        mock_client_instance = Mock()
        mock_proxy_client.return_value = mock_client_instance

        # Mock FastMCP
        mock_server_instance = Mock()
        mock_server_instance.run_async = AsyncMock()
        mock_fastmcp.as_proxy.return_value = mock_server_instance

        # Run the method
        await server.run_stdio()

        # Verify calls
        server._create_transport.assert_called_once()
        mock_proxy_client.assert_called_once_with(mock_transport)
        mock_fastmcp.as_proxy.assert_called_once_with(
            mock_client_instance, name="mcp-proxy-sigv4"
        )
        mock_server_instance.run_async.assert_called_once_with("stdio")

    @pytest.mark.asyncio
    async def test_run_stdio_keyboard_interrupt(self):
        """Test keyboard interrupt handling in stdio run."""
        server = ProxyServer("https://example.com/mcp", enable_auth=False)

        with patch.object(server, "_create_transport", side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                await server.run_stdio()

    @pytest.mark.asyncio
    async def test_run_stdio_exception(self):
        """Test exception handling in stdio run."""
        server = ProxyServer("https://example.com/mcp", enable_auth=False)

        with patch.object(
            server, "_create_transport", side_effect=Exception("Test error")
        ):
            with pytest.raises(Exception, match="Test error"):
                await server.run_stdio()

    @pytest.mark.asyncio
    @patch("mcp_proxy_sigv4.proxy.ProxyClient")
    async def test_test_connection_success(self, mock_proxy_client):
        """Test successful connection test."""
        server = ProxyServer("https://example.com/mcp", enable_auth=False)

        # Mock transport
        mock_transport = Mock()
        server._create_transport = Mock(return_value=mock_transport)

        # Mock ProxyClient with async context manager
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_proxy_client.return_value = mock_client_instance

        # Test connection
        result = await server.test_connection()

        assert result is True
        server._create_transport.assert_called_once()
        mock_proxy_client.assert_called_once_with(mock_transport)

    @pytest.mark.asyncio
    @patch("mcp_proxy_sigv4.proxy.ProxyClient")
    async def test_test_connection_failure(self, mock_proxy_client):
        """Test connection test failure."""
        server = ProxyServer("https://example.com/mcp", enable_auth=False)

        # Mock transport
        mock_transport = Mock()
        server._create_transport = Mock(return_value=mock_transport)

        # Mock ProxyClient to raise exception
        mock_proxy_client.side_effect = Exception("Connection failed")

        # Test connection
        result = await server.test_connection()

        assert result is False
