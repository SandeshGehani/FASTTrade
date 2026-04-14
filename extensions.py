import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import Config
from dotenv import load_dotenv

load_dotenv()

# We use create_engine for synchronous connection since we are keeping sync DB for now.
# pool_pre_ping is enabled in Config for stability.
engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=Config.SQLALCHEMY_ENGINE_OPTIONS.get('pool_pre_ping', True),
    pool_recycle=3600
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
