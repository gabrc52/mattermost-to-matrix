import json
import sys

import markdown
import mautrix.errors
from import_user import import_user
from matrix import config, get_app_service
from mautrix.types import (BaseFileInfo, EventType, Format, ImageInfo,
                           Membership, MemberStateEventContent, MessageType,
                           RoomNameStateEventContent,
                           RoomTopicStateEventContent, TextMessageEventContent)
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


async def import_files_in_message(message, room_id, user_api):
    """
    Send the files in the Mattermost message as separate Matrix messages.

    Returns the Matrix event ID of the last file sent
    """
    for file in message['metadata']['files']:
        # Upload first
        filename = f'../downloaded/media/{file["id"]}'
        with open(filename, 'rb') as f:
            contents = f.read()
            image_uri = await user_api.upload_media(contents, file['mime_type'], file['name'])

        if file['mime_type'].startswith('image'):
            # Images
            event_id = await user_api.send_image(
                room_id,
                url=image_uri,
                info=ImageInfo(
                    mimetype=file['mime_type'],
                    size=file['size'],
                    height=file['height'],
                    width=file['width'],
                ),
                file_name=file['name'],
                timestamp=message['create_at'],
            )
        else:
            # Other attachments
            event_id = await user_api.send_file(
                room_id,
                url=image_uri,
                info=BaseFileInfo(
                    mimetype=file['mime_type'],
                    size=file['size'],
                ),
                file_name=file['name'],
                timestamp=message['create_at'],
            )
    return event_id


async def import_message(message, room_id, topic_equivalent):
    """
    Import a specific message from the Mattermost JSON format
    into the specified room ID

    topic_equivalent can be header, purpose or both, for what to treat
    as a Matrix topic
    """
    app_service = get_app_service()
    api = app_service.bot_intent()

    user_mxid = await import_user(message['user_id'])
    user_api = app_service.intent(user_mxid)

    # Messages without a type are normal messages
    if not message['type']:
        if message['message']:
            # event_id = await user_api.send_text(room_id, message['message'], timestamp=message['create_at'])
            event_id = await user_api.send_message(
                room_id,
                TextMessageEventContent(
                    msgtype=MessageType.TEXT,
                    body=message['message'],
                    formatted_body=md.convert(message['message']),
                    format=Format.HTML,
                ),
                timestamp=message['create_at']
            )

        # Handle media
        if 'files' in message['metadata']:
            event_id = await import_files_in_message(message, room_id, user_api)

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
        await user_api.send_state_event(
            room_id,
            EventType.ROOM_MEMBER,
            MemberStateEventContent(
                membership=Membership.LEAVE
            ),
            removed_matrix_user,
            timestamp=message['create_at'],
        )
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
