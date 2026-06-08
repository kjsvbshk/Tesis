import sys
import os
from sqlalchemy import create_engine, inspect, text

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

with engine.connect() as conn:
    print("Providers:")
    result = conn.execute(text("SELECT id, name, code FROM app.providers")).fetchall()
    for r in result:
        print(r)
    
    print("\nOddsLines schema:")
    result = conn.execute(text("SELECT column_name, is_nullable FROM information_schema.columns WHERE table_schema='app' AND table_name='odds_lines' AND column_name='provider_id'")).fetchall()
    for r in result:
        print(r)
