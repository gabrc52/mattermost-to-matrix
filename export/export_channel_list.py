from login import mm, own_id
from mattermost import ApiException
import json
import os

if not os.path.exists('../downloaded/teams.json'):
    import export_teams
    # No need to do anything else, we have created the file now

teams = json.load(open('../downloaded/teams.json', 'r'))

all_channels = []

for team in teams:
    team_id = team['id']
    try:
        mm.add_user_to_team(team_id, own_id)
        all_channels.extend([channel for channel in mm.get_team_channels(team_id)])
    except ApiException as e:
        print(f"   Can't download team \"{team['display_name']}\": {e.args[0]['message']}")

json.dump(all_channels, open('../downloaded/channels.json', 'w'))