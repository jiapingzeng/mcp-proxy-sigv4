"""AWS SigV4 authentication using requests-aws4auth library."""

import logging
from typing import Any

import boto3
from fastmcp.client.transports import StreamableHttpTransport
from requests_aws4auth import AWS4Auth

logger = logging.getLogger(__name__)


class SigV4Auth(AWS4Auth):
    """AWS SigV4 authentication handler with boto3 credential integration."""

    def __init__(
        self,
        region: str = "us-east-1",
        service: str = "execute-api",
        profile: str | None = None,
    ):
        self.region = region
        self.service = service
        self.profile = profile

        try:
            if profile:
                session = boto3.Session(profile_name=profile)
                logger.debug(f"Using AWS profile: {profile}")
            else:
                session = boto3.Session()
                logger.debug("Using default AWS credentials")

            credentials = session.get_credentials()
            if not credentials:
                raise ValueError("No AWS credentials found")

            super().__init__(
                credentials.access_key,
                credentials.secret_key,
                region,
                service,
                session_token=credentials.token
            )

            logger.debug(f"AWS SigV4 authentication initialized for region {region}, service {service}")

        except Exception as e:
            logger.error(f"Failed to initialize AWS credentials: {e}")
            raise


class SigV4StreamableHttpTransport(StreamableHttpTransport):
    """StreamableHttp transport with AWS SigV4 authentication support."""

    def __init__(
        self,
        url: str,
        *,
        sigv4_auth: SigV4Auth | None = None,
        timeout: float = 30.0,
        **kwargs: Any
    ):
        if timeout and "sse_read_timeout" not in kwargs:
            kwargs["sse_read_timeout"] = timeout

        if sigv4_auth:
            kwargs["auth"] = sigv4_auth

        super().__init__(url, **kwargs)
        self._sigv4_auth = sigv4_auth
