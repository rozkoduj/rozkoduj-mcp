"""Shared test fixtures for rozkoduj-mcp."""

import asyncio
from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp import iam_client
from rozkoduj_mcp.services import scanner


@pytest.fixture(autouse=True)
def _scanner_semaphore() -> Iterator[None]:
    """Pre-init the scanner semaphore so tests that only patch
    ``scanner.client`` do not need to call ``setup_client`` themselves.
    """
    scanner._request_semaphore = asyncio.Semaphore(scanner._MAX_CONCURRENT_REQUESTS)
    try:
        yield
    finally:
        scanner._request_semaphore = None


@pytest.fixture(autouse=True)
def _stub_metadata_server() -> Iterator[None]:
    """Pretend the platform metadata server is unreachable.

    Tests run off-platform so a real fetch would DNS-fail after the httpx
    timeout and slow every test. Patching ``iam_client._fetch`` to return
    ``None`` exercises the local-dev fallback path without any network IO.
    """
    iam_client.reset_cache()
    with patch.object(iam_client, "_fetch", new=AsyncMock(return_value=None)):
        yield
    iam_client.reset_cache()
