import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from export_from_mattermost.media import download_media
import os
import json

# Create subdirectory if needed
if not os.path.exists('../downloaded/media'):
    os.mkdir('../downloaded/media')

for filename in os.listdir('../downloaded/messages'):
    # Skip non-JSON files (such as .gitignore)
    if 'json' not in filename:
        continue

    with open(f'../downloaded/messages/{filename}') as f:
        messages = json.load(f)
    for message in messages:
        if 'files' in message['metadata']:
            for file in message['metadata']['files']:
                media_id = file['id']
                if not os.path.exists(f'../downloaded/media/{media_id}'):
                    download_media(file['id'])

