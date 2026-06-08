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

try:
    # Read the metadata file
    metadata_path = r"c:\Users\Kjsvb\OneDrive\Documentos\Tesis\Tesis\ML\models\metadata\v1.1.0_metadata.json"
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata_json = json.load(f)
        
    metadata_str = json.dumps(metadata_json)
    version = metadata_json.get('version', 'v1.1.0')
    
    with engine.connect() as conn:
        print("Deactivating old versions...")
        conn.execute(text("UPDATE app.model_versions SET is_active = false"))
        
        print(f"Registering new version {version}...")
        conn.execute(
            text("""
                INSERT INTO app.model_versions (version, is_active, model_metadata)
                VALUES (:version, true, :metadata)
            """),
            {"version": version, "metadata": metadata_str}
        )
        conn.commit()
        print("Success! Version registered as active.")
except Exception as e:
    print(f"Error: {e}")
