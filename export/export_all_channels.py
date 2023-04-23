from export_channel import export_channel, mm
from constants import *
import os
import json

own_account = mm.get_user()
own_id = own_account['id']

if not os.path.exists('channels.json'):
    import export_channel_list
    # No need to do anything else, we have created the file now

channels = json.load(open('channels.json', 'r'))

for channel in channels:
    print('Downloading channel', channel['display_name'])

    # Join if necessary
    mm.add_user_to_channel(channel['id'], own_id)

    # Download channel
    export_channel(channel['id'])

