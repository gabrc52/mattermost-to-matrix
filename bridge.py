#!/usr/bin/env python3

import sys
import os
import json
import asyncio
import mattermost.ws
from pprint import pprint
import mautrix.errors
from mautrix.types import TextMessageEventContent, MessageType, PresenceState, MessageEvent, ReactionEvent, RedactionEvent, StateEvent, EventType, MediaMessageEventContent
from mautrix.appservice import AppService

from util import config, is_bridged_user, matrix_to_mattermost_channel, get_mattermost_fake_user

# naming/organization is unfortunate since we didn't plan for a bridge at the start
from import_to_matrix.import_message import import_message
from import_to_matrix.import_channel import get_mattermost_channel, create_channel
from import_to_matrix.import_user import import_user, import_user_from_json
from import_to_matrix.matrix import get_app_service, room_exists
from import_to_matrix.not_in_mautrix import remove_reaction
from import_to_matrix.message_state import MessageState
from export_from_mattermost.login import mm
from export_from_mattermost.mattermost_event import MattermostEvent

import logging
logging.basicConfig(
    # Uncomment to have all our libraries dump loads of log lines
    # level=1
)

bot_user = mm.get_user()
state = MessageState()

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
    if not user_id and e.event not in ('posted', 'user_updated'):
        # Events of type 'posted' have all the data in e.data
        # which is why we can delegate to the other function
        # Similarly for profile changes
        print(f'Warning: event {e.event} has no user ID!')
    if user_id == bot_user['id']:
        return

    user = e.get_mattermost_user()
    user_mxid, user_api = None, None
    if user:
        user_mxid = await import_user_from_json(user)
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
            message = json.loads(e.data['post'])
            event_ids = state.get_matrix_full_event_list(message['id'])
            for event_id in event_ids:
                await user_api.redact(room_id, event_id)            
        case 'post_edited':
            # We are assuming that people will only edit text messages
            # and only the message will change. It is not always true, for instance
            # people may edit the override_username prop in the worst of cases,
            # which isn't bridgeable into a different ghost.
            message = json.loads(e.data['post'])
            original_event_id = state.get_matrix_text_event(message['id'])
            if original_event_id:
                content = TextMessageEventContent(
                    msgtype=MessageType.TEXT,
                    body=message['message']
                )
                content.set_edit(original_event_id)
                event_id = await user_api.send_message(room_id, content)            
                # Because the spec says that you cannot edit an edit, we do not store the event ID
                if message['is_pinned']:
                    # Unimportant bug: pinned messages will show as edited no matter what
                    await user_api.pin_message(room_id, event_id)
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
            # Interestingly, these events only appear for the bot's user ID
            # TODO: see if I've gotten a response in 
            # https://community.mattermost.com/core/pl/fodkj3o7minf5rzg7uc74hnsxr

            # The web client calls this endpoint to get presence
            # https://mattermost.mit.edu/api/v4/users/status/ids

            status = e.data['status']
            matrix_status = {
                'online': PresenceState.ONLINE,
                'away': PresenceState.UNAVAILABLE,
                'offline': PresenceState.OFFLINE,
                'dnd': PresenceState.UNAVAILABLE,
            }

            print(f"{user['username']} is {status}")
            await user_api.set_presence(matrix_status[status])
        case 'user_updated':
            # Display name or profile picture change

            # TODO: my setup assumes people do not change their username.
            # Test what happens if someone does change their username.
            await import_user_from_json(e.data['user'])
        case _:
            print(f"Ignoring unknown event type {e.event}")
        


# define a websocket handler
def handler(mmws, event_data):
    # TODO: remove
    with open('message.log', 'a+') as f:
        pprint(event_data, stream=f)
    # https://stackoverflow.com/questions/44630676/how-can-i-call-an-async-function-without-await
    event = MattermostEvent.from_dict(event_data)
    loop = asyncio.get_event_loop()
    loop.create_task(on_mattermost_message(event))


async def on_matrix_message(evt: MessageEvent) -> None:
    print(evt)
    
    api = app_service_listener.intent

    # so is it Event or any of the union types?
    # does it automatically only send it if the type matches?
    if evt.type == EventType.ROOM_MESSAGE:
        # First, ignore our own messages
        if is_bridged_user(evt.sender):
            print("Ignoring")
            return
        channel_id = await matrix_to_mattermost_channel(mm, api, evt.room_id)
        print("Mattermost:", channel_id)
        # don't like that we're mixing async with sync stuff
        props = await get_mattermost_fake_user(api, evt.sender)
        if isinstance(evt.content, MediaMessageEventContent):
            message = f"[{evt.content.body}]({api.api.get_download_url(evt.content.url)})"
            if evt.content.msgtype == MessageType.IMAGE:
                message = '!' + message
        else:
            message = evt.content.body
        # deal with threads
        matrix_thread_parent = evt.content.get_thread_parent()
        if matrix_thread_parent:
            mattermost_thread_parent = state.get_mattermost_event(matrix_thread_parent)
            post = mm.create_post(channel_id, message, props, root_id=mattermost_thread_parent)
        else:
            post = mm.create_post(channel_id, message, props)
        state.remember_matrix_event(
            mattermost_id=post['id'],
            matrix_id=evt.event_id,
        )


async def on_matrix_state_event(evt: StateEvent):
    if evt.type == EventType.ROOM_MEMBER:
        # no need to join ghost users on the other side, since it's just a webhook
        pass


async def init_matrix_half():
    """
    Initializes the Matrix->Mattermost half of the bridge
    """
    global app_service_listener
    # Note that this lets you get the REST client, through the 
    # `intent` method, so we have a duplicate REST client now.
    # We should deal with it somehow. For now, we can keep using
    # just the AppServiceAPI instead of the IntentAPI
    app_service_listener = AppService(
        server=config.matrix.homeserver_url,
        domain=config.matrix.homeserver,
        as_token=config.matrix.as_token,
        hs_token=config.matrix.hs_token,
        bot_localpart=config.matrix.username,
        id='mattermost',
        bridge_name='mattermost',
    )
    await app_service_listener.start(
        host=config.matrix.listen_address,
        port=config.matrix.listen_port
    )
    app_service_listener.matrix_event_handler(on_matrix_message)
    app_service_listener.matrix_event_handler(on_matrix_state_event)


# connect to websocket and start processing events
# This is enough to initialize the Mattermost->Matrix half
mmws = mattermost.ws.MMws(handler, mm, f"wss://{config.mattermost.instance}/api/v4/websocket")
loop = asyncio.get_event_loop()
loop.create_task(init_matrix_half())
loop.run_forever()
