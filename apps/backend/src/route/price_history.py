from typing import List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_async_session
from src.services.price_service import PriceService
from src.schemas import GoldPriceRead, Gold96PriceRead

router = APIRouter()

@router.get("/gold/latest", response_model=GoldPriceRead)
async def get_latest_gold_price(
    session: AsyncSession = Depends(get_async_session)
):
    """Get the latest gold spot price"""
    try:
        latest_price = await PriceService.get_latest_gold_price(session)
        if not latest_price:
            raise HTTPException(status_code=404, detail="No gold price data found")
        return latest_price
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching latest gold price: {str(e)}")

@router.get("/gold96/latest", response_model=Gold96PriceRead)
async def get_latest_gold96_price(
    session: AsyncSession = Depends(get_async_session)
):
    """Get the latest gold 96 price"""
    try:
        latest_price = await PriceService.get_latest_gold96_price(session)
        if not latest_price:
            raise HTTPException(status_code=404, detail="No gold 96 price data found")
        return latest_price
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching latest gold 96 price: {str(e)}")

@router.get("/gold/history", response_model=List[GoldPriceRead])
async def get_gold_price_history(
    hours: int = Query(24, ge=1, le=168, description="Hours of history to retrieve (1-168)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get gold price history"""
    try:
        history = await PriceService.get_gold_price_history(session, hours, limit)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching gold price history: {str(e)}")

@router.get("/gold96/history", response_model=List[Gold96PriceRead])
async def get_gold96_price_history(
    hours: int = Query(24, ge=1, le=168, description="Hours of history to retrieve (1-168)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get gold 96 price history"""
    try:
        history = await PriceService.get_gold96_price_history(session, hours, limit)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching gold 96 price history: {str(e)}")

@router.get("/gold/range", response_model=List[GoldPriceRead])
async def get_gold_price_range(
    start_time: datetime = Query(..., description="Start time in ISO format"),
    end_time: datetime = Query(..., description="End time in ISO format"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get gold prices in specified time range"""
    try:
        if end_time <= start_time:
            raise HTTPException(status_code=400, detail="End time must be after start time")

        if (end_time - start_time) > timedelta(days=30):
            raise HTTPException(status_code=400, detail="Time range cannot exceed 30 days")

        prices = await PriceService.get_gold_prices_in_range(session, start_time, end_time)
        return prices
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching gold price range: {str(e)}")

@router.get("/gold96/range", response_model=List[Gold96PriceRead])
async def get_gold96_price_range(
    start_time: datetime = Query(..., description="Start time in ISO format"),
    end_time: datetime = Query(..., description="End time in ISO format"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get gold 96 prices in specified time range"""
    try:
        if end_time <= start_time:
            raise HTTPException(status_code=400, detail="End time must be after start time")

        if (end_time - start_time) > timedelta(days=30):
            raise HTTPException(status_code=400, detail="Time range cannot exceed 30 days")

        prices = await PriceService.get_gold96_prices_in_range(session, start_time, end_time)
        return prices
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching gold 96 price range: {str(e)}")

@router.get("/gold/statistics")
async def get_gold_price_statistics(
    hours: int = Query(24, ge=1, le=168, description="Hours for statistics (1-168)"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get gold price statistics"""
    try:
        stats = await PriceService.get_price_statistics(session, "spot", hours)
        if not stats:
            raise HTTPException(status_code=404, detail="No gold price data for statistics")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching gold price statistics: {str(e)}")

@router.get("/gold96/statistics")
async def get_gold96_price_statistics(
    hours: int = Query(24, ge=1, le=168, description="Hours for statistics (1-168)"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get gold 96 price statistics"""
    try:
        stats = await PriceService.get_price_statistics(session, "gold96", hours)
        if not stats:
            raise HTTPException(status_code=404, detail="No gold 96 price data for statistics")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching gold 96 price statistics: {str(e)}")

@router.delete("/cleanup")
async def cleanup_old_prices(
    days_to_keep: int = Query(30, ge=1, le=365, description="Days of data to keep (1-365)"),
    session: AsyncSession = Depends(get_async_session)
):
    """Clean up old price data"""
    try:
        result = await PriceService.cleanup_old_prices(session, days_to_keep)
        return {
            "message": "Cleanup completed successfully",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during cleanup: {str(e)}")
