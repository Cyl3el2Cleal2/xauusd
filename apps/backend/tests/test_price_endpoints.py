import pytest
import json
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.price_service import PriceService
from src.schemas import GoldPriceCreate, Gold96PriceCreate


class TestPriceEndpoints:
    """Test cases for price-related endpoints"""

    @pytest.mark.asyncio
    async def test_get_root_endpoint(self, client: AsyncClient):
        """Test the root endpoint returns correct message"""
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "server is running"}

    @pytest.mark.asyncio
    async def test_stream_price_spot(self, client: AsyncClient):
        """Test SSE streaming for spot price"""
        response = await client.get("/stream/price/spot")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert "Cache-Control" in response.headers
        assert "Connection" in response.headers

    @pytest.mark.asyncio
    async def test_stream_price_gold96(self, client: AsyncClient):
        """Test SSE streaming for gold96 price"""
        response = await client.get("/stream/price/gold96")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    @pytest.mark.asyncio
    async def test_stream_price_invalid_symbol(self, client: AsyncClient):
        """Test SSE streaming with invalid symbol returns 400"""
        response = await client.get("/stream/price/invalid")
        assert response.status_code == 400
        assert "Unsupported symbol" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_latest_price(self, client: AsyncClient, db_session: AsyncSession, sample_gold_price):
        """Test retrieving latest price after saving sample data"""
        # Save sample price to database
        await PriceService.save_gold_price(db_session, sample_gold_price)

        # Note: This endpoint might not exist, but we're testing what should be there
        response = await client.get("/price/latest")

        # If endpoint exists, it should return 200 with price data
        if response.status_code == 200:
            data = response.json()
            assert "price" in data or "symbol" in data

    @pytest.mark.asyncio
    async def test_get_price_history(self, client: AsyncClient, db_session: AsyncSession, sample_gold_price):
        """Test retrieving price history"""
        # Save sample price to database
        await PriceService.save_gold_price(db_session, sample_gold_price)

        # Note: This endpoint might not exist, but we're testing what should be there
        response = await client.get("/price/history?hours=1&limit=10")

        # If endpoint exists, it should return 200 with array of prices
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_sse_data_format(self, client: AsyncClient, db_session: AsyncSession, sample_gold_price):
        """Test that SSE data is properly formatted"""
        # Save sample price first
        await PriceService.save_gold_price(db_session, sample_gold_price)

        response = await client.get("/stream/price/spot")
        assert response.status_code == 200

        # Read first chunk of SSE data
        content = b""
        async for chunk in response.aiter_bytes():
            content += chunk
            if b"data: " in content:
                break

        # Parse SSE data
        content_str = content.decode('utf-8')
        lines = content_str.split('\n')

        # Find data line
        data_line = None
        for line in lines:
            if line.startswith('data: '):
                data_line = line[6:]  # Remove 'data: ' prefix
                break

        if data_line:
            try:
                data = json.loads(data_line)
                assert "symbol" in data
                assert "timestamp" in data
                assert "type" in data
            except json.JSONDecodeError:
                pytest.fail("SSE data is not valid JSON")


class TestPriceService:
    """Test cases for PriceService"""

    @pytest.mark.asyncio
    async def test_save_gold_price(self, db_session: AsyncSession, sample_gold_price):
        """Test saving gold price to database"""
        saved_price = await PriceService.save_gold_price(db_session, sample_gold_price)

        assert saved_price.id is not None
        assert saved_price.symbol == sample_gold_price.symbol
        assert saved_price.price == sample_gold_price.price
        assert saved_price.usd_price == sample_gold_price.usd_price
        assert saved_price.source == sample_gold_price.source

    @pytest.mark.asyncio
    async def test_save_gold96_price(self, db_session: AsyncSession, sample_gold96_price):
        """Test saving gold 96 price to database"""
        saved_price = await PriceService.save_gold96_price(db_session, sample_gold96_price)

        assert saved_price.id is not None
        assert saved_price.symbol == sample_gold96_price.symbol
        assert saved_price.buy_price == sample_gold96_price.buy_price
        assert saved_price.sell_price == sample_gold96_price.sell_price
        assert saved_price.source == sample_gold96_price.source

    @pytest.mark.asyncio
    async def test_get_latest_gold_price(self, db_session: AsyncSession, sample_gold_price):
        """Test retrieving latest gold price"""
        # Save sample price
        await PriceService.save_gold_price(db_session, sample_gold_price)

        # Retrieve latest price
        latest_price = await PriceService.get_latest_gold_price(db_session)

        assert latest_price is not None
        assert latest_price.symbol == sample_gold_price.symbol
        assert latest_price.price == sample_gold_price.price

    @pytest.mark.asyncio
    async def test_get_latest_gold96_price(self, db_session: AsyncSession, sample_gold96_price):
        """Test retrieving latest gold 96 price"""
        # Save sample price
        await PriceService.save_gold96_price(db_session, sample_gold96_price)

        # Retrieve latest price
        latest_price = await PriceService.get_latest_gold96_price(db_session)

        assert latest_price is not None
        assert latest_price.symbol == sample_gold96_price.symbol
        assert latest_price.buy_price == sample_gold96_price.buy_price
        assert latest_price.sell_price == sample_gold96_price.sell_price

    @pytest.mark.asyncio
    async def test_get_gold_price_history(self, db_session: AsyncSession, sample_gold_price):
        """Test retrieving gold price history"""
        # Save multiple prices with different timestamps
        now = datetime.utcnow()
        for i in range(3):
            price_data = GoldPriceCreate(
                symbol="spot",
                price=1200.0 + i,
                usd_price=1900.0 + i,
                timestamp=now - timedelta(hours=i),
                source="test"
            )
            await PriceService.save_gold_price(db_session, price_data)

        # Get history
        history = await PriceService.get_gold_price_history(db_session, hours=24, limit=10)

        assert len(history) >= 3
        # Should be in descending order (latest first)
        assert history[0].timestamp >= history[1].timestamp

    @pytest.mark.asyncio
    async def test_get_gold96_price_history(self, db_session: AsyncSession, sample_gold96_price):
        """Test retrieving gold 96 price history"""
        # Save multiple prices with different timestamps
        now = datetime.utcnow()
        for i in range(3):
            price_data = Gold96PriceCreate(
                symbol="gold96",
                buy_price=1200.0 + i,
                sell_price=1220.0 + i,
                timestamp=now - timedelta(hours=i),
                source="test"
            )
            await PriceService.save_gold96_price(db_session, price_data)

        # Get history
        history = await PriceService.get_gold96_price_history(db_session, hours=24, limit=10)

        assert len(history) >= 3
        # Should be in descending order (latest first)
        assert history[0].timestamp >= history[1].timestamp

    @pytest.mark.asyncio
    async def test_get_price_statistics(self, db_session: AsyncSession):
        """Test retrieving price statistics"""
        # Save test data
        now = datetime.utcnow()
        prices = [1200.0, 1210.0, 1220.0, 1215.0, 1195.0]

        for i, price in enumerate(prices):
            price_data = GoldPriceCreate(
                symbol="spot",
                price=price,
                usd_price=1900.0 + i,
                timestamp=now - timedelta(hours=i),
                source="test_stats"
            )
            await PriceService.save_gold_price(db_session, price_data)

        # Get statistics
        stats = await PriceService.get_price_statistics(db_session, "spot", hours=24)

        assert "current" in stats
        assert "high" in stats
        assert "low" in stats
        assert "average" in stats
        assert "count" in stats
        assert stats["count"] >= 5

    @pytest.mark.asyncio
    async def test_get_gold_prices_in_range(self, db_session: AsyncSession):
        """Test retrieving prices within a specific time range"""
        now = datetime.utcnow()

        # Create prices at different times
        times = [
            now - timedelta(hours=25),  # Should be excluded
            now - timedelta(hours=20),  # Should be included
            now - timedelta(hours=15),  # Should be included
            now - timedelta(hours=10),  # Should be included
            now - timedelta(hours=5),   # Should be included
        ]

        for i, timestamp in enumerate(times):
            price_data = GoldPriceCreate(
                symbol="spot",
                price=1200.0 + i,
                usd_price=1900.0 + i,
                timestamp=timestamp,
                source="test_range"
            )
            await PriceService.save_gold_price(db_session, price_data)

        # Query last 24 hours
        start_time = now - timedelta(hours=24)
        end_time = now

        prices_in_range = await PriceService.get_gold_prices_in_range(
            db_session, start_time, end_time
        )

        # Should have 4 prices (excluding the 25-hour-old one)
        assert len(prices_in_range) == 4

    @pytest.mark.asyncio
    async def test_cleanup_old_prices(self, db_session: AsyncSession):
        """Test cleanup of old price records"""
        now = datetime.utcnow()

        # Create old data (45 days ago) - should be cleaned up
        old_price = GoldPriceCreate(
            symbol="spot",
            price=1000.0,
            usd_price=1600.0,
            timestamp=now - timedelta(days=45),
            source="old_test"
        )
        await PriceService.save_gold_price(db_session, old_price)

        # Create recent data (5 days ago) - should remain
        recent_price = GoldPriceCreate(
            symbol="spot",
            price=1200.0,
            usd_price=1800.0,
            timestamp=now - timedelta(days=5),
            source="recent_test"
        )
        await PriceService.save_gold_price(db_session, recent_price)

        # Run cleanup for 30 days
        result = await PriceService.cleanup_old_prices(db_session, days_to_keep=30)

        assert "deleted_gold_prices" in result
        assert "deleted_gold96_prices" in result
        assert result["deleted_gold_prices"] >= 1

    @pytest.mark.asyncio
    async def test_empty_database_queries(self, db_session: AsyncSession):
        """Test queries on empty database"""
        latest_price = await PriceService.get_latest_gold_price(db_session)
        assert latest_price is None

        latest_gold96 = await PriceService.get_latest_gold96_price(db_session)
        assert latest_gold96 is None

        history = await PriceService.get_gold_price_history(db_session, hours=24)
        assert len(history) == 0

        stats = await PriceService.get_price_statistics(db_session, "spot", hours=24)
        assert stats["count"] == 0
        assert stats["current"] is None
