# Events

I *love* that you only have to listen to ONE websocket/endpoint. It makes it pretty easy to integrate with it as a bridge.

This has documentation: <https://api.mattermost.com/#tag/WebSocket>

Events have an `event` type, `data` about the event, `broadcast` is about who the event was sent to. It also counts the number of requests using `seq`, which seems to be in the same spirit as the transaction IDs in Matrix, except defined much more informally in its spec.

## Gone online (self)

status_change

```py
{'broadcast': {'channel_id': '',
               'omit_users': None,
               'team_id': '',
               'user_id': '911gzgbxy3fwfbdf9eg6z8xgnw'},
 'data': {'status': 'online', 'user_id': '911gzgbxy3fwfbdf9eg6z8xgnw'},
 'event': 'status_change',
 'seq': 1}
```

## Edit an old message

post_edited

```py
{'broadcast': {'channel_id': '1waumyyd6jyczrxntuiopybygy',
               'omit_users': None,
               'team_id': '',
               'user_id': ''},
 'data': {'post': '{"id":"ap8doms33tn1pj3ihjk3gmf4jy","create_at":1682182575935,"update_at":1682311574630,"edit_at":1682311574630,"delete_at":0,"is_pinned":false,"user_id":"cmr7sncacib4xfhd6yo3n4tf5e","channel_id":"1waumyyd6jyczrxntuiopybygy","root_id":"","parent_id":"","original_id":"","message":"(i '
                  'forgot that out of all instances i could have used, this '
                  'specific one is bridged to mattermost)\\n\\nTest editing '
                  'message","type":"","props":{"disable_group_highlight":true},"hashtags":"","pending_post_id":"","reply_count":0,"metadata":{}}'},
 'event': 'post_edited',
 'seq': 2}
```

# Gone away (self)

status_change too. Confusing why our own bot account went away.

```py
{'broadcast': {'channel_id': '',
               'omit_users': None,
               'team_id': '',
               'user_id': '911gzgbxy3fwfbdf9eg6z8xgnw'},
 'data': {'status': 'away', 'user_id': '911gzgbxy3fwfbdf9eg6z8xgnw'},
 'event': 'status_change',
 'seq': 3}
```

## Typing

Yay we can bridge this to Matrix! It is of type `typing`.

"The omit_users field can contain an array of user IDs that were specifically omitted from receiving the event."

Explicitly indicates not to show myself that I'm typing. Well, that's an interesting way to implement, I guess.

```py
{'broadcast': {'channel_id': '1waumyyd6jyczrxntuiopybygy',
               'omit_users': {'cmr7sncacib4xfhd6yo3n4tf5e': True},
               'team_id': '',
               'user_id': ''},
 'data': {'parent_id': '', 'user_id': 'cmr7sncacib4xfhd6yo3n4tf5e'},
 'event': 'typing',
 'seq': 4}
```

## Send message

Event is of type `posted`. The post is an encoded JSON string for some reason.

```py
{'broadcast': {'channel_id': '1waumyyd6jyczrxntuiopybygy',
               'omit_users': None,
               'team_id': '',
               'user_id': ''},
 'data': {'channel_display_name': 'Test 2.0',
          'channel_name': 'test2',
          'channel_type': 'O',
          'post': '{"id":"5greg5b4w3rojmqc188znn8s7c","create_at":1682311948645,"update_at":1682311948645,"edit_at":0,"delete_at":0,"is_pinned":false,"user_id":"cmr7sncacib4xfhd6yo3n4tf5e","channel_id":"1waumyyd6jyczrxntuiopybygy","root_id":"","parent_id":"","original_id":"","message":"message '
                  'sent","type":"","props":{"disable_group_highlight":true},"hashtags":"","pending_post_id":"cmr7sncacib4xfhd6yo3n4tf5e:1682311948590","reply_count":0,"metadata":{}}',
          'sender_name': '@rgabriel',
          'set_online': True,
          'team_id': '68ia7ywnopny8nmcdrkatmytjh'},
 'event': 'posted',
 'seq': 5}
 ```

## Edit message

Event is of type `post_edited`

Note that the ID of the post is kept the same. This should be useful to keep track of which message was deleted.

This also means that to make a bridge, _we need to store a mapping of Mattermost IDs to Matrix !event IDs_, among possibly other things.

I think sqlite doesn't actually seem that bad, considering I've touched SQL.

```py
{'broadcast': {'channel_id': '1waumyyd6jyczrxntuiopybygy',
               'omit_users': None,
               'team_id': '',
               'user_id': ''},
 'data': {'post': '{"id":"5greg5b4w3rojmqc188znn8s7c","create_at":1682311948645,"update_at":1682311952478,"edit_at":1682311952478,"delete_at":0,"is_pinned":false,"user_id":"cmr7sncacib4xfhd6yo3n4tf5e","channel_id":"1waumyyd6jyczrxntuiopybygy","root_id":"","parent_id":"","original_id":"","message":"message '
                  'edited","type":"","props":{"disable_group_highlight":true},"hashtags":"","pending_post_id":"","reply_count":0,"metadata":{}}'},
 'event': 'post_edited',
 'seq': 6}
```

## Delete message

Event is of type `post_deleted`

The message before it was deleted is there.

```py
{'broadcast': {'channel_id': '1waumyyd6jyczrxntuiopybygy',
               'omit_users': None,
               'team_id': '',
               'user_id': ''},
 'data': {'post': '{"id":"5greg5b4w3rojmqc188znn8s7c","create_at":1682311948645,"update_at":1682311952478,"edit_at":1682311952478,"delete_at":0,"is_pinned":false,"user_id":"cmr7sncacib4xfhd6yo3n4tf5e","channel_id":"1waumyyd6jyczrxntuiopybygy","root_id":"","parent_id":"","original_id":"","message":"message '
                  'edited","type":"","props":{"disable_group_highlight":true},"hashtags":"","pending_post_id":"","reply_count":0,"metadata":{}}'},
 'event': 'post_deleted',
 'seq': 7}
```

## Reaction add

This is where the emoji name table will come to handy.

```py
{'broadcast': {'channel_id': '1waumyyd6jyczrxntuiopybygy',
               'omit_users': None,
               'team_id': '',
               'user_id': ''},
 'data': {'reaction': '{"user_id":"cmr7sncacib4xfhd6yo3n4tf5e","post_id":"u4y918f9o3gotgzefgoc1zcj9h","emoji_name":"eyes","create_at":1682313115731}'},
 'event': 'reaction_added',
 'seq': 8}
 ```

## Reaction remove

Analogous to the above, difference is the type of event (`reaction_removed`)

```py
{'broadcast': {'channel_id': '1waumyyd6jyczrxntuiopybygy',
               'omit_users': None,
               'team_id': '',
               'user_id': ''},
 'data': {'reaction': '{"user_id":"cmr7sncacib4xfhd6yo3n4tf5e","post_id":"u4y918f9o3gotgzefgoc1zcj9h","emoji_name":"eyes","create_at":0}'},
 'event': 'reaction_removed',
 'seq': 9}
```

