from bs4 import BeautifulSoup

# Load saved HTML
with open("test_boxscore.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")

# Find teams
teams = soup.select("[class*='TeamName']")
print("=== TEAMS ===")
for i, team in enumerate(teams):
    print(f"{i}: {team.text.strip()} - Classes: {team.get('class')}")

# Find scores - look for numeric values near teams
print("\n=== LOOKING FOR SCORES ===")

# Try to find the game strip or score container
gamestrip = soup.find_all("div", class_=lambda x: x and "Gamestrip" in x if x else False)
print(f"Found {len(gamestrip)} Gamestrip divs")

# Look for elements with score-like classes
score_candidates = soup.find_all(class_=lambda x: x and any(keyword in str(x).lower() for keyword in ['score', 'total', 'final']) if x else False)
print(f"\nFound {len(score_candidates)} elements with score-related classes")
for i, elem in enumerate(score_candidates[:10]):
    text = elem.text.strip()
    if text and len(text) < 10:  # Likely a score
        print(f"  {i}: '{text}' - Tag: {elem.name}, Classes: {elem.get('class')}")

# Look for the actual score display
print("\n=== SPECIFIC SCORE SEARCH ===")
# Scores are usually in spans or divs near team names
for team_elem in teams:
    parent = team_elem.parent
    if parent:
        # Look for siblings or nearby elements with numbers
        siblings = parent.find_all_next(limit=5)
        for sib in siblings:
            text = sib.text.strip()
            if text.isdigit() and int(text) > 50 and int(text) < 200:  # NBA scores range
                print(f"Potential score near {team_elem.text.strip()}: {text}")
                print(f"  Element: {sib.name}, Classes: {sib.get('class')}")
                break
