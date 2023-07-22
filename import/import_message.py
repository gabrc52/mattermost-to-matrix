import json
import sys

import markdown
import mautrix.errors
from import_user import create_user, import_user
from matrix import config, get_app_service, get_bridged_user_mxid
from mautrix.types import (BaseFileInfo, BaseMessageEventContent, EventType,
                           Format, ImageInfo, MediaMessageEventContent,
                           Membership, MemberStateEventContent, MessageType,
                           RoomNameStateEventContent,
                           RoomTopicStateEventContent, TextMessageEventContent)
from message_state import MessageState
from not_in_mautrix import join_user_to_room, pin_message

emojis: dict = json.load(open('../downloaded/emoji.json', 'r'))

md = markdown.Markdown(extensions=[
    'markdown.extensions.fenced_code',
    'markdown.extensions.tables',
    'markdown.extensions.nl2br',
    'pymdownx.magiclink',
    'pymdownx.tilde'
], extension_configs={
    'pymdownx.tilde': {
        'subscript': False,
    }
})

def remove_duplicates_special(tuples):
    """
    From a set of tuples (a,b,c), remove the duplicates
    by ensuring that no two tuples (xa,xb,xc), (ya,yb,yc) have xa=ya and xb=yb

    Fill out c by choosing arbitrarily between any of the duplicates, if applicable
    """
    # Rationale: someone can react with both +1 and thumbsup in Mattermost,
    # and the duplicate reactions appear in the exported JSON.
    # Matrix will complain about duplicate reactions, because they both map to 👍
    helper_dict = {(a,b): c for a,b,c in tuples}
    return {(k[0], k[1], v) for k,v in helper_dict.items()}


def get_reactions(reactions):
    """
    From a Mattermost array of reactions, get a set of tuples as
    (Mattermost user ID, reaction, timestamp)
    """
    return remove_duplicates_special({
        # Currently just use the name for custom reactions because Matrix does not have them yet
        (reaction['user_id'], emojis.get(reaction['emoji_name']) or reaction['emoji_name'], reaction['create_at'])
        for reaction in reactions
    })


async def import_message(message, room_id, topic_equivalent, state: MessageState, thread_sizes = None):
    """
    Import a specific message from the Mattermost JSON format
    into the specified room ID

    topic_equivalent can be header, purpose or both, for what to treat
    as a Matrix topic
    """
    # Process / validate some options related to backfilling
    assert topic_equivalent in ('header', 'purpose', 'both')
    thread_equivalent = config.mattermost.backfill.thread_equivalent
    if thread_equivalent == 'auto' and message['root_id']:
        assert thread_sizes is not None
        if thread_sizes[message['root_id']] >= config.mattermost.backfill.thread_threshold:
            thread_equivalent = 'thread'
        else:
            thread_equivalent = 'reply'
        assert thread_equivalent in ('thread', 'reply')

    app_service = get_app_service()
    api = app_service.bot_intent()

    # Respect request to override username
    if 'override_username' in message['props']:
        username = message['props']['override_username']
        # TODO: use username if force_username is true in config
        display_name = message['props'].get('webhook_display_name') or username
        user_mxid = get_bridged_user_mxid(username)
        # TODO: set the avatar, perhaps a hardcoded one, or the pfp of the account itself
        # if it really is a bot...
        # note that even mattermost itself uses the pfp of the user who created the webhook
        # if "Enable integrations to override profile picture icons" is disabled
        await create_user(user_mxid, display_name)
    else:
        user_mxid = await import_user(message['user_id'])
        
    user_api = app_service.intent(user_mxid)

    # Messages without a type are normal messages
    if not message['type'] or message['type'] == 'slack_attachment':
        # get event IDs of reply/thread if needed
        if message['root_id']:
            mattermost_reply_to = state.most_recent_message_in_thread.get(message['root_id']) or message['root_id']
            matrix_thread_root = state.matrix_event_id[message['root_id']]
            matrix_reply_to = state.matrix_event_id[mattermost_reply_to]
            state.most_recent_message_in_thread[message['root_id']] = message['id']
        
        def set_reply_or_thread(content: BaseMessageEventContent):
            if message['root_id']:                
                if thread_equivalent == 'reply':
                    content.set_reply(matrix_reply_to)
                else:
                    content.set_thread_parent(thread_parent=matrix_thread_root, last_event_in_thread=matrix_reply_to)

        # Handle (rich) text messages
        if message['message']:
            content = TextMessageEventContent(
                msgtype=MessageType.TEXT,
                body=message['message'],
                formatted_body=md.convert(message['message']),
                format=Format.HTML,
            )
            # set reply if needed
            set_reply_or_thread(content)
            # send message
            event_id = await user_api.send_message(
                room_id,
                content,
                timestamp=message['create_at']
            )

        # Handle media
        if 'files' in message['metadata']:
            for file in message['metadata']['files']:
                # Upload first
                filename = f'../downloaded/media/{file["id"]}'
                with open(filename, 'rb') as f:
                    contents = f.read()
                    file_uri = await user_api.upload_media(contents, file['mime_type'], file['name'])
                
                is_image = file['mime_type'].startswith('image')

                # Send message
                content = MediaMessageEventContent(
                    msgtype=MessageType.IMAGE if is_image else MessageType.FILE,
                    body=file['name'],
                    url=file_uri,
                    info=ImageInfo(
                        mimetype=file['mime_type'],
                        size=file['size'],
                        height=file['height'],
                        width=file['width'],
                    ) if is_image else BaseFileInfo(mimetype=file['mime_type'], size=file['size']),
                )
                set_reply_or_thread(content)
                event_id = await user_api.send_message(room_id, content)

        # Handle Slack attachments
        if message['type'] == 'slack_attachment' and 'attachments' in message['props']:
            print('Warning: Slack-type messages are not fully supported. Send an issue/PR if you want better support.', file=sys.stderr)
            for attachment in message['props']['attachments']:
                event_id = await user_api.send_message(
                    room_id,
                    TextMessageEventContent(
                        msgtype=MessageType.TEXT,
                        # as you can see, we are using the "text" but ignoring all the other attributes
                        # (this is why they're partially supported at the moment)
                        body=attachment['text'],
                        formatted_body=f"<pre><code>{attachment['text']}</code></pre>",
                        format=Format.HTML,
                    ),
                    timestamp=message['create_at'],
                )

        # store event ID
        state.matrix_event_id[message['id']] = event_id

        # Handle reactions
        # Specifically, react to the last event ID
        if 'reactions' in message['metadata']:
            for user_id, emoji, timestamp in get_reactions(message['metadata']['reactions']):
                reactor_mxid = await import_user(user_id)
                reactor_api = app_service.intent(reactor_mxid)
                await reactor_api.react(room_id, event_id, emoji, timestamp=timestamp)

        if message['is_pinned']:
            await pin_message(user_api, room_id, event_id, timestamp=message['create_at'])
    elif message['type'] == 'system_join_channel':
        await join_user_to_room(user_mxid, room_id, timestamp=message['create_at'])
    elif message['type'] == 'system_leave_channel':
        await user_api.send_state_event(
            room_id,
            EventType.ROOM_MEMBER,
            MemberStateEventContent(membership=Membership.LEAVE),
            user_mxid,
            timestamp=message['create_at'],
        )
    elif message['type'] == 'system_add_to_channel':
        invited_user_id = message['props']['addedUserId']
        invited_matrix_user = await import_user(invited_user_id)
        invited_api = app_service.intent(invited_matrix_user)
        try:
            await user_api.send_state_event(
                room_id,
                EventType.ROOM_MEMBER,
                MemberStateEventContent(
                    membership=Membership.INVITE,
                    displayname=await user_api.get_displayname(user_mxid),
                ),
                invited_matrix_user,
                timestamp=message['create_at'],
            )
        except mautrix.errors.request.MForbidden:
            # ignore exception if you try to invite someone already in the room
            pass
        await join_user_to_room(invited_matrix_user, room_id, timestamp=message['create_at'])
    elif message['type'] == 'system_remove_from_channel':
        removed_user_id = message['props']['removedUserId']
        removed_matrix_user = await import_user(removed_user_id)
        kick = lambda api: api.send_state_event(
            room_id,
            EventType.ROOM_MEMBER,
            MemberStateEventContent(
                membership=Membership.LEAVE
            ),
            removed_matrix_user,
            timestamp=message['create_at'],
        )
        try:
            await kick(user_api)
        except mautrix.errors.request.MForbidden:
            # kick using app service account if ghost does not have enough permissions
            await kick(api)
    elif message['type'] == 'system_displayname_change':
        await user_api.send_state_event(
            room_id,
            EventType.ROOM_NAME,
            RoomNameStateEventContent(name=message['props']['new_displayname']),
            timestamp=message['create_at'],
        )
    elif message['type'] == 'system_header_change':
        if topic_equivalent in ('header', 'both'):
            await user_api.send_state_event(
                room_id,
                EventType.ROOM_TOPIC,
                RoomTopicStateEventContent(topic=message['props']['new_header']),
                timestamp=message['create_at'],
            )
    elif message['type'] == 'system_purpose_change':
        if topic_equivalent in ('purpose', 'both'):
            await user_api.send_state_event(
                room_id,
                EventType.ROOM_TOPIC,
                RoomTopicStateEventContent(topic=message['props']['new_purpose']),
                timestamp=message['create_at']
            )
    else:
        print('Warning: not bridging unknown message type', message['type'], file=sys.stderr)
