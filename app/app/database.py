import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite URL; change to your Postgres/MySQL URL if you want
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vivclaims.db")

# For sqlite only: allow multithreaded access
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency: yield a Session, then close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




