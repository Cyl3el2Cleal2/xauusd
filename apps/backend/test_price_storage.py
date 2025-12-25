#!/usr/bin/env python3
"""
Test script for price data storage functionality
"""
import asyncio
import json
from datetime import datetime, timedelta

from src.db import create_db_and_tables
from src.schemas import GoldPriceCreate, Gold96PriceCreate
from src.services.price_service import PriceService


async def test_gold_price_storage():
    """Test gold price data storage and retrieval"""
    print("🧪 Testing Gold Price Storage...")

    from src.db import get_async_session

    async with get_async_session() as session:
        # Create test price data
        test_price = GoldPriceCreate(
            symbol="spot",
            price=1250.75,
            usd_price=1985.50,
            timestamp=datetime.utcnow(),
            source="test"
        )

        # Save to database
        saved_price = await PriceService.save_gold_price(session, test_price)
        print(f"✅ Saved gold price: {saved_price.price} (ID: {saved_price.id})")

        # Retrieve latest price
        latest_price = await PriceService.get_latest_gold_price(session)
        print(f"📊 Latest gold price: {latest_price.price} at {latest_price.timestamp}")

        # Get price history
        history = await PriceService.get_gold_price_history(session, hours=1, limit=5)
        print(f"📈 Found {len(history)} historical gold price records")

        # Get statistics
        stats = await PriceService.get_price_statistics(session, "spot", hours=24)
        print(f"📊 Gold price stats: {json.dumps(stats, indent=2)}")


async def test_gold96_price_storage():
    """Test gold 96 price data storage and retrieval"""
    print("\n🧪 Testing Gold 96 Price Storage...")

    from src.db import get_async_session

    async with get_async_session() as session:
        # Create test price data
        test_price = Gold96PriceCreate(
            symbol="gold96",
            buy_price=1250.50,
            sell_price=1270.75,
            timestamp=datetime.utcnow(),
            source="test"
        )

        # Save to database
        saved_price = await PriceService.save_gold96_price(session, test_price)
        print(f"✅ Saved gold 96 price: Buy={saved_price.buy_price}, Sell={saved_price.sell_price} (ID: {saved_price.id})")

        # Retrieve latest price
        latest_price = await PriceService.get_latest_gold96_price(session)
        print(f"📊 Latest gold 96 price: Buy={latest_price.buy_price}, Sell={latest_price.sell_price}")

        # Get price history
        history = await PriceService.get_gold96_price_history(session, hours=1, limit=5)
        print(f"📈 Found {len(history)} historical gold 96 price records")

        # Get statistics
        stats = await PriceService.get_price_statistics(session, "gold96", hours=24)
        print(f"📊 Gold 96 price stats: {json.dumps(stats, indent=2)}")


async def test_price_range_queries():
    """Test price range queries"""
    print("\n🧪 Testing Price Range Queries...")

    from src.db import get_async_session

    async with get_async_session() as session:
        # Create some test data
        now = datetime.utcnow()

        # Create 5 test records with different timestamps
        for i in range(5):
            hours_ago = 24 - (i * 4)  # 24, 20, 16, 12, 8 hours ago
            timestamp = now - timedelta(hours=hours_ago)

            test_price = GoldPriceCreate(
                symbol="spot",
                price=1200.0 + (i * 10),
                usd_price=1900.0 + (i * 10),
                timestamp=timestamp,
                source="test_range"
            )
            await PriceService.save_gold_price(session, test_price)

        # Query prices from last 16 hours
        start_time = now - timedelta(hours=16)
        end_time = now

        prices_in_range = await PriceService.get_gold_prices_in_range(
            session, start_time, end_time
        )
        print(f"📈 Found {len(prices_in_range)} price records in the last 16 hours")

        for price in prices_in_range:
            print(f"   - {price.timestamp}: {price.price}")


async def test_cleanup_functionality():
    """Test cleanup functionality"""
    print("\n🧪 Testing Cleanup Functionality...")

    from src.db import get_async_session

    async with get_async_session() as session:
        # Create old test data (45 days ago)
        old_timestamp = datetime.utcnow() - timedelta(days=45)

        old_price = GoldPriceCreate(
            symbol="spot",
            price=999.99,
            usd_price=1599.99,
            timestamp=old_timestamp,
            source="old_test"
        )
        await PriceService.save_gold_price(session, old_price)

        old_gold96 = Gold96PriceCreate(
            symbol="gold96",
            buy_price=999.50,
            sell_price=1000.50,
            timestamp=old_timestamp,
            source="old_test"
        )
        await PriceService.save_gold96_price(session, old_gold96)

        # Run cleanup for 30 days
        cleanup_result = await PriceService.cleanup_old_prices(session, days_to_keep=30)
        print(f"🧹 Cleanup result: {json.dumps(cleanup_result, indent=2, default=str)}")


async def main():
    """Main test function"""
    print("🚀 Starting Price Storage Tests...")
    print("=" * 50)

    try:
        # Initialize database
        await create_db_and_tables()
        print("✅ Database tables created")

        # Run tests
        await test_gold_price_storage()
        await test_gold96_price_storage()
        await test_price_range_queries()
        await test_cleanup_functionality()

        print("\n" + "=" * 50)
        print("🎉 All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
