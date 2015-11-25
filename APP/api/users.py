__author__ = 'austin'


import json

from APP import app, base_api_v1_ext, base_api_v1_1_ext
from APP.models import ActiveUser, DownloadedUser
from APP.utility import throw_error, make_gen_success, check_authentication
from APP.decorators import deprecated
from flask import jsonify, request, abort, make_response
from mongoengine import DoesNotExist


FILE_TAG = __name__
#todo url query param change u/r/l/<param> to u/r/l?param1=foo&param2=bar


@deprecated("1.1")
@app.route(base_api_v1_ext + '/user/find/<string:query_type>', methods=['GET'])
def find_user_dep(query_type):
    """ FIND USER
        REQUEST FORMAT:
        /account/find/query_type
        Query type should be in String format
        Just return user information or update with attached data
            Most often the update will be in the form of a location update

        query_type : either 'id' or 'email'
        query_param : string, containing either an id or an email
    """
    auth = check_authentication()
    if not auth[0]:
        abort(403)

    data = json.loads(request.data.decode('utf-8'))

    if 'query_param' not in data or not isinstance(data['query_param'], str):
        abort(400)
    query_param = data['query_param']
    # If this doesn't find a user, ABORT
    try:
        if query_type == 'id':
            user = ActiveUser.objects.get(id__exact=query_param)
        elif query_type == 'email':
            user = ActiveUser.objects.get(email=query_param)
        else:
            abort(400, data['query_type'] + ' is not a query_param type')
    except DoesNotExist:
        throw_error('Trying to find a user that does not exist: ' + query_param,
                    400, request, FILE_TAG)

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_response(jsonify(result=user.to_json(), new_token=new_token), 200)


@app.route(base_api_v1_1_ext + '/user/find')
def find_user():
    # Todo!
    """

    :return:
    """
    data = json.loads(request.data.decode('utf-8'))

    user = ActiveUser.objects.get(id__exact=data['user_email'])

    return make_response(jsonify(result=user.to_json()), 200)


@app.route(base_api_v1_ext + '/me', methods=['GET', 'PUT', 'POST'])
@app.route(base_api_v1_1_ext + '/user/me', methods=['GET', 'PUT', 'POST'])
def get_me():
    auth = check_authentication()
    if not auth[0]:
        abort(403)
    try:
        try:
            data = json.loads(request.data.decode('utf-8'))
        except ValueError:
            data = request.form
        user = ActiveUser.objects.get_from_email(data['email'])

        try:
            max_returned = data['max']
            if max_returned == -1:
                max_returned = None
            only_current = data['only_current']
        except KeyError:
            max_returned = None
            only_current = False

        shipments = user.get_json_shipment_list(
            max=max_returned,
            only_current=True
        )
        finished_shipments = user.get_json_shipment_list(
            max=max_returned,
            only_past=True
        )
        used_warehouses = user.get_json_used_warehouses_list()
        if user is None:
            throw_error('No user with email: ' + data['email'], 404, request, FILE_TAG)
    except KeyError:
        throw_error('Key error!', 400, request, FILE_TAG)

    # Get the users current shipments!

    to_return = json.loads(user.to_json())

    # Fugedabout the base_user role, we just want shipper/warehouse/driver/admin
    for role in to_return['roles']:
        if role != 'base_user':
            to_return['user_type'] = role
            break

    # Delete all sensitive stufferooni
    # Todo: delete image paths and create methods to get the image from a GET request
    # Format the location from mongoengine format
    try:
        location = to_return['location']['coordinates']
    except KeyError:
        location = None

    keys_to_delete = ('password',
                      'last_login',
                      'roles',
                      '_cls',
                      'date_registered',
                      'registered_by',
                      'location',
                      'auth_token')
    for key in keys_to_delete:
        del to_return[key]

    to_return['location'] = location
    to_return['shipments'] = shipments
    to_return['finished_shipments'] = finished_shipments
    to_return['used_warehouses'] = used_warehouses
    to_return['rating'] = user.get_rating()

    try:
        return jsonify(user=to_return, new_token=auth[1])
    except IndexError:
        return jsonify(user=to_return)


@app.route(base_api_v1_ext + '/applications', methods=['GET'])
@app.route(base_api_v1_1_ext + '/user/applications', methods=['GET'])
def get_all_applications():
    auth = check_authentication(req_roles=['admin'])
    if not auth[0]:
        abort(403)
    applications = ActiveUser.objects(is_full_account=False)
    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_response(jsonify(result=applications.to_json(), new_token=new_token), 200)


@app.route(base_api_v1_ext + '/downloaded_user/<string:email>', methods=['GET'])
@app.route(base_api_v1_ext + '/downloaded_user', methods=['POST'])
@app.route(base_api_v1_1_ext + '/user/downloaded/<string:email>', methods=['GET'])
@app.route(base_api_v1_1_ext + '/user/downloaded', methods=['POST'])
def add_stolen_email(email=None):
    """
        Save an email and phone number taken from each phone downloaded that has downloaded the app. Hehe.
    :return:
    """
    if request.method == 'GET':
        from mongoengine import DoesNotExist
        try:
            downloaded_user = DownloadedUser.objects.get(email=email)
            return make_response(jsonify(downloaded_user=downloaded_user.to_json()), 200)
        except DoesNotExist as ex:
            throw_error("No downloaded user with email: " + str(email), 404, request, FILE_TAG, exception=ex)

    #  Otherwise we have a post request
    data = json.loads(request.data.decode('utf-8'))
    try:
        # Only add them if they have not already been added
        if len(DownloadedUser.objects(email=data['email'])) == 0:
            DownloadedUser(email=data['email'], phone=data['phone']).save()
    except KeyError as ex:
        throw_error("Key error in downloaded users!", 400, request, FILE_TAG, exception=ex)
    return make_gen_success()


@app.route(base_api_v1_1_ext + '/user/list')
def user_list():
    """Returns a list of users for admins
    Request Style: /user?query_param1=foo&query_param2=bar
    Query Parameters:
        subsets: *required - setting it to'' will search all
            inactive
            active
            applied
            active
        user_type: *optional only for downloaded - '' will search all
            shipper
            driver
            *anything in roles
        email: *optional - do a search by email only
        sort_by: *required - field to sort by
            any user field
        sort_order: *required -order to sort
            + will sort ascending
            - sorts descending
        search_by: *optional -field to search
            email
            phone
            todo add more
        search_term: *optional -what to search for
            any string
        start_index: *required start for paginated results todo make sensible default of 0 to make optional
        max_returned: *required how may results to return


    ~Pydocs style
    :return:
    """
    query_parameters = request.values
    auth = check_authentication(req_roles=['admin'])
    if not auth[0]:
        abort(403)

    users_to_return = []
    total_users = 0
    if 'subsets' in query_parameters:
        if query_parameters['subsets'] == 'inactive':
            subsets = ['downloaded', 'applied']
        elif query_parameters['subsets'] == 'downloaded':
            subsets = ['downloaded']
        elif query_parameters['subsets'] == 'applied':
            subsets = ['applied']
        elif query_parameters['subsets'] == 'active':
            subsets = ['active']
        else:
            subsets = ['downloaded', 'applied', 'active']

        for subset in subsets:#cycle through all of the subsets
            if subset == 'downloaded':
                if 'email' in query_parameters:#search by email specificaly this was included as a parameter though it seems redundant?
                    downloaded_users = DownloadedUser.objects(email=query_parameters['email'])
                else:
                    if query_parameters['search_by'] == 'email':#search by
                        downloaded_users = DownloadedUser.objects(email__contains=query_parameters['search_term'])\
                            .order_by(query_parameters['sort_order'] + query_parameters['sort_by'])#let mongo sort
                    elif query_parameters['search_by'] == 'phone':
                        downloaded_users = DownloadedUser.objects(phone__contains=query_parameters['search_term'])\
                            .order_by(query_parameters['sort_order'] + query_parameters['sort_by'])
                    else:#just get all the objects
                        downloaded_users = DownloadedUser.objects().order_by(query_parameters['sort_order'] + query_parameters['sort_by'])
                    total_users += len(downloaded_users)
                # return only the elements for the page
                if (len(downloaded_users) - int(query_parameters['start_index'])) > int(query_parameters['max_returned']):
                    downloaded_users = downloaded_users[int(query_parameters['start_index']):int(query_parameters['max_returned'])]
                else:
                    downloaded_users = downloaded_users[int(query_parameters['start_index']):len(downloaded_users)]
                #add this subset to users to return
                for user in downloaded_users:
                    users_to_return.append(user.to_json())


    ####ADD USER TYPES DRIVER SHIPPER ETC OPTIONAL TERM#######
    if subset == 'applied':#search next sub set
                if 'email' in query_parameters:
                    applied_users = ActiveUser.objects(email=query_parameters['email'], is_full_account=False)
                else:

                    if query_parameters['search_by'] == 'email':
                        applied_users = ActiveUser.objects(email__contains=query_parameters['search_term'],
                                                           is_full_account=False, roles=query_parameters['user_type']
                                                           ).order_by(query_parameters['sort_order'] + query_parameters['sort_by'])
                    elif query_parameters['search_by'] == 'phone':
                        applied_users = ActiveUser.objects(phone__ontains=query_parameters['search_term'],
                                                           is_full_account=False, roles=query_parameters['user_type']
                                                           ).order_by(query_parameters['sort_order'] + query_parameters['sort_by'])
                    else:
                        applied_users = ActiveUser.objects(is_full_account=False, roles=query_parameters['user_type']
                                                           ).order_by(query_parameters['sort_order'] + query_parameters['sort_by'])
                    total_users += len(applied_users)

                if (len(applied_users) - int(query_parameters['start_index'])) > int(query_parameters['max_returned']):
                    applied_users = applied_users[int(query_parameters['start_index']):int(query_parameters['max_returned'])]
                else:
                    applied_users = applied_users[int(query_parameters['start_index']):len(applied_users)]

                for user in applied_users:
                    users_to_return.append(user.to_json())

            ####ADD OTHER SUBSETS ACTIVE USER#####
    if subset == 'active':#search next sub set
        if 'email' in query_parameters:
            active_users = ActiveUser.objects(email=query_parameters['email'], is_full_account=True)
        else:

            if query_parameters['search_by'] == 'email':
                active_users = ActiveUser.objects(email__contains=query_parameters['search_term'],
                                                  is_full_account=True, roles=query_parameters['user_type']
                                                  ).order_by(query_parameters['sort_order'] + query_parameters['sort_by'])
            elif query_parameters['search_by'] == 'phone':
                active_users = ActiveUser.objects(phone__ontains=query_parameters['search_term'],
                                                  is_full_account=True, roles=query_parameters['user_type']
                                                  ).order_by(query_parameters['sort_order'] + query_parameters['sort_by'])
            else:
                active_users = ActiveUser.objects(is_full_account=True, roles=query_parameters['user_type']
                                                  ).order_by(query_parameters['sort_order'] + query_parameters['sort_by'])
            total_users += len(active_users)

        if (len(active_users) - int(query_parameters['start_index'])) > int(query_parameters['max_returned']):
            active_users = active_users[int(query_parameters['start_index']):int(query_parameters['max_returned'])]
        else:
            active_users = active_users[int(query_parameters['start_index']):len(active_users)]

        for user in active_users:
            users_to_return.append(user.to_json())

    return make_response(jsonify(users=users_to_return), 200)


