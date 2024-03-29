from sqlitedict import SqliteDict

DB_FILE = "db.sqlite"

# We don't want any serialization from sqlitedict

def _encode(str: str):
    return str.encode()

def _decode(obj: bytes):
    return obj.decode()

# But we do want some lists

def _encode_list(items: list[str]) -> bytes:
    return ','.join(items).encode()

def _decode_list(obj: bytes) -> list[str]:
    return obj.decode().split(',')

class MessageState:
    """
    some state to deal with importing messages
    """

    # the most recent message in a given thread, as a mattermost
    # message ID, because mattermost only keeps track of the root
    _most_recent_message_in_thread: SqliteDict
    
    # mapping from mattermost message ID to matrix event ID
    # (last message event: this is used generally)
    _matrix_event_id: SqliteDict

    # The following 2 databases exist only because Matrix currently
    # does not have a way of sending a single message with attachments,
    # and instead they are sent separately
    # (https://github.com/matrix-org/matrix-spec/issues/541,
    #  https://github.com/matrix-org/matrix-spec/issues/242)

    # mapping from mattermost message ID to matrix event ID
    # (only text messages: this is used for bridging message edits)
    _matrix_text_event_id: SqliteDict

    # mapping from mattermost message ID to matrix event ID
    # (full list of events: this is used for bridging message deletions)
    _matrix_event_id_list: SqliteDict

    # mapping from matrix event ID to mattermost message ID
    _mattermost_message_id: SqliteDict

    def __init__(self):
        self.db = SqliteDict(DB_FILE)
        self._most_recent_message_in_thread = SqliteDict(
            DB_FILE,
            tablename="thread",
            autocommit=True,
            encode=_encode,
            decode=_decode,
        )
        self._matrix_event_id = SqliteDict(
            DB_FILE,
            tablename="mm2matrix",
            autocommit=True,
            encode=_encode,
            decode=_decode,
        )
        self._matrix_text_event_id = SqliteDict(
            DB_FILE,
            tablename="mm2matrixtext",
            autocommit=True,
            encode=_encode,
            decode=_decode,
        )
        self._matrix_event_id_list = SqliteDict(
            DB_FILE,
            tablename="mm2matrixfulllist",
            autocommit=True,
            encode=_encode_list,
            decode=_decode_list,
        )
        self._mattermost_message_id = SqliteDict(
            DB_FILE,
            tablename="matrix2mm",
            autocommit=True,
            encode=_encode,
            decode=_decode,
        )

    def get_matrix_event(self, mattermost_id):
        """
        Get the Matrix ID of the message corresponding to the given Mattermost
        message ID. Returns None if we can't remember this Mattermost event ID,
        otherwise returns the Matrix event ID.
        """
        if mattermost_id not in self._matrix_event_id:
            return None
        return self._matrix_event_id[mattermost_id]
    
    def get_matrix_text_event(self, mattermost_id):
        """
        Returns the Matrix ID of the *text* message corresponding to the given
        Mattermost message ID. Returns None if the Mattermost ID does not
        correspond to any text message on Matrix.
        """
        if mattermost_id not in self._matrix_text_event_id:
            return None
        return self._matrix_text_event_id[mattermost_id]
    
    def get_matrix_full_event_list(self, mattermost_id):
        """
        Returns the full list of Matrix event IDs corresponding to the
        given Mattermost post ID, or None if not found.
        """
        if mattermost_id not in self._matrix_event_id_list:
            return None
        return self._matrix_event_id_list[mattermost_id]
    
    def get_mattermost_event(self, matrix_id):
        """
        Returns the Mattermost message ID of the message with given Matrix ID,
        otherwise None if it can't be found
        """
        if matrix_id not in self._mattermost_message_id:
            return None
        return self._mattermost_message_id[matrix_id]

    def remember_matrix_event(self, mattermost_id, matrix_id):
        """
        Remembers that the event with mattermost_id on Mattermost was bridged
        to the event with matrix_id on Matrix (or maybe vice versa).
        """
        assert mattermost_id not in self._matrix_event_id, 'did you bridge this twice?'
        self._matrix_event_id[mattermost_id] = matrix_id
        self._mattermost_message_id[matrix_id] = mattermost_id

    def remember_matrix_text_event(self, mattermost_id, matrix_id):
        """
        Remembers that the event with mattermost_id on Mattermost was bridged
        to the event with matrix_id on Matrix, and that such event is a text message.
        
        (This is needed because Matrix does not support sending messages with attachments,
        so attachments are sent on a separate message each, meaning there is not really
        a one-to-one relationship between mattermost post IDs and Matrix event IDs)
        """
        self._matrix_text_event_id[mattermost_id] = matrix_id
        self._mattermost_message_id[matrix_id] = mattermost_id

    def set_matrix_event_list(self, mattermost_id, event_ids: list[str]):
        """
        Sets the Matrix event ID list corresponding to the given mattermost ID
        """
        self._matrix_event_id_list[mattermost_id] = event_ids

    def get_most_recent_message_in_thread(self, root_mattermost_id):
        """
        Returns the most recent message in a Mattermost thread, given the Mattermost
        message ID of the root of the thread, or None if it can't be found 
        """
        # this might be too much of a hassle to have with the bridge,
        # which is why I might just set it to work with threads to threads
        if root_mattermost_id not in self._most_recent_message_in_thread:
            return None
        return self._most_recent_message_in_thread[root_mattermost_id]
    
    def set_most_recent_message_in_thread(self, root_mattermost_id, mattermost_id):
        """
        Remembers that the most recent message in the thread with ID root_mattermost_id
        on Mattermost is mattermost_id on Mattermost.
        """
        self._most_recent_message_in_thread[root_mattermost_id] = mattermost_id