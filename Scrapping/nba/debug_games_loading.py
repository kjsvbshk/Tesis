from load_data import DataLoader, Config
import pandas as pd
import traceback

def debug_load():
    config = Config()
    # Initialize analyzer first to get metadata
    from load_data import DataAnalyzer
    analyzer = DataAnalyzer(config)
    metadata = analyzer.analyze_all_files()
    
    loader = DataLoader(config, metadata)
    
    print("🕵️ Debugging Games Loading...")
    
    # Metadata already has games if analyze_all_files worked
    if 'games' not in metadata:
        print("❌ Metadata for 'games' not found! Make sure _analyze_processed_dataset is uncommented in load_data.py")
        return
        
    meta = metadata['games']
    print(f"✅ Metadata found: {meta['row_count']} rows, Source: {meta['source_file']}")
    
    # Generate DDL using DDLGenerator
    print("\n🛠️ Generating DDL...")
    from load_data import DDLGenerator
    # Create a subset metadata dict with ONLY games
    games_meta = {'games': meta}
    ddl_gen = DDLGenerator(games_meta, [], config.schema)
    statements = ddl_gen.generate_ddl()
    
    # Execute DDL
    print("🏗️ Executing DDL...")
    try:
        loader.connect()
        loader.execute_ddl(statements)
        print("✅ DDL Executed.")
    except Exception as e:
        print(f"❌ DDL Failed: {e}")
        return

    # Try loading data
    print("\n⬇️ Loading Data...")
    try:
        # Re-read DF to pass to copy
        df = pd.read_csv(meta['source_file'])
        
        # Deduplicate by game_id
        print(f"   Rows before dedup: {len(df)}")
        df = df.drop_duplicates(subset=['game_id'], keep='first')
        print(f"   Rows after dedup: {len(df)}")
        
        loader._copy_from_dataframe('games', df, meta['columns'])
        print("✅ Data Loaded.")
    except Exception as e:
        print(f"❌ Load Failed: {e}")
        traceback.print_exc()
    finally:
        loader.disconnect()

if __name__ == "__main__":
    debug_load()
