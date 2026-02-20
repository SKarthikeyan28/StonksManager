from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import settings

# engine is the core interface to the database
# created using the DATABASE_URL from settings
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# creates database sessions, used to interact with the DB like reads/writes
# useful in creating concurrent sessions to read DB when multiple API requests come in
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()