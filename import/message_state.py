# TODO: we want some longer term persistence
# https://pypi.org/project/sqlitedict/ seems cool.
# or sqlite directly

class MessageState:
    """
    some state to deal with importing messages
    """

    # the most recent message in a given thread, as a mattermost
    # message ID, because mattermost only keeps track of the root
    _most_recent_message_in_thread: dict[str, str]
    
    # mapping from mattermost message ID to matrix event ID
    _matrix_event_id: dict[str, str]

    # mapping from matrix event ID to mattermost message ID
    _mattermost_message_id: dict[str, str]

    def __init__(self):
        self._most_recent_message_in_thread = {}
        self._matrix_event_id = {}
        self._mattermost_message_id = {}

    def get_matrix_event(self, mattermost_id):
        """
        Get the Matrix ID of the message corresponding to the given Mattermost
        message ID. Returns None if we can't remember this Mattermost event ID,
        otherwise returns the Matrix event ID.
        """
        return self._matrix_event_id.get(mattermost_id)
    
    def get_mattermost_event(self, matrix_id):
        """
        Returns the Mattermost message ID of the message with given Matrix ID,
        otherwise None if it can't be found
        """
        return self._mattermost_message_id.get(matrix_id)

    def remember_matrix_event(self, mattermost_id, matrix_id):
        """
        Remembers that the event with mattermost_id on Mattermost was bridged
        to the event with matrix_id on Matrix (or maybe vice versa)
        """
        assert mattermost_id not in self._matrix_event_id, 'did you bridge this twice?'
        self._matrix_event_id[mattermost_id] = matrix_id
        self._mattermost_message_id[matrix_id] = mattermost_id

    def get_most_recent_message_in_thread(self, root_mattermost_id):
        """
        Returns the most recent message in a Mattermost thread, given the Mattermost
        message ID of the root of the thread, or None if it can't be found 
        """
        # this might be too much of a hassle to have with the bridge,
        # which is why I might just set it to work with threads to threads
        return self._most_recent_message_in_thread.get(root_mattermost_id)
    
    def set_most_recent_message_in_thread(self, root_mattermost_id, mattermost_id):
        """
        Remembers that the most recent message in the thread with ID root_mattermost_id
        on Mattermost is mattermost_id on Mattermost.
        """
        self._most_recent_message_in_thread[root_mattermost_id] = mattermost_id