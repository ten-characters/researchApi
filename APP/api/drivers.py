__author__ = 'austin'

from APP import app, base_api_v1_ext, base_api_v1_1_ext
from APP.utility import check_authentication, make_gen_success, throw_error
from APP.models import ActiveUser, DriverIssue, BreadcrumbLocation
from APP.email import send_async_mail, make_issue_message

from flask import abort, request, jsonify, make_response
from mongoengine import DoesNotExist, ValidationError
import json
from datetime import datetime, timedelta

FILE_TAG = __name__


@app.route(base_api_v1_ext + '/drivers/toggle_active', methods=['GET', 'PUT'])
@app.route(base_api_v1_1_ext + '/drivers/toggle_active', methods=['GET', 'PUT'])
def toggle_active():
    """

    :return:
    """
    auth = check_authentication(req_roles=['driver'])
    if not auth[0]:
            abort(403)
    data = json.loads(request.data.decode('utf-8'))

    driver = ActiveUser.objects.get_from_email(data['email'])
    if driver is None:
        throw_error('No driver by email: ' + data['email'], 404, request, FILE_TAG)

    # trolol
    if driver.driver_info:
        driver.driver_info.is_active = not driver.driver_info.is_active
        driver.save()
    else:
        throw_error("Non Driver user trying to toggle!", 404, request, FILE_TAG)

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_gen_success(new_token=new_token)


@app.route(base_api_v1_ext + "/drivers/issue", methods=['PUT', 'POST'])
@app.route(base_api_v1_1_ext + "/drivers/issue", methods=['PUT', 'POST'])
def report_breakdown():
    """

    :return:
    """
    auth = check_authentication(req_roles=['driver'])
    if not auth[0]:
        abort(403)

    # A message should be sent along to both the customer and the consignee
    # Include: Location, can it be delivered today, optional message
    data = json.loads(request.data.decode('utf-8'))
    driver = ActiveUser.objects.get_from_email(data['email'])

    # Necessary
    try:
        # Should be a bool !
        can_deliver = data['can_deliver']
        estimated_delay_hours = None
        if can_deliver:
            estimated_delay_hours = float(data['estimated_delay_hours'])

    except KeyError:
        throw_error("Key error!", 400, request, FILE_TAG)

    # Add issue to driver and then email appropriate parties
    issue = DriverIssue(
        can_deliver=can_deliver,
        estimated_delay_hours=estimated_delay_hours,
        location=driver.location
    )

    driver.update(push__driver_info__issues=issue)
    driver.save()
    # For every shipment in the trucker's trailer, send appropriate email
    for shipment in driver.shipments:
        # If they have canceled before picking up, we should try to find a new driver for this
        if not shipment.is_in_transit:
            # Should just update as unaccepted, then the shipmentWatcher should deal with that
            shipment.update(is_accepted=False)
            issue_message = make_issue_message(shipment, issue)
        else:
            # IF THEY HAVE ALREADY PICKED UP, WE GOTTA DO SOMETHING, SO ALERT US
           issue_message = make_issue_message(shipment, issue, notify_us=True)

        shipment.update(push__issues=issue)

        send_async_mail(issue_message)



    try:
        return make_gen_success(new_token=auth[1])
    except IndexError:
        return make_gen_success()


@app.route(base_api_v1_ext + '/drivers/update_location', methods=['PUT', 'POST'])
@app.route(base_api_v1_1_ext + '/drivers/update_location', methods=['PUT', 'POST'])
def update_driver_location():
    """ SPECIAL UPDATE FOR DRIVERS
        Used for ease up updating location while on duty and updating their shipment locations as well

        Only takes auth creds and a location
        location - [lat,lng] or (lat,lng)
        orientation - float
    """
    auth = check_authentication()
    if not auth[0]:
        abort(403)

    data = json.loads(request.data.decode('utf-8'))

    driver = ActiveUser.objects.get_from_email(data['email'])
    if not driver.driver_info:
        abort(400)

    # Validate location here so we can use it multiple places and not have to re-validate
    try:
        location = data['location']
        if not isinstance(location, (list, tuple)):
            raise ValidationError
    except (ValidationError, KeyError):
        throw_error("Couldn't validate location update for " + data['email'], 400, request, FILE_TAG)

    # Check if the driver has a currently active shipment
    # Right now they will only have one, but eventually maybe more
    # so lets prepare for that
    # Start tracking as soon as the shipment is accepted
    # Will be sorted by the web app
    for shipment in driver.shipments:
        if shipment.is_accepted and not shipment.is_finished:
            # Make a new breadcrumb location update
            loc = BreadcrumbLocation(location=location, time_stamp=datetime.utcnow())
            print("Bread gummy for " + str(shipment.id) + ": " + str(loc.location) + " at " + loc.time_stamp.isoformat())
            shipment.update(push__tracked_locations=loc)
            shipment.save()


    # Get the orientation if attached, if not, default to 0.0
    if 'orientation' in data:
        # I mean, how accurate do we have to be ? !
        orientation = round(float(data['orientation']), ndigits=5)
    else:
        orientation = 0.0

    if 'velocity' in data:
        velocity = round(float(data['velocity']), ndigits=3)
    else:
        velocity = 0.0

    # Now just update the drivers location so that we KNOW
    driver.update(location=location, driver_info__orientation=orientation, driver_info__velocity=velocity)
    driver.save()

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_gen_success(new_token)


# -------------- DRIVERS ------------------ #
@app.route(base_api_v1_ext + '/drivers', methods=['GET'])
@app.route(base_api_v1_1_ext + '/drivers', methods=['GET'])
def get_drivers_in_range():
    """ GET DRIVERS IN RANGE
        REQUEST FORMAT:
            /drivers -d {"rng":rng, "location": [lat,lng]}
            /drivers -d {"rng":rng, "location": (lat,lng)}
         Just return a list of lat/lng combos, don't need everything about the drivers:
         [
            [lat, lng],
            [lat, lng],
            [lat, lng]
         ]
    """
    try:
        auth = check_authentication(req_roles=['shipper'])
        if not auth[0]:
            abort(403)

        # Get range from data
        data = json.loads(request.data.decode('utf-8'))

        rng = data['rng']
        location = data['location']

        # if not isinstance(rng, (float, int)) or not isinstance(location, (tuple, list)):
        #     raise ValueError

        drivers = ActiveUser.objects.get_drivers_in_rng_of(rng, location)

        print(FILE_TAG + "  " + "Num Active Drivers:" + str(len(drivers)))
        locations = []
        if drivers is not None:
            for driver in drivers:
                # Let's start filtering this list to make sure they are really active...
                if datetime.utcnow() > driver.last_request + app.config['ACTIVE_DRIVER_THRESHOLD']:
                    driver.update(driver_info__is_active=False)
                    drivers.remove(driver)
                else:
                    locations.append(driver.location['coordinates'])

        try:
            return make_response(jsonify(result=json.dumps(locations), new_token=auth[1]), 200)
        except IndexError:
            return make_response(jsonify(result=json.dumps(locations)), 200)

    except KeyError as ex:
        throw_error("Key error in driver!", 400, request, FILE_TAG, exception=ex)
    except ValueError as ex:
        throw_error("Value error in driver!", 400, request, FILE_TAG, exception=ex)
    except TypeError as ex:
        throw_error("Type error in driver!", 400, request, FILE_TAG, exception=ex)


@app.route(base_api_v1_ext + '/driver_profile')
@app.route(base_api_v1_1_ext + '/drivers/profile')
def driver_profile():
    """

    :return:
    """
    try:
        auth = check_authentication()
        if not auth[0]:
                abort(403)
        data = json.loads(request.data.decode('utf-8'))

        driver = ActiveUser.objects.get_from_id(data['id'])
        if driver is None:
            throw_error('no driver by id: ' + data['id'], 404, request, FILE_TAG)
        driver = json.loads(driver.to_json())
        # TODO: add all keys to delete for driver profile and make this a def in User model ( get_profile_info(self) )
        keys_to_delete = ('password',
                          'last_login',
                          'roles',
                          '_cls',
                          'date_registered',
                          'registered_by',
                          'location',
                          'auth_token')
        for key in keys_to_delete:
            del driver[key]
        try:
            return make_response(jsonify(result=driver, new_token=auth[1]), 200)
        except IndexError:
            return make_response(jsonify(result=driver), 200)
    except KeyError:
        abort(400, 'Key Error')
    except ValueError:
        abort(400, 'Value Error')
    except TypeError:
        abort(400, 'Type Error')

