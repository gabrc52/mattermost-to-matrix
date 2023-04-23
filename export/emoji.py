"""
Ideas to resolve emoji shortcodes into an actual Unicode character:

1. BeautifulSoup + inspect element + iterate through each, the HTML has everything you need

2. Find something like https://github.com/ikatyang/emoji-cheat-sheet/blob/master/README.md but with the actual Unicode codes

Example: :facepunch:, :fist_oncoming: and :punch: match u+1f44a 👊

<img alt="emoji image" data-testid="fist_oncoming,facepunch,punch" src="/static/files/bb70781ccd4fbf5f99bf8a8060f82662.gif" class="emojisprite emoji-category-people-3 emoji-1f44a" id="emoji-1f44a" aria-label="fist oncoming emoji" role="button">

For now, let us do #1. PRs welcome to add the emojis from more recent versions of Mattermost.
"""

from bs4 import BeautifulSoup, element, PageElement
import json

soup = BeautifulSoup(open('emoji.html', 'r'), 'html.parser')

root = soup.div.div

categories = root.find_all('div', recursive=False)

emoji_map = {}

for category in categories:
    category: element.Tag = category
    header = category.find(class_='emoji-picker__category-header')
    category_name = header.span.string
    if category_name == 'Custom':
        print("Custom emojis not supported yet, skipping")
        continue
    print("Processing", category_name)
    emojis = category.find_all(class_='emoji-picker__item')
    for emoji in emojis:
        names = emoji.div.img['data-testid'].split(',')
        unicode = emoji.div.img['id'].split('-')[1:]
        parsed = ''.join([chr(int(c,16)) for c in unicode])
        for name in names:
            emoji_map[name] = parsed
        print(parsed, end='')
    print()

json.dump(emoji_map, open('emoji.json', 'w'))
