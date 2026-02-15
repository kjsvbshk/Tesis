"""
Debug script para inspeccionar la estructura de __NEXT_DATA__ de NBA.com
"""

import requests
import json
import re

url = "https://www.nba.com/game/chi-vs-bos-0022500778/box-score"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers)

# Extraer __NEXT_DATA__
match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response.text, re.DOTALL)

if match:
    next_data = json.loads(match.group(1))
    
    # Guardar JSON completo para inspección
    with open('debug_next_data_full.json', 'w', encoding='utf-8') as f:
        json.dump(next_data, f, indent=2, ensure_ascii=False)
    
    print("✅ JSON completo guardado en: debug_next_data_full.json")
    
    # Navegar estructura
    print("\n=== Estructura de __NEXT_DATA__ ===")
    print(f"Keys principales: {list(next_data.keys())}")
    
    if 'props' in next_data:
        props = next_data['props']
        print(f"\nKeys en props: {list(props.keys())}")
        
        if 'pageProps' in props:
            page_props = props['pageProps']
            print(f"\nKeys en pageProps: {list(page_props.keys())}")
            
            # Buscar donde están los datos del juego
            for key in page_props.keys():
                if 'game' in key.lower():
                    print(f"\n🎯 Encontrado: {key}")
                    print(f"Tipo: {type(page_props[key])}")
                    if isinstance(page_props[key], dict):
                        print(f"Keys: {list(page_props[key].keys())[:20]}")  # Primeras 20 keys
else:
    print("❌ No se encontró __NEXT_DATA__")
