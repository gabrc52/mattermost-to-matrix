from login import mm
import json

all_users = [user for user in mm.get_users()]

json.dump(all_users, open('../downloaded/users.json', 'w'))