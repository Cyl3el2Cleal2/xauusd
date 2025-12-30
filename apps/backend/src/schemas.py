import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi_users import schemas
from pydantic import BaseModel


class UserRead(schemas.BaseUser[uuid.UUID]):
    money: float


class UserCreate(schemas.BaseUserCreate):
    money: float = 10000.0


class UserUpdate(schemas.BaseUserUpdate):
    money: float = None


# Price data schemas
class GoldPriceBase(BaseModel):
    symbol: str = "spot"
    price: float
    usd_price: float = None
    timestamp: datetime = None
    source: str = None


class GoldPriceCreate(GoldPriceBase):
    pass


class GoldPriceRead(GoldPriceBase):
    id: int

    class Config:
        from_attributes = True


class Gold96PriceBase(BaseModel):
    symbol: str = "gold96"
    buy_price: float
    sell_price: float
    timestamp: datetime = None
    source: str = None


class Gold96PriceCreate(Gold96PriceBase):
    pass


class Gold96PriceRead(Gold96PriceBase):
    id: int

    class Config:
        from_attributes = True


# Trading schemas
class TransactionBase(BaseModel):
    user_id: uuid.UUID
    symbol: str
    transaction_type: str  # "buy" or "sell"
    quantity: float = 0
    price_per_unit: float = 0
    total_amount: float
    status: str = "pending"  # "pending", "processing", "completed", "failed"

class TransactionCreate(TransactionBase):
    pass

class TransactionRead(TransactionBase):
    id: str
    created_at: datetime
    updated_at: datetime
    processing_id: str | None = None  # Redis queue task ID
    poll_url: str | None = None
    error_message: str | None = None

    class Config:
        from_attributes = True

class TransactionStatus(BaseModel):
    transaction_id: str
    status: str
    processing_id: str = None
    error_message: str = None
    updated_at: datetime

class PollingResponse(BaseModel):
    transaction_id: str
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None
