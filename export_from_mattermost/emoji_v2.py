import json

# Source: https://github.com/mattermost/mattermost/blob/master/webapp/channels/src/utils/emoji.json
emoji = json.load(open('../downloaded/emoji_unparsed.json', 'r'))

emoji_map = {}

for emoji in emoji:
    names = emoji['short_names']
    unicode = emoji['unified'].split('-')
    parsed = ''.join([chr(int(c,16)) for c in unicode])
    for name in names:
        emoji_map[name] = parsed
        print(parsed, end='')
print()

json.dump(emoji_map, open('../downloaded/emoji.json', 'w'))
