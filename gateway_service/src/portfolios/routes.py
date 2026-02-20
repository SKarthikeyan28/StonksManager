from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.auth.jwt import get_current_user_id
from src.database import get_db
from src.portfolios.models import Portfolio, PortfolioStock

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


# --- Schemas ---

class CreatePortfolioRequest(BaseModel):
    name: str


class AddStockRequest(BaseModel):
    symbol: str


# --- Routes ---

@router.get("")
def list_portfolios(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    portfolios = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
    return [{"id": p.id, "name": p.name, "stocks": [s.symbol for s in p.stocks]} for p in portfolios]


@router.post("", status_code=201)
def create_portfolio(body: CreatePortfolioRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    portfolio = Portfolio(user_id=user_id, name=body.name)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return {"id": portfolio.id, "name": portfolio.name, "stocks": []}


@router.delete("/{portfolio_id}", status_code=204)
def delete_portfolio(portfolio_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    db.delete(portfolio)
    db.commit()


@router.post("/{portfolio_id}/stocks", status_code=201)
def add_stock(portfolio_id: str, body: AddStockRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if any(s.symbol == body.symbol.upper() for s in portfolio.stocks):
        raise HTTPException(status_code=400, detail="Stock already in portfolio")
    db.add(PortfolioStock(portfolio_id=portfolio_id, symbol=body.symbol.upper()))
    db.commit()
    return {"portfolio_id": portfolio_id, "symbol": body.symbol.upper()}


@router.delete("/{portfolio_id}/stocks/{symbol}", status_code=204)
def remove_stock(portfolio_id: str, symbol: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    stock = db.query(PortfolioStock).filter(
        PortfolioStock.portfolio_id == portfolio_id,
        PortfolioStock.symbol == symbol.upper()
    ).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found in portfolio")
    db.delete(stock)
    db.commit()