from matrix import get_app_service, config, get_alias_mxid, get_user_mxid_by_localpart
import mautrix.errors
import json
import os
import sys
from import_user import import_user
import asyncio

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


async def create_channel(channel_id):
    """
    Create a Mattermost channel (with given `channel_id`) into a Matrix room.
    Returns the room ID on Matrix
    """
    channel = get_mattermost_channel(channel_id)
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
            alias_localpart=alias_localpart,
            name=channel['display_name'],
            power_level_override={
                'users': {user: 100 for user in config.matrix.users}               # As per config
                       | {get_user_mxid_by_localpart(config.matrix.username): 100} # Make ourselves admin
                       | {user_api.mxid: 100}                                      # Make creator admin
            },
        )
        # Invite bot user if needed
        await api.ensure_joined(room_id, bot=user_api) # I see the advantage of this

    # Invite everyone in the config
    for user in config.matrix.users:
        await api.invite_user(room_id, user)

    return room_id


most_recent_message_in_thread = {}


async def import_channel(channel_id):
    """
    Imports the entire Mattermost channel with given ID into a Matrix channel,
    and adds the users chosen in the config and makes them admin
    """
    app_service = get_app_service()
    api = app_service.bot_intent()
    filename = f'../downloaded/messages/{channel_id}.json'
    if not os.path.exists(filename):
        print(f'File does not exist for {channel_id}. Run export_channel.py first.', file=sys.stderr)
        exit(1)
    messages = json.load(open(filename, 'r'))

    room_id = await create_channel(channel_id)

    # Reverse cause reverse chronological order
    for message in reversed(messages):
        # TODO: this is pretty monolithic. Split into several functions

        print(message['message'])
        user_mxid = await import_user(message['user_id'])
        user_api = app_service.intent(user_mxid)

        # Messages without a type are normal messages
        if not message['type']:
            # TODO: handle markdown
            event_id = await user_api.send_text(room_id, message['message'], query_params={'ts': message['create_at']})

            # Handle reactions
            if 'reactions' in message['metadata']:
                for reaction in message['metadata']['reactions']:
                    reactor_mxid = await import_user(reaction['user_id'])
                    reactor_api = app_service.intent(reactor_mxid)
                    emoji_name = reaction['emoji_name']
                    # TODO: Can't send same reaction twice
                    # what happens is it has both +1 and thumbsup by the same person for some reason (?!)
                    await reactor_api.react(room_id, event_id, emojis.get(emoji_name) or emoji_name, query_params={'ts': reaction['create_at']})


            # TODO: Handle media

            if message['is_pinned']:
                # TODO: ensure we have permissions to pin(?)
                await user_api.pin_message(room_id, event_id)
        elif message['type'] == 'system_join_channel':
            # TODO: set timestamp
            # TODO: allow making the room public so bridged users can just join without duplicate events in the timeline
            await user_api.ensure_joined(room_id)
        elif message['type'] == 'system_leave_channel':
            # TODO: set timestamp
            await user_api.leave_room(room_id)
        elif message['type'] == 'system_add_to_channel':
            invited_user_id = message['props']['addedUserId']
            invited_matrix_user = await import_user(invited_user_id)
            invited_api = app_service.intent(invited_matrix_user)
            await user_api.invite_user(room_id, invited_matrix_user)
            await invited_api.ensure_joined(room_id)
        # TODO: implement these other types
        # elif message['type'] == 'system_remove_from_channel':
        #     pass
        # elif message['type'] == 'system_header_change':
        #     pass
        # elif message['type'] == 'system_displayname_change':
        #     pass
        # elif message['type'] == 'system_purpose_change':
        #     pass
        else:
            print('Warning: not bridging unknown message type', message['type'], file=sys.stderr)

        # Remember most recent message in thread
        # TODO: actually use it to reply
        if message['root_id']:
            most_recent_message_in_thread[message['root_id']] = message['id']
