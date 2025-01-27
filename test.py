import pandas as pd
from datetime import datetime, timedelta
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy import text
import logging
from sqlalchemy.exc import SQLAlchemyError


try:
    with engine.connect() as conn:
        conn.execute("SELECT 1")  # Simple query to check connection
    print("Database connection successful!")
except Exception as e:
    print(f"Database connection failed: {e}")
