import yaml
from typing import Optional
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


@dataclass_json
@dataclass
class Config:
    mattermost: MattermostConfig
    matrix: MatrixConfig


config: Config = Config.from_dict(yaml.load(open("config.yaml", "r"), yaml.Loader))
