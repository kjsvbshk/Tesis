import requests

url = "https://www.nba.com/game/chi-vs-bos-0022500778/box-score"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers)

print(f"Status: {response.status_code}")
print(f"Content length: {len(response.text)}")
print("\n=== First 2000 chars ===")
print(response.text[:2000])
print("\n=== Search for 'GameBoxscore' ===")
if 'GameBoxscore' in response.text:
    print("✅ Found GameBoxscore")
else:
    print("❌ GameBoxscore NOT found - página usa JavaScript")
    
print("\n=== Search for '__NEXT_DATA__' (Next.js) ===")
if '__NEXT_DATA__' in response.text:
    print("✅ Found __NEXT_DATA__ - es una app Next.js")
    # Buscar el JSON
    import re
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response.text, re.DOTALL)
    if match:
        print("✅ Encontrado JSON data")
        import json
        data = json.loads(match.group(1))
        print(f"Keys: {list(data.keys())}")
else:
    print("❌ __NEXT_DATA__ NOT found")
