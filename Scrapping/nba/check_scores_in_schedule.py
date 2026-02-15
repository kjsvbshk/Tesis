import json

# Cargar el JSON de debug del schedule que ya teníamos
try:
    with open('debug_schedule_json.json', encoding='utf-8') as f:
        data = json.load(f)

    page_props = data['props']['pageProps']
    modules = page_props.get('gameCardFeed', {}).get('modules', [])

    print("Buscando scores en la estructura del schedule...")

    for module in modules:
        cards = module.get('cards', [])
        for card in cards:
            card_data = card.get('cardData', {})
            home_team = card_data.get('homeTeam', {})
            away_team = card_data.get('awayTeam', {})
            
            print(f"\nJuego: {away_team.get('teamTricode')} @ {home_team.get('teamTricode')}")
            print(f"  Home Score Key: {home_team.get('score')}")
            print(f"  Away Score Key: {away_team.get('score')}")
            print(f"  Keys en homeTeam: {list(home_team.keys())}")
            
except Exception as e:
    print(f"Error: {e}")
