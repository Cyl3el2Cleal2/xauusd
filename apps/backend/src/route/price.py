from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from src.external.ticker import gold_96_price, gold_spot_price

router = APIRouter()

@router.get('/stream/price/{symbol}')
async def stream_price(symbol: str):
    try:
        # Use the synchronous version to avoid event loop issues
        # AsyncGenerator won't work properly with StreamingResponse when using blocking operations
        if symbol == "spot":
            return StreamingResponse(
                gold_spot_price(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )
        if symbol == "gold96":
            return StreamingResponse(
                gold_96_price(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start price stream: {str(e)}")