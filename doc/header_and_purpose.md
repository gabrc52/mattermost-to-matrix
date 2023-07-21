Mattermost has a concept of "header" and "purpose". Matrix has only "topic" which is used in both the header and the list of rooms. Mattermost uses the header to show in the channel, and the purpose to show in the channel list.

The official descriptions are the following:

# [Matrix](https://spec.matrix.org/v1.7/client-server-api/#mroomtopic)

## Topic

> A topic is a short message detailing what is currently being discussed in the room. It can also be used as a way to display extra information about the room, which may not be suitable for the room name. The room topic can also be set when creating a room using /createRoom with the topic key.

# [Mattermost](https://docs.mattermost.com/channels/set-channel-preferences.html)

## Header

> A channel header refers to text that displays under a channel name at the top of the screen. A channel header can be up to 1024 characters in length and is often used to summarize the channel’s focus or to provide links to frequently accessed documents, tools, or websites.
> 
> Change the channel header by selecting Edit Channel Header. You can use Markdown to [format channel header text](https://docs.mattermost.com/messaging/formatting-text.html) using the same Markdown for messages. Any channel member can change a channel header, unless the system admin has [restricted permissions to do so](https://docs.mattermost.com/configure/configuration-settings.html#enable-public-channel-renaming-for).

## Purpose

> A channel purpose refers to text that displays when users select View Info for a channel. A channel purpose can be up to 250 characters in length and is often used to help users decide whether to join the channel.
> 
> Change the channel purpose by selecting Edit Channel Purpose. Any channel member can change a channel purpose, unless the system admin has [restricted permissions to do so using advanced permissions](https://docs.mattermost.com/onboard/advanced-permissions.html).