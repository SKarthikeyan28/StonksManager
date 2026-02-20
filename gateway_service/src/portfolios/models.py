import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # cascade="all, delete-orphan" — deleting a portfolio automatically deletes its stocks
    stocks: Mapped[list["PortfolioStock"]] = relationship(
        "PortfolioStock", back_populates="portfolio", cascade="all, delete-orphan"
    )


class PortfolioStock(Base):
    __tablename__ = "portfolio_stocks"

    # Composite PK — a symbol can only appear once per portfolio
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolios.id"), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="stocks")