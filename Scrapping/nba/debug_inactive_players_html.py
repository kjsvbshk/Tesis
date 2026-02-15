"""
Script para verificar la estructura HTML de jugadores inactivos en NBA.com
"""

import requests
from bs4 import BeautifulSoup

url = "https://www.nba.com/game/chi-vs-bos-0022500778/box-score"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'lxml')

# Buscar sección de INACTIVE PLAYERS
print("=== Buscando INACTIVE PLAYERS ===\n")

# Método 1: Buscar por texto "INACTIVE PLAYERS"
inactive_sections = soup.find_all(string=lambda text: text and 'INACTIVE PLAYERS' in text.upper())
print(f"Encontradas {len(inactive_sections)} secciones con 'INACTIVE PLAYERS'")

for i, section in enumerate(inactive_sections):
    print(f"\n--- Sección {i+1} ---")
    print(f"Texto: {section[:200]}")
    print(f"Parent tag: {section.parent.name}")
    print(f"Parent class: {section.parent.get('class', [])}")
    
    # Buscar el contenedor padre
    parent = section.parent
    while parent and parent.name != 'section':
        parent = parent.parent
    
    if parent:
        print(f"\nContenedor section encontrado")
        # Buscar el div con los nombres
        content_div = parent.find('div', class_='Block_blockContent__6iJ_n')
        if content_div:
            print(f"Contenido completo:\n{content_div.get_text()[:500]}")

# Método 2: Buscar directamente Block_blockContent que contenga equipos
print("\n\n=== Método 2: Buscar por estructura ===")
block_contents = soup.find_all('div', class_='Block_blockContent__6iJ_n')
print(f"Total Block_blockContent encontrados: {len(block_contents)}")

for i, block in enumerate(block_contents):
    text = block.get_text()
    if 'CHI:' in text or 'BOS:' in text or 'INACTIVE' in text.upper():
        print(f"\n--- Block {i+1} con equipos ---")
        print(text[:300])
