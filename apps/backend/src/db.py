from collections.abc import AsyncGenerator
from datetime import datetime

from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/backend")


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    money = Column(Float, default=10000.0, nullable=False)  # Starting balance


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


class Transaction(Base):
    """Trading transactions"""
    __tablename__ = "transactions"

    id = Column(String(100), primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)  # UUID as string
    symbol = Column(String(20), nullable=False, index=True)
    transaction_type = Column(String(10), nullable=False)  # "buy" or "sell"
    quantity = Column(Float, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)  # "pending", "processing", "completed", "failed"
    processing_id = Column(String(100), nullable=True, index=True)  # Redis queue task ID
    poll_url = Column(String(500), nullable=True)
    error_message = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_transaction_user', 'user_id'),
        Index('idx_transaction_symbol', 'symbol'),
        Index('idx_transaction_status', 'status'),
        Index('idx_transaction_created', 'created_at'),
        Index('idx_transaction_processing_id', 'processing_id'),
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
