__author__ = 'austin'

import json

from APP import app, base_api_ext, base_api_v1_ext, base_api_v1_1_ext
from APP.models import ActiveUser
from APP.utility import make_gen_success, throw_error, check_authentication
from flask import request, abort, make_response, jsonify

FILE_TAG = __name__

# END POINTS
@app.route(base_api_ext + '/login', methods=['PUT', 'POST'])
@app.route(base_api_v1_ext + '/login', methods=['PUT', 'POST'])
@app.route(base_api_v1_1_ext + '/login', methods=['PUT', 'POST'])
def login():
    if not request.data:
        throw_error('No data in request!', 400, request, FILE_TAG)
    else:
        data = json.loads(request.data.decode('utf-8'))

    # First try to find the user with the email
    try:
        user = ActiveUser.objects.get_from_email(data['email'])
        if user is None:
            user = ActiveUser.objects(email=data['email'])
            throw_error('Cannot find user by email:' + data['email'], 404, request, FILE_TAG)

        # Then try to authenticate with their credentials
        # We will only try to log them in with the
        if user.login(data['password']):
            # Return the auth token, if authenticated
            user.reload()
            return make_response(jsonify(token=user.auth_token), 200)
        # If they cannot be logged in, we want to return a 403 not authenticated code
        throw_error('Unauthenticated', 403, request, FILE_TAG)
    except KeyError:
        throw_error('Key error', 400, request, FILE_TAG)


@app.route(base_api_ext + '/logout', methods=['GET', 'POST'])
@app.route(base_api_v1_ext + '/logout', methods=['GET', 'POST'])
@app.route(base_api_v1_1_ext + '/logout', methods=['GET', 'POST'])
def logout():
    # Why try to logout when you're not signed in?
    if not check_authentication():
        abort(400)
    data = json.loads(request.data.decode('utf-8'))

    # Delete the users auth token from their records
    try:
        user = ActiveUser.objects.get_from_email(data['email'])
    except KeyError:
        throw_error('Key Error!', 400, request, FILE_TAG)
    if user is None:
        throw_error('Cannot find user by email:' + data['email'], 404, request, FILE_TAG)

    # Set their auth_token to an empty string. Won't pass inspection
    user.auth_token = ""
    # If they are a driver, make sure that they are set as not active as well
    if user.driver_info:
        user.driver_info.is_active = False

    user.save()
    return make_gen_success()
