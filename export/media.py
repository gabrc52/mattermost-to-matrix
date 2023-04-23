import mattermost
from constants import *

mm = mattermost.MMApi("https://mattermost.mit.edu/api")
mm.login(USERNAME, PASSWORD)

def download_media(media_id):
    """
    Dumps the desired media by ID into a file inside the `media` folder
    """
    response = mm._get(f'/v4/files/{media_id}', raw=True)
    with open(f'media/{media_id}', 'wb') as f:
        f.write(response.content)

