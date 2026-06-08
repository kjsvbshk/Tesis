import psycopg2
import json
from datetime import datetime
import pandas as pd
from load_data import Config
from dateutil import parser
import pytz
import sys

# Windows console encoding fix
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def map_and_normalize_odds():
    config = Config()
    conn = None
    try:
        conn = psycopg2.connect(**config.db_config)
        cur = conn.cursor()
        
        print("🚀 Starting Odds Mapping and Normalization...")
        
        # 0. Create Tables if not exist
        print("   🛠️ Checking/Creating normalization tables...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS espn.odds_event_game_map (
                odds_id TEXT PRIMARY KEY,
                game_id BIGINT
            );
            
            CREATE TABLE IF NOT EXISTS espn.game_odds (
                id SERIAL PRIMARY KEY,
                game_id BIGINT,
                odds_type TEXT,
                odds_value NUMERIC,
                line_value NUMERIC,
                provider TEXT,
                UNIQUE(game_id, odds_type, provider, line_value)
            );
        """)
        conn.commit()

        # 1. Fetch ESPN Games (Target)
        print("   📥 Fetching ESPN games...")
        cur.execute("SELECT game_id, fecha, home_team, away_team FROM espn.games")
        espn_games = cur.fetchall()
        print(f"   ✅ Loaded {len(espn_games)} ESPN games.")
        
        # TEAM MAPPING DICTIONARY (Full -> Short)
        TEAM_MAPPING = {
            "atlanta hawks": "hawks",
            "boston celtics": "celtics",
            "brooklyn nets": "nets",
            "charlotte hornets": "hornets",
            "chicago bulls": "bulls",
            "cleveland cavaliers": "cavaliers",
            "dallas mavericks": "mavericks",
            "denver nuggets": "nuggets",
            "detroit pistons": "pistons",
            "golden state warriors": "warriors",
            "houston rockets": "rockets",
            "indiana pacers": "pacers",
            "los angeles clippers": "clippers",
            "la clippers": "clippers",
            "los angeles lakers": "lakers",
            "memphis grizzlies": "grizzlies",
            "miami heat": "heat",
            "milwaukee bucks": "bucks",
            "minnesota timberwolves": "timberwolves",
            "new orleans pelicans": "pelicans",
            "new york knicks": "knicks",
            "oklahoma city thunder": "thunder",
            "orlando magic": "magic",
            "philadelphia 76ers": "76ers",
            "sixers": "76ers",
            "phoenix suns": "suns",
            "portland trail blazers": "trail blazers",
            "sacramento kings": "kings",
            "san antonio spurs": "spurs",
            "toronto raptors": "raptors",
            "utah jazz": "jazz",
            "washington wizards": "wizards"
        }

        def normalize_team(name):
            clean_name = name.lower().strip()
            # Try direct mapping
            if clean_name in TEAM_MAPPING:
                return TEAM_MAPPING[clean_name]
            
            # Try partial mapping (suffix check)
            for full, short in TEAM_MAPPING.items():
                if full in clean_name or clean_name in full:
                     return short
                     
            return clean_name

        # Index games type 1: (date_str, home_norm, away_norm)
        games_map = {}
        # Index games type 2: (date_str, home_norm) -> List of games (for partial matching)
        games_by_date_home = {}
        
        for g in espn_games:
            game_id, fecha, home, away = g
            if not home or not away or not fecha: continue
            
            date_str = fecha.strftime('%Y-%m-%d')
            h_norm = normalize_team(home)
            a_norm = normalize_team(away)
            
            key = (date_str, h_norm, a_norm)
            games_map[key] = game_id
            
            dh_key = (date_str, h_norm)
            if dh_key not in games_by_date_home: games_by_date_home[dh_key] = []
            games_by_date_home[dh_key].append((a_norm, game_id))
            
        # 2. Fetch Raw Odds
        print("   📥 Fetching Raw Odds...")
        cur.execute("SELECT game_id, commence_time, home_team, away_team, bookmakers FROM espn.odds")
        raw_odds = cur.fetchall()
        print(f"   ✅ Loaded {len(raw_odds)} odds records.")
        
        mapped_count = 0
        odds_entries = []

        for row in raw_odds:
            odds_api_id, commence_time_str, home_raw, away_raw, bookmakers = row
            
            # Parse Date
            dt_utc = parser.parse(commence_time_str)
            dt_et = dt_utc.astimezone(pytz.timezone('US/Eastern'))
            game_date_str = dt_et.strftime('%Y-%m-%d')
            
            # Normalize with Mapping
            h_norm = normalize_team(home_raw)
            a_norm = normalize_team(away_raw)
            
            matched_game_id = None
            
            # Attempt 1: Exact Match (Short Name Key)
            # The games_map keys are now (date, short_home, short_away)
            # We need to construct keys using our normalized short names
            
            # Fuzzy date window: check target date, +1 day, -1 day
            from datetime import timedelta
            date_window = [
                game_date_str, 
                (dt_et + timedelta(days=1)).strftime('%Y-%m-%d'),
                (dt_et - timedelta(days=1)).strftime('%Y-%m-%d')
            ]
            
            for d_str in date_window:
                key_exact = (d_str, h_norm, a_norm)
                if key_exact in games_map:
                    matched_game_id = games_map[key_exact]
                    break # Found match
            
            # If still not found, try partial match in window
            if not matched_game_id:
                for d_str in date_window:
                    dh_key = (d_str, h_norm)
                    if dh_key in games_by_date_home:
                        candidates = games_by_date_home[dh_key]
                        for cand_away, cand_id in candidates:
                             if cand_away == a_norm:
                                 matched_game_id = cand_id
                                 break
                    if matched_game_id: break
            
            if matched_game_id:
                # Insert into odds_event_game_map
                try:
                    cur.execute("""
                        INSERT INTO espn.odds_event_game_map (odds_id, game_id)
                        VALUES (%s, %s)
                        ON CONFLICT (odds_id) DO UPDATE SET game_id = EXCLUDED.game_id
                    """, (odds_api_id, matched_game_id))
                    mapped_count += 1
                except Exception as e:
                    print(f"Error inserting map: {e}")

                # Process Bookmakers for Game Odds
                # "bookmakers" is likely a JSON string or dict list.
                # In DB it might be text if created as such, or jsonb.
                # load_data conversion: df['bookmakers'] = df['bookmakers'].apply(json.dumps) -> likely text
                
                b_data = bookmakers
                if isinstance(b_data, str):
                    b_data = json.loads(b_data)
                    
                for bookie in b_data:
                    provider = bookie.get('key', 'unknown')
                    for market in bookie.get('markets', []):
                        m_key = market.get('key')
                        outcomes = market.get('outcomes', [])
                        
                        # Extract logic
                        if m_key == 'h2h':
                            for out in outcomes:
                                name = out.get('name')
                                price = out.get('price')
                                # Identify home/away
                                # We need to match name to home_raw or away_raw
                                o_type = None
                                if name == home_raw: o_type = 'moneyline_home'
                                elif name == away_raw: o_type = 'moneyline_away'
                                
                                if o_type:
                                    odds_entries.append((matched_game_id, o_type, price, None, provider))

                        elif m_key == 'spreads':
                            for out in outcomes:
                                name = out.get('name')
                                price = out.get('price')
                                point = out.get('point')
                                o_type = None
                                if name == home_raw: o_type = 'spread_home'
                                elif name == away_raw: o_type = 'spread_away'
                                
                                if o_type:
                                    odds_entries.append((matched_game_id, o_type, price, point, provider))

                        elif m_key == 'totals':
                             for out in outcomes:
                                name = out.get('name') # Over or Under
                                price = out.get('price')
                                point = out.get('point')
                                o_type = 'over_under'
                                # Store Over/Under? Table schema has 'over_under' as type.
                                # Usually we store the LINE value (point) and maybe price?
                                # Schema: (game_id, odds_type, odds_value, line_value, provider)
                                # For Over/Under, usually the line is the key. 
                                # But we have 2 outcomes: Over and Under prices.
                                # Let's store line_value = point, odds_value = price. 
                                # Wait, odds_type check constraint: 'over_under'.
                                # If I insert 'over_under', does it mean Just the line? 
                                # Or do we separate 'over' and 'under'?
                                # Schema check seems to suggest single 'over_under' line. 
                                # But prices distinct. 
                                # Let's skip detailed O/U price split for now or store line.
                                if name.lower() == 'over':
                                    odds_entries.append((matched_game_id, 'over_under', price, point, provider))
                                # Only storing OVER for line reference for now? 
                                # Or maybe create 'over' and 'under' types? 
                                # Schema constraint limits us. 
                                # Let's use 'over_under' and store the 'Over' price/line, assuming symmetry or just line focus.
                                
            else:
                # Debugging unmatched
                try:
                    with open('unmatched.log', 'a', encoding='utf-8') as log_f:
                        log_f.write(f"⚠️ Unmatched: {game_date_str} | {h_norm} vs {a_norm}\n")
                        
                        # Print games on this date
                        matching_keys = [k for k in games_map.keys() if k[0] == game_date_str]
                        if matching_keys:
                            log_f.write(f"   Games found on {game_date_str}: {matching_keys}\n")
                        else:
                            log_f.write(f"   NO Games found on {game_date_str} in games_map.\n")
                except Exception as e:
                    print(f"Log error: {e}")
                    
                print(f"⚠️ Unmatched: {game_date_str} | {h_norm} vs {a_norm}")

        conn.commit()
        print(f"   ✅ Mapped {mapped_count} games.")
        
        # Batch Insert Game Odds
        print(f"   📥 Inserting {len(odds_entries)} normalized odds records...")
        
        # Prepare batch
        args_str = ','.join(cur.mogrify("(%s, %s, %s, %s, %s)", x).decode('utf-8') for x in odds_entries)
        
        if odds_entries:
            cur.execute(f"""
                INSERT INTO espn.game_odds (game_id, odds_type, odds_value, line_value, provider)
                VALUES {args_str}
                ON CONFLICT DO NOTHING
            """)
            print(f"   ✅ inserted rows from batch.")
        
        conn.commit()
        print("🚀 Done.")

    except Exception as e:
        print(f"❌ Error: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    map_and_normalize_odds()
