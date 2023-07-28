#!/bin/bash

# Change to script directory
# https://stackoverflow.com/a/16349776/5031798
cd "${0%/*}"

echo Downloading team list
python export_teams.py
echo Downloading user list
python export_users.py
echo Downloading channel list
python export_channel_list.py
echo Downloading all public messages
python export_all_channels.py
echo Downloading all media in those channels
python download_media.py
echo Downloading profile pictures
python download_profile_pictures.py

