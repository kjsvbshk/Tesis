import requests
import json
import re

url = "https://www.nba.com/games?date=2026-02-13"  # Ayer, debería tener juegos

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers)

# Extraer __NEXT_DATA__
match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response.text, re.DOTALL)

if match:
    next_data = json.loads(match.group(1))
    
    # Guardar para inspección
    with open('debug_schedule_json.json', 'w', encoding='utf-8') as f:
        json.dump(next_data, f, indent=2, ensure_ascii=False)
    
    print("✅ JSON guardado en: debug_schedule_json.json")
    
    # Navegar estructura
    props = next_data.get('props', {})
    page_props = props.get('pageProps', {})
    
    print(f"\nKeys en pageProps: {list(page_props.keys())}")
    
    # Buscar donde están los juegos
    for key in page_props.keys():
        if 'game' in key.lower() or 'schedule' in key.lower():
            print(f"\n🎯 Key relacionado a juegos: {key}")
            print(f"Tipo: {type(page_props[key])}")
            if isinstance(page_props[key], list):
                print(f"Longitud: {len(page_props[key])}")
                if page_props[key]:
                    print(f"Primer elemento keys: {list(page_props[key][0].keys()) if isinstance(page_props[key][0], dict) else 'Not a dict'}")
else:
    print("❌ No se encontró __NEXT_DATA__")
