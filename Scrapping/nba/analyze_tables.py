import requests
from bs4 import BeautifulSoup

game_id = "401704650"
url = f"https://www.espn.com/nba/boxscore/_/gameId/{game_id}"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

res = requests.get(url, headers=headers)
soup = BeautifulSoup(res.text, "lxml")

# Find all tables
tables = soup.find_all("table", class_="Table")
print(f"Found {len(tables)} tables with class 'Table'")

# Check for team stats tables
for i, table in enumerate(tables[:5]):
    print(f"\n=== TABLE {i} ===")
    rows = table.find_all("tr")
    print(f"Rows: {len(rows)}")
    
    # Check first few rows
    for j, row in enumerate(rows[:3]):
        cells = row.find_all("td")
        if cells:
            print(f"  Row {j}: {len(cells)} cells - First: '{cells[0].get_text(strip=True)[:20]}'")
            if len(cells) >= 17:
                print(f"    -> Has 17+ cells (potential team totals)")

# Look for alternative table structures
print("\n=== ALTERNATIVE SEARCH ===")
all_tables = soup.find_all("table")
print(f"Total tables (any class): {len(all_tables)}")

# Look for tbody with team stats
tbodies = soup.find_all("tbody")
print(f"Total tbody elements: {len(tbodies)}")
for i, tbody in enumerate(tbodies[:3]):
    rows = tbody.find_all("tr")
    if rows:
        cells = rows[0].find_all("td")
        print(f"  tbody {i}: {len(rows)} rows, first row has {len(cells)} cells")
