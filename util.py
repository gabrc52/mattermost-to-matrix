from mautrix.appservice import IntentAPI
import mautrix.errors
from mattermost import MMApi
from import_to_matrix.matrix import get_app_service
from import_to_matrix.not_in_mautrix import get_room_aliases
from config import config

def is_bridged_user(mxid: str) -> bool:
    """
    whether this is a fake/ghost/bridged user that belongs to us
    """
    localpart, homeserver = mxid[1:].split(':')
    return homeserver == config.matrix.homeserver \
        and localpart.startswith(config.matrix.user_prefix)


async def matrix_to_mattermost_channel(mm_api: MMApi, matrix_api: IntentAPI, room_id: str) -> str:
    """
    Given a Matrix room ID, get a Mattermost channel ID.
    Returns None if it could not be found.
    """
    # Try using a custom state event first
    try:
        # TODO: send these on import
        custom_state = await matrix_api.get_state_event(room_id, 'edu.mit.sipb.mattermost')
        return custom_state['channel_id']
    except mautrix.errors.MNotFound:
        # Otherwise, get it from the alias
        aliases = await get_room_aliases(matrix_api, room_id)
        for alias in aliases:
            localpart, homeserver = alias[1:].split(':')
            if localpart.startswith(config.matrix.room_prefix) and homeserver == config.matrix.homeserver:
                team_name, channel_name = localpart[len(config.matrix.room_prefix):].split('_')
                # I could've used the downloaded files, but I'd rather ask Mattermost
                teams = mm_api.get_teams()
                team = [team for team in teams if team['name'] == team_name][0]
                channel = mm_api.get_channel_by_name(team['id'], channel_name)
                return channel['id']
    