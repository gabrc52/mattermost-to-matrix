"""
Download all user and team profile pictures
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from export_from_mattermost.media import download_media, download_profile_picture, download_team_picture

import json

# Create subdirectory if needed
if not os.path.exists('../downloaded/pfp'):
    os.mkdir('../downloaded/pfp')

users = json.load(open('../downloaded/users.json', 'r'))
teams = json.load(open('../downloaded/teams.json', 'r'))

# TODO: this redownloads all pictures every time you run the file
# It might be good to persist which ones have been downloaded and not been changed
for user in users:
    if 'last_picture_update' in user:
        # Otherwise the API just returns a generic profile picture
        download_profile_picture(user['id'])

for team in teams:
    if 'last_team_icon_update' in team:
        download_team_picture(team['id'])