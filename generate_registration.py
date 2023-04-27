import yaml
from config import config

# https://spec.matrix.org/v1.6/application-service-api/#registration
registration = {
    "as_token": config.matrix.as_token,
    "hs_token": config.matrix.hs_token,
    "id": "Mattermost migration tool",
    "namespaces": {
        # There is no need to keep the namespaces exclusive, because an actual bridge
        # might want to reuse them
        "aliases": [
            # TODO: escape the dots from homeserver which mean any character and not just dot?
            {"exclusive": False, "regex": f"#{config.matrix.room_prefix}.+:{config.matrix.homeserver}"},
        ],
        "rooms": [],
        "users": [
            {"exclusive": False, "regex": f"@{config.matrix.user_prefix}.+"},
        ],
    },
    "rate_limited": False,
    "sender_localpart": config.matrix.username,

    # This is not a bridge, at least for now. Just the backfill part so it does not need to *receive* messages
    "url": None,
}

yaml.dump(registration, open("registration.yaml", "w"), yaml.Dumper)