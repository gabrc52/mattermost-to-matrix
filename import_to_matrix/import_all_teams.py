#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import asyncio
from import_to_matrix.import_team import import_team
import os

# change to the script's location
os.chdir(os.path.dirname(__file__))

teams = json.load(open('../downloaded/teams.json', 'r'))

async def import_all_teams():
    for team in teams:
        print(f"# Importing {team['display_name']}")
        await import_team(team['name'])

if __name__ == '__main__':
    asyncio.run(import_all_teams())