import asyncio
import json
import os
import sys

import magic
from matrix import get_app_service, get_bridged_user_mxid

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
    # TODO: add config option to only use username

    # Being preentive if people have a spare space after their first name
    full_name = (user['first_name']+' '+user['last_name']).strip().replace('  ', ' ')
    username = user['username']
    if full_name:
        return full_name
    else:
        return username


async def import_user(user_id):
    """
    Creates a given Mattermost user into a Matrix bridged user,
    if it does not exist already.

    Returns its MXID.
    """
    app_service = get_app_service()
    api = app_service.bot_intent()
    user = get_mattermost_user(user_id)
    username = user['username']
    mxid = get_bridged_user_mxid(username)

    # Get user API
    user_api = app_service.intent(mxid)

    # Create user if needed
    await user_api.ensure_registered()

    # Set user display name
    await user_api.set_displayname(get_displayname(user))

    filename = f"../downloaded/pfp/{user_id}"
    
    # Set user profile picture if needed
    # TODO: this assumes the profile picture never changes
    # If this turns into a bridge, bridge pfp changes too
    avatar_url = await user_api.get_avatar_url(mxid)
    if not avatar_url and os.path.exists(filename):
        with open(filename, 'rb') as f:
            contents = f.read()
            image_uri = await user_api.upload_media(contents, magic.from_buffer(contents, mime=True), f.name)
            await user_api.set_avatar_url(image_uri)

    return mxid

