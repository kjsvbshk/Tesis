import sys
import os
from sqlalchemy import create_engine, text

from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv("NEON_DB_HOST") or os.getenv("DB_HOST")
DB_PORT = os.getenv("NEON_DB_PORT", "5432")
DB_NAME = os.getenv("NEON_DB_NAME") or os.getenv("DB_NAME")
DB_USER = os.getenv("NEON_DB_USER") or os.getenv("DB_USER")
DB_PASSWORD = os.getenv("NEON_DB_PASSWORD") or os.getenv("DB_PASSWORD")
DB_SSLMODE = os.getenv("NEON_DB_SSLMODE", "require")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={DB_SSLMODE}"

engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        print("Altering odds_lines table to make provider_id nullable...")
        conn.execute(text("ALTER TABLE app.odds_lines ALTER COLUMN provider_id DROP NOT NULL"))
        conn.commit()
        print("Success!")
except Exception as e:
    print(f"Error: {e}")
