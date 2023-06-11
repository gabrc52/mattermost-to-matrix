from matrix import get_app_service
from mautrix.api import Method, Path

"""
Join the user to the given room ID/alias
at the specified time
"""
async def join_user_to_room(user_id, room_id, timestamp):
    # TODO:
    # https://spec.matrix.org/v1.7/application-service-api/#timestamp-massaging
    # This does not actually work
    # > Other endpoints, such as /kick, do not support ts: instead, callers can use
    # the PUT /state endpoint to mimic the behaviour of the other APIs.


    # Ideally, this method should not be needed.
    # I don't want to recreate the state store so we will add
    # the users every time
    app_service = get_app_service()
    user_api = app_service.intent(user_id)
    await user_api.api.request(
        Method.POST,
        # Path.v3.join[room _id],
        Path.v3.rooms[room_id].join,
        query_params={
            'ts': timestamp,
            'user_id': user_id,
        },
    )