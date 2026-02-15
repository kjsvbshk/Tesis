import json

with open('debug_schedule_json.json', encoding='utf-8') as f:
    d = json.load(f)

pp = d['props']['pageProps']
gcf = pp.get('gameCardFeed', {})

print('Keys en gameCardFeed:', list(gcf.keys()))

games = gcf.get('games', [])
print(f'\nTotal games: {len(games)}')

if games:
    print(f'\nPrimer juego keys: {list(games[0].keys())}')
    print(f'\nPrimer juego completo:')
    print(json.dumps(games[0], indent=2))
else:
    print('\nNo games found')
