import json

# Cargar el JSON del schedule
with open('debug_schedule_json.json', encoding='utf-8') as f:
    data = json.load(f)

page_props = data['props']['pageProps']

# Explorar la estructura de modules
game_card_feed = page_props.get('gameCardFeed', {})
modules = game_card_feed.get('modules', [])

print(f"Total modules: {len(modules)}")

# Buscar módulos que contengan juegos
for i, module in enumerate(modules):
    print(f"\n=== Module {i} ===")
    print(f"Keys: {list(module.keys())}")
    
    if 'cards' in module:
        cards = module['cards']
        print(f"Cards: {len(cards)}")
        
        if cards:
            print(f"\nPrimer card keys: {list(cards[0].keys())}")
            
            # Buscar gameId en el card
            if 'cardData' in cards[0]:
                card_data = cards[0]['cardData']
                print(f"\ncardData keys: {list(card_data.keys())}")
                
                if 'gameId' in card_data:
                    print(f"\n✅ Encontrado gameId: {card_data['gameId']}")
                    print(f"\nCard completo:")
                    print(json.dumps(cards[0], indent=2)[:500])
