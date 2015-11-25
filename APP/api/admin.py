__author__ = 'austin'

from APP import app, bcrypt, base_api_v1_ext, base_api_v1_1_ext, PALLET_SECRET_ADMIN_PASS, TEMP_MEDIA_FOLDER, DEBUG
from APP.models import ActiveUser, Address, Error
from APP.utility import check_authentication, make_gen_success, throw_error, format_string_to_date
from APP.decorators import deprecated

from flask import request, jsonify, abort, make_response, send_from_directory
from mongoengine import ValidationError
import json


FILE_TAG = __name__


# AUTHENTICATION REQUIRED
@app.route(base_api_v1_ext + '/admin/shutdown', methods=['POST'])
@app.route(base_api_v1_1_ext + '/admin/shutdown', methods=['POST'])
def shutdown_server():
    ''' SHUTDOWN THE API
        A pretty simple endpoint, for admin functionality only
        Just sending an empty post request to this endpoint will quickly shut down the whole server
    '''
    auth = check_authentication(req_roles=['admin'])
    if not auth[0]:
        abort(403)

    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is None:
        raise RuntimeError('No Werkzeug server is running..')
    shutdown_func()
    return jsonify(response='Shutting down the server!')


@deprecated('1.1')
@app.route(base_api_v1_ext + '/admin/add', methods=['POST'])
def add_admin():
    if not request.data:
        abort(400)
    else:
        data = json.loads(request.data.decode('utf-8'))

    # We will authenticate the first admin, and then add
    # all other admins through that one
    # or allow any admin to activate another --> or check_authentication(req_roles=['admin'])[0]
    # In the future we should have tiers of admins
    if len(ActiveUser.objects()) == 0:
        # Only add an admin if this is the first user or if the admin is authenticated
        try:
            # Gather Billing Info
            billing_info = Address(
                address=data['address'],
                state=data['state'],
                city=data['city'],
                country=data['country'],
                zip=data['zip']
            )

            dob = format_string_to_date(data['dob'])
            if dob is None:
                abort(400)

            pass_hash = bcrypt.generate_password_hash(data['password'])
            notif_key_hash = bcrypt.generate_password_hash(data['email'])

            roles = ['base_user', 'admin']

            ActiveUser(
                registered_by=data['service'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                dob=dob,
                password=pass_hash,
                notification_key=notif_key_hash,
                roles=roles,
                phone=data['phone'],
                billing_info=billing_info,
                company=data['company'],
                location=data['location']
            ).save()
        except (KeyError, ValidationError):
            abort(400)
        return make_gen_success()
    else:
        return throw_error("First admin already made!", 400, request, FILE_TAG)


@app.route(base_api_v1_ext + '/admin/downloaded_user_list/<string:response_type>', methods=['GET', 'PUT'])
@app.route(base_api_v1_1_ext + '/admin/downloaded_user_list/<string:response_type>', methods=['GET', 'PUT'])
def get_downloaded_users(response_type):
    """
        Generate either a json response or a csv file with all the downloaded user info

    response_type: string, either 'csv' or 'json'

    :return:
    """

    # Start by checking auth
    auth = check_authentication(req_roles=['admin'])
    if not auth[0] or not DEBUG:
        abort(403)

    from APP.models import DownloadedUser
    downloaded_users = DownloadedUser.objects()

    if response_type == 'json':
        json_formatted = []
        for user in downloaded_users:
            json_formatted.append(user.to_json())

        return make_response(jsonify(downloaded_users=json_formatted), 200)

    elif response_type == 'csv':
        from datetime import datetime
        # Add a lil "random" string to the filename so concurrent request aren't overwritten
        filename = str(datetime.utcnow().microsecond) + 'downloadedUsers.csv'

        import csv
        with open(TEMP_MEDIA_FOLDER + '/' + filename, 'w') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list((json.loads((downloaded_users[0].to_json())).keys())))
            writer.writeheader()
            for user in downloaded_users:
                writer.writerow(json.loads(user.to_json()))
        try:
            return send_from_directory(TEMP_MEDIA_FOLDER, filename)
        finally:
            #  Always delete this temp file after it has been sent away
            import os
            os.remove(TEMP_MEDIA_FOLDER + '/' + filename)

    else:
        # If they haven't provided a valid response type, aka json or csv
        throw_error("Not a valid response type!", 400, request, FILE_TAG)


@app.route(base_api_v1_ext + '/admin/send_email_to', methods=['POST'])
@app.route(base_api_v1_1_ext + '/admin/send_email_to', methods=['POST'])
def send_email_to():
    """
        This could be a very useful tool.
        We want to allow a gui to efficiently email mass sections of our user base.
        Allows us to create as custom a message as the baseEmail.html template allows
        Options for querying:
            user_base:
                downloaded_users
                    unique options:
                        only_unemailed: if we only want to contact unemailed downloads,
                            otherwise will go to the whole list
                # Todo
                active_users
                deleted_users
                applied_users
                all

            universal options:
                email


        All in data:
            {
                user_base:,
                message_header,
                message_body:,
                message_link_text:
                message_link_url:,
                options: [ ]
            }

    :return:
    """
    # Start by checking auth
    auth = check_authentication(req_roles=['admin'])
    if not auth[0]:
        abort(403)

    data = json.loads(request.data.decode('utf-8'))

    try:
        # Start by getting the appropriate email list
        user_base = data['user_base']
        email_list = []
        if user_base == 'downloaded_users':
            # Gather the options if there are any
            # unique options: only_unemailed

            # Defaults to email everyone on the list!
            only_unemailed = False
            if 'only_unemailed' in data['options']:
                only_unemailed = True

            from APP.models import DownloadedUser
            for user in DownloadedUser.objects():
                # So discrete, the only case where the second portion should be false is when
                # we only want unemailed people and they have already been emailed
                if user.email not in email_list and (not (only_unemailed and user.has_been_emailed)):
                    # Make sure to mark that we have sent them an emailio!
                    if not user.has_been_emailed:
                        user.update(has_been_emailed=True)
                    email_list.append(user.email)
        else:
            # Todo: Account for all user bases!
            pass

        # Todo: alert if there are no users found
        # Next gather all the message parts
        message_header = data['message_header']
        message_body = data['message_body']

        message_link_text = None; message_link_url = None
        if 'message_link_text' in data:
            message_link_text = data['message_link_text']
        if 'message_link_url' in data:
            message_link_url = data['message_link_url']

        # Now send off the message
        from APP.email import make_generic_email, send_async_mail
        # WE ONLY WANT TO SEND PERSONAL EMAILS, NOT GROUP SO EVERYONE CAN'T VIEW EVERYONE
        for email in email_list:
            send_async_mail(make_generic_email([email], message_header, message_body, message_link_text, message_link_url))

    except KeyError as ex:
        throw_error("Key error!", 400, request, FILE_TAG, exception=ex)

    try:
        return make_gen_success(new_token=auth[1])
    except IndexError:
        return make_gen_success()


@app.route(base_api_v1_1_ext + '/errors')
def get_errors():
    auth = check_authentication(req_roles=['admin'])
    if not auth[0]:
        abort(403)

    errors = Error.objects()

    try:
        return make_gen_success(new_token=auth[1])
    except IndexError:
        return make_gen_success()




