"""Tests for SigV4 authentication."""

from unittest.mock import Mock, patch

import pytest

from mcp_proxy_sigv4.sigv4_auth import SigV4Auth, SigV4StreamableHttpTransport


class TestSigV4Auth:
    """Test SigV4Auth functionality."""

    def test_init_with_default_params(self, mock_boto3_session, mock_aws_credentials):
        """Test SigV4Auth initialization with default parameters."""
        auth = SigV4Auth()

        assert auth.region == "us-east-1"
        assert auth.service == "execute-api"
        assert auth.profile is None

    def test_init_with_custom_params(self, mock_boto3_session, mock_aws_credentials):
        """Test SigV4Auth initialization with custom parameters."""
        auth = SigV4Auth(region="us-west-2", service="lambda", profile="test-profile")

        assert auth.region == "us-west-2"
        assert auth.service == "lambda"
        assert auth.profile == "test-profile"

    def test_init_with_profile(self, mock_aws_credentials):
        """Test SigV4Auth initialization with AWS profile."""
        with patch("boto3.Session") as mock_session:
            mock_session.return_value.get_credentials.return_value = (
                mock_aws_credentials
            )

            SigV4Auth(profile="test-profile")

            mock_session.assert_called_once_with(profile_name="test-profile")

    def test_init_without_credentials_fails(self):
        """Test SigV4Auth fails when no credentials available."""
        with patch("boto3.Session") as mock_session:
            mock_session.return_value.get_credentials.return_value = None

            with pytest.raises(ValueError, match="No AWS credentials found"):
                SigV4Auth()

    def test_auth_inherits_from_aws4auth(
        self, mock_boto3_session, mock_aws_credentials
    ):
        """Test that SigV4Auth properly inherits from AWS4Auth."""
        from requests_aws4auth import AWS4Auth

        auth = SigV4Auth()
        assert isinstance(auth, AWS4Auth)

    @patch("requests_aws4auth.AWS4Auth.__init__")
    def test_aws4auth_initialization(
        self, mock_aws4auth_init, mock_boto3_session, mock_aws_credentials
    ):
        """Test that AWS4Auth is initialized with correct parameters."""
        mock_aws4auth_init.return_value = None

        SigV4Auth(region="us-west-2", service="lambda")

        mock_aws4auth_init.assert_called_once_with(
            "test_access_key",
            "test_secret_key",
            "us-west-2",
            "lambda",
            session_token="test_session_token",
        )


class TestSigV4StreamableHttpTransport:
    """Test SigV4StreamableHttpTransport functionality."""

    def test_init_with_sigv4_auth(self):
        """Test transport initialization with SigV4 auth."""
        mock_auth = Mock()

        with patch(
            "mcp_proxy_sigv4.sigv4_auth.StreamableHttpTransport.__init__"
        ) as mock_parent_init:
            mock_parent_init.return_value = None

            SigV4StreamableHttpTransport(
                url="https://example.com/mcp", sigv4_auth=mock_auth, timeout=60.0
            )

            # Check that auth was passed to parent
            args, kwargs = mock_parent_init.call_args
            assert args[0] == "https://example.com/mcp"
            assert kwargs["auth"] == mock_auth
            assert kwargs["sse_read_timeout"] == 60.0

    def test_init_without_auth(self):
        """Test transport initialization without authentication."""
        with patch(
            "mcp_proxy_sigv4.sigv4_auth.StreamableHttpTransport.__init__"
        ) as mock_parent_init:
            mock_parent_init.return_value = None

            SigV4StreamableHttpTransport(url="https://example.com/mcp", timeout=30.0)

            args, kwargs = mock_parent_init.call_args
            assert args[0] == "https://example.com/mcp"
            assert "auth" not in kwargs
            assert kwargs["sse_read_timeout"] == 30.0

    def test_timeout_handling(self):
        """Test that timeout is converted to sse_read_timeout."""
        with patch(
            "mcp_proxy_sigv4.sigv4_auth.StreamableHttpTransport.__init__"
        ) as mock_parent_init:
            mock_parent_init.return_value = None

            SigV4StreamableHttpTransport(url="https://example.com/mcp", timeout=45.0)

            args, kwargs = mock_parent_init.call_args
            assert kwargs["sse_read_timeout"] == 45.0

    def test_existing_sse_timeout_not_overridden(self):
        """Test that existing sse_read_timeout is not overridden."""
        with patch(
            "mcp_proxy_sigv4.sigv4_auth.StreamableHttpTransport.__init__"
        ) as mock_parent_init:
            mock_parent_init.return_value = None

            SigV4StreamableHttpTransport(
                url="https://example.com/mcp", timeout=45.0, sse_read_timeout=90.0
            )

            args, kwargs = mock_parent_init.call_args
            assert kwargs["sse_read_timeout"] == 90.0  # Should not be overridden
