import mattermost
from login import mm

def download_media(media_id):
    """
    Dumps the desired media by ID into a file inside the `media` folder

    Assumes the `media` folder already exists
    """
    response = mm._get(f'/v4/files/{media_id}', raw=True)
    with open(f'../downloaded/media/{media_id}', 'wb') as f:
        f.write(response.content)


def download_profile_picture(user_id):
    """
    Dumps the desired profile picture by user ID into a file inside the `pfp`
    folder.

    Assumes the `pfp` folder already exists.
    """
    response = mm._get(f'/v4/users/{user_id}/image', raw=True)
    with open(f'../downloaded/pfp/{user_id}', 'wb') as f:
        f.write(response.content)