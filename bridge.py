#!/usr/bin/env python3

import sys
import os
import json
import asyncio
import mattermost.ws
from pprint import pprint
from dataclasses import dataclass
from dataclasses_json import dataclass_json
import mautrix.errors
from mautrix.types import TextMessageEventContent, MessageType

from config import config

# naming/organization is unfortunate since we didn't plan for a bridge at the start
from import_to_matrix.import_message import import_message, get_emoji
from import_to_matrix.import_channel import get_mattermost_channel, create_channel
from import_to_matrix.import_user import get_mattermost_user, import_user
from import_to_matrix.matrix import get_app_service, room_exists
from import_to_matrix.not_in_mautrix import remove_reaction
from import_to_matrix.message_state import MessageState
from export_from_mattermost.login import mm

bot_user = mm.get_user()
state = MessageState()

@dataclass_json
@dataclass
class MattermostEvent:
    # Event type
    event: str

    # The actual event
    data: dict

    # Info about where the event was emitted
    broadcast: dict

    # Counter
    seq: int

    def get_mattermost_user_id(self):
        """
        Gets the Mattermost user ID of the event,
        or None if not found
        """
        if 'user_id' in self.broadcast and self.broadcast['user_id']:
            return self.broadcast['user_id']
        if 'user_id' in self.data and self.data['user_id']:
            return self.data['user_id']
        # Reactions have it elsewhere
        if 'reaction' in self.data:
            return json.loads(self.data['reaction'])['user_id']
        # Posts have it elsewhere
        if 'post' in self.data:
            return json.loads(self.data['post'])['user_id']

    
    def get_mattermost_user(self):
        """
        Gets the Mattermost user dict of the event,
        or None if not found
        """
        user_id = self.get_mattermost_user_id()
        if user_id:
            return get_mattermost_user(user_id)
        
    def get_reaction(self):
        """
        Assumes this is a reaction event. Returns a tuple
        with (mattermost message ID, reaction emoji)
        """
        assert 'reaction' in self.data
        dict = json.loads(self.data['reaction'])
        return dict['post_id'], get_emoji(dict['emoji_name'])

        


async def on_mattermost_message(e: MattermostEvent) -> None:
    app_service = get_app_service()

    # Honor channels to ignore
    channel_id = e.broadcast['channel_id']
    if channel_id in config.mattermost.skip_channels:
        return
    channel = get_mattermost_channel(channel_id) if channel_id else None
    room_id = None
    if channel:
        # Not all events are associated with a channel
        room_id, _ = await create_channel(channel_id)

    # Ignore own messages/events
    user_id = e.get_mattermost_user_id()
    if not user_id and e.event != 'posted':
        # Events of type 'posted' have all the data in e.data
        # which is why we can delegate to the other function
        print(f'Warning: event {e.event} has no user ID!')
    if user_id == bot_user['id']:
        return
    
    # TODO: this would fail if someone signs up to Mattermost AFTER the download
    # script has run. Think carefully about all the missing data cases.
    user = e.get_mattermost_user()
    user_mxid, user_api = None, None
    if user:
        user_mxid = await import_user(user_id)
        user_api = app_service.intent(user_mxid)

    match e.event:
        case 'posted':
            print(f"{e.data['sender_name']} sent a message on {e.data['channel_display_name']}")
            # This is a regular message, or system message
            message = json.loads(e.data['post'])
            await import_message(
                message,
                room_id,
                # TODO: don't hardcode and add to config (w/o auto)
                topic_equivalent='both',
                thread_equivalent='thread', # wait, 'reply' would work trivially, just not 'auto'
                state=state,
            )
        case 'post_deleted':
            # TODO: I know this will break when a Mattermost post goes to more than
            # one Matrix message (https://github.com/matrix-org/matrix-spec/issues/541)
            # A solution would be to store the full list of Matrix events for a given Mattermost ID
            # instead of a one-to-one relationship

            message = json.loads(e.data['post'])
            event_id = state.get_matrix_event(message['id'])
            await user_api.redact(room_id, event_id)
        case 'post_edited':
            # We are assuming that people will only edit text messages
            # and only the message will change. It is not always true, for instance
            # people may edit the override_username prop in the worst of cases,
            # which isn't bridgeable into a different ghost.

            # TODO: Due to the same issue of Matrix separating messages,
            # this will also break when attempting to edit a message with attachments
            # The most straightforward solution is to keep ANOTHER table with
            # the event IDs of the text messages 
            
            message = json.loads(e.data['post'])
            original_event_id = state.get_matrix_event(message['id'])
            content = TextMessageEventContent(
                msgtype=MessageType.TEXT,
                body=message['message']
            )
            content.set_edit(original_event_id)
            event_id = await user_api.send_message(room_id, content)            
            # Because the spec says that you cannot edit an edit, we do not store the event ID
        case 'reaction_added':
            try:
                post_id, emoji = e.get_reaction()
                event_id = state.get_matrix_event(post_id)
                await user_api.react(room_id, event_id, emoji)
            except mautrix.errors.MatrixUnknownRequestError as error:
                if error.errcode == 'M_DUPLICATE_ANNOTATION':
                    # Silence errors where Mattermost tries to send the same reaction twice
                    pass
                else:
                    raise error
        case 'reaction_removed':
            post_id, emoji = e.get_reaction()
            event_id = state.get_matrix_event(post_id)
            await remove_reaction(user_api, room_id, event_id, emoji)
        case 'typing':
            print(f"{user['username']} is typing on {channel['name']}")
            await user_api.set_typing(room_id, 2000)
        case 'status_change':
            # TODO bridge
            status = e.data['status']
            print(f"{user['username']} is {status} on {channel['name']}")
        case 'user_update':
            # TODO bridge
            # Display name or profile picture change (or username!)
            pass
        case _:
            print(f"Ignoring unknown event type {e.event}")
        


# define a websocket handler
def handler(mmws, event_data):
    with open('message.log', 'a+') as f:
        pprint(event_data, stream=f)
    # https://stackoverflow.com/questions/44630676/how-can-i-call-an-async-function-without-await
    event = MattermostEvent.from_dict(event_data)
    loop = asyncio.get_event_loop()
    loop.create_task(on_mattermost_message(event))


# connect to websocket and start processing events
mmws = mattermost.ws.MMws(handler, mm, f"wss://{config.mattermost.instance}/api/v4/websocket")

while True: pass