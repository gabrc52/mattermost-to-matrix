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

    # User MXIDs to add and give admin in created rooms or spaces
    users: list[str]

    # Prefix to use for aliases
    room_prefix: Optional[str] = "_mattermost_"

    # Prefix to use for localparts of bridged users
    user_prefix: Optional[str] = "_mattermost_"

    # The username to allocate for this application service
    username: Optional[str] = "mattermostbot"


@dataclass_json
@dataclass
class MattermostConfig:
    username: str
    password: str
    instance: str

    # What to backfill as a Matrix "topic".
    # * header: backfill only header changes as topic changes
    # * purpose: backfill only purpose changes as topic changes
    # * both: backfill both header changes and purpose changes as topic changes
    # * auto: backfill header changes as topic changes only if the channel does not
    #         have any purpose changes, and purpose changes otherwise
    backfill_topic_equivalent: Literal["header"] | Literal["purpose"] | Literal["both"] | Literal["auto"]

    # Channel IDs to skip exporting
    skip_channels: tuple[str] = ()


@dataclass_json
@dataclass
class Config:
    mattermost: MattermostConfig
    matrix: MatrixConfig


config: Config = Config.from_dict(yaml.load(open("config.yaml", "r"), yaml.Loader))
