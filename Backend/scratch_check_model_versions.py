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
        print("Model Versions in DB:")
        result = conn.execute(text("SELECT id, version, is_active FROM app.model_versions")).fetchall()
        for r in result:
            print(f"ID: {r[0]}, Version: {r[1]}, Active: {r[2]}")
            
        print("\nChecking metadata structure for active version:")
        result = conn.execute(text("SELECT model_metadata FROM app.model_versions WHERE is_active=true")).fetchone()
        if result and result[0]:
            print(str(result[0])[:500])
except Exception as e:
    print(f"Error: {e}")
