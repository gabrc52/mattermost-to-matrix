import mattermost
from constants import *

mm = mattermost.MMApi("https://mattermost.mit.edu/api")
mm.login(USERNAME, PASSWORD)