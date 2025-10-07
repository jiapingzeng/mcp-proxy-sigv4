"""Pytest configuration and shared fixtures."""

import os
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_aws_credentials():
    """Mock AWS credentials for testing."""
    mock_creds = Mock()
    mock_creds.access_key = "test_access_key"
    mock_creds.secret_key = "test_secret_key"
    mock_creds.token = "test_session_token"
    return mock_creds


@pytest.fixture
def mock_boto3_session(mock_aws_credentials):
    """Mock boto3 session."""
    with patch('boto3.Session') as mock_session:
        mock_session.return_value.get_credentials.return_value = mock_aws_credentials
        yield mock_session


@pytest.fixture
def clean_env():
    """Clean environment variables for testing."""
    # Store original values
    original_bearer_token = os.environ.get('BEARER_TOKEN')

    # Clean up
    if 'BEARER_TOKEN' in os.environ:
        del os.environ['BEARER_TOKEN']

    yield

    # Restore original values
    if original_bearer_token is not None:
        os.environ['BEARER_TOKEN'] = original_bearer_token


@pytest.fixture
def sample_endpoint():
    """Sample MCP endpoint for testing."""
    return "https://api.example.com/mcp"


@pytest.fixture
def sample_bearer_token():
    """Sample JWT bearer token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
