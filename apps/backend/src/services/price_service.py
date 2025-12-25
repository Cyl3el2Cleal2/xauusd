from typing import List, Optional
from datetime import datetime, timedelta

from sqlalchemy import select, delete, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import GoldPrice, Gold96Price
from src.schemas import GoldPriceCreate, Gold96PriceCreate


class PriceService:
    """Service for managing price data in database"""

    @staticmethod
    async def save_gold_price(
        session: AsyncSession,
        price_data: GoldPriceCreate
    ) -> GoldPrice:
        """Save gold spot price to database"""
        db_price = GoldPrice(
            symbol=price_data.symbol,
            price=price_data.price,
            usd_price=price_data.usd_price,
            timestamp=price_data.timestamp or datetime.utcnow(),
            source=price_data.source or "investing.com"
        )
        session.add(db_price)
        await session.commit()
        await session.refresh(db_price)
        return db_price

    @staticmethod
    async def save_gold96_price(
        session: AsyncSession,
        price_data: Gold96PriceCreate
    ) -> Gold96Price:
        """Save gold 96 price to database"""
        db_price = Gold96Price(
            symbol=price_data.symbol,
            buy_price=price_data.buy_price,
            sell_price=price_data.sell_price,
            timestamp=price_data.timestamp or datetime.utcnow(),
            source=price_data.source or "goldtraders.or.th"
        )
        session.add(db_price)
        await session.commit()
        await session.refresh(db_price)
        return db_price

    @staticmethod
    async def get_latest_gold_price(
        session: AsyncSession
    ) -> Optional[GoldPrice]:
        """Get latest gold spot price"""
        stmt = select(GoldPrice).order_by(desc(GoldPrice.timestamp)).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_latest_gold96_price(
        session: AsyncSession
    ) -> Optional[Gold96Price]:
        """Get latest gold 96 price"""
        stmt = select(Gold96Price).order_by(desc(Gold96Price.timestamp)).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_gold_price_history(
        session: AsyncSession,
        hours: int = 24,
        limit: int = 100
    ) -> List[GoldPrice]:
        """Get gold price history for specified hours"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(GoldPrice)
            .where(GoldPrice.timestamp >= start_time)
            .order_by(desc(GoldPrice.timestamp))
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_gold96_price_history(
        session: AsyncSession,
        hours: int = 24,
        limit: int = 100
    ) -> List[Gold96Price]:
        """Get gold 96 price history for specified hours"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(Gold96Price)
            .where(Gold96Price.timestamp >= start_time)
            .order_by(desc(Gold96Price.timestamp))
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_gold_prices_in_range(
        session: AsyncSession,
        start_time: datetime,
        end_time: datetime
    ) -> List[GoldPrice]:
        """Get gold prices in specified time range"""
        stmt = (
            select(GoldPrice)
            .where(and_(
                GoldPrice.timestamp >= start_time,
                GoldPrice.timestamp <= end_time
            ))
            .order_by(desc(GoldPrice.timestamp))
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_gold96_prices_in_range(
        session: AsyncSession,
        start_time: datetime,
        end_time: datetime
    ) -> List[Gold96Price]:
        """Get gold 96 prices in specified time range"""
        stmt = (
            select(Gold96Price)
            .where(and_(
                Gold96Price.timestamp >= start_time,
                Gold96Price.timestamp <= end_time
            ))
            .order_by(desc(Gold96Price.timestamp))
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def cleanup_old_prices(
        session: AsyncSession,
        days_to_keep: int = 30
    ) -> dict:
        """Clean up old price data beyond specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        # Delete old gold prices
        gold_stmt = delete(GoldPrice).where(GoldPrice.timestamp < cutoff_date)
        gold_result = await session.execute(gold_stmt)
        gold_deleted = gold_result.rowcount

        # Delete old gold 96 prices
        gold96_stmt = delete(Gold96Price).where(Gold96Price.timestamp < cutoff_date)
        gold96_result = await session.execute(gold96_stmt)
        gold96_deleted = gold96_result.rowcount

        await session.commit()

        return {
            "gold_prices_deleted": gold_deleted,
            "gold96_prices_deleted": gold96_deleted,
            "cutoff_date": cutoff_date
        }

    @staticmethod
    async def get_price_statistics(
        session: AsyncSession,
        symbol: str,
        hours: int = 24
    ) -> dict:
        """Get price statistics for specified period"""
        from sqlalchemy import func

        if symbol == "spot":
            stmt = select(
                func.count(GoldPrice.id).label('count'),
                func.min(GoldPrice.price).label('min_price'),
                func.max(GoldPrice.price).label('max_price'),
                func.avg(GoldPrice.price).label('avg_price')
            ).where(
                GoldPrice.timestamp >= datetime.utcnow() - timedelta(hours=hours)
            )
            result = await session.execute(stmt)
            row = result.first()
            return {
                "symbol": symbol,
                "period_hours": hours,
                "count": row.count,
                "min_price": float(row.min_price) if row.min_price else None,
                "max_price": float(row.max_price) if row.max_price else None,
                "avg_price": float(row.avg_price) if row.avg_price else None
            }

        elif symbol == "gold96":
            stmt = select(
                func.count(Gold96Price.id).label('count'),
                func.min(Gold96Price.buy_price).label('min_buy'),
                func.max(Gold96Price.buy_price).label('max_buy'),
                func.avg(Gold96Price.buy_price).label('avg_buy'),
                func.min(Gold96Price.sell_price).label('min_sell'),
                func.max(Gold96Price.sell_price).label('max_sell'),
                func.avg(Gold96Price.sell_price).label('avg_sell')
            ).where(
                Gold96Price.timestamp >= datetime.utcnow() - timedelta(hours=hours)
            )
            result = await session.execute(stmt)
            row = result.first()
            return {
                "symbol": symbol,
                "period_hours": hours,
                "count": row.count,
                "buy_price": {
                    "min": float(row.min_buy) if row.min_buy else None,
                    "max": float(row.max_buy) if row.max_buy else None,
                    "avg": float(row.avg_buy) if row.avg_buy else None
                },
                "sell_price": {
                    "min": float(row.min_sell) if row.min_sell else None,
                    "max": float(row.max_sell) if row.max_sell else None,
                    "avg": float(row.avg_sell) if row.avg_sell else None
                }
            }

        return {}
