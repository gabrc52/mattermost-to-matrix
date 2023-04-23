from media import download_media
import os
import json

# Create subdirectory if needed
if not os.path.exists('media'):
    os.mkdir('media')

for filename in os.listdir('messages'):
    with open(f'messages/{filename}') as f:
        messages = json.load(f)
    for message in messages:
        if 'files' in message['metadata']:
            for file in message['metadata']['files']:
                media_id = file['id']
                if not os.path.exists(f'media/{media_id}'):
                    download_media(file['id'])

