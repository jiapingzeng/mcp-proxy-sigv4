"""Integration tests for the MCP proxy server."""

import os
from unittest.mock import Mock, patch

import pytest


class TestIntegration:
    """Integration tests that test components working together."""

    def test_bearer_token_env_var_integration(self, clean_env):
        """Test that BEARER_TOKEN env var works end-to-end with CLI."""
        from click.testing import CliRunner

        from mcp_proxy_sigv4.cli import main

        os.environ["BEARER_TOKEN"] = "test-env-token"

        with patch("mcp_proxy_sigv4.cli.ProxyServer") as mock_proxy:
            mock_instance = Mock()
            mock_proxy.return_value = mock_instance

            runner = CliRunner()
            runner.invoke(main, ["--endpoint", "https://example.com/mcp"])

            # Should succeed and pass the env var token
            mock_proxy.assert_called_once()
            args, kwargs = mock_proxy.call_args
            assert kwargs["bearer_token"] == "test-env-token"

    def test_aws_sigv4_integration(self, mock_boto3_session, mock_aws_credentials):
        """Test AWS SigV4 authentication integration."""
        from mcp_proxy_sigv4.proxy import ProxyServer
        from mcp_proxy_sigv4.sigv4_auth import SigV4Auth

        # Create server with SigV4 auth
        server = ProxyServer("https://example.com/mcp", aws_region="us-west-2")

        # Should have initialized SigV4 auth
        assert server._sigv4_auth is not None
        assert isinstance(server._sigv4_auth, SigV4Auth)
        assert server._bearer_auth is None

    def test_bearer_token_integration(self):
        """Test bearer token authentication integration."""
        from mcp_proxy_sigv4.proxy import ProxyServer

        server = ProxyServer("https://example.com/mcp", bearer_token="test-token")

        # Should have initialized bearer token auth
        assert server._bearer_auth == "test-token"
        assert server._sigv4_auth is None

    def test_no_auth_integration(self):
        """Test no authentication integration."""
        from mcp_proxy_sigv4.proxy import ProxyServer

        server = ProxyServer("https://example.com/mcp", enable_auth=False)

        # Should have no authentication
        assert server._bearer_auth is None
        assert server._sigv4_auth is None

    @patch("mcp_proxy_sigv4.proxy.StreamableHttpTransport")
    def test_transport_creation_integration(self, mock_base_transport):
        """Test that different auth types create appropriate transports."""
        from mcp_proxy_sigv4.proxy import ProxyServer

        mock_transport_instance = Mock()
        mock_base_transport.return_value = mock_transport_instance

        # Test bearer token transport
        server = ProxyServer("https://example.com/mcp", bearer_token="test-token")
        server._create_transport()

        mock_base_transport.assert_called_with(
            url="https://example.com/mcp", auth="test-token", sse_read_timeout=30.0
        )

    def test_cli_to_server_parameter_passing(self):
        """Test that CLI parameters are correctly passed to ProxyServer."""
        from click.testing import CliRunner

        from mcp_proxy_sigv4.cli import main

        with patch("mcp_proxy_sigv4.cli.ProxyServer") as mock_proxy:
            mock_instance = Mock()
            mock_proxy.return_value = mock_instance

            runner = CliRunner()
            runner.invoke(
                main,
                [
                    "--endpoint",
                    "https://test.com/mcp",
                    "--aws-region",
                    "eu-central-1",
                    "--aws-service",
                    "apigateway",
                    "--aws-profile",
                    "test-profile",
                    "--bearer-token",
                    "test-jwt",
                    "--timeout",
                    "45",
                    "--verbose",
                ],
            )

            mock_proxy.assert_called_once()
            args, kwargs = mock_proxy.call_args

            assert kwargs["server_endpoint"] == "https://test.com/mcp"
            assert kwargs["aws_region"] == "eu-central-1"
            assert kwargs["aws_service"] == "apigateway"
            assert kwargs["aws_profile"] == "test-profile"
            assert kwargs["bearer_token"] == "test-jwt"
            assert kwargs["timeout"] == 45.0
            assert kwargs["verbose"] is True
            assert (
                kwargs["enable_auth"] is True
            )  # Should be True when bearer token provided


class TestErrorHandling:
    """Test error handling across components."""

    def test_invalid_endpoint_error_propagation(self):
        """Test that invalid endpoint errors are properly handled."""
        from mcp_proxy_sigv4.proxy import ProxyServer

        with pytest.raises(ValueError, match="Invalid server endpoint URL"):
            ProxyServer("not-a-url")

    def test_missing_aws_credentials_error(self):
        """Test handling of missing AWS credentials."""
        from mcp_proxy_sigv4.sigv4_auth import SigV4Auth

        with patch("boto3.Session") as mock_session:
            mock_session.return_value.get_credentials.return_value = None

            with pytest.raises(ValueError, match="No AWS credentials found"):
                SigV4Auth()

    def test_cli_validation_errors(self):
        """Test CLI validation error handling."""
        from click.testing import CliRunner

        from mcp_proxy_sigv4.cli import main

        runner = CliRunner()

        # Test conflicting auth options
        result = runner.invoke(
            main,
            [
                "--endpoint",
                "https://example.com/mcp",
                "--bearer-token",
                "token",
                "--no-auth",
            ],
        )

        assert result.exit_code == 1
        assert "Cannot specify both bearer token and --no-auth" in result.output
