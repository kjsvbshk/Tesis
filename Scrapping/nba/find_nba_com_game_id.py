"""
Investigar cómo obtener el game_id de NBA.com desde ESPN

Opciones:
1. Scrapear el schedule de NBA.com y hacer match por fecha + equipos
2. Buscar el game_id de NBA.com en la página de ESPN
3. Usar la API de NBA.com para buscar por fecha + equipos
"""

import requests
from bs4 import BeautifulSoup
import json
import re

# Probar con un partido conocido
espn_game_id = "401584089"
espn_url = f"https://www.espn.com/nba/game/_/gameId/{espn_game_id}"

print(f"Buscando game_id de NBA.com en ESPN...")
print(f"URL: {espn_url}\n")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(espn_url, headers=headers)

# Buscar referencias a nba.com en el HTML
nba_com_links = re.findall(r'nba\.com/game/([^"\'>\s]+)', response.text)

if nba_com_links:
    print(f"✅ Enlaces a NBA.com encontrados:")
    for link in set(nba_com_links[:10]):
        print(f"  - {link}")
else:
    print("❌ No se encontraron enlaces a NBA.com")

# Buscar el __NEXT_DATA__ si existe
if '__NEXT_DATA__' in response.text:
    print("\n✅ Encontrado __NEXT_DATA__ en ESPN")
else:
    print("\n❌ No hay __NEXT_DATA__ en ESPN")

# Buscar cualquier ID que parezca de NBA.com (formato 00XXXXX)
nba_ids = re.findall(r'\b(00\d{8})\b', response.text)
if nba_ids:
    print(f"\n✅ Posibles NBA.com game IDs encontrados:")
    for nba_id in set(nba_ids[:10]):
        print(f"  - {nba_id}")
else:
    print("\n❌ No se encontraron IDs con formato NBA.com")

# Guardar HTML para inspección manual
with open('debug_espn_page.html', 'w', encoding='utf-8') as f:
    f.write(response.text)

print(f"\n💾 HTML guardado en: debug_espn_page.html")
