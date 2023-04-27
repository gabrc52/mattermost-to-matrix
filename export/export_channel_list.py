from login import mm
import json
import os

if not os.path.exists('../downloaded/teams.json'):
    import export_teams
    # No need to do anything else, we have created the file now

teams = json.load(open('../downloaded/teams.json', 'r'))
team_ids = [team['id'] for team in teams]

all_channels = []

for team_id in team_ids:
    all_channels.extend([channel for channel in mm.get_team_channels(team_id)])

json.dump(all_channels, open('../downloaded/channels.json', 'w'))