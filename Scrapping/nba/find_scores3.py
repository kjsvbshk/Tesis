from bs4 import BeautifulSoup
import re

with open("test_boxscore.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")

# Find the section with team names
teams = soup.select(".BoxscoreItem__TeamName")
print(f"Found {len(teams)} teams")

# For each team, find the parent container and look for scores
for i, team in enumerate(teams):
    team_name = team.text.strip()
    print(f"\n=== {team_name} ===")
    
    # Navigate up to find the BoxscoreItem container
    container = team
    for _ in range(5):  # Go up max 5 levels
        container = container.parent
        if container and 'BoxscoreItem' in str(container.get('class', [])):
            print(f"Found BoxscoreItem container")
            # Print all text content
            all_text = list(container.stripped_strings)
            print(f"All text in container: {all_text[:10]}")
            
            # Look for numbers that could be scores
            for text in all_text:
                if text.isdigit() and 50 < int(text) < 200:
                    print(f"  -> Potential score: {text}")
            break
