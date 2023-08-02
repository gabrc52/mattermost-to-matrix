# Another Mattermost to Matrix bridge

This project can do 2 things:

1. Automate migrating from Mattermost team to Matrix (back up [from Mattermost] and restore [to Matrix])

2. Bridge Matrix spaces <-> Mattermost teams

Essentially, this is a backfill bridge to Matrix, except you have to run part 1 and part 2 separately, if you wish to use backfill.

## Instructions to use

You don't need a bot account or admin access on the Mattermost side to use this bridge (you can authenticate with either token or user/password). On the Matrix side you need to be able to register an application service.

1. Copy `config.sample.yaml` to `config.yaml` and edit with your own settings.

> Important Note: If you wish to migrate messages and use this as a bridge as well, please leave `enable_bridge: false`. You can set it to `true` after you finish message migration and before you start the bridge.

2. Export your Mattermost data using the helper script: `export_from_mattermost/download_everything.sh`. For more info about specific things that you can export, see [export_from_mattermost/README.md](export_from_mattermost/README.md), 

3. Generate a Matrix registration file using `python generate_registration.py`, which will be called `registration.yaml` but you can rename.

4. Register it to your homeserver, for instance <https://docs.mau.fi/bridges/general/registering-appservices.html>. If you are running Synapse you can copy the registration file to a new directory `/etc/matrix-synapse/appservices` and then edit your Synapse config to add the application service, like this:

```yaml
app_service_config_files:
 - /etc/matrix-synapse/appservices/mattermost_migration.yaml
```

5. Run the import script `import_to_matrix/import_all_teams.py`. Alternatively, you may wish to import only some teams or channels, e.g. `import_to_matrix/import_team.py sipb` or `import_to_matrix/import_channel.py 3g5jnmyzzi8a9pcksonnraxzgy`, with the team name or channel ID, respectively.

6. If all you wish is to migrate your messages, once that's done, you can revert the changes you made to your Synapse `config.yaml` or `conf.d`, since it is a good idea to revoke unused credentials.

7. If you wish to use the bridge, you should change `enable_bridge: true` in the config, and re-regenerate the registration file, then edit the file in Synapse's config, then restart Syanpse. The URL field at the bottom will change.

8. You can now start `bridge.py` and keep it always running (e.g. through a systemd unit) to use the bridge.

## What's supported

This program aims to preserve as much as possible fidelity from Mattermost to Matrix

* User display name and profile picture changes 
* Mattermost team -> Matrix space (public channels only)
* Rich text messages (most but not all Markdown features)
* Images and other attachments
* Joins/leaves
* Header/purpose changes -> Matrix topic changes (with customizable behavior)
* Reactions (on Matrix->Mattermost the bot will react on the Matrix user's behalf, and only adding reactions is supported)
* Replies and threads (with customizable behavior, since Mattermost conflates them)
* Channel name changes -> Matrix room name changes
* Webhooks (but messages of type `slack_webhook` are only partially supported)
* Pinned messages (only fully supported on backfill)
* Typing notifications (Mattermost->Matrix only)
* Edits
* Deletions

## What's currently not supported

Because I didn't/haven't implemented them (PRs are welcome):

* Private channels or DMs
* During backfill, edited messages are not marked as edited on Matrix
* Full slack-webhook support (rendering author and all fields)
* Webhooks with profile pictures
* Some Markdown features
    * Lists without any newline between any preceding text and the start of the list
    * Inline emojis (#15)
    * LaTeX
    * Mentions*
* Pinning a Mattermost message from Matrix (#16)
* Some emoji reactions may not work due to emoji variation selectors (#17)
* Presence / online status
* Deletions from Mattermost->Matrix when the message contains multiple attachments
* Room name changes, or other team changes

Due to platform differences:

* Custom reactions (not yet supported by Matrix, bridged as the name of the reaction)
* Reacting with arbitrary strings (not supported by Mattermost)
* Typing notifications from Matrix->Mattermost (that would require creating ghost users on the Mattermost side too like https://github.com/dalcde/matrix-appservice-mattermost does)

* Note that when you delete a message on Mattermost, all of its children get deleted too. So if you delete the root of a thread on Matrix, its children will be visible on Matrix **but will be gone on Mattermost**.