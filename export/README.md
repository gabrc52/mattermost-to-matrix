# Mattermost export scripts

## Configuration:

`constants.py`: You must create this file before using any of the export scripts. Must contain `USERNAME`, `PASSWORD`, `DOMAIN` (such as mattermost.example.com, without any protocol), and `TEAM_ID` as Python variables.

## Export scripts:

Everything will be downloaded into JSON files.

 * **`download_everything.sh`**: Convenience script that just calls all the Python scripts to download everything.

 * `export_teams.py`: Export all teams. I am using a single-team Mattermost, so if you wish to do something with other teams, you need to run the scripts with a different `TEAM_ID`. PRs welcome.

 * `export_users.py`: Exports the user directory. Note that at the moment, profile pictures are ***not*** downloaded.

 * `export_channel_list.py`: Exports the channel directory.

 * `export_channel.py`: Export all messages from a single channel of your choosing. Accepts the channel ID as parameter. Call: `python export_channel.py channel_id`

 * `export_all_channels.py`: Exports all messages from **every public channel in the team**.

 * `download_media.py`: Once you export messages, it can go over the media in them, and download it. You can safely run it more than once if you download more messages later, as it will only download media that has not already been downloaded.

 * `emoji.py`: Re-generates emoji.json based on the content of emoji.html, which comes from "Inspect element"ing Mattermost. It still needs testing with new Mattermost versions.

## Other scripts:
 
 * `view_channel.py`: View a dumped channel in the browser. Call: `python view_channel.py channel_id`. This is more of a proof-of-concept, since the final destination is Matrix, so it needs some love if someone does want that.