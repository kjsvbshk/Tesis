import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.config import db_config
import pandas as pd

def detailed_verification():
    engine = create_engine(db_config.get_database_url())
    with engine.connect() as conn:
        conn.execute(text("SET search_path TO ml, public"))
        
        print("🔍 Querying ml.ml_ready_games for detailed status...")
        df = pd.read_sql("SELECT * FROM ml.ml_ready_games", engine)
        
        total = len(df)
        print(f"\n📊 Total records: {total}")
        
        # Check fill rates for new features
        new_features = [
            'home_ppg_last5', 'away_ppg_last5', 'ppg_diff',
            'home_net_rating_last10', 'away_net_rating_last10', 'net_rating_diff_rolling',
            'home_pace_rolling', 'away_pace_rolling', 'pace_diff',
            'home_off_rating_rolling', 'away_off_rating_rolling', 'off_rating_diff',
            'home_def_rating_rolling', 'away_def_rating_rolling', 'def_rating_diff',
            'home_rest_days', 'away_rest_days', 'rest_days_diff',
            'home_b2b', 'away_b2b'
        ]
        
        print("\n📈 Fill Rates and Stats for New Features:")
        print(f"{'Feature':<30} | {'Fill %':<8} | {'Mean':<8} | {'Min':<8} | {'Max':<8}")
        print("-" * 75)
        
        for feat in new_features:
            if feat in df.columns:
                count = df[feat].count()
                fill_pct = 100 * count / total
                if df[feat].dtype in ['float64', 'int64', 'Int64']:
                    mean_val = df[feat].mean()
                    min_val = df[feat].min()
                    max_val = df[feat].max()
                    print(f"{feat:<30} | {fill_pct:>7.1f}% | {mean_val:>8.2f} | {min_val:>8.2f} | {max_val:>8.2f}")
                else:
                    print(f"{feat:<30} | {fill_pct:>7.1f}% | {'N/A':<8} | {'N/A':<8} | {'N/A':<8}")
            else:
                print(f"{feat:<30} | MISSING!")

        print("\n🏆 Sample Differentials (Latest 5 Games):")
        sample = df.sort_values('fecha', ascending=False).head(5)
        for _, r in sample.iterrows():
            print(f"Game {r['game_id']} ({r['fecha']}): {r['home_team']} vs {r['away_team']}")
            print(f"   PPG Diff: {r['ppg_diff']:.2f}, NetRtg Diff: {r['net_rating_diff_rolling']:.2f}")
            print(f"   Pace Diff: {r['pace_diff']:.2f}, OffRtg Diff: {r['off_rating_diff']:.2f}, DefRtg Diff: {r['def_rating_diff']:.2f}")

if __name__ == "__main__":
    detailed_verification()
