__author__ = 'austin'

from APP import app, base_api_ext
from APP.utility import make_gen_success

@app.route(base_api_ext + '/githook/push', methods=['POST'])
def git_push():
    # Todo
    # Will make a script to shutdown, pull, and restart the server
    return make_gen_success()
