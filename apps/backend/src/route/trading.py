from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, cast
from datetime import datetime
from pydantic import BaseModel
import uuid

from src.db import async_session_maker, Transaction
from src.schemas import (
    TransactionCreate,
    TransactionRead,
    PollingResponse
)
from src.services.trading_service import TradingService
from src.services.redis_queue import enqueue_trading_task, get_trading_task_status, queue_manager
from src.users import current_active_user, User
from sqlalchemy import update

router = APIRouter(prefix="/trading", tags=["trading"])


class NewOrder(BaseModel):
  symbol: str
  amount: float  # Amount in THB - for buy: money to spend, for sell: money to receive

def _convert_transaction_to_read(db_transaction) -> TransactionRead:  # type: ignore
    """Helper function to convert database transaction to TransactionRead"""
    return TransactionRead(
        id=str(cast(str, getattr(db_transaction, 'id'))),
        user_id=uuid.UUID(str(cast(str, getattr(db_transaction, 'user_id')))),
        symbol=str(cast(str, getattr(db_transaction, 'symbol'))),
        transaction_type=str(cast(str, getattr(db_transaction, 'transaction_type'))),
        quantity=float(cast(float, getattr(db_transaction, 'quantity'))),
        price_per_unit=float(cast(float, getattr(db_transaction, 'price_per_unit'))),
        total_amount=float(cast(float, getattr(db_transaction, 'total_amount'))),
        status=str(cast(str, getattr(db_transaction, 'status'))),
        poll_url=cast(str | None, getattr(db_transaction, 'poll_url')),
        processing_id=cast(str | None, getattr(db_transaction, 'processing_id')),
        created_at=cast(datetime, getattr(db_transaction, 'created_at')),
        updated_at=cast(datetime, getattr(db_transaction, 'updated_at')),
        error_message=cast(str | None, getattr(db_transaction, 'error_message'))
    )


@router.post("/buy", response_model=TransactionRead)
async def create_buy_transaction(
    order: NewOrder,
    user: User = Depends(current_active_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> TransactionRead:
    """Create a buy transaction and enqueue for processing"""
    return await _create_transaction("buy", order.symbol, order.amount, user, background_tasks)


@router.post("/sell", response_model=TransactionRead)
async def create_sell_transaction(
    order: NewOrder,
    user: User = Depends(current_active_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> TransactionRead:
    """Create a sell transaction and enqueue for processing"""
    return await _create_transaction("sell", order.symbol, order.amount, user, background_tasks)


async def _create_transaction(
    transaction_type: str,
    symbol: str,
    amount: float,
    user: User,
    background_tasks: BackgroundTasks
) -> TransactionRead:
    """Common transaction creation logic"""
    try:
        async with async_session_maker() as session:
            # Get current price
            current_price_data = await TradingService.get_current_price(session, symbol)
            if not current_price_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"No current price data available for {symbol}"
                )

            # Determine price based on transaction type
            if symbol == "spot":
                price_per_unit = current_price_data["price"]
            elif symbol == "gold96":
                price_per_unit = (
                    current_price_data["buy_price"] if transaction_type == "buy"
                    else current_price_data["sell_price"]
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Symbol must be 'spot' or 'gold96'"
                )

            # Calculate total amount

            # Create transaction data
            transaction_data = TransactionCreate(
                user_id=user.id,
                symbol=symbol,
                transaction_type=transaction_type,
                quantity=0.0,  # Will be calculated during execution
                price_per_unit=price_per_unit,
                total_amount=amount,
                status="pending"
            )

            # Validate transaction data with user ID
            validation_result = await TradingService.validate_transaction_data(session, transaction_data, str(user.id))
            if not validation_result["is_valid"]:
                raise HTTPException(
                    status_code=400,
                    detail={"errors": validation_result["errors"]}
                )

            # Create transaction in database
            db_transaction = await TradingService.create_transaction(
                session,
                transaction_data,
                poll_url=""
            )

            # Create proper poll URL with actual transaction ID
            poll_url = TradingService.create_poll_url(str(db_transaction.id))  # type: ignore
            await TradingService.update_transaction_status(  # type: ignore
                session,
                str(db_transaction.id),
                "pending"
            )
            await TradingService.update_transaction_status(  # type: ignore
                session,
                str(db_transaction.id),
                "processing"
            )

            # Calculate quantity for task data (will be refined during execution)
            if transaction_type == "buy":
                task_quantity = amount / price_per_unit if price_per_unit > 0 else 0.0
            else:
                task_quantity = amount / price_per_unit if price_per_unit > 0 else 0.0  # For sell, also calculate quantity from amount

            # Prepare task data for Redis queue
            task_data = {
                "processing_id": db_transaction.processing_id,
                "transaction_id": db_transaction.id,
                "user_id": str(user.id),
                "symbol": symbol,
                "transaction_type": transaction_type,
                "quantity": task_quantity,
                "price_per_unit": price_per_unit,
                "total_amount": amount,
                "created_at": db_transaction.created_at.isoformat()
            }

            # For buy transactions, deduct balance immediately
            if transaction_type == "buy":
                balance_updated = await TradingService.update_user_balance(  # type: ignore
                    session,
                    str(user.id),
                    -amount
                )
                if not balance_updated:
                    await TradingService.update_transaction_status(  # type: ignore
                        session,
                        str(db_transaction.id),
                        "failed",
                        "Failed to update user balance"
                    )
                    raise HTTPException(
                        status_code=400,
                        detail="Failed to update user balance"
                    )

            # Enqueue task to Redis
            try:
                await enqueue_trading_task(task_data)
            except Exception as e:
                # If Redis fails, update transaction status
                await TradingService.update_transaction_status(  # type: ignore
                    session,
                    str(db_transaction.id),
                    "failed",
                    f"Failed to enqueue task: {str(e)}"
                )
                # For buy transactions, refund the deducted amount
                if transaction_type == "buy":
                    await TradingService.update_user_balance(  # type: ignore
                        session,
                        str(user.id),
                        amount  # Refund
                    )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to enqueue task: {str(e)}"
                )

            # Update transaction with correct poll URL
            await session.execute(
                update(Transaction).where(Transaction.id == db_transaction.id).values(poll_url=poll_url)
            )
            await session.commit()
            await session.refresh(db_transaction)

            # Convert to TransactionRead for response
            return _convert_transaction_to_read(db_transaction)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create transaction: {str(e)}"
        )


async def _handle_off_hours_transaction(user_id: str, transaction_data: TransactionCreate):
    """Handle transactions created outside market hours"""
    # This could implement logic like:
    # - Send notification to user
    # - Queue for when market opens
    # - Different processing logic
    pass


@router.get("/poll/{transaction_id}", response_model=PollingResponse)
async def poll_transaction_status(
    transaction_id: str,
    user: User = Depends(current_active_user)
) -> PollingResponse:
    """Poll for transaction status"""
    try:
        async with async_session_maker() as session:
            # Get transaction from database
            transaction = await TradingService.get_transaction_by_id(session, transaction_id)
            if not transaction:
                raise HTTPException(
                    status_code=404,
                    detail="Transaction not found"
                )

            # Verify user owns this transaction
            if transaction.user_id != str(user.id):
                raise HTTPException(
                    status_code=403,
                    detail="Access denied"
                )

            # Check Redis status for real-time updates
            redis_status = None
            if transaction.processing_id:
                redis_status = await get_trading_task_status(transaction.processing_id)

            # Determine final status
            final_status = transaction.status
            message = "Transaction pending"
            data = None

            if transaction.status == "pending":
                message = "Transaction is pending processing"
            elif transaction.status == "processing":
                message = "Transaction is being processed"
                if redis_status and redis_status.get("status"):
                    final_status = redis_status["status"]
                    if final_status == "completed":
                        message = "Transaction completed successfully"
                        data = redis_status.get("result")
                    elif final_status == "failed":
                        message = "Transaction failed"
                        data = redis_status.get("result")
                    else:
                        message = f"Transaction status: {final_status}"

            elif transaction.status == "completed":
                message = "Transaction completed successfully"
            elif transaction.status == "failed":
                error_msg = transaction.error_message if transaction.error_message else "Unknown error"
                message = f"Transaction failed: {error_msg}"

            return TradingService.create_polling_response(
                transaction,
                message,
                data
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to poll transaction status: {str(e)}"
        )


@router.get("/history", response_model=List[TransactionRead])
async def get_transaction_history(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(current_active_user)
) -> List[TransactionRead]:
    """Get user's transaction history"""
    try:
        async with async_session_maker() as session:
            transactions = await TradingService.get_transactions_by_user(
                session,
                str(user.id),
                limit,
                offset
            )
            # Convert to TransactionRead for response
            return [_convert_transaction_to_read(tx) for tx in transactions]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get transaction history: {str(e)}"
        )


@router.get("/transaction/{transaction_id}", response_model=TransactionRead)
async def get_transaction_details(
    transaction_id: str,
    user: User = Depends(current_active_user)
) -> TransactionRead:
    """Get details of a specific transaction"""
    try:
        async with async_session_maker() as session:
            transaction = await TradingService.get_transaction_by_id(session, transaction_id)
            if not transaction:
                raise HTTPException(
                    status_code=404,
                    detail="Transaction not found"
                )

            # Verify user owns this transaction
            if str(transaction.user_id) != str(user.id):
                raise HTTPException(
                    status_code=403,
                    detail="Access denied"
                )

            # Convert to TransactionRead for response
            return _convert_transaction_to_read(transaction)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get transaction details: {str(e)}"
        )


@router.post("/cancel/{transaction_id}")
async def cancel_transaction(
    transaction_id: str,
    user: User = Depends(current_active_user)
) -> Dict[str, str]:
    """Cancel a pending transaction"""
    try:
        async with async_session_maker() as session:
            transaction = await TradingService.get_transaction_by_id(session, transaction_id)
            if not transaction:
                raise HTTPException(
                    status_code=404,
                    detail="Transaction not found"
                )

            # Verify user owns this transaction
            if str(transaction.user_id) != str(user.id):
                raise HTTPException(
                    status_code=403,
                    detail="Access denied"
                )

            # Can only cancel pending transactions
            if str(cast(str, getattr(transaction, 'status'))) not in ["pending", "processing"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot cancel transaction in '{str(cast(str, getattr(transaction, 'status')))}' status"
                )

            # Update transaction status
            await TradingService.update_transaction_status(  # type: ignore
                session,
                transaction_id,
                "failed",
                "Cancelled by user"
            )

            return {"message": "Transaction cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel transaction: {str(e)}"
        )


@router.get("/queue/health")
async def get_queue_health(user: User = Depends(current_active_user)) -> Dict[str, Any]:
    """Get Redis queue health status"""
    try:
        # Get queue sizes
        trading_queue_size = await queue_manager.get_queue_size("trading_tasks")
        high_priority_queue_size = await queue_manager.get_queue_size("trading_high_priority")

        # Get Redis health
        redis_health = await queue_manager.get_health()

        return {
            "redis": redis_health,
            "queues": {
                "trading": trading_queue_size,
                "high_priority": high_priority_queue_size
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get queue health: {str(e)}"
        )


@router.get("/price/{symbol}")
async def get_current_price(
    symbol: str,
    user: User = Depends(current_active_user)
) -> Dict[str, Any]:
    """Get current price for trading"""
    try:
        if symbol not in ["spot", "gold96"]:
            raise HTTPException(
                status_code=400,
                detail="Symbol must be 'spot' or 'gold96'"
            )

        async with async_session_maker() as session:
            price_data = await TradingService.get_current_price(session, symbol)
            if not price_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No price data available for {symbol}"
                )

            # Add market hours info
            market_open = await TradingService.validate_market_hours()

            return {
                "symbol": symbol,
                "price_data": price_data,
                "market_open": market_open,
                "timestamp": datetime.utcnow().isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get current price: {str(e)}"
        )


@router.get("/balance")
async def get_user_balance(
    user: User = Depends(current_active_user)
) -> Dict[str, Any]:
    """Get user's current balance"""
    try:
        async with async_session_maker() as session:
            balance = await TradingService.get_user_balance(session, str(user.id))  # type: ignore
            if balance is None:
                raise HTTPException(
                    status_code=404,
                    detail="User balance not found"
                )

            return {
                "user_id": str(user.id),
                "balance": balance,
                "currency": "THB",
                "timestamp": datetime.utcnow().isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user balance: {str(e)}"
        )


@router.post("/balance/add")
async def add_balance(
    amount: float,
    user: User = Depends(current_active_user)
) -> Dict[str, str]:
    """Add money to user's balance (admin function)"""
    try:
        if amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Amount must be positive"
            )

        async with async_session_maker() as session:
            success = await TradingService.update_user_balance(session, str(user.id), amount)  # type: ignore
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update balance"
                )

            return {
                "message": f"Successfully added {amount} THB to balance",
                "amount_added": f"{amount}"
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add balance: {str(e)}"
        )


@router.get("/portfolio")
async def get_user_portfolio(
    user: User = Depends(current_active_user)
) -> Dict[str, Any]:
    """Get user's portfolio (balance + holdings)"""
    try:
        async with async_session_maker() as session:
            # Get balance
            balance = await TradingService.get_user_balance(session, str(user.id))  # type: ignore
            if balance is None:
                balance = 0.0

            # Get current prices
            spot_price_data = await TradingService.get_current_price(session, "spot")
            gold96_price_data = await TradingService.get_current_price(session, "gold96")

            # Calculate holdings (mock data - in real implementation, you'd have a Portfolio table)
            holdings = {
                "spot_grams": 0.0,
                "gold96_baht": 0.0
            }

            # Get transaction history to calculate holdings
            transactions = await TradingService.get_transactions_by_user(session, str(user.id), limit=1000)

            for tx in transactions:
                # Skip transactions without valid quantity data
                if not tx.quantity or tx.quantity <= 0:
                    continue

                tx_status = tx.status
                tx_symbol = tx.symbol
                tx_type = tx.transaction_type

                if tx_status == "completed":
                    if tx_symbol == "spot":
                        if tx_type == "buy":
                            holdings["spot_grams"] += float(tx.quantity)
                        else:
                            holdings["spot_grams"] -= float(tx.quantity)
                    elif tx_symbol == "gold96":
                        if tx_type == "buy":
                            holdings["gold96_baht"] += float(tx.quantity)
                        else:
                            holdings["gold96_baht"] -= float(tx.quantity)

            # Calculate current values
            portfolio_value = balance
            if spot_price_data and holdings["spot_grams"] > 0:
                spot_value = holdings["spot_grams"] * float(spot_price_data["price"])
                portfolio_value += spot_value
            else:
                spot_value = 0.0

            if gold96_price_data and holdings["gold96_baht"] > 0:
                gold96_value = holdings["gold96_baht"] * float(gold96_price_data["sell_price"])  # Use sell price for portfolio value
                portfolio_value += gold96_value
            else:
                gold96_value = 0.0

            return {
                "user_id": str(user.id),
                "balance": balance,
                "holdings": holdings,
                "holdings_value": {
                    "spot": spot_value,
                    "gold96": gold96_value
                },
                "total_portfolio_value": portfolio_value,
                "currency": "THB",
                "timestamp": datetime.utcnow().isoformat(),
                "current_prices": {
                    "spot": float(spot_price_data["price"]) if spot_price_data else None,
                    "gold96": {
                        "buy": float(gold96_price_data["buy_price"]) if gold96_price_data else None,
                        "sell": float(gold96_price_data["sell_price"]) if gold96_price_data else None
                    } if gold96_price_data else None
                }
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get portfolio: {str(e)}"
        )
