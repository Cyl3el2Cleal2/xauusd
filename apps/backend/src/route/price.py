from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import weakref
import logging


from src.external.ticker import (
    gold_spot_price_stream,
    gold_96_price_stream,
    stream_with_retry,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Connection management
active_connections: dict[str, weakref.ref] = {}
connection_lock = asyncio.Lock()

def current_time_ms() -> int:
    """Get current timestamp in milliseconds"""
    return int(asyncio.get_event_loop().time() * 1000)

@router.get('/stream/price/{symbol}')
async def stream_price(symbol: str):
    """
    Stream price data using optimized SSE
    Supports 'spot' and 'gold96' symbols
    """

    # Validate symbol
    if symbol not in ["spot", "gold96"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported symbol '{symbol}'. Supported symbols: spot, gold96"
        )

    # Generate unique client ID for this connection
    client_id = f"{symbol}_{current_time_ms()}"

    # Select appropriate stream function
    if symbol == "spot":
        stream_function = gold_spot_price_stream
    else:  # gold96
        stream_function = gold_96_price_stream

    # Create response with optimized headers
    response = StreamingResponse(
        stream_with_retry(stream_function, symbol, client_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",  # CORS for SSE
            "Access-Control-Allow-Headers": "Cache-Control",
        }
    )

    # Set up cleanup on disconnect
    async def cleanup_on_disconnect():
        try:
            async with connection_lock:
                active_connections[client_id] = weakref.ref(lambda: None)
            yield
        finally:
            # Cleanup will be handled by the ticker module
            async with connection_lock:
                if client_id in active_connections:
                    del active_connections[client_id]
            logger.info(f"Cleaned up connection for client {client_id}")

    response.background = cleanup_on_disconnect()

    return response