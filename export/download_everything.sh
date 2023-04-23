#!/bin/bash

echo Downloading team list
python export_teams.py
echo Downloading user list for desired team
python export_users.py
echo Downloading channel list for desired team
python export_channel_list.py
echo Downloading all public messages for desired team
python export_all_channels.py
echo Downloading all media in those channels
python download_media.py
