import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")


# Only set this for SQLite; on Postgres, leave it empty
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

