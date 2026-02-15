import requests
from bs4 import BeautifulSoup

game_id = "401704650"
url = f"https://www.espn.com/nba/boxscore/_/gameId/{game_id}"

headers = {'User-Agent': 'Mozilla/5.0'}
res = requests.get(url, headers=headers)
soup = BeautifulSoup(res.text, "lxml")

tables = soup.find_all("table", class_="Table")

# Find team totals rows
team_totals = []
for table in tables:
    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 14:
            first_cell = cells[0].get_text(strip=True)
            if first_cell == "" or first_cell.lower() == "team":
                team_totals.append([c.get_text(strip=True) for c in cells])

print(f"Found {len(team_totals)} team totals rows\n")
for i, totals in enumerate(team_totals):
    print(f"Team {i}: {len(totals)} cells")
    for j, val in enumerate(totals):
        print(f"  [{j}]: {val}")
    print()
