from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import json
import time
from src.db import async_session_maker
from src.services.price_service import PriceService
from src.users import current_active_user, User

router = APIRouter()

# SSE Endpoints - Efficient real-time data from database
async def create_sse_data(data: dict) -> str:
    """Create properly formatted SSE data"""
    return f"data: {json.dumps(data)}\n\n"

async def price_sse_generator(symbol: str):
    """Generate SSE data from database for given symbol"""
    last_spot_price = None
    last_gold96_price = None

    while True:
        try:
            async with async_session_maker() as session:
                current_time = time.time()

                # Get latest prices
                if symbol in ["spot"]:
                    spot_price = await PriceService.get_latest_gold_price(session)
                    if spot_price and spot_price.timestamp:
                        spot_data = {
                            "symbol": spot_price.symbol,
                            "price": spot_price.price,
                            "usd_price": spot_price.usd_price,
                            "timestamp": spot_price.timestamp.isoformat(),
                            "source": spot_price.source,
                            "type": "price_update"
                        }

                        # Only send if price is new or different
                        if (not last_spot_price or
                            spot_price.timestamp != last_spot_price.get('timestamp') or
                            spot_price.price != last_spot_price.get('price')):
                            yield await create_sse_data(spot_data)
                            last_spot_price = {
                                'timestamp': spot_price.timestamp,
                                'price': spot_price.price
                            }

                if symbol in ["gold96"]:
                    gold96_price = await PriceService.get_latest_gold96_price(session)
                    if gold96_price and gold96_price.timestamp:
                        gold96_data = {
                            "symbol": gold96_price.symbol,
                            "buy_price": gold96_price.buy_price,
                            "sell_price": gold96_price.sell_price,
                            "timestamp": gold96_price.timestamp.isoformat(),
                            "source": gold96_price.source,
                            "type": "price_update"
                        }

                        # Only send if price is new or different
                        if (not last_gold96_price or
                            gold96_price.timestamp != last_gold96_price.get('timestamp') or
                            gold96_price.buy_price != last_gold96_price.get('buy_price') or
                            gold96_price.sell_price != last_gold96_price.get('sell_price')):
                            yield await create_sse_data(gold96_data)
                            last_gold96_price = {
                                'timestamp': gold96_price.timestamp,
                                'buy_price': gold96_price.buy_price,
                                'sell_price': gold96_price.sell_price
                            }

                # Send heartbeat every 30 seconds
                if int(current_time) % 30 == 0:
                    heartbeat = {
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat(),
                        "symbols": symbol
                    }
                    yield await create_sse_data(heartbeat)

                # Check every 5 seconds for new data
                await asyncio.sleep(5)

        except Exception as e:
            error_data = {
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat(),
                "type": "error"
            }
            yield await create_sse_data(error_data)
            await asyncio.sleep(10)  # Wait before retrying

@router.get('/stream/price/{symbol}')
async def stream_price(symbol: str):
    """
    Stream price data using SSE from database
    Supports 'spot', 'gold96', and 'all' symbols
    """

    # Validate symbol
    if symbol not in ["spot", "gold96"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported symbol '{symbol}'. Supported symbols: spot, gold96, all"
        )

    # Create SSE response
    return StreamingResponse(
        price_sse_generator(symbol),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",  # CORS for SSE
            "Access-Control-Allow-Headers": "Cache-Control",
        }
    )
