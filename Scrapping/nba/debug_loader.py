from load_data import Config, DataAnalyzer
import json

def debug_analyzer():
    config = Config()
    analyzer = DataAnalyzer(config)
    
    print("🔍 Analyzing data...")
    metadata = analyzer.analyze_all_files()
    
    print("\n📊 Metadata Keys Found:")
    for key in metadata.keys():
        print(f" - {key}")
        
    if 'odds' in metadata:
        print(f"\n🎲 Odds Metadata: {metadata['odds'].get('source_files', [])}")
    else:
        print("\n❌ Odds metadata MISSING")
        
    if 'standings' in metadata:
        print(f"\n🏆 Standings Metadata: {metadata['standings'].get('source_files', [])}")
    else:
        print("\n❌ Standings metadata MISSING")

    if 'team_stats' in metadata:
        print(f"\n📈 Team Stats Metadata found (count: {metadata['team_stats'].get('row_count')})")
        # print specific details if needed
    else:
        print("\n❌ Team Stats metadata MISSING")

if __name__ == "__main__":
    debug_analyzer()
