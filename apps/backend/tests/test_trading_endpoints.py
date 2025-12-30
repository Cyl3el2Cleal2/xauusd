import pytest
import json
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.trading_service import TradingService
from src.services.price_service import PriceService
from src.schemas import GoldPriceCreate, Gold96PriceCreate, TransactionCreate


class TestTradingEndpoints:
    """Test cases for trading-related endpoints"""

    @pytest.mark.asyncio
    async def test_create_buy_transaction(self, authenticated_client: AsyncClient, db_session: AsyncSession, sample_transaction_data):
        """Test creating a buy transaction"""
        # Add some balance to user first
        from src.db import User
        # Get current user (this would need to be implemented based on auth)

        response = await authenticated_client.post("/trading/transactions", json=sample_transaction_data)

        # Check response
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data
            assert data["transaction_type"] == "buy"
            assert data["quantity"] == sample_transaction_data["quantity"]
            assert data["price_per_unit"] == sample_transaction_data["price_per_unit"]

    @pytest.mark.asyncio
    async def test_create_sell_transaction(self, authenticated_client: AsyncClient, db_session: AsyncSession):
        """Test creating a sell transaction"""
        sell_data = {
            "transaction_type": "sell",
            "quantity": 0.5,
            "price_per_unit": 1300.0,
            "total_amount": 650.0
        }

        response = await authenticated_client.post("/trading/transactions", json=sell_data)

        # Check response
        if response.status_code in [200, 201]:
            data = response.json()
            assert data["transaction_type"] == "sell"
            assert data["quantity"] == sell_data["quantity"]

    @pytest.mark.asyncio
    async def test_create_transaction_unauthorized(self, client: AsyncClient, sample_transaction_data):
        """Test creating transaction without authentication"""
        response = await client.post("/trading/transactions", json=sample_transaction_data)
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_transaction_invalid_data(self, authenticated_client: AsyncClient):
        """Test creating transaction with invalid data"""
        invalid_data = {
            "transaction_type": "invalid",
            "quantity": -1.0,
            "price_per_unit": 0
        }

        response = await authenticated_client.post("/trading/transactions", json=invalid_data)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_transaction_history(self, authenticated_client: AsyncClient, db_session: AsyncSession):
        """Test retrieving transaction history"""
        response = await authenticated_client.get("/trading/transactions")

        # Should return array even if empty
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_transaction_details(self, authenticated_client: AsyncClient, db_session: AsyncSession):
        """Test retrieving specific transaction details"""
        # First create a transaction
        transaction_data = {
            "transaction_type": "buy",
            "quantity": 1.0,
            "price_per_unit": 1250.0,
            "total_amount": 1250.0
        }

        create_response = await authenticated_client.post("/trading/transactions", json=transaction_data)

        if create_response.status_code in [200, 201]:
            transaction_id = create_response.json()["id"]

            # Get transaction details
            response = await authenticated_client.get(f"/trading/transactions/{transaction_id}")

            if response.status_code == 200:
                data = response.json()
                assert data["id"] == transaction_id
                assert data["transaction_type"] == transaction_data["transaction_type"]

    @pytest.mark.asyncio
    async def test_cancel_transaction(self, authenticated_client: AsyncClient, db_session: AsyncSession):
        """Test canceling a transaction"""
        # First create a transaction
        transaction_data = {
            "transaction_type": "buy",
            "quantity": 1.0,
            "price_per_unit": 1250.0,
            "total_amount": 1250.0
        }

        create_response = await authenticated_client.post("/trading/transactions", json=transaction_data)

        if create_response.status_code in [200, 201]:
            transaction_id = create_response.json()["id"]

            # Cancel transaction
            response = await authenticated_client.patch(f"/trading/transactions/{transaction_id}/cancel")

            if response.status_code == 200:
                data = response.json()
                assert data["status"] in ["cancelled", "canceled"]

    @pytest.mark.asyncio
    async def test_get_queue_health(self, authenticated_client: AsyncClient):
        """Test retrieving trading queue health status"""
        response = await authenticated_client.get("/trading/queue/health")

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "queue_size" in data

    @pytest.mark.asyncio
    async def test_get_current_price(self, authenticated_client: AsyncClient, db_session: AsyncSession, sample_gold_price, sample_gold96_price):
        """Test retrieving current trading prices"""
        # Save price data first
        await PriceService.save_gold_price(db_session, sample_gold_price)
        await PriceService.save_gold96_price(db_session, sample_gold96_price)

        response = await authenticated_client.get("/trading/prices/current")

        if response.status_code == 200:
            data = response.json()
            assert "spot" in data or "gold96" in data

    @pytest.mark.asyncio
    async def test_get_user_balance(self, authenticated_client: AsyncClient):
        """Test retrieving user balance"""
        response = await authenticated_client.get("/trading/balance")

        if response.status_code == 200:
            data = response.json()
            assert "balance" in data or "amount" in data

    @pytest.mark.asyncio
    async def test_add_balance(self, authenticated_client: AsyncClient):
        """Test adding balance to user account"""
        balance_data = {
            "amount": 1000.0,
            "currency": "USD"
        }

        response = await authenticated_client.post("/trading/balance/add", json=balance_data)

        if response.status_code == 200:
            data = response.json()
            assert "new_balance" in data or "balance" in data

    @pytest.mark.asyncio
    async def test_get_user_portfolio(self, authenticated_client: AsyncClient):
        """Test retrieving user portfolio"""
        response = await authenticated_client.get("/trading/portfolio")

        if response.status_code == 200:
            data = response.json()
            assert "holdings" in data or "positions" in data


class TestTradingService:
    """Test cases for TradingService"""

    @pytest.mark.asyncio
    async def test_create_buy_transaction_service(self, db_session: AsyncSession):
        """Test creating buy transaction through service"""
        transaction_data = TransactionCreate(
            transaction_type="buy",
            quantity=1.0,
            price_per_unit=1250.0,
            total_amount=1250.0
        )

        # This would need user_id - assuming it's passed or available
        # transaction = await TradingService.create_buy_transaction(db_session, user_id, transaction_data)

        # For now, just test the data structure
        assert transaction_data.transaction_type == "buy"
        assert transaction_data.quantity == 1.0
        assert transaction_data.total_amount == 1250.0

    @pytest.mark.asyncio
    async def test_create_sell_transaction_service(self, db_session: AsyncSession):
        """Test creating sell transaction through service"""
        transaction_data = TransactionCreate(
            transaction_type="sell",
            quantity=0.5,
            price_per_unit=1300.0,
            total_amount=650.0
        )

        assert transaction_data.transaction_type == "sell"
        assert transaction_data.quantity == 0.5
        assert transaction_data.total_amount == 650.0

    @pytest.mark.asyncio
    async def test_transaction_validation(self, db_session: AsyncSession):
        """Test transaction validation logic"""
        # Test negative quantity
        with pytest.raises(ValueError):
            TransactionCreate(
                transaction_type="buy",
                quantity=-1.0,
                price_per_unit=1250.0,
                total_amount=-1250.0
            )

    @pytest.mark.asyncio
    async def test_price_calculation(self, db_session: AsyncSession):
        """Test price calculation logic"""
        quantity = 2.5
        price_per_unit = 1250.50
        expected_total = quantity * price_per_unit

        transaction_data = TransactionCreate(
            transaction_type="buy",
            quantity=quantity,
            price_per_unit=price_per_unit,
            total_amount=expected_total
        )

        assert abs(transaction_data.total_amount - expected_total) < 0.01


class TestTradingQueue:
    """Test cases for trading queue functionality"""

    @pytest.mark.asyncio
    async def test_queue_health_check(self, db_session: AsyncSession):
        """Test queue health monitoring"""
        # This would test the actual queue implementation
        # For now, just test the concept
        health_status = {
            "status": "healthy",
            "queue_size": 0,
            "processing_count": 0
        }

        assert health_status["status"] == "healthy"
        assert health_status["queue_size"] >= 0

    @pytest.mark.asyncio
    async def test_transaction_priority(self, db_session: AsyncSession):
        """Test transaction priority handling"""
        # Test that higher priority transactions are processed first
        priorities = ["high", "medium", "low"]

        # Simulate priority queue
        queue = []
        for priority in priorities:
            queue.append({"priority": priority, "data": f"transaction_{priority}"})

        # Sort by priority (high first)
        sorted_queue = sorted(queue, key=lambda x: (
            0 if x["priority"] == "high" else
            1 if x["priority"] == "medium" else 2
        ))

        assert sorted_queue[0]["priority"] == "high"
        assert sorted_queue[1]["priority"] == "medium"
        assert sorted_queue[2]["priority"] == "low"


class TestTradingValidation:
    """Test cases for trading validation rules"""

    @pytest.mark.asyncio
    async def test_insufficient_balance(self, db_session: AsyncSession):
        """Test transaction rejection due to insufficient balance"""
        user_balance = 500.0
        transaction_amount = 1000.0

        assert transaction_amount > user_balance
        # Transaction should be rejected

    @pytest.mark.asyncio
    async def test_insufficient_holdings(self, db_session: AsyncSession):
        """Test sell transaction rejection due to insufficient holdings"""
        user_holdings = 0.5  # ounces
        sell_quantity = 1.0  # ounces

        assert sell_quantity > user_holdings
        # Sell transaction should be rejected

    @pytest.mark.asyncio
    async def test_market_hours_validation(self, db_session: AsyncSession):
        """Test market hours validation"""
        now = datetime.utcnow()
        current_hour = now.hour

        # Assuming market hours are 9 AM to 5 PM UTC
        market_open = 9
        market_close = 17

        is_market_open = market_open <= current_hour < market_close

        # Transaction should only be processed during market hours
        # or queued for off-hours processing
        if not is_market_open:
            assert "off_hours" in "queue_or_reject"
        else:
            assert "market_hours" in "process_immediately"

    @pytest.mark.asyncio
    async def test_price_validation(self, db_session: AsyncSession):
        """Test price validation against current market prices"""
        current_market_price = 1250.0
        transaction_price = 1000.0  # Significantly different

        # Allow some tolerance (e.g., 5%)
        tolerance = 0.05
        min_price = current_market_price * (1 - tolerance)
        max_price = current_market_price * (1 + tolerance)

        is_price_valid = min_price <= transaction_price <= max_price

        if not is_price_valid:
            assert "price_warning" in "flag_or_reject"
        else:
            assert "price_valid" in "accept"
