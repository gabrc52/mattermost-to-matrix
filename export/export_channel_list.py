from login import mm
from constants import *
import json

all_channels = [channel for channel in mm.get_team_channels(TEAM_ID)]

json.dump(all_channels, open('channels.json', 'w'))