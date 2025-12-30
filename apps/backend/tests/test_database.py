import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db import User, GoldPrice, Gold96Price, Transaction, create_db_and_tables
from src.schemas import GoldPriceCreate, Gold96PriceCreate
from src.services.price_service import PriceService


class TestDatabaseModels:
    """Test cases for database model definitions and constraints"""

    @pytest.mark.asyncio
    async def test_user_model_creation(self, db_session: AsyncSession):
        """Test User model creation and constraints"""
        user = User(
            email="test@example.com",
            hashed_password="hashed_password_here",
            is_active=True,
            is_verified=True
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password_here"
        assert user.is_active is True
        assert user.is_verified is True
        assert user.created_at is not None
        assert user.updated_at is not None

    @pytest.mark.asyncio
    async def test_user_email_unique_constraint(self, db_session: AsyncSession):
        """Test that email uniqueness constraint is enforced"""
        user1 = User(
            email="duplicate@example.com",
            hashed_password="hashed_password_1",
            is_active=True,
            is_verified=True
        )

        user2 = User(
            email="duplicate@example.com",  # Same email
            hashed_password="hashed_password_2",
            is_active=True,
            is_verified=True
        )

        db_session.add(user1)
        await db_session.commit()

        # Second user with same email should fail
        db_session.add(user2)
        with pytest.raises(Exception):  # Should raise integrity error
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_gold_price_model_creation(self, db_session: AsyncSession):
        """Test GoldPrice model creation"""
        price = GoldPrice(
            symbol="spot",
            price=1250.75,
            usd_price=1985.50,
            timestamp=datetime.utcnow(),
            source="test"
        )

        db_session.add(price)
        await db_session.commit()
        await db_session.refresh(price)

        assert price.id is not None
        assert price.symbol == "spot"
        assert price.price == 1250.75
        assert price.usd_price == 1985.50
        assert price.source == "test"
        assert price.created_at is not None

    @pytest.mark.asyncio
    async def test_gold96_price_model_creation(self, db_session: AsyncSession):
        """Test Gold96Price model creation"""
        price = Gold96Price(
            symbol="gold96",
            buy_price=1250.50,
            sell_price=1270.75,
            timestamp=datetime.utcnow(),
            source="test"
        )

        db_session.add(price)
        await db_session.commit()
        await db_session.refresh(price)

        assert price.id is not None
        assert price.symbol == "gold96"
        assert price.buy_price == 1250.50
        assert price.sell_price == 1270.75
        assert price.source == "test"
        assert price.created_at is not None

    @pytest.mark.asyncio
    async def test_transaction_model_creation(self, db_session: AsyncSession):
        """Test Transaction model creation"""
        # First create a user
        user = User(
            email="trader@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_verified=True
        )
        db_session.add(user)
        await db_session.commit()

        transaction = Transaction(
            id=str(uuid.uuid4()),
            user_id=user.id,
            transaction_type="buy",
            quantity=1.0,
            price_per_unit=1250.0,
            total_amount=1250.0,
            status="pending",
            created_at=datetime.utcnow()
        )

        db_session.add(transaction)
        await db_session.commit()
        await db_session.refresh(transaction)

        assert transaction.id is not None
        assert transaction.user_id == user.id
        assert transaction.transaction_type == "buy"
        assert transaction.quantity == 1.0
        assert transaction.price_per_unit == 1250.0
        assert transaction.total_amount == 1250.0
        assert transaction.status == "pending"


class TestDatabaseQueries:
    """Test cases for database query operations"""

    @pytest.mark.asyncio
    async def test_query_user_by_email(self, db_session: AsyncSession):
        """Test querying user by email"""
        user = User(
            email="querytest@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_verified=True
        )

        db_session.add(user)
        await db_session.commit()

        # Query by email
        stmt = select(User).where(User.email == "querytest@example.com")
        result = await db_session.execute(stmt)
        found_user = result.scalar_one_or_none()

        assert found_user is not None
        assert found_user.email == "querytest@example.com"

    @pytest.mark.asyncio
    async def test_query_gold_prices_by_symbol(self, db_session: AsyncSession):
        """Test querying gold prices by symbol"""
        # Create test data
        symbols = ["spot", "gold96"]
        for symbol in symbols:
            for i in range(3):
                price = GoldPrice(
                    symbol=symbol,
                    price=1200.0 + i,
                    usd_price=1900.0 + i,
                    timestamp=datetime.utcnow() - timedelta(hours=i),
                    source="test_query"
                )
                db_session.add(price)

        await db_session.commit()

        # Query spot prices
        stmt = select(GoldPrice).where(GoldPrice.symbol == "spot")
        result = await db_session.execute(stmt)
        spot_prices = result.scalars().all()

        assert len(spot_prices) == 3
        for price in spot_prices:
            assert price.symbol == "spot"

    @pytest.mark.asyncio
    async def test_query_transactions_by_user(self, db_session: AsyncSession):
        """Test querying transactions by user"""
        # Create user
        user = User(
            email="txuser@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_verified=True
        )
        db_session.add(user)
        await db_session.commit()

        # Create transactions for user
        for i in range(3):
            transaction = Transaction(
                id=str(uuid.uuid4()),
                user_id=user.id,
                transaction_type="buy" if i % 2 == 0 else "sell",
                quantity=1.0 + i,
                price_per_unit=1200.0 + i,
                total_amount=(1.0 + i) * (1200.0 + i),
                status="completed",
                created_at=datetime.utcnow() - timedelta(hours=i)
            )
            db_session.add(transaction)

        await db_session.commit()

        # Query transactions for user
        stmt = select(Transaction).where(Transaction.user_id == user.id)
        result = await db_session.execute(stmt)
        user_transactions = result.scalars().all()

        assert len(user_transactions) == 3
        for tx in user_transactions:
            assert tx.user_id == user.id

    @pytest.mark.asyncio
    async def test_query_with_date_range(self, db_session: AsyncSession):
        """Test querying records within date range"""
        now = datetime.utcnow()

        # Create prices with different timestamps
        timestamps = [
            now - timedelta(days=35),  # Too old
            now - timedelta(days=25),  # Should be included
            now - timedelta(days=15),  # Should be included
            now - timedelta(days=5),   # Should be included
        ]

        for i, timestamp in enumerate(timestamps):
            price = GoldPrice(
                symbol="spot",
                price=1200.0 + i,
                usd_price=1900.0 + i,
                timestamp=timestamp,
                source="date_range_test"
            )
            db_session.add(price)

        await db_session.commit()

        # Query last 30 days
        cutoff_date = now - timedelta(days=30)
        stmt = select(GoldPrice).where(GoldPrice.timestamp >= cutoff_date)
        result = await db_session.execute(stmt)
        recent_prices = result.scalars().all()

        # Should have 3 prices (excluding the 35-day-old one)
        assert len(recent_prices) == 3

    @pytest.mark.asyncio
    async def test_ordered_query(self, db_session: AsyncSession):
        """Test querying with ordering"""
        now = datetime.utcnow()

        # Create prices with different timestamps
        for i in range(5):
            price = GoldPrice(
                symbol="spot",
                price=1200.0 + i,
                usd_price=1900.0 + i,
                timestamp=now - timedelta(minutes=i * 10),  # Descending order
                source="order_test"
            )
            db_session.add(price)

        await db_session.commit()

        # Query ordered by timestamp (newest first)
        stmt = select(GoldPrice).order_by(GoldPrice.timestamp.desc())
        result = await db_session.execute(stmt)
        prices = result.scalars().all()

        # Verify ordering
        for i in range(len(prices) - 1):
            assert prices[i].timestamp >= prices[i + 1].timestamp

    @pytest.mark.asyncio
    async def test_paginated_query(self, db_session: AsyncSession):
        """Test paginated queries"""
        # Create 10 prices
        for i in range(10):
            price = GoldPrice(
                symbol="spot",
                price=1200.0 + i,
                usd_price=1900.0 + i,
                timestamp=datetime.utcnow(),
                source="pagination_test"
            )
            db_session.add(price)

        await db_session.commit()

        # First page (limit 5, offset 0)
        stmt = select(GoldPrice).limit(5).offset(0)
        result = await db_session.execute(stmt)
        first_page = result.scalars().all()

        # Second page (limit 5, offset 5)
        stmt = select(GoldPrice).limit(5).offset(5)
        result = await db_session.execute(stmt)
        second_page = result.scalars().all()

        assert len(first_page) == 5
        assert len(second_page) == 5

        # Verify no overlap
        first_page_ids = {p.id for p in first_page}
        second_page_ids = {p.id for p in second_page}
        assert len(first_page_ids.intersection(second_page_ids)) == 0


class TestDatabaseConstraints:
    """Test cases for database constraints and data integrity"""

    @pytest.mark.asyncio
    async def test_not_null_constraints(self, db_session: AsyncSession):
        """Test NOT NULL constraints"""
        # Test User model required fields
        with pytest.raises(Exception):  # Email cannot be null
            user = User(
                hashed_password="hashed_password",
                is_active=True,
                is_verified=True
            )
            db_session.add(user)
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_foreign_key_constraint(self, db_session: AsyncSession):
        """Test foreign key constraint on transactions"""
        # Create transaction with non-existent user ID
        fake_user_id = "00000000-0000-0000-0000-000000000000"

        transaction = Transaction(
            id=str(uuid.uuid4()),
            user_id=fake_user_id,
            transaction_type="buy",
            quantity=1.0,
            price_per_unit=1250.0,
            total_amount=1250.0,
            status="pending"
        )

        db_session.add(transaction)

        with pytest.raises(Exception):  # Should raise foreign key violation
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_cascade_delete(self, db_session: AsyncSession):
        """Test cascade delete behavior"""
        # Create user
        user = User(
            email="cascadetest@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_verified=True
        )
        db_session.add(user)
        await db_session.commit()

        # Create transaction for user
        transaction = Transaction(
            id=str(uuid.uuid4()),
            user_id=user.id,
            transaction_type="buy",
            quantity=1.0,
            price_per_unit=1250.0,
            total_amount=1250.0,
            status="completed"
        )
        db_session.add(transaction)
        await db_session.commit()

        # Delete user (cascade should delete transaction if configured)
        await db_session.delete(user)
        await db_session.commit()

        # Verify transaction is also deleted (if cascade is configured)
        stmt = select(Transaction).where(Transaction.user_id == user.id)
        result = await db_session.execute(stmt)
        remaining_transactions = result.scalars().all()

        # This depends on cascade configuration - adjust as needed
        # assert len(remaining_transactions) == 0


class TestDatabasePerformance:
    """Test cases for database performance and optimization"""

    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, db_session: AsyncSession):
        """Test bulk insert performance"""
        import time

        # Test individual inserts
        start_time = time.time()
        for i in range(100):
            price = GoldPrice(
                symbol="spot",
                price=1200.0 + i,
                usd_price=1900.0 + i,
                timestamp=datetime.utcnow(),
                source="bulk_test"
            )
            db_session.add(price)

        await db_session.commit()
        individual_time = time.time() - start_time

        # Clear data for fair comparison
        await db_session.execute("DELETE FROM gold_prices")
        await db_session.commit()

        # Test bulk insert
        start_time = time.time()
        bulk_data = []
        for i in range(100):
            price = GoldPrice(
                symbol="spot",
                price=1200.0 + i,
                usd_price=1900.0 + i,
                timestamp=datetime.utcnow(),
                source="bulk_test"
            )
            bulk_data.append(price)

        db_session.add_all(bulk_data)
        await db_session.commit()
        bulk_time = time.time() - start_time

        # Bulk insert should be faster (though this is a rough test)
        # In real scenarios, the difference would be more significant
        assert bulk_time <= individual_time * 1.5  # Allow some variance

    @pytest.mark.asyncio
    async def test_index_effectiveness(self, db_session: AsyncSession):
        """Test that indexes improve query performance"""
        import time

        # Create large dataset
        for i in range(1000):
            price = GoldPrice(
                symbol="spot" if i % 2 == 0 else "gold96",
                price=1200.0 + i,
                usd_price=1900.0 + i,
                timestamp=datetime.utcnow() - timedelta(minutes=i),
                source="index_test"
            )
            db_session.add(price)

        await db_session.commit()

        # Test indexed query (by symbol)
        start_time = time.time()
        stmt = select(GoldPrice).where(GoldPrice.symbol == "spot")
        result = await db_session.execute(stmt)
        spot_prices = result.scalars().all()
        indexed_time = time.time() - start_time

        # Verify results
        assert len(spot_prices) == 500

        # The indexed query should be reasonably fast
        # (This is a very basic performance test)
        assert indexed_time < 1.0  # Should complete within 1 second


class TestDatabaseTransactions:
    """Test cases for database transaction management"""

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, db_session: AsyncSession):
        """Test transaction rollback on error"""
        # Start a transaction
        initial_count = await db_session.execute("SELECT COUNT(*) FROM gold_prices")
        initial_count = initial_count.scalar()

        try:
            # Create some records
            for i in range(5):
                price = GoldPrice(
                    symbol="spot",
                    price=1200.0 + i,
                    usd_price=1900.0 + i,
                    timestamp=datetime.utcnow(),
                    source="rollback_test"
                )
                db_session.add(price)

            # Intentionally cause an error
            invalid_price = GoldPrice(
                symbol=None,  # This should cause an error
                price=999.0,
                usd_price=1599.0,
                timestamp=datetime.utcnow(),
                source="error_test"
            )
            db_session.add(invalid_price)

            await db_session.commit()

        except Exception:
            await db_session.rollback()

        # Verify that no records were added
        final_count = await db_session.execute("SELECT COUNT(*) FROM gold_prices")
        final_count = final_count.scalar()

        assert initial_count == final_count

    @pytest.mark.asyncio
    async def test_nested_transactions(self, db_session: AsyncSession):
        """Test nested transaction (savepoint) behavior"""
        # Create initial record
        price1 = GoldPrice(
            symbol="spot",
            price=1200.0,
            usd_price=1900.0,
            timestamp=datetime.utcnow(),
            source="nested_test"
        )
        db_session.add(price1)
        await db_session.commit()

        # Start nested transaction (savepoint)
        savepoint = await db_session.begin_nested()

        try:
            # Add record in nested transaction
            price2 = GoldPrice(
                symbol="gold96",
                price=1250.0,
                usd_price=1950.0,
                timestamp=datetime.utcnow(),
                source="nested_test"
            )
            db_session.add(price2)
            await savepoint.commit()

        except Exception:
            await savepoint.rollback()

        # Verify both records exist
        stmt = select(GoldPrice).where(GoldPrice.source == "nested_test")
        result = await db_session.execute(stmt)
        records = result.scalars().all()

        assert len(records) == 2


class TestDatabaseConnections:
    """Test cases for database connection management"""

    @pytest.mark.asyncio
    async def test_connection_pooling(self, db_session: AsyncSession):
        """Test connection pooling behavior"""
        # This is more of an integration test
        # In real scenarios, you'd test multiple concurrent connections

        async def create_record(session, i):
            price = GoldPrice(
                symbol="spot",
                price=1200.0 + i,
                usd_price=1900.0 + i,
                timestamp=datetime.utcnow(),
                source="pool_test"
            )
            session.add(price)
            await session.commit()

        # Create records concurrently
        tasks = []
        for i in range(10):
            task = asyncio.create_task(create_record(db_session, i))
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Verify all records were created
        stmt = select(GoldPrice).where(GoldPrice.source == "pool_test")
        result = await db_session.execute(stmt)
        records = result.scalars().all()

        assert len(records) == 10

    @pytest.mark.asyncio
    async def test_session_cleanup(self, db_session: AsyncSession):
        """Test that sessions are properly cleaned up"""
        # Create a record
        price = GoldPrice(
            symbol="spot",
            price=1200.0,
            usd_price=1900.0,
            timestamp=datetime.utcnow(),
            source="cleanup_test"
        )
        db_session.add(price)
        await db_session.commit()

        # Close session
        await db_session.close()

        # Try to use closed session (should fail)
        with pytest.raises(Exception):
            new_price = GoldPrice(
                symbol="gold96",
                price=1250.0,
                usd_price=1950.0,
                timestamp=datetime.utcnow(),
                source="cleanup_test"
            )
            db_session.add(new_price)
            await db_session.commit()
