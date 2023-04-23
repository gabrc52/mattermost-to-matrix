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

    # Hardcoded behavior for my use-case. TODO: generalize to a list of blocked channels or keywords
    if 'High Volume' in channel['display_name']:
        print('   skipping')
        break

    # Join if necessary
    mm.add_user_to_channel(channel['id'], own_id)

    # Download channel
    export_channel(channel['id'])

