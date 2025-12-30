import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from src.db import async_session_maker, Transaction
from src.services.trading_service import TradingService
from src.services.redis_queue import queue_manager, TRADING_QUEUE, HIGH_PRIORITY_QUEUE, task_processor

logger = logging.getLogger(__name__)


class TradingTaskProcessor:
    """Background task processor for trading operations"""

    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background task processor"""
        if self.running:
            logger.warning("Task processor is already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._process_tasks())
        logger.info("Trading task processor started")

    async def stop(self):
        """Stop the background task processor"""
        if not self.running:
            return

        self.running = False

        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

        logger.info("Trading task processor stopped")

    async def _process_tasks(self):
        """Main task processing loop"""
        logger.info("Starting task processing loop")

        try:
            # Connect to Redis
            await queue_manager.connect()

            while self.running:
                try:
                    # Process high priority tasks first
                    await self._process_queue(HIGH_PRIORITY_QUEUE, timeout=1)

                    # Process normal tasks
                    await self._process_queue(TRADING_QUEUE, timeout=1)

                    # Small delay to prevent busy waiting
                    await asyncio.sleep(0.1)

                except asyncio.CancelledError:
                    logger.info("Task processor cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in task processing loop: {e}")
                    await asyncio.sleep(1)  # Wait before retrying

        except Exception as e:
            logger.error(f"Fatal error in task processor: {e}")
        finally:
            await queue_manager.disconnect()
            logger.info("Task processing loop ended")

    async def _process_queue(self, queue_name: str, timeout: int = 1):
        """Process tasks from a specific queue"""
        try:
            # Get task from queue
            task_data = await queue_manager.dequeue_task(queue_name, timeout=timeout)
            if not task_data:
                return

            task_id = task_data.get("processing_id")
            transaction_id = task_data.get("transaction_id")

            logger.info(f"Processing task {task_id} for transaction {transaction_id}")

            # Update task status to processing in Redis
            await queue_manager.set_task_status(task_id, "processing")

            # Process the transaction
            try:
                result = await self._process_transaction(task_data)

                # Update task status to completed
                await queue_manager.set_task_status(task_id, "completed", result)

                # Update database transaction status
                await self._update_transaction_status(transaction_id, "completed", None, result)

                logger.info(f"Task {task_id} completed successfully")

            except Exception as e:
                # Update task status to failed
                error_data = {"error": str(e)}
                await queue_manager.set_task_status(task_id, "failed", error_data)

                # Update database transaction status
                await self._update_transaction_status(transaction_id, "failed", str(e))

                logger.error(f"Task {task_id} failed: {e}")

        except Exception as e:
            logger.error(f"Error processing queue {queue_name}: {e}")

    @staticmethod
    async def _process_transaction(task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single transaction"""
        transaction_id = task_data.get("transaction_id")
        symbol = task_data.get("symbol")
        transaction_type = task_data.get("transaction_type")
        original_price_per_unit = task_data.get("price_per_unit")
        total_amount = task_data.get("total_amount")

        # Get current market price at execution time
        async with async_session_maker() as session:
            current_price_data = await TradingService.get_current_price(session, symbol)
            if not current_price_data:
                raise Exception(f"No current price data available for {symbol}")

            # Determine current price based on symbol and transaction type
            if symbol == "spot":
                current_price_per_unit = current_price_data["price"]
            elif symbol == "gold96":
                current_price_per_unit = (
                    current_price_data["buy_price"] if transaction_type == "buy"
                    else current_price_data["sell_price"]
                )
            else:
                raise Exception(f"Invalid symbol: {symbol}")

        # Calculate actual quantity based on current price
        # Both buy and sell should calculate quantity from amount consistently
        actual_quantity = total_amount / current_price_per_unit if current_price_per_unit > 0 else 0.0

        # Simulate processing time (in real implementation, this would:
        # - Check user balance
        # - Execute trade with broker/exchange
        # - Update portfolio
        # - Handle risk management
        # - etc.)
        await asyncio.sleep(0.1)  # Simulate processing delay

        # Calculate actual execution amount
        actual_execution_amount = actual_quantity * current_price_per_unit

        # Mock successful transaction
        result = {
            "transaction_id": transaction_id,
            "executed_price": current_price_per_unit,
            "original_price": original_price_per_unit,
            "executed_quantity": actual_quantity,
            "executed_amount": total_amount,  # Keep original total_amount as requested
            "calculated_amount": actual_execution_amount,  # Actual amount based on current price
            "price_change": current_price_per_unit - original_price_per_unit,
            "balance_adjustment": 0.0,  # Will be calculated for buy transactions
            "executed_at": datetime.utcnow().isoformat(),
            "reference_id": f"TXN{transaction_id}",
            "status": "executed"
        }

        # Handle balance adjustments based on transaction type
        if transaction_type == "buy":
            # For buy transactions, adjust balance based on price difference
            # User was already charged total_amount when order was created
            # Now adjust based on actual execution amount
            balance_difference = total_amount - actual_execution_amount

            if balance_difference > 0:
                # Price went down - refund difference to user
                await TradingService.update_user_balance(
                    async_session_maker(),
                    task_data.get("user_id"),
                    balance_difference  # Refund
                )
                result["balance_adjustment"] = balance_difference
                result["adjustment_type"] = "refund"
            elif balance_difference < 0:
                # Price went up - charge additional amount (this might fail if insufficient balance)
                try:
                    await TradingService.update_user_balance(
                        async_session_maker(),
                        task_data.get("user_id"),
                        balance_difference  # Additional charge (negative value)
                    )
                    result["balance_adjustment"] = balance_difference
                    result["adjustment_type"] = "additional_charge"
                except Exception as e:
                    # If user doesn't have enough balance for additional charge, fail the transaction
                    raise Exception(f"Insufficient balance for price increase. Additional amount needed: {abs(balance_difference)}")
            else:
                # No price change - no adjustment needed
                result["balance_adjustment"] = 0.0
                result["adjustment_type"] = "none"

        elif transaction_type == "sell":
            # For sell transactions, add money to user balance based on current price
            # Note: For sell transactions, user wants to sell quantity calculated from amount
            # The amount they receive is based on actual_quantity * current_price_per_unit
            try:
                await TradingService.update_user_balance(
                    async_session_maker(),
                    task_data.get("user_id"),
                    actual_execution_amount
                )
                result["balance_adjustment"] = actual_execution_amount
                result["adjustment_type"] = "credit"
                result["balance_updated"] = True
            except Exception as e:
                # Log error but don't fail transaction
                import logging
                logging.error(f"Failed to update balance for sell transaction: {e}")
                result["balance_updated"] = False

        return result

    @staticmethod
    async def _update_transaction_status(
        transaction_id: str,
        status: str,
        error_message: Optional[str] = None,
        result_data: Optional[Dict[str, Any]] = None
    ):
        """Update transaction status in database"""
        try:
            async with async_session_maker() as session:
                # Update transaction with actual execution details if successful
                if status == "completed" and result_data:

                    # Update transaction with execution details
                    stmt = (
                        update(Transaction)
                        .where(Transaction.id == transaction_id)
                        .values(
                            status=status,
                            price_per_unit=result_data.get("executed_price"),
                            quantity=result_data.get("executed_quantity"),
                            total_amount=result_data.get("calculated_amount"),  # Update to actual execution amount
                            updated_at=datetime.utcnow()
                        )
                    )
                    await session.execute(stmt)
                    await session.commit()
                else:
                    # Regular status update for failed/pending transactions
                    await TradingService.update_transaction_status(
                        session,
                        transaction_id,
                        status,
                        error_message
                    )

                # If transaction failed, refund money for buy transactions
                if status == "failed":
                    transaction = await TradingService.get_transaction_by_id(session, transaction_id)
                    if transaction and transaction.transaction_type == "buy":
                        # Refund the original total_amount that was deducted when order was created
                        await TradingService.update_user_balance(
                            session,
                            transaction.user_id,
                            transaction.total_amount
                        )
                        logger.info(f"Refunded {transaction.total_amount} to user {transaction.user_id} for failed buy transaction {transaction_id}")

                # Store additional result data if needed
                if result_data:
                    # You could extend the Transaction model to store more details
                    # or create a separate TransactionResult table
                    pass

        except Exception as e:
            logger.error(f"Failed to update transaction {transaction_id} status: {e}")


# Global processor instance
task_processor_instance = TradingTaskProcessor()


# Lifecycle management functions for FastAPI
async def start_task_processor():
    """Start the background task processor"""
    await task_processor_instance.start()


async def stop_task_processor():
    """Stop the background task processor"""
    await task_processor_instance.stop()


def get_processor_status() -> Dict[str, Any]:
    """Get the current status of the task processor"""
    return {
        "running": task_processor_instance.running,
        "task_active": task_processor_instance.task is not None
    }


# Convenience decorators for specific task types
@task_processor("trading_tasks")
async def process_buy_transaction(task_data: Dict[str, Any]):
    """Process buy transaction task"""
    # Add buy-specific logic here
    return await TradingTaskProcessor._process_transaction(task_data)


@task_processor("trading_tasks")
async def process_sell_transaction(task_data: Dict[str, Any]):
    """Process sell transaction task"""
    # Add sell-specific logic here
    return await TradingTaskProcessor._process_transaction(task_data)


@task_processor("trading_high_priority")
async def process_urgent_transaction(task_data: Dict[str, Any]):
    """Process urgent/high priority transaction"""
    # Add urgent transaction logic here
    # For example: market orders, large trades, etc.
    return await TradingTaskProcessor._process_transaction(task_data)


# Manual task processing for testing/admin
async def process_single_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Manually process a single task by ID"""
    try:
        # Get task status from Redis
        task_status = await queue_manager.get_task_status(task_id)
        if not task_status:
            return {"error": "Task not found"}

        # Get transaction from database
        async with async_session_maker() as session:
            transaction = await TradingService.get_transaction_by_id(session, task_status.get("transaction_id"))
            if not transaction:
                return {"error": "Transaction not found"}

            # Prepare task data
            task_data = {
                "processing_id": task_id,
                "transaction_id": transaction.id,
                "user_id": transaction.user_id,
                "symbol": transaction.symbol,
                "transaction_type": transaction.transaction_type,
                "quantity": transaction.quantity,
                "price_per_unit": transaction.price_per_unit,
                "total_amount": transaction.total_amount,
                "created_at": transaction.created_at.isoformat()
            }

            # Process the task
            result = await TradingTaskProcessor._process_transaction(task_data)

            # Update status
            await queue_manager.set_task_status(task_id, "completed", result)
            await TradingService.update_transaction_status(session, transaction.id, "completed", None, result)

            return result

    except Exception as e:
        # Update status to failed
        await queue_manager.set_task_status(task_id, "failed", {"error": str(e)})
        return {"error": str(e)}


# Health check
async def get_task_processor_health() -> Dict[str, Any]:
    """Get comprehensive health status of the task processor"""
    try:
        # Get queue sizes
        trading_queue_size = await queue_manager.get_queue_size(TRADING_QUEUE)
        high_priority_queue_size = await queue_manager.get_queue_size(HIGH_PRIORITY_QUEUE)

        # Get Redis health
        redis_health = await queue_manager.get_health()

        # Get processor status
        processor_status = get_processor_status()

        return {
            "processor": processor_status,
            "redis": redis_health,
            "queues": {
                "trading": trading_queue_size,
                "high_priority": high_priority_queue_size
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        return {
            "processor": {"running": False, "error": str(e)},
            "redis": {"connected": False, "error": str(e)},
            "queues": {"trading": {"total": 0}, "high_priority": {"total": 0}},
            "timestamp": datetime.utcnow().isoformat()
        }
