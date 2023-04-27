"""
Get some sense of how to use Mautrix Python, despite its missing documentation.

The Maunium room is a useful room to ask questions in.

To see an example which does not use any library and uses requests and Flask,
see https://github.com/sipb/matrix-zephyr-bridge/
"""


from mautrix.appservice import AppService, AppServiceAPI, state_store
from mautrix.types import UserID, RoomID
from config import config
from mautrix.util.logging import TraceLogger
import asyncio

# AppServiceAPI implements IntentAPI which extends StoreUpdatingAPI which extends ClientAPI
# See their docstrings for what they are

async def main():
    app_service = AppServiceAPI(
        base_url=config.matrix.homeserver_url,
        bot_mxid=UserID(f'@{config.matrix.username}:{config.matrix.homeserver}'),
        token=config.matrix.as_token,
        # The log and state_store are needed even if AppServiceAPI technically accepts leaving it blank
        log=TraceLogger('log'),
        state_store=state_store.FileASStateStore(path='mx-state.json', binary=False),
    )

    api = app_service.bot_intent()

    # Logged in as application service
    print(await api.whoami())

    # Username to test acting as
    username = f'@{config.matrix.user_prefix}testuser:{config.matrix.homeserver}'

    # Get API to act as the user
    user_api = app_service.intent(username)

    # Make sure user exists (create if not)
    await user_api.ensure_registered()

    # Logged in as user
    print(await user_api.whoami())

    # Do things as user
    await user_api.set_displayname('Test User')
    room = f'#_mattermost_testroom:{config.matrix.homeserver}'
    room_id = (await api.resolve_room_alias(room)).room_id
    await user_api.join_room(room)
    await user_api.send_text(RoomID(room_id), 'This is a third message')

    # Close the session (thanks bramenn)
    await app_service.session.close()


asyncio.run(main())
