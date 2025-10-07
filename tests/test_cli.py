"""Tests for the CLI module."""

import os
from unittest.mock import Mock, patch

from click.testing import CliRunner

from mcp_proxy_sigv4.cli import main


class TestCLI:
    """Test CLI functionality."""

    def test_help_command(self):
        """Test --help flag works."""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert 'MCP proxy server' in result.output
        assert '--endpoint' in result.output
        assert '--bearer-token' in result.output

    def test_missing_endpoint_fails(self):
        """Test that missing --endpoint fails."""
        runner = CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code == 2  # Click error code for missing required option
        assert 'Missing option' in result.output

    def test_invalid_endpoint_url(self):
        """Test that invalid URL fails validation."""
        runner = CliRunner()
        result = runner.invoke(main, ['--endpoint', 'invalid-url'])
        assert result.exit_code == 1
        assert 'Invalid endpoint URL' in result.output

    def test_bearer_token_and_no_auth_conflict(self):
        """Test that --bearer-token and --no-auth cannot be used together."""
        runner = CliRunner()
        result = runner.invoke(main, [
            '--endpoint', 'https://example.com/mcp',
            '--bearer-token', 'test-token',
            '--no-auth'
        ])
        assert result.exit_code == 1
        assert 'Cannot specify both bearer token and --no-auth' in result.output

    def test_bearer_token_env_var(self, clean_env, sample_endpoint, sample_bearer_token):
        """Test that BEARER_TOKEN environment variable is used."""
        os.environ['BEARER_TOKEN'] = sample_bearer_token

        with patch('mcp_proxy_sigv4.cli.ProxyServer') as mock_proxy:
            mock_instance = Mock()
            mock_proxy.return_value = mock_instance

            runner = CliRunner()
            runner.invoke(main, ['--endpoint', sample_endpoint])

            # Should not exit with error due to missing token
            mock_proxy.assert_called_once()
            args, kwargs = mock_proxy.call_args
            assert kwargs['bearer_token'] == sample_bearer_token

    def test_cli_bearer_token_takes_precedence(self, clean_env, sample_endpoint):
        """Test that CLI bearer token takes precedence over environment variable."""
        os.environ['BEARER_TOKEN'] = 'env-token'
        cli_token = 'cli-token'

        with patch('mcp_proxy_sigv4.cli.ProxyServer') as mock_proxy:
            mock_instance = Mock()
            mock_proxy.return_value = mock_instance

            runner = CliRunner()
            runner.invoke(main, [
                '--endpoint', sample_endpoint,
                '--bearer-token', cli_token
            ])

            mock_proxy.assert_called_once()
            args, kwargs = mock_proxy.call_args
            assert kwargs['bearer_token'] == cli_token

    def test_bearer_token_env_var_and_no_auth_conflict(self, clean_env, sample_endpoint, sample_bearer_token):
        """Test that BEARER_TOKEN env var conflicts with --no-auth."""
        os.environ['BEARER_TOKEN'] = sample_bearer_token

        runner = CliRunner()
        result = runner.invoke(main, [
            '--endpoint', sample_endpoint,
            '--no-auth'
        ])
        assert result.exit_code == 1
        assert 'Cannot specify both bearer token and --no-auth' in result.output

    @patch('mcp_proxy_sigv4.cli.ProxyServer')
    def test_aws_options_passed_correctly(self, mock_proxy, sample_endpoint):
        """Test that AWS options are passed to ProxyServer correctly."""
        mock_instance = Mock()
        mock_proxy.return_value = mock_instance

        runner = CliRunner()
        runner.invoke(main, [
            '--endpoint', sample_endpoint,
            '--aws-region', 'us-west-2',
            '--aws-service', 'lambda',
            '--aws-profile', 'test-profile',
            '--timeout', '60'
        ])

        mock_proxy.assert_called_once()
        args, kwargs = mock_proxy.call_args

        assert kwargs['server_endpoint'] == sample_endpoint
        assert kwargs['aws_region'] == 'us-west-2'
        assert kwargs['aws_service'] == 'lambda'
        assert kwargs['aws_profile'] == 'test-profile'
        assert kwargs['timeout'] == 60.0
        assert kwargs['enable_auth'] is True

