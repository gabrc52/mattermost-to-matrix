import asyncio
from import_channel import import_channel, channels, teams, create_room
from matrix import get_app_service, config
from mautrix.types import RoomCreateStateEventContent, RoomType, RoomCreatePreset

def get_team_by_name(team_name):
    """
    Get a team JSON by name
    """
    return [team for team in teams if team['name'] == team_name][0]


def get_channels_by_team(team_id):
    """
    Get all the channels with the given mattermost team ID
    """
    return [channel for channel in channels if channel['team_id'] == team_id]


def get_team_alias_localpart(team_name):
    return config.matrix.room_prefix + team_name


async def create_space_for_team(team):
    """
    Given a team JSON, create its space on Matrix, and invite the list of users
    on the config
    """
    # TODO: icon
    await create_room(
        alias_localpart=get_team_alias_localpart(team['name']),
        name=team['display_name'],
        creation_content=RoomCreateStateEventContent(type=RoomType.SPACE),
        preset=RoomCreatePreset.PUBLIC,
    )


async def import_team(team_name):
    """
    Import a Mattermost team by name. Currently only imports public
    channels.
    """
    team = get_team_by_name(team_name)
    await create_space_for_team(team)
    channels = get_channels_by_team(team['id'])


