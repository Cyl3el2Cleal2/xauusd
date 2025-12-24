import asyncio
import json
import random
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI()

# --- Mock Database / State ---
current_price = 150.00
trade_history = []

class Order(BaseModel):
    symbol: str
    quantity: int
    side: str  # "buy" or "sell"

# --- SSE: Real-Time Price Stream ---
async def price_generator():
    """Simulates a stock price moving every second."""
    global current_price
    while True:
        # Simulate market volatility
        change = random.uniform(-0.5, 0.5)
        current_price = round(current_price + change, 2)
        
        # SSE Format: "data: <message>\n\n"
        yield f"data: {json.dumps({'price': current_price, 'time': str(datetime.now())})}\n\n"
        await asyncio.sleep(1)

@app.get("/stream/price")
async def stream_price():
    return StreamingResponse(price_generator(), media_type="text/event-stream")

# --- REST: Trade Strategy & Execution ---
@app.post("/trade")
async def execute_trade(order: Order):
    """Executes a trade based on a simple strategy."""
    # Simple Strategy Check: Only 'Buy' if price is below 151
    if order.side == "buy" and current_price > 151.00:
        raise HTTPException(status_code=400, detail="Strategy rejected: Price too high to buy")

    # Mock Execution
    receipt = {
        "id": random.randint(1000, 9999),
        "executed_price": current_price,
        **order.dict(),
        "status": "filled"
    }
    trade_history.append(receipt)
    return {"message": "Trade successful", "data": receipt}