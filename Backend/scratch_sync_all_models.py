import sys
import os
import json
import re
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
active_version = "v1.6.0"

try:
    with engine.connect() as conn:
        print("Synchronizing all available model versions...")
        
        # Get all metadata files
        files = [f for f in os.listdir(metadata_dir) if f.endswith('_metadata.json')]
        
        for filename in files:
            # Extract version (e.g., v1.6.0 from v1.6.0_metadata.json)
            version = filename.replace('_metadata.json', '')
            metadata_path = os.path.join(metadata_dir, filename)
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata_json = json.load(f)
            
            metadata_str = json.dumps(metadata_json)
            is_active = (version == active_version)
            
            print(f"Syncing version {version}...")
            
            existing = conn.execute(
                text("SELECT id FROM app.model_versions WHERE version = :version"),
                {"version": version}
            ).fetchone()
            
            if existing:
                conn.execute(
                    text("UPDATE app.model_versions SET model_metadata = :metadata WHERE version = :version"),
                    {"version": version, "metadata": metadata_str}
                )
                # Only set active if it's the requested active version
                if is_active:
                    conn.execute(text("UPDATE app.model_versions SET is_active = false"))
                    conn.execute(
                        text("UPDATE app.model_versions SET is_active = true WHERE version = :version"),
                        {"version": version}
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
        print("✅ All available versions synchronized successfully.")
except Exception as e:
    print(f"❌ Error during synchronization: {e}")
