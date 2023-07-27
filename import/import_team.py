import asyncio
import os
import magic
from import_channel import channels, teams, create_room, import_channel
from matrix import get_app_service, config, get_room_avatar, set_room_avatar
from mautrix.types import RoomCreateStateEventContent, RoomType, RoomCreatePreset, EventType, SpaceChildStateEventContent, SpaceParentStateEventContent

# change to the script's location
os.chdir(os.path.dirname(__file__))

def get_team_by_name(team_name):
    """
    Get a team JSON by name
    """
    return [team for team in teams if team['name'] == team_name][0]


def get_channels_by_team(team_id):
    """
    Get all the channel IDs with the given mattermost team ID
    """
    return [
        channel['id']
        for channel in channels
        if channel['team_id'] == team_id and channel['id'] not in config.mattermost.skip_channels
    ]


def get_team_alias_localpart(team_name):
    return config.matrix.room_prefix + team_name


async def create_space_for_team(team):
    """
    Given a team JSON, create its space on Matrix, and invite the list of users
    on the config
    """
    app_service = get_app_service()
    api = app_service.bot_intent()
    
    # Create the space (room) (if it doesn't already exist)
    room_mxid, _ = await create_room(
        alias_localpart=get_team_alias_localpart(team['name']),
        name=team['display_name'],
        creation_content=RoomCreateStateEventContent(type=RoomType.SPACE),
        preset=RoomCreatePreset.PUBLIC,
        topic=team['description'],
    )

    # Set avatar if not set
    filename = f"../downloaded/pfp/{team['id']}"
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            avatar = f.read()
        if not await get_room_avatar(room_mxid):
            avatar_mxc = await api.upload_media(
                data=avatar,
                mime_type=magic.from_buffer(avatar, mime=True),
                filename=team['name'],
            )
            await set_room_avatar(room_mxid, avatar_mxc)

    return room_mxid


async def import_team(team_name):
    """
    Import a Mattermost team by name. Currently only imports public
    channels.
    """
    app_service = get_app_service()
    api = app_service.bot_intent()

    team = get_team_by_name(team_name)
    team_id = await create_space_for_team(team)
    channels = get_channels_by_team(team['id'])

    # spec on spaces: https://spec.matrix.org/v1.7/client-server-api/#spaces

    for channel_id in channels:
        room_id = await import_channel(channel_id)
        await api.send_state_event(team_id, EventType.SPACE_CHILD, SpaceChildStateEventContent(via=[config.matrix.homeserver]), room_id)
        await api.send_state_event(room_id, EventType.SPACE_PARENT, SpaceParentStateEventContent(via=[config.matrix.homeserver]), team_id)


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: import_team.py [mattermost team name]", file=sys.stderr)
        print('You may get the channel ID from the Mattermost URL.', file=sys.stderr)
        exit(1)
    team_name = sys.argv[1]
    asyncio.run(import_team(team_name))
    # Close the session when done
    asyncio.run(get_app_service().session.close())
