"""
This is for the bridge, not the import.

Unfortunately I did not have enough oversight to use dataclasses for Mattermost,
which has proven a bit['annoying'], but not annoying enough to do a large refactoring.
"""

import json
from dataclasses import dataclass
from dataclasses_json import dataclass_json

from import_to_matrix.import_user import get_mattermost_user
from import_to_matrix.import_message import get_emoji

@dataclass_json
@dataclass
class MattermostEvent:
    # Event type
    event: str

    # The actual event
    data: dict

    # Info about where the event was emitted
    broadcast: dict

    # Counter
    seq: int

    def get_mattermost_user_id(self):
        """
        Gets the Mattermost user ID of the event,
        or None if not found
        """
        if 'user_id' in self.broadcast and self.broadcast['user_id']:
            return self.broadcast['user_id']
        if 'user_id' in self.data and self.data['user_id']:
            return self.data['user_id']
        # Reactions have it elsewhere
        if 'reaction' in self.data:
            return json.loads(self.data['reaction'])['user_id']
        # Posts have it elsewhere
        if 'post' in self.data:
            return json.loads(self.data['post'])['user_id']

    
    def get_mattermost_user(self):
        """
        Gets the Mattermost user dict of the event,
        or None if not found
        """
        user_id = self.get_mattermost_user_id()
        if user_id:
            return get_mattermost_user(user_id)
        
    def get_reaction(self):
        """
        Assumes this is a reaction event. Returns a tuple
        with (mattermost message ID, reaction emoji)
        """
        assert 'reaction' in self.data
        dict = json.loads(self.data['reaction'])
        return dict['post_id'], get_emoji(dict['emoji_name'])
