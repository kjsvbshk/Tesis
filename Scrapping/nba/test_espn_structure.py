import requests
from bs4 import BeautifulSoup

# Test scraping a recent game
game_id = "401704650"
url = f"https://www.espn.com/nba/boxscore/_/gameId/{game_id}"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

print(f"Fetching: {url}")
res = requests.get(url, headers=headers)
print(f"Status: {res.status_code}")

soup = BeautifulSoup(res.text, "lxml")

# Save HTML for inspection
with open("test_boxscore.html", "w", encoding="utf-8") as f:
    f.write(soup.prettify())
print("HTML saved to test_boxscore.html")

# Test old selectors
print("\n=== OLD SELECTORS ===")
teams_old = soup.select(".ScoreCell__TeamName")
scores_old = soup.select(".ScoreCell__Score")
print(f"Teams (old): {len(teams_old)} - {[t.text for t in teams_old]}")
print(f"Scores (old): {len(scores_old)} - {[s.text for s in scores_old]}")

# Try alternative selectors
print("\n=== TESTING ALTERNATIVES ===")

# Try finding team names in different ways
team_selectors = [
    ".Gamestrip__Team .Gamestrip__TeamName",
    ".ScoreCell .ScoreCell__TeamName",
    ".Gamestrip__TeamName",
    "[class*='TeamName']",
    "[class*='Team'] [class*='Name']"
]

for selector in team_selectors:
    elements = soup.select(selector)
    if elements:
        print(f"✓ {selector}: {len(elements)} - {[e.text.strip() for e in elements[:4]]}")

# Try finding scores
score_selectors = [
    ".Gamestrip__Score",
    ".ScoreCell .ScoreCell__Score",
    "[class*='Score']",
    ".Gamestrip__Team .Gamestrip__Score"
]

for selector in score_selectors:
    elements = soup.select(selector)
    if elements:
        print(f"✓ {selector}: {len(elements)} - {[e.text.strip() for e in elements[:4]]}")

# Look for game header
print("\n=== GAME HEADER ===")
header = soup.find("div", class_="Gamestrip")
if header:
    print("Found Gamestrip div")
    print(header.prettify()[:500])
