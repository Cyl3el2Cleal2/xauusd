import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import Transaction
from src.schemas import TransactionCreate, PollingResponse


class TradingService:
    """Unified service for managing trading transactions and validation"""

    # Transaction Management Methods

    @staticmethod
    async def create_transaction(
        session: AsyncSession,
        transaction_data: TransactionCreate,
        poll_url: str
    ) -> Transaction:
        """Create a new transaction and save to database"""
        db_transaction = Transaction(
            id=str(uuid.uuid4()),  # Generate unique transaction ID
            user_id=str(transaction_data.user_id),
            symbol=transaction_data.symbol,
            transaction_type=transaction_data.transaction_type,
            quantity=transaction_data.quantity,
            price_per_unit=transaction_data.price_per_unit,
            total_amount=transaction_data.total_amount,
            status=transaction_data.status,
            poll_url=poll_url,
            processing_id=str(uuid.uuid4()),  # Generate unique processing ID
        )

        session.add(db_transaction)
        await session.commit()
        await session.refresh(db_transaction)
        return db_transaction

    @staticmethod
    async def get_transaction_by_id(
        session: AsyncSession,
        transaction_id: str
    ) -> Optional[Transaction]:
        """Get transaction by ID"""
        stmt = select(Transaction).where(Transaction.id == transaction_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_transactions_by_user(
        session: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Transaction]:
        """Get transactions for a specific user"""
        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(desc(Transaction.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update_transaction_status(
        session: AsyncSession,
        transaction_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[Transaction]:
        """Update transaction status"""
        stmt = (
            update(Transaction)
            .where(Transaction.id == transaction_id)
            .values(
                status=status,
                error_message=error_message,
                updated_at=datetime.utcnow()
            )
        )

        await session.execute(stmt)
        await session.commit()

        # Return updated transaction
        return await TradingService.get_transaction_by_id(session, transaction_id)

    @staticmethod
    async def get_transaction_by_processing_id(
        session: AsyncSession,
        processing_id: str
    ) -> Optional[Transaction]:
        """Get transaction by processing ID (for queue processing)"""
        stmt = select(Transaction).where(Transaction.processing_id == processing_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_pending_transactions(
        session: AsyncSession,
        limit: int = 10
    ) -> List[Transaction]:
        """Get pending transactions for queue processing"""
        stmt = (
            select(Transaction)
            .where(Transaction.status == "pending")
            .order_by(Transaction.created_at)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    def create_poll_url(transaction_id: str) -> str:
        """Generate polling URL for transaction status"""
        return f"/trading/poll/{transaction_id}"

    @staticmethod
    def create_polling_response(
        transaction: Transaction,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> PollingResponse:
        """Create polling response from transaction"""
        # Ensure data is always a dictionary for completed/failed transactions
        response_data = data or {}

        return PollingResponse(
            transaction_id=transaction.id,
            status=transaction.status,
            message=message,
            data=transaction,
            completed_at=transaction.updated_at if transaction.status in ["completed", "failed"] else None
        )

    # Validation Methods

    @staticmethod
    async def validate_transaction_data(
        session: AsyncSession,
        transaction_data: TransactionCreate,
        user_id: str
    ) -> Dict[str, Any]:
        """Validate transaction data and return validation result"""
        errors = []

        # Validate transaction type
        if transaction_data.transaction_type not in ["buy", "sell"]:
            errors.append("Transaction type must be 'buy' or 'sell'")

        # Validate symbol
        if transaction_data.symbol not in ["spot", "gold96"]:
            errors.append("Symbol must be 'spot' or 'gold96'")

        # Check user balance for buy transactions
        if transaction_data.transaction_type == "buy":
            from src.db import User
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                errors.append("User not found")
            elif user.money < transaction_data.total_amount:
                errors.append(f"Insufficient balance: required {transaction_data.total_amount}, available {user.money}")

        # Check if user has enough gold for sell transactions
        if transaction_data.transaction_type == "sell":
            # In a real implementation, you'd check the user's gold portfolio
            # For now, we'll assume they have enough (this would need a Portfolio table)
            pass

        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }

    @staticmethod
    async def update_user_balance(
        session: AsyncSession,
        user_id: str,
        amount: float
    ) -> bool:
        """Update user balance by specified amount (positive for deposit, negative for withdrawal)"""
        from src.db import User

        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return False

        # Check if withdrawal would result in negative balance
        if amount < 0 and user.money + amount < 0:
            return False

        user.money += amount
        await session.commit()
        return True

    @staticmethod
    async def get_user_balance(
        session: AsyncSession,
        user_id: str
    ) -> Optional[float]:
        """Get user's current balance"""
        from src.db import User

        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        return user.money if user else None

    @staticmethod
    async def get_current_price(
        session: AsyncSession,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Get current price for symbol"""
        from src.services.price_service import PriceService

        if symbol == "spot":
            price = await PriceService.get_latest_gold_price(session)
            if price:
                return {
                    "price": price.price,
                    "usd_price": price.usd_price,
                    "timestamp": price.timestamp
                }
        elif symbol == "gold96":
            price = await PriceService.get_latest_gold96_price(session)
            if price:
                return {
                    "buy_price": price.buy_price,
                    "sell_price": price.sell_price,
                    "timestamp": price.timestamp
                }

        return None

    @staticmethod
    async def validate_market_hours() -> bool:
        """Check if market is open (simple implementation)"""
        current_hour = datetime.now().hour
        current_weekday = datetime.now().weekday()

        # Check if it's weekend (5=Saturday, 6=Sunday)
        if current_weekday >= 5:
            return False

        # Check if it's within market hours (9 AM - 5 PM)
        return 9 <= current_hour <= 17
