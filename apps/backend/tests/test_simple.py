
import pytest
from httpx import AsyncClient, ASGITransport
from src.app import app


@pytest.mark.asyncio
async def test_simple_endpoint():
    """Simple test to verify basic functionality"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "server is running"}


@pytest.mark.asyncio
async def test_price_stream_response():
    """Test that price stream endpoint responds correctly"""
    import asyncio

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=5.0) as client:
        try:
            response = await client.get("/stream/price/spot")
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            # Read first chunk with timeout to avoid hanging
            content = b""
            try:
                async for chunk in response.aiter_bytes():
                    content += chunk
                    if len(content) > 100:  # Just check we got some data
                        break
            except asyncio.TimeoutError:
                pass  # It's ok if we timeout, we just want to check connection

            # Should have received some data
            assert len(content) > 0

        except Exception as e:
            # If streaming fails, at least check endpoint exists
            assert False, f"Streaming endpoint failed: {e}"


@pytest.mark.asyncio
async def test_invalid_stream_endpoint():
    """Test invalid stream endpoint"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=5.0) as client:
        response = await client.get("/stream/price/invalid")
        assert response.status_code == 400


def test_basic_math():
    """Basic test to verify pytest is working"""
    assert 1 + 1 == 2


@pytest.mark.asyncio
async def test_async_basic():
    """Basic async test"""
    async def add(a, b):
        return a + b

    result = await add(2, 3)
    assert result == 5
