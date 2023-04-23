import os
from pprint import pprint
import json
from datetime import datetime
from tempfile import NamedTemporaryFile
import webbrowser

# Note the reverse chronological order

if not os.path.exists('users.json'):
    print("File users.json does not exist. Please run export_users.py first", file=sys.stderr)
    exit(1)

users = json.load(open('users.json', 'r'))
users_by_id = {user['id']:user for user in users}

def get_username(user_id):
    return users_by_id[user_id]['username']

def get_full_name(user_id):
    return ' '.join((users_by_id[user_id]['first_name'], users_by_id[user_id]['last_name']))

def get_printable_time(timestamp):
    time = datetime.fromtimestamp(timestamp / 1000)
    return f"{time:%Y-%m-%d %H:%M}" # removed :%S, don't want to print

def view_channel(channel_id):
    filename = f'messages/{channel_id}.json'
    if not os.path.exists(filename):
        print(f'File does not exist for {channel_id}. Run export_channel.py first.', file=sys.stderr)
        exit(1)
    messages = json.load(open(filename, 'r'))

    html = NamedTemporaryFile(prefix='mattermost', mode='w')
    print('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Exported Messages</title><link rel="stylesheet" href="https://cdn.simplecss.org/simple.min.css"></head><body>', file=html)
    print('<table>', file=html)
    print('<thead><tr><th>Date</th><th>Sender</th><th>Message</th></tr></thead>', file=html)
    print('<tbody>', file=html)
    # Reverse cause reverse chronological order
    for message in reversed(messages):
        date_str = get_printable_time(message['create_at'])
        username = get_username(message['user_id'])
        # Override for webhooks
        if 'override_username' in message['props']:
            username = message['props']['override_username']
        content = message['message']
        edited = message['update_at'] != message['create_at']
        if content:
            # No content probably means image
            print(f'<tr><td>{date_str}</td><td>{username}</td><td>{content}</td>', file=html)
        if 'files' in message['metadata']:
            for file in message['metadata']['files']:
                print(f'<tr><td>{date_str}</td><td>{username}</td><td><img src="file://{os.getcwd()}/media/{file["id"]}"></td>', file=html)
        print('</tr>', file=html)
    print('</tbody>', file=html)
    print('</table>', file=html)
    print('</body></html>', file=html)
    html.flush()
    webbrowser.open(html.name)
    html.close()

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: view_channel.py [mattermost channel ID]", file=sys.stderr)
        print("You may get the channel ID by running export_channel_list.py and looking for the desired channel.", file=sys.stderr)
        exit(1)
    channel_id = sys.argv[1]
    view_channel(channel_id)
