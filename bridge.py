#!/usr/bin/env python3

import sys
import os
import json
import asyncio
import mattermost.ws
from pprint import pprint
from dataclasses import dataclass
from dataclasses_json import dataclass_json

from config import config

# naming/organization is unfortunate since we didn't plan for a bridge at the start
from import_to_matrix.import_message import import_message
from import_to_matrix.import_channel import get_mattermost_channel, create_channel
from import_to_matrix.import_user import get_mattermost_user
from import_to_matrix.matrix import get_app_service, room_exists
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


async def on_mattermost_message(e: MattermostEvent) -> None:
    # Honor channels to ignore
    channel_id = e.broadcast['channel_id']
    channel = get_mattermost_channel(channel_id) if channel_id else None
    if channel_id in config.mattermost.skip_channels:
        return

    # Ignore own messages/events
    user_id = e.broadcast['user_id']
    if user_id == bot_user['id']:
        return

    user = get_mattermost_user(user_id) if user_id else None

    match e.event:
        case 'posted':
            print(f"{e.data['sender_name']} sent a message on {e.data['channel_display_name']}")
            # This is a regular message, or system message
            message = json.loads(e.data['post'])
            room_id, already_existed = await create_channel(channel_id)
            await import_message(
                message,
                room_id,
                # TODO: don't hardcode and add to config (w/o auto)
                topic_equivalent='both',
                thread_equivalent='thread', # wait, 'reply' would work trivially, just not 'auto'
                state=state,
            )
        case 'post_edited':
            # TODO implement
            pass
        case 'post_deleted':
            # TODO implement
            pass
        case 'reaction_added':
            # TODO implement
            # TODO refactor reaction code for DRY
            pass
        case 'reaction_removed':
            # TODO implement
            pass
        case 'typing':
            # broadcast -> user_id is not defined for some odd reason
            # but broadcast -> user_id is (and parent_id)
            user_id = e.broadcast['user_id']
            user = get_mattermost_user(user_id) if user_id else None
            # TODO implement
            print(f"{user['username']} is typing on ")
            pass
        case 'status_change':
            # TODO bridge
            status = e.data['status']
            print(f"{user['username']} is {status} on {channel['name']}")
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
