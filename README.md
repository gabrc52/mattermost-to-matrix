# Mattermost to Matrix migration

Automate migrating from Mattermost team to Matrix

Note that this is for migrating past messages to Matrix. To copy over present and future messages in real-time, what you need is a bridge, such as [matrix-appservice-mattermost](https://matrix.org/bridges/#mattermost) or [matterbridge](https://github.com/42wim/matterbridge/) (note that as of April 2023, full Matrix integration in matterbridge is an unmerged PR).

## Instructions to use

1. Copy `config.sample.yaml` to `config.yaml` and edit with your own settings.

2. Export your Mattermost data using the helper script: `export/download_everything.sh`. For more info about specific things that you can export, see <export/README.md>, 

*Next steps are not implemented yet:*

3. Generate a Matrix registration file using `python generate_registration.py`, which will be called `registration.yaml` but you can rename.

4. Register it to your homeserver, for instance <https://docs.mau.fi/bridges/general/registering-appservices.html>. If you are running Synapse you can copy the registration file to a new directory `/etc/matrix-synapse/appservices` and then edit your Synapse config to add the application service, like this:

```yaml
app_service_config_files:
 - /etc/matrix-synapse/appservices/mattermost_migration.yaml
```

5. Run the import script `python import_all.py`. To export an individual Mattermost room to a Matrix room, you can use 

6. Once you have imported your messages, you can revert the changes you made to your Synapse `config.yaml` or `conf.d`, since it is a good idea to revoke unused credentials.

## This is work-in-progres

Also, once this import & export code is done, there should be mapping between Mattermost messages and Matrix messages, so the code could be adapted to turn into a bridge since half of the effort will have been done. (I didn't want yet another bridge though, but we'll see.)
