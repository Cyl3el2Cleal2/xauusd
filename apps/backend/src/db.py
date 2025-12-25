from collections.abc import AsyncGenerator
from datetime import datetime

from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/backend"


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    pass


class GoldPrice(Base):
    """Gold spot price data from investing.com"""
    __tablename__ = "gold_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, default="spot")
    price = Column(Float, nullable=False)
    usd_price = Column(Float, nullable=True)  # Original USD price
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    source = Column(String(100), nullable=True)

    __table_args__ = (
        Index('idx_gold_price_timestamp', 'timestamp'),
        Index('idx_gold_price_symbol', 'symbol'),
    )


class Gold96Price(Base):
    """Gold 96 price data from goldtraders.or.th"""
    __tablename__ = "gold96_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, default="gold96")
    buy_price = Column(Float, nullable=False)
    sell_price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    source = Column(String(100), nullable=True)

    __table_args__ = (
        Index('idx_gold96_price_timestamp', 'timestamp'),
        Index('idx_gold96_price_symbol', 'symbol'),
    )


engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Alias for get_async_session for clarity"""
    async with async_session_maker() as session:
        yield session
