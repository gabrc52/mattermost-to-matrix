import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from import_to_matrix.matrix import get_app_service
from mautrix.api import Method, Path
from mautrix.appservice import IntentAPI
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

# TODO (very easy): contribute to mautrix so this allows timestamp
# all you need is to add *kwargs to pin_message
async def pin_message(user_api: IntentAPI, room_id, event_id, timestamp):
    """
    pin_message but it supports timestamp massaging
    """
    # copied and pasted from pin_message in intent.py except I actually pass
    # in the timestamp
    events = await user_api.get_pinned_messages(room_id)
    if event_id not in events:
        events.append(event_id)
        await user_api.set_pinned_messages(room_id, events, timestamp=timestamp)


class MessageReaction:
    """
    A Matrix message reaction
    """

    event_id: str
    sender: str
    reaction: str

    def __init__(self, event_id, sender, reaction):
        self.event_id = event_id
        self.sender = sender
        self.reaction = reaction

    @staticmethod
    def from_json(dict):
        return MessageReaction(
            event_id=dict['event_id'],
            sender=dict['sender'],
            reaction=dict['content']['m.relates_to']['key'],
        )
        

async def get_reactions(room_id, event_id) -> list[MessageReaction]:
    """
    Gets all reactions for a given message by room ID and event ID
    """
    app_service = get_app_service()
    user_api = app_service.bot_intent()
    response = await user_api.api.request(
        Method.GET,
        Path.v1.rooms[room_id].relations[event_id]['m.annotation']['m.reaction'],
    )
    return [MessageReaction.from_json(reaction) for reaction in response['chunk']]


async def remove_reaction(user_api: IntentAPI, room_id, event_id, emoji):
    """
    Using the given user API, removes the given reaction identified by room ID,
    event ID and emoji (or text). If the reaction does not exist, do nothing.
    """
    reactions = await get_reactions(room_id, event_id)
    result = [
        reaction for reaction in reactions
        if reaction.sender == user_api.mxid
            and reaction.reaction == emoji
    ]
    # Do not proceed if we could not find a reaction
    if not result:
        return
    # Now we can redact it
    reaction = result[0]
    return await user_api.redact(room_id, reaction.event_id)


async def get_room_aliases(user_api: IntentAPI, room_id) -> list[str]:
    response = await user_api.api.request(
        Method.GET,
        Path.v3.rooms[room_id].aliases
    )
    return response['aliases']