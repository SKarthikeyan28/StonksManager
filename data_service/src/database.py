from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import settings

# Create the SQLAlchemy engine — this is the connection pool to PostgreSQL.
# pool_pre_ping=True makes SQLAlchemy test connections before using them,
# which prevents errors from stale/dropped connections (common in containers).
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# SessionLocal is a factory — calling SessionLocal() gives you a new
# database session (a conversation with the DB). We use this in the worker
# to get a session, do work, then close it.
SessionLocal = sessionmaker(bind=engine)


# DeclarativeBase is SQLAlchemy 2.0's way of saying "all my models inherit
# from this". When we call Base.metadata.create_all(), it creates tables
# for every model class that inherits from Base.
class Base(DeclarativeBase):
    pass
