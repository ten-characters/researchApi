__author__ = 'austin'


from APP import app, bcrypt, server, DEBUG, PALLET_SECRET_ADMIN_PASS, base_web_url, base_api_ext, base_api_v1_ext, base_api_v1_1_ext
from APP.models import ActiveUser, Contact, Truck, \
    Trailer, Address, DriverInfo, Warehouse
from APP.utility import log_error, throw_error, make_gen_success, \
    check_authentication, remove_special_chars, format_string_to_date, make_simple_random_string
from APP.email import make_application_thankyou_message, make_application_approved_message, make_application_rejected_message, send_async_mail
from APP.api.upload import upload_internally, delete_s3_file
from APP.decorators import deprecated

from flask import jsonify, request, abort, make_response, render_template, redirect
from mongoengine import DoesNotExist, ValidationError, NotUniqueError
import braintree
from pygeocoder import Geocoder, GeocoderError
import json
import datetime
import random

FILE_TAG = __name__

# ----------------- ADMIN ----------------- #
# REQUIRES AUTHENTICATION
@app.route(base_api_v1_ext + '/apply/decision/<string:app_id>', methods=['POST', 'PUT'])
@app.route(base_api_v1_1_ext + '/user/apply/decision/<string:app_id>', methods=['POST', 'PUT'])
def application_decision(app_id):
    """
        For each individual piece of a users application, at least for drivers,
        we need to individually approve their information

        New process:
        Regular auth data
        Send along both an app_id aaand

        :arg fields_for_approval: {
            'field' : 'status',
            'field' : 'status',
            'field' : 'status'
        }

        if application is an admin:
            must provide a password to check the legitimacy of the admin!
            :arg admin_password: @PALLET_SECRET_ADMIN_PASS
    :param app_id: string, database id from mongo
    :return:
    """
    # Convert from a UserApplication to just an ActiveUser !
    auth = check_authentication(req_roles=['admin'])
    if not auth[0]:
        abort(403)

    data = json.loads(request.data.decode('utf-8'))

    # Load the admin user so we can reference
    admin_user = ActiveUser.objects.get(email=data['email'])

    # Find in database
    try:
        user = ActiveUser.objects.get(id__exact=app_id)
    except DoesNotExist:
        throw_error("Trying to respond to an application that doesn't exist: " + app_id,
                    400, request, FILE_TAG)

    try:
        # For admins
        # If the user is an admin, the approving admin must send along a secret password
        # to verify that they truly has
        if 'admin' in user.roles:
            # Check the password
            if not data['admin_password'] == PALLET_SECRET_ADMIN_PASS:
                throw_error("Admin password didn't match for admin: " + admin_user.email + " for application: " + app_id,
                            403, request, FILE_TAG)

        user.update(fields_for_approval=data['fields_for_approval'])
        user.reload()
    except KeyError:
        throw_error("Can't find approval fields for decision on app: " + app_id,
                    400, request, FILE_TAG)

    # Check if user has completed all the fields and if they have, give em a full account!
    if user.has_all_fields():
        user.update(is_full_account=True, approved_by=admin_user)
        #  Give them a notification key now that we know their cool
        notif_key_hash = make_simple_random_string(10)
        # Pop off all special character that could be in an email address
        email_without_special_chars = remove_special_chars(user.email)

        notif_key_hash += email_without_special_chars

        user.update(notification_key=notif_key_hash)

        # Congratulate them!
        send_async_mail(make_application_approved_message(user))
    else:
        # Todo! If we have to outright reject them then what happens huh?
        pass

    # Try to see if they have a new auth token
    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_gen_success(new_token=new_token)


# ---------- ADDING TO DATABASE ----------- #
@app.route(base_api_ext + '/apply/user', methods=['POST'])
@app.route(base_api_v1_ext + '/apply/user', methods=['POST'])
@app.route(base_api_v1_1_ext + '/user/apply', methods=['POST'])
def apply():
    """
        Couple different options:
        All:
            Need:
                email
                password
                type
                first_name
                last_name

        Driver:
            Need:

        Shipper/Warehouse:
            Need:

                # address
                # state
                # city
                # country
                # zip
        Admin:
            email
            password
            type
    :return:
    """
    if len(request.form) != 0:
        # THIS IS A POST REQUEST from the application form
        data = request.form
    else:
        # THIS IS A POST REQUEST from (hopefully) a python script of ours
        data = json.loads(request.data.decode('utf-8'))

    try:
        # Confirm that all information common to all accounts is there
        # Could combine all clauses into one if, but that seems less clear
        # These are just provisional checks to make sure they have not applied before
        potential_active_dup = ActiveUser.objects(email=data['email'])
        if len(potential_active_dup) != 0:
            throw_error('User already exists with name: ' + data['first_name'], 400, request, FILE_TAG)

        pass_hash = bcrypt.generate_password_hash(data['password'])

        referral_code_hash = ''
        while referral_code_hash == '' or len(ActiveUser.objects(referral_code=referral_code_hash)) != 0:
            referral_code_hash = make_simple_random_string(8)

        # We really only want their email and password so they can have a temporary login
        # Can only be registered by the web right now

        # Must assign roles!
        roles = [data['type']]

        if data['type'] == 'driver':
            referral_user = None
            try:
                referral_user = ActiveUser.objects.get(referral_code=data['referral_code'])
            except (DoesNotExist, KeyError):
                # might do something cool l8r
                pass

            driver_info = DriverInfo()
            new_user = ActiveUser(
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                password=pass_hash,
                registered_by='web',
                driver_info=driver_info,
                referral_user=referral_user,
                roles=roles,
                referral_code=referral_code_hash
            ).save()

            if referral_user is not None:
                referral_user.update(inc__num_referred=1, push__users_referred=new_user)

        elif data['type'] == 'shipper' or data['type'] == 'warehouse':
            # May differentiate shipper/warehouse later on but for now
            # They have the same information
            # Takes all information necessary from application

            # Gather billing information
            # Might be in the next edition
            # billing_info = Address(
            #     address=data['address'].capitalize(),
            #     state=data['state'].upper(),
            #     city=data['city'].capitalize(),
            #     country=data['country'].upper(),
            #     zip=data['zip']
            # )
            # location = (Geocoder.geocode(billing_info.address + "," + billing_info.city + "," + billing_info.state))[0].coordinates
            billing_info = None
            location = None

            new_user = ActiveUser(
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                password=pass_hash,
                registered_by='web',
                billing_info=billing_info,
                location=location,
                roles=roles,
                referral_code=referral_code_hash
            ).save()

        elif data['type'] == 'admin':
            # Todo: Store who admitted them and maybe a job title/level ?
            new_user = ActiveUser(
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                password=pass_hash,
                registered_by='web',
                roles=roles,
                referral_code=referral_code_hash
            ).save()
        else:
            throw_error('Not a user type: ' + data['type'], 400, request, FILE_TAG)

        # This will set the basic fields for approval
        new_user.basic_init()

    except ValidationError as ex:
        throw_error(
            'Failed to validate a new user form for user: ' + data['email'],
            400, request, FILE_TAG, exception=ex)
    except KeyError as ex:
        throw_error('Key Error! ', 400, request, FILE_TAG, exception=ex)
    except NotUniqueError as ex:
        throw_error(
            'Trying to activate a user that already exists: ' + data['email'],
                400, request, FILE_TAG, exception=ex)
    except GeocoderError as ex:
        throw_error(
            'Failed to geocode billing addr: ' + billing_info.to_json() + ' for user: ' + data['email'],
                400, request, FILE_TAG, exception=ex)

    # Lastly give them a braintree customer id
    res = braintree.Customer.create({
        "first_name": new_user.first_name,
        "last_name": new_user.last_name,
        "email": new_user.email
    })

    if not res.is_success:
        log_error("Can't create braintree customer for: " + new_user.email, FILE_TAG)
    else:
        new_user.update(customer_id=res.customer.id)

    # All gooood!
    if not DEBUG:
        send_async_mail(make_application_thankyou_message(new_user))

    # Also check if their email is on the downloaded email list
    # Importing here because it might not stay
    from APP.models import DownloadedUser
    potential_downloaded_email = DownloadedUser.objects(email=data['email'])
    if len(potential_downloaded_email) != 0:
        potential_downloaded_email[0].delete()

    return make_gen_success()


@deprecated("1.1.1", reason="Moved to user/update")
@app.route(base_api_v1_ext + '/register/truck', methods=['POST'])
@app.route(base_api_v1_1_ext + '/truck/register', methods=['POST'])
def register_truck():
    """
        in data:
            plate:
            year:
            model:

        in files:
            truck:
    :return:
    """
    auth = check_authentication(req_roles=['driver'])
    if not auth[0]:
        abort(403)

    data = json.loads(request.data.decode('utf-8'))

    # First find the user that is trying to register a trailer
    user = ActiveUser.objects.get(email__exact=data['email'])

    try:
        uploaded_files = upload_internally('truck', request.files['truck'], want_thumb=True)

        truck = Truck(
            plate=data['plate'],
            year=data['year'],
            model=data['model'],
            photo_path=uploaded_files[0],
            photo_thumb_path=uploaded_files[1]
        )
        user.update(push__driver_info__trucks=truck)

    except ValidationError as ex:
        delete_s3_file(uploaded_files[0], uploaded_files[1])
        throw_error("Failed to validate new trailer for: " + data['email'], 400, request, FILE_TAG, exception=ex)
    except KeyError as ex:
        delete_s3_file(uploaded_files[0], uploaded_files[1])
        throw_error("Key error while registering a new trailer for: " + data['email'], 400, request, FILE_TAG, exception=ex)

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_gen_success(new_token=new_token)


@deprecated("1.1.1", reason="Moved to user/update")
@app.route(base_api_v1_ext + '/register/trailer', methods=['POST'])
@app.route(base_api_v1_1_ext + '/register/trailer', methods=['POST'])
def register_trailer():
    """
        in data:
            plate:
            year:
            model:
            model_type:
            size:

        in files:
            trailer:
    :return:
    """
    auth = check_authentication(req_roles=['driver'])
    if not auth[0]:
        abort(403)

    data = json.loads(request.data.decode('utf-8'))

    # First find the user that is trying to register a trailer
    user = ActiveUser.objects.get(email__exact=data['email'])

    try:
        trailer_photo = upload_internally('trailer', request.files['trailer'])
        trailer_thumb_photo = upload_internally('trailer', request.files['trailer'], want_thumb=True)

        trailer = Trailer(
                    plate=data['plate'],
                    year=data['year'],
                    model=data['model'],
                    model_type=data['model_type'],
                    size=data['size'],
                    photo_path=trailer_photo,
                    photo_thumb_path=trailer_thumb_photo
                )
        user.update(push__driver_info__trailers=trailer)

    except ValidationError as ex:
        delete_s3_file(trailer_photo)
        throw_error("Failed to validate new trailer for: " + data['email'], 400, request, FILE_TAG, exception=ex)
    except KeyError as ex:
        delete_s3_file(trailer_photo)
        throw_error("Key error while registering a new trailer for: " + data['email'], 400, request, FILE_TAG, exception=ex)

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_gen_success(new_token=new_token)


# REQUIRES AUTHENTICATION
@app.route(base_api_v1_ext + '/register/warehouse', methods=['POST'])
@app.route(base_api_v1_1_ext + '/warehouse/register', methods=['POST'])
def register_warehouse():
    """
    Takes parameters :

    contact list -> [ { 'email' , 'name' , 'phone' } , ... ]
    :return:
    """
    if not check_authentication(req_roles=['warehouse']):
        abort(403)
    data = json.loads(request.data.decode('utf-8'))

    # First check to make sure this manager person is legit
    # Must have a manager id if not registering the warehouse internally
    # This will only happen when a warehouse signs up explicitly
    # Todo: Make a claim_warehouse() function for warehouse managers to claim already registered warehouses
    if 'manager_id' not in data or not isinstance(data['manager_id'], str):
        abort(400)
    else:
        try:
            manager = ActiveUser.objects.get(id__exact=data['manager_id'])
        except DoesNotExist:
            throw_error(
                'Trying to register a warehouse to a non-existent manager: ' + data['manager_id'],
                400, request, FILE_TAG)

    # Then check to make sure the person registering is a real person
    if 'user_id' not in data or not isinstance(data['user_id'], str):
        abort(400)
    else:
        # Check to see if it is the manager who is registering. If so, no need to re-query
        if data['user_id'] != data['manager_id']:
            try:
                user = ActiveUser.objects.get(id__exact=data['user_id'])
            except DoesNotExist:
                throw_error(
                    'Trying to register a warehouse by a non-existent user: ' + data['user_id'],
                    400, request, FILE_TAG)
        else:
            user = manager

    # So they pass the legitness test... but does the data?
    if 'name' not in data or not isinstance(data['name'], str):
        abort(400)

    # Check to see if the warehaus has already been registered by name
    try:
        Warehouse.objects.get(name__exact=data['name'])
        # Should only get here if the query returned a warehouse
        throw_error('Warehouse already registered', 400, request, FILE_TAG)
    except DoesNotExist:
        # Awesome this is what we totally want cewl
        pass

    # OTHER INFO
    if 'service' not in data or not isinstance(data['service'], str):
        abort(400)
    try:
        # Gather Billing Info
        address_info = Address(
            address=data['address'],
            state=data['state'],
            city=data['city'],
            country=data['country'],
            zip=data['zip']
        )
    except (ValidationError, KeyError):
        abort(400)

    # Build the contact list!
    contact_list = []
    for contact in data['contact_list']:
        try:
            ext = None
            try:
                ext = contact['ext']
            except KeyError:
                pass

            new_contact = Contact(
                name=contact['name'],
                email=contact['email'],
                phone=contact['phone'],
                ext=ext
            )
            contact_list.append(new_contact)
        except ValidationError as ex:
            # Just log the error, shouldn't destroy the whole request
            # although we should never get here @ craig ...
            template = "An exception of type {0} occured. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            log_error(message, 400, request, FILE_TAG)

    if len(contact_list) == 0:
        primary_email = None
    else:
        primary_email = contact_list[0]

    # OPTIONALS
    pickup = None
    dropoff = None
    if 'pickup_instructions' in data and isinstance(data['pickup_instructions'], str):
        pickup = data['pickup_instructions']
    if 'dropoff_instructions' in data and isinstance(data['dropoff_instructions'], str):
        dropoff = data['dropoff_instructions']


    # Now we can save!
    Warehouse(
        registered_by_service=data['service'],
        registered_by_user=user,
        name=data['name'],
        location=data['location'],
        address=address_info,
        pickup_instructions=pickup,
        dropoff_instructions=dropoff,
        primary_email=primary_email,
        contact_list=contact_list,
        manager=manager
    ).save()
    # Todo: Claim Warehouse endpoint where Manager users can store the warehouse ids and the warehouses take their emails
    return make_gen_success()


# Will never have a manager when being registered internally
def register_warehouse_internally(service, user, warehouse_name, location, address, contact_list, pickup_instructions=None, dropoff_instructions=None):
    """
    :param service: string
    :param user: User object
    :param warehouse_name: string
    :param location: [float, float]
    :param address: Address object
    :param contact_list: an array of dicts
    :param pickup_instructions: string
    :param dropoff_instructions: string
    :return:
    """

    # This will still work if people are accidentally trying to register the same warehouse
    # Need to add method to add contact to warehouse !
    if len(contact_list) == 0:
        throw_error("Must register the warehouse with at least one contact!", 400, request, FILE_TAG)

    # See if we can find another warehouse already registered by the same name (case insensitive) and address
    try:
        new_warehouse = Warehouse.objects.get(name=warehouse_name, address=address)
    except DoesNotExist:
        primary_email = contact_list[0].email

        new_warehouse = Warehouse(
            registered_by_service=service,
            registered_by_user=user,
            name=warehouse_name,
            location=location,
            address=address,
            primary_email=primary_email,
            pickup_instructions=pickup_instructions,
            dropoff_instructions=dropoff_instructions
        ).save()
    except ValidationError:
        throw_error("Failed to register a warehouse internally by user: " + str(user),
                    400, request, FILE_TAG)

    # Add all contacts to the warehouse if they are not already there!
    for contact in contact_list:
        # Do a quick cycle through to make sure this is a new contact
        is_new = True
        for listed_contact in new_warehouse.contacts_list:
            if contact.name.lower() == listed_contact.name.lower():
                is_new = False
        if is_new:
            new_warehouse.update(push__contacts_list=contact)

    user.update(push__used_warehouses=new_warehouse)
    return new_warehouse


