import uuid
from datetime import datetime

from fastapi_users import schemas
from pydantic import BaseModel


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


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
