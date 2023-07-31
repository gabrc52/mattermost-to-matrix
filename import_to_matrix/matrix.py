import asyncio
import os
# Import config from parent directory
# TODO: use an actual module?
# source: https://stackoverflow.com/questions/16780014/import-file-from-parent-directory
import sys

import mautrix.errors
from mautrix.appservice import AppServiceAPI, state_store
from mautrix.types import UserID, EventType, RoomAvatarStateEventContent
from mautrix.util.logging import TraceLogger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

# Let only one instance exist
__app_service: AppServiceAPI = None

# TODO: it might be cursed but if we initialize the AppServiceAPI
# from the bridge, we might need a set_app_service to set this global
# The problem is THAT is an IntentAPI and this is an AppServiceAPI

def get_app_service():
    """
    Creates an object of type AppServiceAPI with our configuration, if it has not been created yet,
    and returns it.

    It can be used to retrieve a Matrix Application-Server client by calling bot_intent() on it,
    or a specific Application-Server API client that acts as a bridged user by calling
    intent(username) on it.
    """
    global __app_service
    if __app_service is None:
        __app_service = AppServiceAPI(
        base_url=config.matrix.homeserver_url,
        bot_mxid=UserID(f'@{config.matrix.username}:{config.matrix.homeserver}'),
        token=config.matrix.as_token,
        # The log and state_store are needed even if AppServiceAPI technically accepts leaving it blank
        log=TraceLogger('log'),
        state_store=state_store.FileASStateStore(path='mau-state.json', binary=False),
    )
    return __app_service    


def get_user_mxid_by_localpart(localpart):
    return f'@{localpart}:{config.matrix.homeserver}'


def get_bridged_user_mxid(username):
    """
    Given the username of a bridged user, return the full MXID
    Given the localpart (username) of a local user, return the full MXID
    """
    return get_user_mxid_by_localpart(config.matrix.user_prefix + username)


def get_alias_mxid(localpart):
    """
    Given the localpart of a room alias, return the full MXID
    """
    return f'#{localpart}:{config.matrix.homeserver}'


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


async def get_room_avatar(room_mxid):
    """
    Gets the room picture, if any.
    Returns None if there is no room picture.
    """
    app_service = get_app_service()
    api = app_service.bot_intent()
    try:
        return await api.get_state_event(room_mxid, EventType.ROOM_AVATAR)
    except mautrix.errors.request.MNotFound:
        return None


async def set_room_avatar(room_mxid, avatar_mxc):
    """
    Sets the room picture.
    """
    app_service = get_app_service()
    api = app_service.bot_intent()
    await api.send_state_event(room_mxid, EventType.ROOM_AVATAR, RoomAvatarStateEventContent(avatar_mxc))