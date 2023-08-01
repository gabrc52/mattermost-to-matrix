import mattermost

# Import config from parent directory
# TODO: use an actual module?
# source: https://stackoverflow.com/questions/16780014/import-file-from-parent-directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

mm = mattermost.MMApi(f"https://{config.mattermost.instance}/api")

if config.mattermost.token is not None:
    print("Logging in with token!")
    mm.login(bearer=config.mattermost.token)
else:
    assert config.mattermost.username and config.mattermost.password, "You must specify an authentication method"
    mm.login(config.mattermost.username, config.mattermost.password)

own_account = mm.get_user()
own_id = own_account['id']
