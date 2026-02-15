from bs4 import BeautifulSoup

with open("test_boxscore.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")

# Find teams
teams = soup.select(".BoxscoreItem__TeamName")
print("Teams:", [t.text.strip() for t in teams])

# Find scores - look for BoxscoreItem with Score in class
all_boxscore_items = soup.find_all(class_=lambda x: x and "BoxscoreItem" in str(x) if x else False)
print(f"\nFound {len(all_boxscore_items)} BoxscoreItem elements")

scores_found = []
for item in all_boxscore_items:
    classes = item.get('class', [])
    class_str = ' '.join(classes)
    if 'Score' in class_str:
        text = item.text.strip()
        if text.isdigit():
            scores_found.append((text, classes))
            print(f"Score: {text} - Classes: {classes}")

if not scores_found:
    print("\nTrying alternative: looking for numeric text near teams")
    for team in teams:
        # Look in parent container
        container = team.find_parent(class_=lambda x: x and "BoxscoreItem" in str(x) if x else False)
        if container:
            # Find all text in container
            all_text = container.stripped_strings
            for text in all_text:
                if text.isdigit() and 50 < int(text) < 200:
                    print(f"Found score {text} near {team.text.strip()}")
