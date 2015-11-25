__author__ = 'austin'

from APP import app, bcrypt, base_api_ext, base_api_v1_ext, base_api_v1_1_ext, merchant_master_id
from APP.api.upload import upload_internally, delete_s3_file
from APP.email import send_async_mail, make_password_reset_message, make_password_reset_success
from APP.models import ActiveUser, Address, Truck, Trailer
from APP.utility import throw_error, make_gen_success, check_authentication, \
    make_simple_random_string, format_string_to_date
from flask import request, abort
from mongoengine import DoesNotExist, ValidationError
import json
from datetime import datetime
import braintree

FILE_TAG = __name__


# -------------- ACCOUNTS ------------------ #
@app.route(base_api_v1_ext + '/account/update', methods=['PUT'])
@app.route(base_api_v1_1_ext + '/user/update', methods=['PUT'])
def update_user():
    """ UPDATE USER

        # MUST HAVE
        'email'
        'token'

        Just  update with attached data
            ALL DATA IS OPTIONAL
            Most often the update will be in the form of a location update from drivers

        Keys:
        'first_name': str
        'last_name': str
        'phone' : str
        'dob': str
        'billing_info': str
            # json.dumps({          // This is to account for form data, where nested dicts fail to encode
                'address':''
                'city':''
                'state':''
                'country':''
                'zip':''
            })
        'company'
        'location': (tuple, list) of (float, int)

        If there is driver info to update
        'driver_info' : str
            json.dumps({
                'dot_number':''
                'hut_number':''
                'mc_number:''
                'truck':
                    {
                        plate:
                        year:
                        model:
                    }
                'trailer':
                    {
                        plate:
                        year:
                        model:
                        model_type:
                        size:
                    }
                })

        Files:

        profile_picture
        insurance
        license


        When updating truck and trailer photos, you need a plate to find the truck/trailer

        truck_photo: file
            - Other needs:
                plate: str
        trailer_photo: file
            - Other needs:
                plate: str

        :options dob: '%m/%d/%Y-%H:%M:%S'
                        '%m/%d/%Y'
                        '%Y-%m-%d-%H:%M:%S'
                        '%Y-%m-%d'
    """

    auth = check_authentication()
    if not auth[0]:
        abort(403)

    # Must support both just data and form data as there could be files sent along in a multi-part form
    if len(request.data) != 0:
        data = json.loads(request.data.decode('utf-8'))
    else:
        data = request.form

    files = request.files

    # First try to find the user
    try:
        email = data['email'].lower()
        user = ActiveUser.objects.get(email__exact=email)
    except KeyError:
        throw_error('Key error', 400, request, FILE_TAG)
    except DoesNotExist:
        throw_error('Trying to find a user that does not exist: ' + data['email'],
                    404, request, FILE_TAG)

    # Update user
    if 'first_name' in data and isinstance(data['first_name'], str):
        user.update(first_name=data['first_name'])
    if 'road_name' in data and isinstance(data['road_name'], str):
        user.update(road_name=data['road_name'])
    if 'last_name' in data and isinstance(data['last_name'], str):
        user.update(last_name=data['last_name'])
    if 'phone' in data and isinstance(data['phone'], str):
        user.update(phone=data['phone'])
    if 'billing_info' in data and isinstance(data['billing_info'], str):
        billing = json.loads(data['billing_info'])
        try:
            updated_info = Address(
                address=billing['address'],
                city=billing['city'],
                state=billing['state'],
                country=billing['country'],
                zip=billing['zip'])
            user.update(billing_info=updated_info)
        except ValidationError:
            abort(400)

    if 'company' in data and isinstance(data['company'], str):
        user.update(company=data['company'])

    if 'location' in data and isinstance(data['location'], (list, tuple)):
        user.update(location=data['location'])

    if 'dob' in data and isinstance(data['dob'], str):
        dob = format_string_to_date(data['dob'])
        if dob is not None:
            user.update(dob=dob)

    # SECTION
    # PHOTOS
    if 'profile_picture' in files:
        # Upload both a thumbnail and a full size !
        uploaded_files = upload_internally('profile_picture', files['profile_picture'], want_thumb=True)

        # Delete oldies before storing newies
        if user.profile_picture_path != '':
            delete_s3_file(user.profile_picture_path)
        if user.profile_picture_thumb_path != '':
            delete_s3_file(user.profile_picture_thumb_path)

        user.update(profile_picture_path=uploaded_files[0])
        user.update(profile_picture_thumb_path=uploaded_files[1])

    # IN NEED OF APPROVAL
    # Todo: should we archive their information for a certain period of time?
    if 'insurance' in files:
        if user.driver_info.insurance_form_path != '':
            delete_s3_file(user.driver_info.insurance_form_path)
        # Store key to delete after successful upload
        user.update(driver_info__insurance_form_path=upload_internally('insurance', files['insurance']))
        user.fields_for_approval.update(insurance="pending_approval")
        user.save()

    if 'license' in files:
        if user.driver_info.license_form_path != '':
            delete_s3_file(user.driver_info.license_form_path)
            
        user.update(driver_info__license_form_path=upload_internally('license', files['license']))
        user.fields_for_approval.update(license="pending_approval")
        user.save()

    if 'truck_photo' in files:
        try:
            plate = data['plate']
        except KeyError as ex:
            throw_error("No plate!", 400, request, FILE_TAG, exception=ex)
        # First find the truck
        truck = None
        for t in user.driver_info.trucks:
            if t.plate == data['plate']:
                truck = t

        if truck is None:
            throw_error("Can't find a truck with plate: " + plate, 404, request, FILE_TAG)
        
        uploaded_files = upload_internally('truck', files['truck_photo'], want_thumb=True)
        if truck.photo_path != '':
            delete_s3_file(truck.photo_path)
        if truck.photo_thumb_path != '':
            delete_s3_file(truck.photo_thumb_path)
        
        updated_truck = truck
        updated_truck.photo_path = uploaded_files[0]
        updated_truck.photo_thumb_path = uploaded_files[1]
        # Pull the old truck and then push the new one!
        user.update(pull__driver_info__trucks=truck)
        user.update(push__driver_info__trucks=updated_truck)
        
    if 'trailer_photo' in files:
        try:
            plate = data['plate']
        except KeyError as ex:
            throw_error("No plate!", 400, request, FILE_TAG, exception=ex)
        # First find the trailer
        trailer = None
        for t in user.driver_info.trailers:
            if t.plate == data['plate']:
                trailer = t

        if trailer is None:
            throw_error("Can't find a trailer with plate: " + plate, 404, request, FILE_TAG)
        
        uploaded_files = upload_internally('trailer', files['trailer_photo'], want_thumb=True)
        if trailer.photo_path != '':
            delete_s3_file(trailer.photo_path)
        if trailer.photo_thumb_path != '':
            delete_s3_file(trailer.photo_thumb_path)
        
        updated_trailer = trailer
        updated_trailer.photo_path = uploaded_files[0]
        updated_trailer.photo_thumb_path = uploaded_files[1]
        # Pull the old trailer and then push the new one!
        user.update(pull__driver_info__trailers=trailer)
        user.update(push__driver_info__trailers=updated_trailer)

    # SECTION
    # OTHER DRIVER INFO

    # Only allow them to add a referring user once!
    if 'referral_code' in data and user.referral_user is not None:
        referral_user = None
        try:
            referral_user = ActiveUser.objects.get(referral_code=data['referral_code'])
            referral_user.update(inc__num_referred=1)
            user.update(referral_user=referral_user)
        except (DoesNotExist):
            # Todo: just pass for now
            # should we send back a bad response?
            pass

    # Ok, this is the part that gets kind of weird
    # So, for some reason, you can't send nested dicts in a multipart form
    # --> *** thus, flatten them into its json representation ***
    # --> and put as the value of key: 'driver_info'
    if 'driver_info' in data and isinstance(data['driver_info'], str):
        try:
            if user.driver_info is None:
                throw_error('User is not registered as a driver: ' + email, 400, request, FILE_TAG)

            # info = ast.literal_eval(data['driver_info'])
            info = json.loads(data['driver_info'])

            if 'hut_number' in info:
                user.update(driver_info__hut_number=info['hut_number'])

            # These fields are for approval
            # Todo: Make these fields for approval!
            #  Need to decide if we will temp suspend their account while we review these updates
            #     Document uploads
            if 'mc_number' in info:
                user.update(driver_info__mc_number=info['mc_number'])
                user.fields_for_approval.update(mc_number="pending_approval")
                user.save()
            if 'dot_number' in info:
                user.update(driver_info__dot_number=info['dot_number'])
                user.fields_for_approval.update(dot_number="pending_approval")
                user.save()

            if 'trailer' in info:
                try:
                    trailer = Trailer(
                                plate=data['plate'],
                                year=data['year'],
                                model=data['model'],
                                model_type=data['model_type'],
                                size=data['size']
                            )
                    user.update(push__driver_info__trailers=trailer)

                except ValidationError as ex:
                    throw_error("Failed to validate new trailer for: " + data['email'], 400, request, FILE_TAG, exception=ex)
                except KeyError as ex:
                    throw_error("Key error while registering a new trailer for: " + data['email'], 400, request, FILE_TAG, exception=ex)

            if 'truck' in info:
                try:
                    truck = Truck(
                        plate=data['plate'],
                        year=data['year'],
                        model=data['model']
                    )
                    user.update(push__driver_info__trucks=truck)

                except ValidationError as ex:
                    throw_error("Failed to validate new trailer for: " + data['email'], 400, request, FILE_TAG, exception=ex)
                except KeyError as ex:
                    throw_error("Key error while registering a new trailer for: " + data['email'], 400, request, FILE_TAG, exception=ex)

        except ValidationError:
            throw_error('Validation error when updating: ' + email,
                        400, request, FILE_TAG)

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_gen_success(new_token=new_token)


@app.route(base_api_v1_ext + '/account/delete', methods=['DELETE'])
@app.route(base_api_v1_1_ext + '/user', methods=['DELETE'])
def delete_account():
    """ DELETE ACCOUNT
    REQUEST FORMAT:
        /account/delete
        id should be an object id in string form
        Don't call this method willy-nilly, must make sure the user reeeeaally wants to go

        Delete a user with the attached data. Moves the Deleted user to an archived collection
    """
    auth = check_authentication()
    if not auth[0]:
        abort(403)
    data = json.loads(request.data.decode('utf-8'))

    if 'reason' not in data or not isinstance(data['reason'], str):
        abort(400)
    if 'service' not in data or not isinstance(data['service'], str):
        abort(400)

    try:
        # Gets a reference to the ActiveUser object
        to_delete = ActiveUser.objects.get(email__exact=data['email'].lower())
        # Delete it from the active user collections
        to_delete.delete()
        # Switch, add deleted field points, then save it to a new collection
        to_delete.switch_collection('deleted_user')
        to_delete.date_deleted = datetime.utcnow()
        to_delete.deleted_by = data['']
        to_delete.reason_deleted = data['reason']
        to_delete.save()
    except DoesNotExist:
        throw_error('Trying to delete a user that does not exist: ' + data['email'], 400, request, FILE_TAG)

    # No need to send back a refreshed token, they won't need it anymore :(
    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_gen_success(new_token=new_token)


@app.route(base_api_v1_ext + '/account/reset', methods=['PUT', 'POST'])
@app.route(base_api_v1_1_ext + '/user/passwordreset', methods=['PUT', 'POST'])
def reset_password():
    """
        Two types, either asking for a reset or trying to reset.
        PUT - Asking
            - data:
                - email
        POST - Trying to reset
            - data:
                - email
                - reset_hash
                - new_password
    :return:
    """
    data = json.loads(request.data.decode('utf-8'))
    try:
        user = ActiveUser.objects.get_from_email(data['email'])
    except KeyError as ex:
        throw_error('No email in data!', 400, request, FILE_TAG, exception=ex)

    if user is None:
            throw_error('No user found with email: ' + data['email'], 404, request, FILE_TAG)

    if request.method == 'PUT':
        # Send the email with the password reset hash

        reset_password_key = make_simple_random_string(10)
        user.update(reset_key=reset_password_key)

        # Send the hash in the email, linking to the web app
        reset_hash = bcrypt.generate_password_hash(reset_password_key)

        # now send the email
        send_async_mail(make_password_reset_message(user, reset_hash))
        return make_gen_success()

#     Else this is POST
    try:
        if bcrypt.check_password_hash(data['reset_hash'], user.reset_key):
            # Make sure to clear the reset_hash
            # This will make sure that each link will have a one usage life
            user.update(password=bcrypt.generate_password_hash(data['new_password']), reset_key='')
            send_async_mail(make_password_reset_success(user))
            return make_gen_success()
        else:
            return throw_error('The password reset key did not match for user: ' + user.email, 400, request, FILE_TAG)
    except KeyError as ex:
        throw_error('Key error resetting password!', 400, request, FILE_TAG, exception=ex)


@app.route(base_api_ext + '/user/add_payment', methods=['GET', 'POST'])
@app.route(base_api_v1_ext + '/user/add_payment', methods=['GET', 'POST'])
@app.route(base_api_v1_1_ext + '/user/add_payment', methods=['GET', 'POST'])
def add_payment():
    """
        In data:
            - normal auth stuff
            - account_number
            - routing_number
    :return:
    """
    if request.form:
        # No need to send back a new token, should be a fraash login
        data = request.form
        auth = check_authentication(form_data=True)
    else:
        data = json.loads(request.data.decode('utf-8'))
        auth = check_authentication()

    if not auth[0]:
        abort(403)

    user = ActiveUser.objects.get_from_email(data['email'])

    try:
        result = braintree.MerchantAccount.create({
            'individual': {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': user.phone,
                'date_of_birth': user.dob,
                'address': {
                    'street_address': user.billing_info.address,
                    'locality': user.billing_info.city,
                    'region': user.billing_info.state,
                    'postal_code': user.billing_info.zip
                }
            },
            'funding': {
                'descriptor': "Pallet Payment",
                'destination': braintree.MerchantAccount.FundingDestination.Bank,
                'account_number': data['account_number'],
                'routing_number': data['routing_number']
            },
            'tos_accepted': True,
            'master_merchant_account_id': merchant_master_id,
            'id': user.customer_id
        })

        if isinstance(result, braintree.ErrorResult):
            throw_error("Error in your info: " + result.errors.deep_errors[0].message, 400, request, FILE_TAG)

    except KeyError as ex:
        throw_error("Key error while creating sub-merchant!", 400, request, FILE_TAG, exception=ex)

    # Now update their fields for approval
    user.fields_for_approval.braintree = "Processing"
    user.save()

    try:
        return make_gen_success(new_token=auth[1])
    except IndexError:
        return make_gen_success()
