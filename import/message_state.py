class MessageState:
    """
    some state to deal with importing messages
    """

    # the most recent message in a given thread, as a mattermost
    # message ID, because mattermost only keeps track of the root
    most_recent_message_in_thread: dict[str, str]
    
    # mapping from mattermost message ID to matrix event ID
    matrix_event_id: dict[str, str]

    def __init__(self):
        self.most_recent_message_in_thread = {}
        self.matrix_event_id = {}