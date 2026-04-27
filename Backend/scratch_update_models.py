import sys
import os
import json
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

metadata_dir = r"c:\Users\Kjsvb\OneDrive\Documentos\Tesis\Tesis\ML\models\metadata"
versions_to_register = ["v1.6.0", "v2.1.0"]
active_version = "v1.6.0"

try:
    with engine.connect() as conn:
        print("Deactivating all current versions...")
        conn.execute(text("UPDATE app.model_versions SET is_active = false"))
        
        for version in versions_to_register:
            metadata_path = os.path.join(metadata_dir, f"{version}_metadata.json")
            if not os.path.exists(metadata_path):
                print(f"⚠️ Metadata for {version} not found at {metadata_path}, skipping.")
                continue
                
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata_json = json.load(f)
                
            metadata_str = json.dumps(metadata_json)
            is_active = (version == active_version)
            
            print(f"Registering version {version} (Active: {is_active})...")
            
            # Use ON CONFLICT or check if exists to avoid duplicates if ID is serial
            # Assuming we can just insert and they get new IDs, or update if version exists
            existing = conn.execute(
                text("SELECT id FROM app.model_versions WHERE version = :version"),
                {"version": version}
            ).fetchone()
            
            if existing:
                conn.execute(
                    text("UPDATE app.model_versions SET is_active = :is_active, model_metadata = :metadata WHERE version = :version"),
                    {"version": version, "is_active": is_active, "metadata": metadata_str}
                )
            else:
                conn.execute(
                    text("""
                        INSERT INTO app.model_versions (version, is_active, model_metadata)
                        VALUES (:version, :is_active, :metadata)
                    """),
                    {"version": version, "is_active": is_active, "metadata": metadata_str}
                )
        
        conn.commit()
        print("✅ Models registered successfully.")
except Exception as e:
    print(f"❌ Error: {e}")
