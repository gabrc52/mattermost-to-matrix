from login import mm
import json

all_teams = [team for team in mm.get_teams()]

print(f'Found teams {", ".join(team["name"] for team in all_teams)}')
json.dump(all_teams, open('../downloaded/teams.json', 'w'))