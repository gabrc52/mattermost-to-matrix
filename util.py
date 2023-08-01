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


def localpart_or_full_mxid(mxid):
    """
    Given a username, get a localpart if local,
    or the full MXID if remote
    """
    localpart, homeserver = mxid[1:].split(':')
    if homeserver == config.matrix.homeserver:
        return localpart
    else:
        return mxid
    

async def get_mattermost_fake_user(matrix_api: IntentAPI, mxid):
    """
    Given a Matrix MXID, get the Mattermost props
    needed to impersonate it
    """
    props = {
        'from_webhook': 'true',
        'from_matrix': 'true',
        'from_bot': 'true',
        'override_username': localpart_or_full_mxid(mxid),
    }
    # override profile picture
    # TODO respect room-specific profile pictures
    avatar_mxc = await matrix_api.get_avatar_url(mxid)
    if avatar_mxc:
        props['override_icon_url'] = str(matrix_api.api.get_download_url(
            avatar_mxc,
            download_type='thumbnail'
        )) + '?width=128&height=128'
    # (attempt to) override display name
    display_name = await matrix_api.get_displayname(mxid)
    if display_name:
        props['webhook_display_name'] = display_name
    return props
    

# TODO: contribute these 2 functoins upstream to the Mattermost API

def pin_mattermost_message(mm_api: MMApi, post_id):
    """
    Pins a Mattermost message by post ID
    """
    mm_api._post(f'/v4/posts/{post_id}/pin')


def unpin_mattermost_message(mm_api: MMApi, post_id):
    """
    Unpins the Mattermost message by post ID
    """
    mm_api._post(f'/v4/posts/{post_id}/unpin')