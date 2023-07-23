import mattermost
from login import mm

def download_media(media_id):
    """
    Dumps the desired media by ID into a file inside the `media` folder

    Assumes the `media` folder already exists
    """
    response = mm.get_file(media_id)
    with open(f'../downloaded/media/{media_id}', 'wb') as f:
        f.write(response.content)


def download_profile_picture(user_id):
    """
    Dumps the desired profile picture by user ID into a file inside the `pfp`
    folder.

    Assumes the `pfp` folder already exists, and that the user has a profile picture.
    """
    response = mm._get(f'/v4/users/{user_id}/image', raw=True)
    with open(f'../downloaded/pfp/{user_id}', 'wb') as f:
        f.write(response.content)


def download_team_picture(team_id):
    """
    Dumps the desired team profile picture by team ID into a file inside the `pfp`
    folder.

    Assumes the `pfp` folder already exists, and that the team has a profile picture.
    """
    response = mm._get(f'/v4/teams/{team_id}/image', raw=True)
    with open(f'../downloaded/pfp/{team_id}', 'wb') as f:
        f.write(response.content)
