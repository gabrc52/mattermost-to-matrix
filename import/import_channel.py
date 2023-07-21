from matrix import get_app_service, config, get_alias_mxid, get_user_mxid_by_localpart
from mautrix.types import ImageInfo, BaseFileInfo, RoomCreatePreset, EventType, MemberStateEventContent, Membership, TextMessageEventContent, MessageType, Format, RoomNameStateEventContent, RoomTopicStateEventContent
import mautrix.errors
import json
import os
import sys
from import_user import import_user
from not_in_mautrix import join_user_to_room, pin_message
import asyncio
import markdown
from progress.bar import Bar

md = markdown.Markdown(extensions=[
    'markdown.extensions.fenced_code',
    'markdown.extensions.tables',
    'markdown.extensions.nl2br',
    'pymdownx.magiclink',
    'pymdownx.tilde'
], extension_configs={
    'pymdownx.tilde': {
        'subscript': False,
    }
})

emojis: dict = json.load(open('../downloaded/emoji.json', 'r'))

if not os.path.exists('../downloaded/channels.json'):
    print(f'channels.json not found! Run export_channel_list.py first.', file=sys.stderr)
    exit(1)
channels = json.load(open('../downloaded/channels.json', 'r'))


def get_mattermost_channel(channel_id):
    """
    Get the Mattermost record from the given channel, by reading
    the exported data.
    """
    results = [channel for channel in channels if channel['id'] == channel_id]
    if not results:
        raise ValueError('Inexistent Mattermost channel ID')
    return results[0]


async def room_exists(room_alias):
    """
    Does the room with the given alias exist?
    """
    app_service = get_app_service()
    api = app_service.bot_intent()
    try:
        alias_info = await api.resolve_room_alias(room_alias)
        return True
    except mautrix.errors.request.MNotFound:
        return False


async def create_channel_from_json(channel):
    """
    Creates a Mattermost channel with the given channel JSON into a Matrix room.
    Returns the room ID on Matrix
    """
    # TODO: do something like _mattermost_sipb_uplink (add team too)
    # but make it configureable
    alias_localpart = config.matrix.room_prefix + channel['name']

    app_service = get_app_service()
    api = app_service.bot_intent()

    # First, check if the room already exists
    already_exists = await room_exists(get_alias_mxid(alias_localpart))

    # If it already exists, resolve its ID
    if already_exists:
        alias_info = await api.resolve_room_alias(get_alias_mxid(alias_localpart))
        room_id = alias_info.room_id

    # If it doesn't exist, create it
    if not already_exists:
        creator_mxid = await import_user(channel['creator_id'])
        user_api = app_service.intent(creator_mxid)
        room_id = await user_api.create_room(
            preset=RoomCreatePreset.PUBLIC,
            alias_localpart=alias_localpart,
            name=channel['display_name'],
            power_level_override={
                'events': {
                    # everyone has permission to rename rooms in mattermost
                    "m.room.name": 0,
                    # everyone has permission to pin in mattermost
                    "m.room.pinned_events": 0,
                    # leave the rest as default (if ommitted, they are not merged into this dict,
                    # giving everyone permission to do everything - i think?)
                    "m.room.power_levels": 100,
                    "m.room.history_visibility": 100,
                    "m.room.canonical_alias": 50,
                    "m.room.avatar": 50,
                    "m.room.tombstone": 100,
                    "m.room.server_acl": 100,
                    "m.room.encryption": 100
                },
                # everyone can invite
                'invite': 0,
                'users': {user: 100 for user in config.matrix.users}               # As per config
                       | {get_user_mxid_by_localpart(config.matrix.username): 100} # Make ourselves admin
                       | {user_api.mxid: 100},                                     # Make creator admin
            },
        )
        # Invite bot user if needed
        await api.ensure_joined(room_id, bot=user_api) # I see the advantage of this

    # Invite everyone in the config
    for user in config.matrix.users:
        await api.invite_user(room_id, user)

    return room_id


async def create_channel(channel):
    """
    Create a Mattermost channel (with given `channel_id`) into a Matrix room.
    Returns the room ID on Matrix
    """
    channel = get_mattermost_channel(channel_id)
    return await create_channel_from_json(channel)


most_recent_message_in_thread = {}


def remove_duplicates_special(tuples):
    """
    From a set of tuples (a,b,c), remove the duplicates
    by ensuring that no two tuples (xa,xb,xc), (ya,yb,yc) have xa=ya and xb=yb

    Fill out c by choosing arbitrarily between any of the duplicates, if applicable
    """
    # Rationale: someone can react with both +1 and thumbsup in Mattermost,
    # and the duplicate reactions appear in the exported JSON.
    # Matrix will complain about duplicate reactions, because they both map to 👍
    helper_dict = {(a,b): c for a,b,c in tuples}
    return {(k[0], k[1], v) for k,v in helper_dict.items()}


def get_reactions(reactions):
    """
    From a Mattermost array of reactions, get a set of tuples as
    (Mattermost user ID, reaction, timestamp)
    """
    return remove_duplicates_special({
        # Currently just use the name for custom reactions because Matrix does not have them yet
        (reaction['user_id'], emojis.get(reaction['emoji_name']) or reaction['emoji_name'], reaction['create_at'])
        for reaction in reactions
    })


async def import_files_in_message(message, room_id, user_api):
    """
    Send the files in the Mattermost message as separate Matrix messages.

    Returns the Matrix event ID of the last file sent
    """
    for file in message['metadata']['files']:
        # Upload first
        filename = f'../downloaded/media/{file["id"]}'
        with open(filename, 'rb') as f:
            contents = f.read()
            image_uri = await user_api.upload_media(contents, file['mime_type'], file['name'])

        if file['mime_type'].startswith('image'):
            # Images
            event_id = await user_api.send_image(
                room_id,
                url=image_uri,
                info=ImageInfo(
                    mimetype=file['mime_type'],
                    size=file['size'],
                    height=file['height'],
                    width=file['width'],
                ),
                file_name=file['name'],
                timestamp=message['create_at'],
            )
        else:
            # Other attachments
            event_id = await user_api.send_file(
                room_id,
                url=image_uri,
                info=BaseFileInfo(
                    mimetype=file['mime_type'],
                    size=file['size'],
                ),
                file_name=file['name'],
                timestamp=message['create_at'],
            )
    return event_id


async def import_message(message, room_id, topic_equivalent):
    """
    Import a specific message from the Mattermost JSON format
    into the specified room ID

    topic_equivalent can be header, purpose or both, for what to treat
    as a Matrix topic
    """
    app_service = get_app_service()
    api = app_service.bot_intent()

    user_mxid = await import_user(message['user_id'])
    user_api = app_service.intent(user_mxid)

    # Messages without a type are normal messages
    if not message['type']:
        if message['message']:
            # event_id = await user_api.send_text(room_id, message['message'], timestamp=message['create_at'])
            event_id = await user_api.send_message(
                room_id,
                TextMessageEventContent(
                    msgtype=MessageType.TEXT,
                    body=message['message'],
                    formatted_body=md.convert(message['message']),
                    format=Format.HTML,
                ),
                timestamp=message['create_at']
            )

        # Handle media
        if 'files' in message['metadata']:
            event_id = await import_files_in_message(message, room_id, user_api)

        # Handle reactions
        # Specifically, react to the last event ID
        if 'reactions' in message['metadata']:
            for user_id, emoji, timestamp in get_reactions(message['metadata']['reactions']):
                reactor_mxid = await import_user(user_id)
                reactor_api = app_service.intent(reactor_mxid)
                await reactor_api.react(room_id, event_id, emoji, timestamp=timestamp)

        if message['is_pinned']:
            await pin_message(user_api, room_id, event_id, timestamp=message['create_at'])
    elif message['type'] == 'system_join_channel':
        await join_user_to_room(user_mxid, room_id, timestamp=message['create_at'])
    elif message['type'] == 'system_leave_channel':
        await user_api.send_state_event(
            room_id,
            EventType.ROOM_MEMBER,
            MemberStateEventContent(membership=Membership.LEAVE),
            user_mxid,
            timestamp=message['create_at'],
        )
    elif message['type'] == 'system_add_to_channel':
        invited_user_id = message['props']['addedUserId']
        invited_matrix_user = await import_user(invited_user_id)
        invited_api = app_service.intent(invited_matrix_user)
        try:
            await user_api.send_state_event(
                room_id,
                EventType.ROOM_MEMBER,
                MemberStateEventContent(
                    membership=Membership.INVITE,
                    displayname=await user_api.get_displayname(user_mxid),
                ),
                invited_matrix_user,
                timestamp=message['create_at'],
            )
        except mautrix.errors.request.MForbidden:
            # ignore exception if you try to invite someone already in the room
            pass
        await join_user_to_room(invited_matrix_user, room_id, timestamp=message['create_at'])
    elif message['type'] == 'system_remove_from_channel':
        removed_user_id = message['props']['removedUserId']
        removed_matrix_user = await import_user(removed_user_id)
        await user_api.send_state_event(
            room_id,
            EventType.ROOM_MEMBER,
            MemberStateEventContent(
                membership=Membership.LEAVE
            ),
            removed_matrix_user,
            timestamp=message['create_at'],
        )
    elif message['type'] == 'system_displayname_change':
        await user_api.send_state_event(
            room_id,
            EventType.ROOM_NAME,
            RoomNameStateEventContent(name=message['props']['new_displayname']),
            timestamp=message['create_at'],
        )
    elif message['type'] == 'system_header_change':
        if topic_equivalent in ('header', 'both'):
            await user_api.send_state_event(
                room_id,
                EventType.ROOM_TOPIC,
                RoomTopicStateEventContent(topic=message['props']['new_header']),
                timestamp=message['create_at'],
            )
    elif message['type'] == 'system_purpose_change':
        if topic_equivalent in ('purpose', 'both'):
            await user_api.send_state_event(
                room_id,
                EventType.ROOM_TOPIC,
                RoomTopicStateEventContent(topic=message['props']['new_purpose']),
                timestamp=message['create_at']
            )
    else:
        print('Warning: not bridging unknown message type', message['type'], file=sys.stderr)


async def import_channel(channel_id):
    """
    Imports the entire Mattermost channel with given ID into a Matrix channel,
    and adds the users chosen in the config and makes them admin
    """
    filename = f'../downloaded/messages/{channel_id}.json'
    if not os.path.exists(filename):
        print(f'File does not exist for {channel_id}. Run export_channel.py first.', file=sys.stderr)
        exit(1)
    messages = json.load(open(filename, 'r'))

    channel = get_mattermost_channel(channel_id)
    room_id = await create_channel_from_json(channel)

    # If we chose "auto" for topic changes, choose just one to bridge
    topic_equivalent = config.mattermost.backfill_topic_equivalent
    if topic_equivalent == 'both':
        # Prefer purpose if there is at least one purpose change
        if any(message['type'] == 'system_purpose_change' for message in messages):
            topic_equivalent = 'purpose'
        # Otherwise, use the header change
        else:
            topic_equivalent = 'header'

    # Reverse cause reverse chronological order
    with Bar(f"Importing {channel['name']}", max=len(messages)) as bar:
        for message in reversed(messages):
            await import_message(message, room_id, topic_equivalent)

            # Remember most recent message in thread
            # TODO: actually use it to reply or make a thread
            if message['root_id']:
                most_recent_message_in_thread[message['root_id']] = message['id']
            
            bar.next()

    # Close the session when done
    await get_app_service().session.close()


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: import_channel.py [mattermost channel ID]", file=sys.stderr)
        print('You may get the channel ID from Mattermost ("view info") or channels.json.', file=sys.stderr)
        exit(1)
    channel_id = sys.argv[1]
    asyncio.run(import_channel(channel_id))
