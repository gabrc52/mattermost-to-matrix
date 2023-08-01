import yaml
from typing import Literal, Optional
from dataclasses import dataclass
from dataclasses_json import dataclass_json

@dataclass_json
@dataclass
class MatrixConfig:
    # Token used by the homeserver to communicate with the appservice
    hs_token: str

    # Token that the appservice uses to communicate with the homeserver
    as_token: str

    # The homeserver (right part of MXIDs)
    homeserver: str

    # Homeserver URL, where you can actually reach the Matrix REST API
    homeserver_url: str

    # Whether to enable the bridge (and include a URL in the registration file)
    enable_bridge: bool

    # Where the appservice should listen its REST API in
    listen_address: str
    listen_port: int

    # User MXIDs to add and give admin in created rooms or spaces
    users: list[str]

    # List of prefixes to ignore for user MXIDs, to avoid
    # double-bridging messages from other bridges
    bridge_ignore_user_prefixes: Optional[tuple[str]] = ()

    # Prefix to use for aliases
    room_prefix: Optional[str] = "_mattermost_"

    # Prefix to use for localparts of bridged users
    user_prefix: Optional[str] = "_mattermost_"

    # The username to allocate for this application service
    username: Optional[str] = "mattermostbot"

    # Whether to skip already existing rooms when importing
    skip_existing: Optional[bool] = True

    # Display name "template". {name} will be replaced with display name,
    # and {platform} with Mattermost or Zephyr accordingly
    display_name_format: Optional[str] = "{name} - {platform}"


@dataclass_json
@dataclass
class MattermostBackfillConfig:
    # What to backfill as a Matrix "topic".
    # * header: backfill only header changes as topic changes
    # * purpose: backfill only purpose changes as topic changes
    # * both: backfill both header changes and purpose changes as topic changes
    # * auto: backfill header changes as topic changes only if the channel does not
    #         have any purpose changes, and purpose changes otherwise
    topic_equivalent: Literal["header", "purpose", "both", "auto"]

    # What to backfill instead of a Mattermost thread:
    # * thread: always use a Matrix thread
    # * reply: always use a Matrix reply, to the latest message in the Mattermost thread
    # * auto: use a Matrix thread if and only if the Mattermost thread contains at least
    #         `thread_threshold` messages
    thread_equivalent: Literal["thread", "reply", "auto"]

    # Only applied if `thread_equivalent` is 'auto': How many messages should there be in 
    # the Mattermost thread to use a Matrix thread instead of a Matrix reply?
    thread_threshold: int = 3


@dataclass_json
@dataclass
class MattermostBridgeConfig:
    # Similar to topic_equivalent above, but 'auto' is disallowed
    topic_equivalent: Literal["header", "purpose", "both"] = "both"

    # Similar to thread_equivalent above, but 'auto' is disallowed
    thread_equivalent: Literal["thread", "reply"] = "thread"

    # List of users to ignore when bridging
    ignore_users: tuple[str] = ()


@dataclass_json
@dataclass
class MattermostConfig:
    username: str
    password: str
    instance: str

    backfill: MattermostBackfillConfig
    bridge: MattermostBridgeConfig

    # Channel IDs to skip exporting
    skip_channels: tuple[str] = ()

    # List of channels to always thread, regardless of the above options
    always_thread: Optional[tuple[str]] = ()


@dataclass_json
@dataclass
class Config:
    mattermost: MattermostConfig
    matrix: MatrixConfig
    prefer_usernames: bool = False


config: Config = Config.from_dict(yaml.load(open("config.yaml", "r"), yaml.Loader))
