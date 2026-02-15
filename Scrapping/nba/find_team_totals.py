import requests
from bs4 import BeautifulSoup

game_id = "401704650"
url = f"https://www.espn.com/nba/boxscore/_/gameId/{game_id}"

headers = {'User-Agent': 'Mozilla/5.0'}
res = requests.get(url, headers=headers)
soup = BeautifulSoup(res.text, "lxml")

tables = soup.find_all("table", class_="Table")
print(f"Found {len(tables)} tables\n")

# Find the team totals rows
for i, table in enumerate(tables):
    print(f"=== TABLE {i} ===")
    rows = table.find_all("tr")
    
    for j, row in enumerate(rows):
        cells = row.find_all("td")
        if len(cells) >= 10:  # Team stats likely have many cells
            first_cell = cells[0].get_text(strip=True).lower()
            
            # Look for "team" row (totals)
            if first_cell == "team" or first_cell == "":
                print(f"  Row {j}: {len(cells)} cells - POTENTIAL TEAM TOTALS")
                print(f"    First 5 cells: {[c.get_text(strip=True) for c in cells[:5]]}")
                print(f"    All cells: {[c.get_text(strip=True) for c in cells]}")
                break
