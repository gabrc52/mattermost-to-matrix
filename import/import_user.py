from matrix import get_app_service, get_bridged_user_mxid
import json
import os
import asyncio

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
    # TODO: add config option to only use username (important for mattermost.mit.edu
    # because it's patched to display usernames)

    # Being preentive if people have a spare space after their first name
    full_name = (user['first_name']+' '+user['last_name']).strip().replace('  ', ' ')
    username = user['username']
    if full_name:
        return full_name
    else:
        return username


async def import_user(user_id):
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
    # Set user profile picture
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            contents = f.read()
            # TODO: they are all PNG for me, but it would be best not to hardcode
            mime_type = 'image/png'
            image_uri = await user_api.upload_media(contents, mime_type, f.name)
            await user_api.set_avatar_url(image_uri)

