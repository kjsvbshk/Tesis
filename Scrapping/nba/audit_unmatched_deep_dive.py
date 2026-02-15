"""
Auditoría profunda de juegos sin match.
Intenta encontrar el juego en NBA.com usando criterios relajados para entender la causa del fallo.
"""

import json
from tqdm import tqdm
from datetime import datetime, timedelta

def load_data():
    print("Cargando datos...")
    with open('data/nba_com_schedule.json', 'r', encoding='utf-8') as f:
        nba_games = json.load(f)
    
    with open('data/unmatched_espn_games.json', 'r') as f:
        unmatched_ids = json.load(f)
        
    return nba_games, unmatched_ids

def audit_matches():
    nba_games, unmatched_ids = load_data()
    
    # Indexar NBA games por (Home, Away) para búsqueda rápida
    nba_by_teams = {}
    for g in nba_games:
        key = (g['home_tricode'], g['away_tricode'])
        if key not in nba_by_teams:
            nba_by_teams[key] = []
        nba_by_teams[key].append(g)

    TEAM_NAME_TO_TRICODE = {
        'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN', 
        'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE', 
        'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET', 
        'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND', 
        'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM', 
        'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN', 
        'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC', 
        'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX', 
        'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS', 
        'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
    }

    print(f"\nAnalizando {len(unmatched_ids)} juegos sin match...")
    
    causes = {
        'corrupted_file': 0,
        'teams_not_found_together': 0,
        'score_mismatch': 0,
        'multiple_candidates': 0,
        'team_conversion_failed': 0
    }
    
    samples_score_mismatch = []
    
    for espn_id in tqdm(unmatched_ids[:500]): # Analizar muestra de 500
        try:
            with open(f"data/raw/boxscores/{espn_id}.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            home = data.get('home_team')
            away = data.get('away_team')
            home_score = data.get('home_score')
            away_score = data.get('away_score')
            
            if not home or not away:
                causes['corrupted_file'] += 1
                continue
                
            home_tri = TEAM_NAME_TO_TRICODE.get(home)
            away_tri = TEAM_NAME_TO_TRICODE.get(away)
            
            if not home_tri or not away_tri:
                causes['team_conversion_failed'] += 1
                continue
                
            # Buscar candidatos por equipos
            candidates = nba_by_teams.get((home_tri, away_tri), [])
            
            if not candidates:
                causes['teams_not_found_together'] += 1
                continue
            
            # Verificar si alguno coincide por score
            match_score = False
            candidates_with_scores = []
            
            for cand in candidates:
                candidates_with_scores.append(f"{cand['date']} ({cand['away_score']}-{cand['home_score']})")
                if str(cand['home_score']) == str(home_score) and str(cand['away_score']) == str(away_score):
                    match_score = True
                    break
            
            if match_score:
                # Si coincide el score pero está en unmatched, algo raro pasa (quizás duplicado?)
                causes['multiple_candidates'] += 1
            else:
                causes['score_mismatch'] += 1
                if len(samples_score_mismatch) < 10:
                    samples_score_mismatch.append({
                        'espn': f"{away_tri} @ {home_tri} ({away_score}-{home_score})",
                        'candidates': candidates_with_scores
                    })
                    
        except Exception:
            continue

    print("\nResultados del Diagnóstico (Muestra 500):")
    for k, v in causes.items():
        print(f"  {k}: {v}")
        
    print("\nEjemplos de Score Mismatch:")
    for s in samples_score_mismatch:
        print(f"  ESPN: {s['espn']}")
        print(f"  NBA Candidates: {s['candidates']}")
        print("-" * 40)

if __name__ == '__main__':
    audit_matches()
