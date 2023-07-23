import asyncio
import json
import os
import sys

from import_message import import_message
from import_user import import_user
from matrix import (config, get_alias_mxid, get_app_service,
                    get_user_mxid_by_localpart, room_exists)
from mautrix.types import RoomCreatePreset
from message_state import MessageState
from progress.bar import Bar

if not os.path.exists('../downloaded/channels.json'):
    print(f'channels.json not found! Run export_channel_list.py first.', file=sys.stderr)
    exit(1)
channels = json.load(open('../downloaded/channels.json', 'r'))
teams = json.load(open('../downloaded/teams.json', 'r'))

def get_mattermost_channel(channel_id):
    """
    Get the Mattermost record from the given channel, by reading
    the exported data.
    """
    results = [channel for channel in channels if channel['id'] == channel_id]
    if not results:
        raise ValueError('Inexistent Mattermost channel ID')
    return results[0]


def get_alias_localpart(channel):
    """
    Given a Mattermost channel (JSON), get the localpart
    of the Matrix alias to it
    """
    # perhaps this is where we can add a configuration option to omit the
    # team name
    team = [team for team in teams if team['id'] == channel['team_id']][0]
    return f"{config.matrix.room_prefix}{team['name']}_{channel['name']}"


async def create_room(alias_localpart, power_level_override: dict=None, creator_mxid=None, **kwargs):
    """
    Creates a Matrix room with the given properties, and invites and makes admin the
    specified people in the config. Returns the room ID of the newly created room or 
    the already existing room, if it already exists, and whether the channel has just
    been created, as a tuple.
    Accepted kwargs include:
    * name
    * power_level_override
    Full list: https://docs.mau.fi/python/latest/api/mautrix.client.api.html#mautrix.client.ClientAPI.create_room
    """
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
        # Make everyone in config admin
        if not power_level_override: power_level_override = {}
        power_level_override.setdefault('users', {})
        power_level_override['users'] |= \
            {user: 100 for user in config.matrix.users} | \
            {get_user_mxid_by_localpart(config.matrix.username): 100} # plus the bot account ofc
        if creator_mxid:
            user_api = app_service.intent(creator_mxid)
        else:
            user_api = app_service.bot_intent()
        room_id = await user_api.create_room(
            alias_localpart=alias_localpart, 
            power_level_override=power_level_override,
            **kwargs
        )
        # Invite bot user if needed
        await api.ensure_joined(room_id, bot=user_api) # I see the advantage of this

    # Invite everyone in the config
    for user in config.matrix.users:
        await api.invite_user(room_id, user)

    return room_id, already_exists


async def create_channel_from_json(channel):
    """
    Creates a Mattermost channel with the given channel JSON into a Matrix room.
    Returns the room ID on Matrix
    """
    alias_localpart = get_alias_localpart(channel)
    creator_mxid = await import_user(channel['creator_id']) if channel['creator_id'] else None
    power_level_override = {
        'events': {
            # everyone has permission to rename rooms in mattermost
            "m.room.name": 0,
            # everyone has permission to pin in mattermost
            "m.room.pinned_events": 0,
            # everyone has permission to change the topic
            "m.room.topic": 0,
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
    }
    # Make creator admin
    if creator_mxid:
        power_level_override.setdefault('users', {})
        power_level_override['users'] |= {creator_mxid: 100}
    return await create_room(
        alias_localpart=alias_localpart,
        creator_mxid=creator_mxid,
        preset=RoomCreatePreset.PUBLIC,
        name=channel['display_name'],
        power_level_override=power_level_override,
    )
    


async def create_channel(channel):
    """
    Create a Mattermost channel (with given `channel_id`) into a Matrix room.
    Returns the room ID on Matrix
    """
    channel = get_mattermost_channel(channel_id)
    return await create_channel_from_json(channel)



async def import_channel(channel_id):
    """
    Imports the entire Mattermost channel with given ID into a Matrix channel,
    and adds the users chosen in the config and makes them admin
    """
    state = MessageState()
    filename = f'../downloaded/messages/{channel_id}.json'
    if not os.path.exists(filename):
        print(f'File does not exist for {channel_id}. Run export_channel.py first.', file=sys.stderr)
        exit(1)
    messages = json.load(open(filename, 'r'))

    channel = get_mattermost_channel(channel_id)
    room_id, already_existed = await create_channel_from_json(channel)

    # If we chose "auto" for topic changes, choose just one to bridge
    topic_equivalent = config.mattermost.backfill.topic_equivalent
    if topic_equivalent == 'auto':
        # Prefer purpose if there is at least one purpose change
        if any(message['type'] == 'system_purpose_change' for message in messages):
            topic_equivalent = 'purpose'
        # Otherwise, use the header change
        else:
            topic_equivalent = 'header'

    # If we choose "auto" for thread changes, calculate thread sizes
    # (including the root)
    thread_sizes = None
    if config.mattermost.backfill.thread_equivalent == 'auto':
        thread_sizes = {message['id']: 1 for message in messages}
        for message in messages:
            if message['root_id']:
                thread_sizes[message['root_id']] += 1
                del thread_sizes[message['id']]

    # Reverse cause reverse chronological order
    if already_existed and config.matrix.skip_existing:
        print(f'Skipping import of already existing channel "{channel["display_name"]}"')
    else:
        with Bar(f"Importing {channel['name']}", max=len(messages)) as bar:
            for message in reversed(messages):
                await import_message(message, room_id, topic_equivalent, state, thread_sizes)
                
                bar.next()

    return room_id


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: import_channel.py [mattermost channel ID]", file=sys.stderr)
        print('You may get the channel ID from Mattermost ("view info") or channels.json.', file=sys.stderr)
        exit(1)
    channel_id = sys.argv[1]
    asyncio.run(import_channel(channel_id))
    # Close the session when done
    asyncio.run(get_app_service().session.close())
