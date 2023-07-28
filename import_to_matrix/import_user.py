import asyncio
import json
import os
import sys
import magic
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from import_to_matrix.matrix import get_app_service, get_bridged_user_mxid, config

if not os.path.exists('../downloaded/users.json'):
    print(f'users.json not found! Run export_users.py first.', file=sys.stderr)
    exit(1)

users = json.load(open('../downloaded/users.json'))

def get_mattermost_user(user_id):
    """
    Get the Mattermost record from the given user, by reading
    the exported data.
    """
    results = [user for user in users if user['id'] == user_id]
    if not results:
        # TODO: maybe this may arise if someone deleted their account
        raise ValueError('Inexistent Mattermost user ID')
    return results[0]


def get_displayname(user: dict):
    """
    Given a Mattermost user dictionary, get their display name
    (the concatenation of first name and last name if applicable, otherwise,
    their username)
    """
    # Being preentive if people have a spare space after their first name
    full_name = (user['first_name']+' '+user['last_name']).strip().replace('  ', ' ')
    username = user['username']

    if config.prefer_usernames or not full_name:
        return username
    else:
        return full_name


async def create_user(mxid, display_name, avatar_mxc=None, avatar_bytes=None, avatar_filename=None):
    """
    Creates a matrix user with the given mxid, display name
    and avatar (either mxc or bytes). If avatar_bytes is specified,
    avatar_filename may be specified too. Returns its MXID
    """
    # specifying either type of avatar is mutually exclusive
    assert avatar_mxc is None or avatar_bytes is None

    app_service = get_app_service()
    user_api = app_service.intent(mxid)

    # Create user if needed
    await user_api.ensure_registered()

    # Set user display name
    await user_api.set_displayname(display_name, check_current=True)

    # Set profile picture if not set
    # TODO: If this turns into a bridge, bridge pfp changes too
    if not await user_api.get_avatar_url(mxid):
        if avatar_bytes:
            avatar_mxc = await user_api.upload_media(
                data=avatar_bytes,
                mime_type=magic.from_buffer(avatar_bytes, mime=True),
                filename=avatar_filename or 'pfp',
            )
        await user_api.set_avatar_url(avatar_mxc)
    
    return mxid


async def import_user(user_id):
    """
    Creates a given Mattermost user into a Matrix bridged user,
    if it does not exist already.

    Returns its MXID.
    """
    user = get_mattermost_user(user_id)
    username = user['username']
    mxid = get_bridged_user_mxid(username)

    filename = f"../downloaded/pfp/{user_id}"
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            avatar = f.read()
    else:
        avatar = None

    display_name = config.matrix.display_name_format.format(
        name=get_displayname(user),
        platform='Mattermost',
    )

    return await create_user(mxid, display_name, avatar_bytes=avatar)

