from login import mm
import json

all_teams = [team for team in mm.get_teams()]

json.dump(all_teams, open('teams.json', 'w'))