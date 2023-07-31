import json

# Source: https://github.com/mattermost/mattermost/blob/master/webapp/channels/src/utils/emoji.json
emoji = json.load(open('../downloaded/emoji_unparsed.json', 'r'))

# Names to emoji
emoji_map = {}

# Emoji to names
emoji_inverse_map = {}

for emoji in emoji:
    main_name = emoji['short_name']
    names = emoji['short_names']
    unicode = emoji['unified'].split('-')
    parsed = ''.join([chr(int(c,16)) for c in unicode])
    emoji_inverse_map[parsed] = main_name
    for name in names:
        emoji_map[name] = parsed
        print(parsed, end='')
print()

json.dump(emoji_map, open('../downloaded/emoji.json', 'w'))
json.dump(emoji_inverse_map, open('../downloaded/emoji_inverse.json', 'w'))
