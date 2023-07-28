from login import mm, own_id, config
import json
import os

# Create subdirectory if needed
if not os.path.exists('../downloaded/media'):
    os.mkdir('../downloaded/media')

def export_channel(channel_id):
    """
    Dump the channel by ID into a JSON file in the `messages` directory

    If the JSON file already exists, it updates it to add the newest messages
    Note that edits are not reflected.
    """
    filename = f'../downloaded/messages/{channel_id}.json'

    if os.path.exists(filename):
        print("   File already found, updating instead")
        existing_posts = json.load(open(filename, 'r'))
        existing_ids = {post['id'] for post in existing_posts}
        new_posts = []
        for post in mm.get_posts_for_channel(channel_id):
            # Break at first old post found
            # because it means that everything beyond that has already been saved
            if post['id'] in existing_ids:
                break
            new_posts.append(post)
        all_posts = new_posts + existing_posts
    else:
        all_posts = [post for post in mm.get_posts_for_channel(channel_id)]

    json.dump(all_posts, open(filename, 'w'))


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: export_channel.py [mattermost channel ID]", file=sys.stderr)
        print("You may get the channel ID by running export_channel_list.py and looking for the desired channel.", file=sys.stderr)
        exit(1)
    channel_id = sys.argv[1]
    export_channel(channel_id)
