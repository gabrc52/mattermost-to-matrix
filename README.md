# Mattermost to Matrix migration

Automate migrating from Mattermost to Matrix

Note that this is for migrating past messages to Matrix. To copy over present and future messages in real-time, what you need is a bridge, such as [matrix-appservice-mattermost](https://matrix.org/bridges/#mattermost) or [matterbridge](https://github.com/42wim/matterbridge/) (note that as of April 2023, full Matrix integration in matterbridge is an unmerged PR).

Also, once this is done, there should be mapping between Mattermost messages and Matrix messages, so the code could be adapted to turn into a bridge since half of the effort will have been done. (I didn't want yet another bridge though, but we'll see.)

**This is work-in-progress**

See the respective subdirectories to read their READMEs

* [Exporting messages from Mattermost](export/README.md)
* Importing messages to Matrix (TBD)

