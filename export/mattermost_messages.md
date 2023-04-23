# Some docs about Mattermost

***Important note: The Mattermost server I am running this on likely has an outdated version of Mattermost, so things may differ for you.***

Here is some documentation on the way the Mattermost JSON payloads for messages are formed.

This is based on observation (because there does not seem to be a useful mattermost spec for a lot of this).

Please don't expect it to be good. It's quite bad, and just meant for myself.

## Fields in the message

 * `id`: ID of the message

 * `create_at`: Timestamp of the message

 * `update_at`: When the message was last updated, usually just the 

 * `edit_at`: When the message was last edited. 0 if not edited

 * `delete_at`: When the message was last deleted. 0 if not deleted. Seems to be always 0, which makes sense, because deleted messages would not exist anymore.

 * `is_pinned`: Whether the message is pinned

 * `user_id`: The ID of the sender

 * `root_id`: ID of the first post in the thread. Empty string if not set

 * `metadata`: Images or reactions. See the notes about message types.

### Redundant/Deprecated/Useless

 * `channel_id`: The ID of the channel, redundant

 * `parent_id`: legacy column according to engineer (https://forum.mattermost.com/t/what-is-the-difference-between-rootid-and-parentid-about-post/8584)

 * `original_id`: supposedly the original ID before it was edited. Empty string if not set. It seems to always be the empty string even if the message was edited

 * `hashtags`: Contains the #hashtags of the message. Usually just people thinking it's Discord and using `#` instead of `~` to mention a channel. Also I don't think it has a Matrix equivalent.

 * `pending_post_id`: Seems useless. No idea what it is. No search results, apart from the API documentation, which only says it's a string but gives no description. It also seems to be always the empty string in my testing.

 * `reply_count`: Same. Seems to always be 0 in my testing, even if part of a thread.

## Some notes about Mattermost message types

But googling gives this result: https://github.com/mattermost/mattermost-server/blob/v5.39.3/model/post.go#L20

there are more than the ones i have

Types (i.e. `message['type']`) of messages:

### normal messages

type is "" (including messages with reactions and files AND webhooks)

### messages with reactions

no special type, just ""

metadata.reactions is defined and is an array

user_id, emoji_name and create_at are available for each reaction

note that it is emoji names!!! how to resolve it into an actual emoji?? who knows. they might be standard names

### messages with files

no special type, just ""

metadata.files is defined and is an array

(also both reactions and files have redundant fields for user id, channel id, etc. might be good to assert that they are what they are supposed to be)

This is a current missing feature from Matrix and proposed MSC (sending a message with media attached, for now it would have to be bridged as one message for the message, and one message per piece of media attached).

### system_join_channel

props.username has the person added

### system_leave_channel

analogous to above

### system_add_to_channel

props.username has the inviter (note the inconsistency, not the joiner)
props.addedUsername has the person added

(Note: for this and similar endpoints use Id instead of name to get the ID instead)

### system_remove_from_channel

analogous to above, with `removed` instead of `added`

### system_header_change

channel description changed

### system_join_team, system_leave_team, system_add_to_team, system_remove_from_team

for joining/leaving the TEAM

DON'T BRIDGE THIS! it's unnecssary

props.new_header, props.old_header and props.username

### system_displayname_change

renaming a channel

props.new_displayname, props.old_displayname and props.username

### system_purpose_change

channel description was changed

props.new_purpose, props.old_purpose and props.username

### other event types

There were no other event types in SIPB Mattermost

https://github.com/mattermost/mattermost-server/blob/v5.39.3/model/post.go#L20

would be good to just end the program or gracefully skip in this case, and then accept PRs and issues about them

### for bridged zephyr message (webhook)

*Note to anyone reading not from SIPB: This is not a Mattermost feature, it is a Mattermost integration that bridges with another network*

they all come from the same user id

props.from_zephyr is the string (not boolean) "true"
props.from_webhook is the string "true"
props.override_username has the actual username
props.class and props.instance has the original zephyr source
