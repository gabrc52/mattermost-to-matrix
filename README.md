# Mattermost to Matrix migration

Automate migrating from Mattermost team to Matrix

Note that this is for migrating past messages to Matrix. To copy over present and future messages in real-time, what you need is a bridge, such as [matrix-appservice-mattermost](https://matrix.org/bridges/#mattermost) or [matterbridge](https://github.com/42wim/matterbridge/) (note that as of April 2023, full Matrix integration in matterbridge is an unmerged PR).

## Instructions to use

You don't need a bot account or admin access on the Mattermost side to use these export and import scripts. On the Matrix side you need to be able to register an application service.

1. Copy `config.sample.yaml` to `config.yaml` and edit with your own settings.

2. Export your Mattermost data using the helper script: `export/download_everything.sh`. For more info about specific things that you can export, see <export/README.md>, 

3. Generate a Matrix registration file using `python generate_registration.py`, which will be called `registration.yaml` but you can rename.

4. Register it to your homeserver, for instance <https://docs.mau.fi/bridges/general/registering-appservices.html>. If you are running Synapse you can copy the registration file to a new directory `/etc/matrix-synapse/appservices` and then edit your Synapse config to add the application service, like this:

```yaml
app_service_config_files:
 - /etc/matrix-synapse/appservices/mattermost_migration.yaml
```

5. Run the import script `python import/import_all_teams.py`. Alternatively, you may wish to import only some teams or channels, e.g. `python import_team.py sipb` or `python import_channel.py 3g5jnmyzzi8a9pcksonnraxzgy`, with the team name or channel ID, respectively.

6. Once you have imported your messages, you can revert the changes you made to your Synapse `config.yaml` or `conf.d`, since it is a good idea to revoke unused credentials.

## What's supported

This program aims to preserve as much as possible fidelity from Mattermost to Matrix

* Mattermost team -> Matrix space (public channels only)
* Rich text messages (Markdown)
* Images
* Other attachments
* Joins/leaves
* Header/purpose changes -> Matrix topic changes (with customizable behavior)
* Reactions
* Replies and threads (with customizable behavior, since Mattermost conflates them)
* Channel name changes -> Matrix room name changes
* Webhooks (but messages of type `slack_webhook` are only partially supported)

## What's currently not supported

Because I didn't/haven't implemented them:

* Private channels or DMs
* Edits are not reflected on Matrix
* Full slack-webhook support (rendering author and all fields)
* Webhooks with profile pictures
* Some Markdown features
    * Lists without any newline between any preceding text and the start of the list
    * Inline emojis
    * LaTeX

Due to platform differences:

* Custom reactions (not yet supported by Matrix)

## Upcoming bridge

I plan to turn this into a bridge soon enough.