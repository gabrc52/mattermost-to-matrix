"""
utility script to remove all rooms in a space, or at least the closest
matrix supports to deleting a space. specifically:

1. resetting the aliases so this bridge can make rooms again
2. removing everyone since according to the spec this makes the rooms eligible for deletion

(aka i ran this bridge and fucked up so i need to redo everything)
"""

import sys
import asyncio
from import_to_matrix.matrix import get_app_service
from import_to_matrix.not_in_mautrix import get_room_aliases
from mautrix.types import EventType
import mautrix.errors
from progress.bar import Bar

async def get_children(room_id):
    """
    gets all the children of this space
    """
    # yeah we still need a more high level library
    # this isn't accessible enough for people willing to integrate with matrix but
    # not willing to learn the nitty-gritty of how rooms and state events work **internally**
    # Or we can contribute to this library to add more methods (like get all aliases,
    # get all children in a space, etc)
    state_events = await api.get_state(room_id)
    return [
        event.state_key
        for event in state_events
        if event.type == EventType.SPACE_CHILD
    ]


def get_localpart(mxid):
    return mxid[1:].split(':')[0]


async def remove_all_aliases(room_id):
    """
    remove all aliases in this room
    """
    # remove all aliases
    for alias in await get_room_aliases(api, room_id):
        await api.remove_room_alias(get_localpart(alias))
    # remove canonical alias
    await api.send_state_event(
        room_id,
        EventType.ROOM_CANONICAL_ALIAS,
        {},
    )


async def kick_everyone(room_id):
    members = await api.get_members(room_id)
    # Kick everyone but the bot
    for member in members:
        user_id = member.state_key
        if user_id == api.mxid:
            continue
        try:
            await api.kick_user(room_id, user_id)
        except mautrix.errors.request.MForbidden as e:
            try:
                await app_service.intent(user_id).leave_room(room_id)
            except Exception as e:
                print(user_id, e)
    # Leave as the bot
    await api.leave_room(room_id)


async def delete_space(space_id):
    """
    deletes the aliases of all rooms in this space
    (not recursive)
    """
    global app_service, api
    app_service = get_app_service()
    api = app_service.bot_intent()


    children = await get_children(space_id)
    with Bar(f'"Deleting" space', max=len(children)) as bar:
        for room_id in children:
            await remove_all_aliases(room_id)
            await api.set_room_name(room_id, "delete me")
            await kick_everyone(room_id)
            bar.next()

    await app_service.session.close()


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} [space ID]", file=sys.stderr)
        print('You may get the channel ID from Mattermost ("view info") or channels.json.', file=sys.stderr)
        exit(1)
    space_id = sys.argv[1]
    asyncio.run(delete_space(space_id))
