import json

# Cargar el JSON de __NEXT_DATA__
with open('debug_next_data_full.json', encoding='utf-8') as f:
    data = json.load(f)

game = data['props']['pageProps']['game']

# Verificar qué keys existen
print("Keys en game:", list(game.keys()))

# Buscar inactives
if 'inactives' in game:
    inactives = game['inactives']
    print(f"\n✅ Encontrado 'inactives': {len(inactives)} jugadores")
    if inactives:
        print(f"\nPrimer inactive:")
        print(json.dumps(inactives[0], indent=2))
else:
    print("\n❌ No hay key 'inactives'")

# Buscar players
if 'players' in game:
    players = game['players']
    print(f"\n✅ Encontrado 'players': {len(players)} jugadores")
    if players:
        print(f"\nPrimer player:")
        print(json.dumps(players[0], indent=2))
else:
    print("\n❌ No hay key 'players'")

# Buscar homeTeam/awayTeam
if 'homeTeam' in game:
    print(f"\n✅ Encontrado 'homeTeam'")
    print(f"Keys en homeTeam: {list(game['homeTeam'].keys())}")
    
if 'awayTeam' in game:
    print(f"\n✅ Encontrado 'awayTeam'")
    print(f"Keys en awayTeam: {list(game['awayTeam'].keys())}")
