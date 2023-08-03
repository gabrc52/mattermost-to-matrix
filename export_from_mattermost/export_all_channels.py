import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from export_from_mattermost.export_channel import export_channel, mm, own_id, config
import json

if not os.path.exists('../downloaded/channels.json'):
    import export_channel_list
    # No need to do anything else, we have created the file now

channels = json.load(open('../downloaded/channels.json', 'r'))
teams = json.load(open('../downloaded/teams.json', 'r'))

def team_by_id(team_id):
    for team in teams:
        if team['id'] == team_id:
            return team

for channel in channels:
    print('Downloading channel', channel['display_name'], 'in', team_by_id(channel['team_id'])['display_name'])

    # Skip channels as per config
    if channel['id'] in config.mattermost.skip_channels:
        print('   skipping')
        continue

    # Download channel
    export_channel(channel['id'])

