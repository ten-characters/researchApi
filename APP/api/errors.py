""" Simple error handlers
    They are routed to every time there is an abort(code) call
    Respond with a detailed message in debug mode
"""
__author__ = 'austin'

from flask import make_response, jsonify, request

from APP import app, DEBUG
from APP.utility import AlreadyAcceptedException, log_error

FILE_TAG = __name__


# ----------- ERROR HANDLERS --------------- #
@app.errorhandler(400)
def bad_request(error):
    if not DEBUG:
        send_error_email(error, 400)
    return make_response(jsonify(error=error.description), 400)


@app.errorhandler(403)
def not_authorized(error):
    """

    :param error:
    :return:
    """
    return make_response(jsonify(error=error.description, code=403), 403)


@app.errorhandler(404)
def not_found(error):
    """

    :param error:
    :return:
    """
    if not DEBUG:
        send_error_email(error, 404)
    return make_response(jsonify(error=error.description, code=404), 404)


@app.errorhandler(500)
def server_error(error):
    """

    :param error:
    :return:
    """
    if not DEBUG:
        send_error_email(error, 500)
    return make_response(jsonify(error=error.description), 500)


@app.errorhandler(AlreadyAcceptedException)
def already_accepted(error):
    """

    :param error:
    :return:
    """
    return make_response(jsonify(error=error.to_dict()), error.status_code)


def send_error_email(error, code):
    """

    :param error:
    :param code:
    :return:
    """
    # Send us a lil update
    from APP.email import make_admin_error_email, send_async_mail
    if len(request.form) != 0:
        data = str(request.form)
    else:
        data = str(request.data)

    try:
        send_async_mail(make_admin_error_email(
            error.name,
            code,
            error.description,
            request.url,
            data)
        )
    except Exception as ex:
        # TODO: Some errors, such as ValueErrors are not formatted so nicely as others are.
        log_error("Can't format email from exception: " + str(ex), FILE_TAG, exception=ex)
    return
