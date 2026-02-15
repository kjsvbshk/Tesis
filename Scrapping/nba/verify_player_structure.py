import json

# Cargar el JSON
with open('debug_next_data_full.json', encoding='utf-8') as f:
    data = json.load(f)

game = data['props']['pageProps']['game']

# Extraer homeTeam players e inactives
home_team = game['homeTeam']
away_team = game['awayTeam']

print(f"Home Team: {home_team['teamName']} ({home_team['teamTricode']})")
print(f"Players: {len(home_team['players'])}")
print(f"Inactives: {len(home_team['inactives'])}")

print(f"\nAway Team: {away_team['teamName']} ({away_team['teamTricode']})")
print(f"Players: {len(away_team['players'])}")
print(f"Inactives: {len(away_team['inactives'])}")

# Mostrar primer jugador activo
if home_team['players']:
    print(f"\n=== Primer jugador HOME (activo) ===")
    player = home_team['players'][0]
    print(f"Keys: {list(player.keys())}")
    print(json.dumps(player, indent=2))

# Mostrar primer jugador inactivo
if home_team['inactives']:
    print(f"\n=== Primer jugador HOME (inactivo) ===")
    inactive = home_team['inactives'][0]
    print(f"Keys: {list(inactive.keys())}")
    print(json.dumps(inactive, indent=2))
