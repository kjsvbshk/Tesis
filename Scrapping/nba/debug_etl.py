import os
import json
from loguru import logger

# Configure logger to see output
logger.remove()
logger.add(lambda msg: print(msg, end=''), colorize=True, format="{time:HH:mm:ss} | {level} | {message}")

# Test reading boxscores
boxscores_dir = "data/raw/boxscores"
files = [f for f in os.listdir(boxscores_dir) if f.endswith('.json')]

logger.info(f"Total JSON files found: {len(files)}")

# Try to read first 5
boxscores_data = []
for i, filename in enumerate(files[:5]):
    filepath = os.path.join(boxscores_dir, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
        
        # Check if it has required fields
        if game_data.get('game_id') and game_data.get('home_team') and game_data.get('away_team'):
            logger.info(f"✓ {filename}: {game_data.get('away_team')} @ {game_data.get('home_team')}")
            boxscores_data.append(game_data)
        else:
            logger.warning(f"✗ {filename}: Missing required fields")
            
    except Exception as e:
        logger.error(f"Error reading {filename}: {e}")

logger.info(f"\nSuccessfully processed: {len(boxscores_data)}/5")

# Now test the ETL function
logger.info("\n" + "="*60)
logger.info("Testing ETL read_boxscores_data function...")
logger.info("="*60)

from etl.transform_consolidate import read_boxscores_data

result = read_boxscores_data()
if result is not None:
    logger.info(f"✓ ETL read_boxscores_data SUCCESS: {len(result)} games")
    logger.info(f"  Columns: {list(result.columns)}")
    logger.info(f"  Sample:\n{result.head(2)}")
else:
    logger.error("✗ ETL read_boxscores_data FAILED: returned None")
