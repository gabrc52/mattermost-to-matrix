from media import download_media, download_profile_picture
import os
import json

# Create subdirectory if needed
if not os.path.exists('../downloaded/pfp'):
    os.mkdir('../downloaded/pfp')

users = json.load(open('../downloaded/users.json', 'r'))

# TODO: this redownloads all pictures every time you run the file
# It might be good to persist which ones have been downloaded and not been changed
for user in users:
    if 'last_picture_update' in user:
        # Otherwise the API just returns a generic profile picture
        download_profile_picture(user['id'])
