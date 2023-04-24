import mattermost
from constants import *

mm = mattermost.MMApi(f"https://{DOMAIN}/api")
mm.login(USERNAME, PASSWORD)