# File: backend/database_connector.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

# The database connection string from the .env file.
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set.")

try:
    # Create a SQLAlchemy engine for Oracle using the `oracledb` driver.
    # The `thick_mode=None` uses the Thin driver, which is recommended.
    engine = create_engine(DATABASE_URL, echo=False)
    
    # Verify the connection by trying to connect.
    with engine.connect() as connection:
        print("Successfully connected to the Oracle database.")
        
except SQLAlchemyError as e:
    print(f"Error connecting to the Oracle database: {e}")
    # It's crucial to handle this error appropriately in a real application.
    # For this example, we raise the exception.
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """
    A dependency to provide a database session.
    FastAPI uses this to inject a session into each request,
    and it ensures the session is properly closed afterward.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
