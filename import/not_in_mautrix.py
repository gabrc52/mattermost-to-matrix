from matrix import get_app_service
from mautrix.api import Method, Path
import mautrix.errors

async def join_user_to_room(user_id, room_id, timestamp):
    """
    Join the user to the given room ID/alias
    at the specified time
    """
    # Works around https://github.com/mautrix/python/issues/151
    # In practice, mautrix accepts timestamp for leave events but not join events
    app_service = get_app_service()
    user_api = app_service.intent(user_id)
    try:
        await user_api.api.request(
            Method.PUT,
            Path.v3.rooms[room_id].state['m.room.member'][user_id],
            timestamp=timestamp,
            content={'membership': 'join'},
        )
    except mautrix.errors.request.MForbidden as e:
        # swallow "is already in the room." errors
        pass
