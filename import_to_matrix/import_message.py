import json
import sys
import markdown
import mautrix.errors
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from import_to_matrix.import_user import create_user, import_user
from import_to_matrix.matrix import config, get_app_service, get_bridged_user_mxid
from mautrix.types import (BaseFileInfo, BaseMessageEventContent, EventType,
                           Format, ImageInfo, MediaMessageEventContent,
                           Membership, MemberStateEventContent, MessageType,
                           RoomNameStateEventContent,
                           RoomTopicStateEventContent, TextMessageEventContent)
from import_to_matrix.message_state import MessageState
from import_to_matrix.not_in_mautrix import join_user_to_room, pin_message
from export_from_mattermost.login import mm

emojis: dict = json.load(open('../downloaded/emoji.json', 'r'))
emojis_inverse: dict = json.load(open('../downloaded/emoji_inverse.json', 'r'))

# https://stackoverflow.com/a/70921001/5031798
# Remove <p> tags which don't play with Element Android
class EMarkdown(markdown.Markdown):
    def convert(self, text):
        t = super().convert(text)
        t = t.removeprefix("<p>").removesuffix("</p>")
        return t

md = EMarkdown(extensions=[
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


def get_emoji(emoji_name):
    """
    Get an emoji from a Mattermost emoji name
    """
    # Currently just use the name for custom reactions because Matrix does not have them yet
    return emojis.get(emoji_name) or emoji_name


def get_emoji_name(emoji):
    """
    Get a Mattermost emoji name from an emoji, if any
    """
    return emojis_inverse.get(emoji)


def get_reaction(reaction):
    """
    From a Mattermost reaction, get a tuple
    (Mattermost user ID, reaction, timestamp)
    """
    return (reaction['user_id'], get_emoji(reaction['emoji_name']), reaction['create_at'])


def get_reactions(reactions):
    """
    From a Mattermost array of reactions, get a set of tuples as
    (Mattermost user ID, reaction, timestamp)
    """
    return remove_duplicates_special({get_reaction(reaction) for reaction in reactions})


async def import_message(message, room_id, topic_equivalent, thread_equivalent, state: MessageState, thread_sizes = None):
    """
    Import a specific message from the Mattermost JSON format
    into the specified room ID

    topic_equivalent can be header, purpose or both, for what to treat
    as a Matrix topic

    thread_equivalent can be reply, thread or auto. If thread_equivalent is auto,
    it will only import threads if they have enough messages, which requires knowing
    how many messages the thread has, so it only works in backfill mode (since for
    bridge mode we can't predict how many messages the thread *will have*)
    """
    # Process / validate some options related to backfilling
    assert topic_equivalent in ('header', 'purpose', 'both')
    if thread_equivalent == 'auto' and message['root_id']:
        assert thread_sizes is not None
        if thread_sizes[message['root_id']] >= config.mattermost.backfill.thread_threshold:
            thread_equivalent = 'thread'
        else:
            thread_equivalent = 'reply'
        assert thread_equivalent in ('thread', 'reply')
    # Honor the "always thread" option
    if message['channel_id'] in config.mattermost.always_thread:
        thread_equivalent = 'thread'

    app_service = get_app_service()
    api = app_service.bot_intent()

    # Respect request to override username
    if 'override_username' in message['props']:
        username = message['props']['override_username']
        if config.prefer_usernames:
            display_name = username
        else:
            display_name = message['props'].get('webhook_display_name') or username
        user_mxid = get_bridged_user_mxid(username)
        platform = 'Mattermost' # or mattermost webhook perhaps?
        # Apply a custom prefix if using Zephyr (MIT-specific functionality)
        if 'from_zephyr' in message['props']:
            user_mxid = user_mxid.replace(config.matrix.user_prefix, '_zephyr_')
            platform = 'Zephyr'
        display_name = config.matrix.display_name_format.format(name=display_name, platform=platform)
        # TODO: set the avatar, perhaps a hardcoded one, or the pfp of the account itself
        # if it really is a bot...
        # note that even mattermost itself uses the pfp of the user who created the webhook
        # if "Enable integrations to override profile picture icons" is disabled
        await create_user(user_mxid, display_name, is_zephyr=platform == 'Zephyr')

        # add user to the room, otherwise the join timestamp will be wrong...
        await join_user_to_room(user_mxid, room_id, timestamp=message['create_at'])
    else:
        user_mxid = await import_user(message['user_id'])
        
    user_api = app_service.intent(user_mxid)
    event_ids = []

    # Messages without a type are normal messages
    if not message['type'] or message['type'] == 'slack_attachment':
        # We stop typing when we send a message
        await user_api.set_typing(room_id, 0)

        matrix_thread_root = state.get_matrix_event(message['root_id'])
        # the second condition is needed because malfunctioning Mattermost bots may reply to a "System message"
        # which we do not consider a message (although they do have Matrix event IDs; I'm not sure if
        # you can technically reply to a member event, but tbh you shouldn't)
        if message['root_id'] and matrix_thread_root:
            # not really the message we are replying to but the one above, because
            # Mattermost does not keep track of which message you clicked "reply" on
            mattermost_reply_to = state.get_most_recent_message_in_thread(message['root_id']) or message['root_id']
            matrix_reply_to = state.get_matrix_event(mattermost_reply_to)
            
            # application services may not necessarily process messages in order
            # which is another reason why we cannot easily support `thread_equivalent='reply'`
            # when running on real-time
            state.set_most_recent_message_in_thread(message['root_id'], message['id'])

            def set_reply_or_thread(content: BaseMessageEventContent):
                if thread_equivalent == 'reply':
                    content.set_reply(matrix_reply_to)
                else:
                    content.set_thread_parent(thread_parent=matrix_thread_root, last_event_in_thread=matrix_reply_to)
        else:
            def set_reply_or_thread(_):
                pass
        
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
            event_ids.append(text_event_id := await user_api.send_message(
                room_id,
                content,
                timestamp=message['create_at']
            ))
            state.remember_matrix_text_event(
                mattermost_id=message['id'],
                matrix_id=text_event_id,
            )
            # TODO: if edited, edit it right after so it says edited

        # Handle media
        if 'files' in message['metadata']:
            for file in message['metadata']['files']:
                # Upload first
                filename = f'../downloaded/media/{file["id"]}'
                if os.path.exists(filename):
                    with open(filename, 'rb') as f:
                        contents = f.read()
                else:
                    # Download if we haven't yet (only in memory is fine)
                    contents = mm.get_file(file['id']).content
                    
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
                event_ids.append(await user_api.send_message(room_id, content, timestamp=message['create_at']))

        # Handle Slack attachments
        if message['type'] == 'slack_attachment' and 'attachments' in message['props']:
            print('Warning: Slack-type messages are not fully supported. Send an issue/PR if you want better support.', file=sys.stderr)
            for attachment in message['props']['attachments']:
                event_ids.append(await user_api.send_message(
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
                ))

        # if there was no message sent, there is nothing left to do
        if not event_ids: return

        # Store the full list of event IDs
        # We will need it for deletions
        state.set_matrix_event_list(message['id'], event_ids)

        # Get the last event ID
        event_id = event_ids[-1]

        # store event ID
        state.remember_matrix_event(mattermost_id=message['id'], matrix_id=event_id)

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
        try:
            await user_api.send_state_event(
                room_id,
                EventType.ROOM_MEMBER,
                MemberStateEventContent(
                    membership=Membership.INVITE,
                    displayname=await user_api.get_displayname(invited_matrix_user),
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
    elif message['type'] in ('system_join_team', 'system_leave_team', 'system_add_to_team', 'system_remove_from_team'):
        # ignore team joins/leaves, they're unnecessary spam
        # (they _could_ be bridged into space-room joins/leaves but, why.)
        # PRs welcome if you disagree
        pass
    else:
        print('Warning: not bridging unknown message type', message['type'], file=sys.stderr)
