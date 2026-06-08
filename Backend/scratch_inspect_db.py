import sys
import os
from sqlalchemy import create_engine, inspect

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
inspector = inspect(engine)

tables_to_check = [
    'requests',
    'predictions',
    'odds_snapshots',
    'odds_lines',
    'outbox',
    'audit_log'
]

print("Database columns inspection:")
for table in tables_to_check:
    print(f"\n--- {table} ---")
    try:
        columns = inspector.get_columns(table, schema='app')
        for c in columns:
            print(f"- {c['name']} ({c['type']})")
    except Exception as e:
        print(f"Error checking {table}: {e}")
