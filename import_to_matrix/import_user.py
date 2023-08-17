import asyncio
import json
import os
import sys
import magic
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from import_to_matrix.matrix import get_app_service, get_bridged_user_mxid, config
from export_from_mattermost.login import mm
from export_from_mattermost.media import get_profile_picture_bytes
os.chdir(os.path.dirname(__file__))

if not os.path.exists('../downloaded/users.json'):
    print(f'users.json not found! Run export_users.py first.', file=sys.stderr)
    exit(1)

users = json.load(open('../downloaded/users.json'))

def get_mattermost_user(user_id):
    """
    Get the Mattermost record from the given user, by querying Mattermost
    if possible, otherwise by reading the downloaded data.
    """
    try:
        return mm.get_user(user_id)
    except:
        results = [user for user in users if user['id'] == user_id]
        if not results:
            raise ValueError(f'Inexistent Mattermost user ID {user_id}')
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


async def create_user(mxid, display_name, avatar_mxc=None, avatar_bytes=None, avatar_filename=None, is_zephyr=False):
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
    # NOTE: we avoid changing the display name for zephyr ghosts if it is already set,
    # since we are likely downgrading it from display name to just username
    current_displayname = await user_api.get_displayname(mxid)
    if ((is_zephyr and current_displayname is None) or not is_zephyr) and display_name != current_displayname:
        await user_api.set_displayname(display_name)

    # Set profile picture if needed
    if avatar_bytes:
        current_avatar_mxc = await user_api.get_avatar_url(mxid)
        if current_avatar_mxc:
            current_avatar = await user_api.download_media(current_avatar_mxc)

        # If picture has changed, update it
        # (hopefully this isn't too slow overall, otherwise we would need some optimizations
        #  to reduce the amount of traffic)
        if not current_avatar_mxc or avatar_bytes != current_avatar:
            avatar_mxc = await user_api.upload_media(
                data=avatar_bytes,
                mime_type=magic.from_buffer(avatar_bytes, mime=True),
                filename=avatar_filename or 'pfp',
            )
            await user_api.set_avatar_url(avatar_mxc)
    elif avatar_bytes is None:
        # Unset profile picture
        # We are setting it to the empty string. It is not defined anywhere, but it seems to work 
        # (https://github.com/matrix-org/matrix-spec/issues/1606)
        await user_api.set_avatar_url('')
    
    return mxid


async def import_user_from_json(user):
    """
    Creates or updates a given Mattermost user from a Mattermost dictionary.
    Returns its MXID.
    """
    username = user['username']
    user_id = user['id']
    mxid = get_bridged_user_mxid(username)

    avatar = None
    try:
        # Only download if the user has a profile picture
        # Otherwise we get an image file with the person's initials
        if 'last_picture_update' in user:
            avatar = get_profile_picture_bytes(user_id)
    except:
        # Use downloaded profile picture only if request to Mattermost
        # failed for some reason
        filename = f"../downloaded/pfp/{user_id}"
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                avatar = f.read()
    
    display_name = config.matrix.display_name_format.format(
        name=get_displayname(user),
        platform='Mattermost',
    )

    return await create_user(mxid, display_name, avatar_bytes=avatar)


async def import_user(user_id):
    """
    Creates or updates a given Mattermost user into a Matrix bridged user.
    Returns its MXID.
    """
    user = get_mattermost_user(user_id)
    return await import_user_from_json(user)

