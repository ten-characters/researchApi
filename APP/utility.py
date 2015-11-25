__author__ = 'austin'

from APP.models import ActiveUser, Error
from APP.decorators import deprecated

from flask import jsonify, request
from flask import abort, make_response
from json import JSONEncoder, JSONDecoder, loads
from datetime import datetime

FILE_TAG = __name__


# SECTION
def log(message, tag):
    """

    :param message:
    :param tag:
    :return:
    """
    log_message = "{tag}: {date_string} : {message}".format(tag=tag,
                                                            date_string=str(datetime.utcnow()),
                                                            message=message)
    print(log_message)


def format_exception(ex):
    """

    :param ex:
    :type ex: Exception
    :return:
    """
    return "An exception of type {ex_type} occured. Arguments:\n{args}".format(ex_type=str(type(ex)), args=ex.args)


# Error Handlers
def throw_error(message, code, request_obj, tag, exception=None, new_token=None):
    """

        :param message:
        :type message: str
        :param code:
        :type code: int
        :param request_obj:
        :type request_obj: flask.request
        :param tag:
        :type tag: str
        :keyword exception:
        :type exception: Exception
        :keyword new_token:
        :type new_token:
        :return:
    """
    from mongoengine import ValidationError

    if exception is not None:
        exception = format_exception(exception)

    try:
        # Save the hopefully more descriptive error
        Error(
            message=message,
            code=code,
            url_request=request_obj.base_url,
            remote_addr=request_obj.environ['REMOTE_ADDR'],
            user_agent=request_obj.user_agent.string,
            tag=tag,
            exception=exception
        ).save()
    except ValidationError:
        # Could also just create a new error here
        # Just aborts
        pass

    abort(code, description=message)
    return


def log_error(message, tag, exception=None):
    """

    :param message:
    :param tag:
    :param exception:
    :return:
    """
    if exception is not None:
        exception = format_exception(exception)
    log(message, tag)
    Error(message=message, tag=tag, exception=exception).save()


# SECTION
def check_authentication(req_roles=None, form_data=False):
    """

    :param req_roles: a list of roles
    :param form_data: a boolean, whether the data is wrapped in the request form or not
    :return:
    """
    # Try to get the user from the email provided and then check auth
    if not(request.form or request.data) and form_data is None:
        throw_error("No Auth Data!", 403, request, FILE_TAG)
    else:
        if form_data:
            # Support for multi-part forms
            # could build dict data and always pass
            data = form_data
        else:
            if request.data:
                data = loads(request.data.decode('utf-8'))
            else:
                data = request.form

    try:
        user = ActiveUser.objects.get_from_email(data['email'])
        if user is None:
            throw_error('No User with email: ' + data['email'], 404, request, FILE_TAG)

        # auth_with_token returns a tuple, (bool, new_token=None)
        auth = user.auth_with_token(data['token'])
        if not auth[0]:
            # If they are unauthenticated, send a 403 response back
            # telling them to log in again
            return False, None

        new_token = None
        if auth[1] is not None:
            new_token = auth[1]

    except KeyError:
        throw_error('Key Error!', 403, request, FILE_TAG)

    if req_roles is not None:
        user_roles = user.get_roles()
        # Check to make sure all required roles are had by user

        if 'admin' in req_roles and 'admin' not in user_roles:
            return False, new_token

        # 'admin' is allowed all access
        if 'admin' not in user_roles:
            passes = True
            for r in req_roles:
                # Check if a listed role is not in the user roles
                if r not in user_roles:
                    passes = False
            if not passes:
                return False, new_token

    return True, new_token


from flask import render_template
import pdfkit
from APP.api.upload import upload_internally
import os
import json
from APP import TEMP_MEDIA_FOLDER, STATIC_FOLDER
from werkzeug.datastructures import FileStorage
def create_pod(shipment, signature_file, signee_name):
    """
        Given a shipment, a signature photo file, and a
    :param shipment: APP.mondels.Shipment Object
    :param signature_file: FileStorage Object
    :param signee_name:
    :return: filename (in s3 storage) of the new pod
    """
    # Gather all necessary parts of the pod from the shipment object
    ref_numbers = dict(shipment.reference_numbers)
    pod_number = shipment.proof_of_delivery_number
    commodity = shipment.commodity
    num_pallets = shipment.num_pallets
    num_pieces = shipment.num_pieces_per_pallet
    weight = shipment.weight

    shipper_address_dict = json.loads(shipment.shipper.billing_info.to_json())
    shipper_company = shipment.shipper.company

    pickup_address_dict = json.loads(shipment.start_warehouse.address.to_json())
    pickup_name = shipment.start_warehouse.name
    pickup_phone = shipment.start_contact.phone

    dropoff_address_dict = json.loads(shipment.end_warehouse.address.to_json())
    dropoff_name = shipment.end_warehouse.name
    dropoff_phone = shipment.end_contact.phone

    # Save the signature file to be used in the rendering
    name, ext = os.path.splitext(signature_file.filename)
    local_sign_file = create_temp_file('sign' + ext)
    local_sign_file.close()
    signature_file = FileStorage(signature_file)
    signature_file.save(local_sign_file.name)

    pallet_logo_file = open(STATIC_FOLDER + '/' + 'pallet_logo_large.png')

    # render the html string, oh its big
    pod_html = render_template('pod.html',
                               logo_file_path=pallet_logo_file.name,
                               ref_numbers=ref_numbers,
                               pod_number=pod_number,
                               commodity=commodity,
                               num_pallets=num_pallets,
                               num_pieces=num_pieces,
                               weight=weight,
                               shipper_phone=shipment.shipper.phone,
                               shipper_address_dict=shipper_address_dict,
                               shipper_company=shipper_company,
                               pickup_address_dict=pickup_address_dict,
                               pickup_company=pickup_name,
                               pickup_phone=pickup_phone,
                               dropoff_address_dict=dropoff_address_dict,
                               dropoff_company=dropoff_name,
                               dropoff_phone=dropoff_phone,
                               signee_name=signee_name,
                               signature_path=local_sign_file.name,
                               date=(datetime.utcnow()).strftime("%B %d, %Y"))

    # create the output file
    output = create_temp_file('pod.pdf')
    output.close()

    # Fits on a 8-11 sheet of paper
    pdf_options = {
        'page-size': 'Letter',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8"
    }

    worked = pdfkit.from_string(pod_html, output.name, options=pdf_options)

    # Now upload the file
    # Todo: This should never fail, but in the unexpected case that it does, what do we do? Save the signature somewhere?
    pod_file_to_upload = FileStorage(open(output.name))
    # Wrap it up into a FileStorage object
    pod_filename = upload_internally('proof_of_delivery', pod_file_to_upload, is_local=True)
    # Now delete all the local files
    # The output file is removed with the upload internally function
    os.remove(local_sign_file.name)

    return pod_filename


from APP import TEMP_MEDIA_FOLDER
def create_temp_file(name, dest=TEMP_MEDIA_FOLDER, mode='w'):
    """

    :param name: file name + ext
    :param dest: destination folder, defaults to the Temp media folder
    :param mode: the mode to open the file with
    :return: A file object, IOTextWrapper
    """
    now = str(datetime.now())  # get milliseconds to append on the file name to avoid duplicates
    now = now.rsplit('.')[1]
    temp_filename = now + name
    return open(dest + '/' + temp_filename, mode=mode)

# should be used whenever successfully returning a request
# IF NOT: must make sure to check the new_auth_token_field
def make_gen_success(new_token=None):
    """

    :param new_token:
    :return:
    """
    return make_response(jsonify(message="Great Success", new_token=new_token), 200)


def make_custom_response(message, code):
    """

    :param message:
    :param code:
    :return:
    """
    return make_response(jsonify(message=message), code)


def miles_to_meters(miles):
    """

    :param miles:
    :type miles: number
    :return:
    """
    return miles * 1609.34


def remove_special_chars(string):
    """

    :param string:
    :return:
    """
    special_chars = ['!', '#', '$', '%', '&', '*', '+', '-', '/', '=', '?', '^',
                         '_', '`', '{', '|', '}', '~', '.', '@', 'á', 'é', 'í', 'ó', 'ú',
                         'ü', 'ñ', '<', ' ', '>']
    for char in special_chars:
        string = string.replace(char, "")

    return string


# Accounts for a few common date formats, should add more
# Returns none if no date format is found
# Could create our own exception to alert if the format is super weird
def format_string_to_date(datestring):
    """

    :param datestring:
    :return: if successful: datetime , otherwise: None
    """
    formats = [
        '%m/%d/%Y-%H:%M:%S',
        '%m/%d/%Y',
        '%Y-%m-%d-%H:%M:%S',
        '%Y-%m-%d',
    ]

    date = None
    for form in formats:
        try:
            date = datetime.strptime(datestring, form)
            break
        except ValueError:
            pass

    return date


def make_simple_random_string(num_chars):
    """

    :param num_chars:
    :return:
    """
    import random
    return ''.join(random.choice('0123456789qwertyuioplkjhgfdsazxcvbnm') for i in range(num_chars))


from APP import SHIPMENT_HOURS_OFFER
def estimate_time_taken_to_find_driver(shipment):
    """
        If we later want to go and put in a more complicated,
        how much time we will need to offer the shipment
        Depends on the context, like how many drivers are in the area, their response rates, etc.

    :param shipment:
    :return: timedelta , representing an estimate of how many hours we need to find a driver
    """
    return SHIPMENT_HOURS_OFFER


# SECTION
# Helper Classes
class AlreadyAcceptedException(Exception):
    """
        Extends the Exception class to raise a custom Exception if a shipper tries to cancel a shipment that has
        already been accetpted
    """
    status_code = 600

    def __init__(self, message):
        Exception.__init__(self)
        if message is not None:
            self.message = message

    def to_dict(self):
        to_return = dict(())
        to_return['message'] = self.message
        to_return['code'] = self.status_code
        return to_return


# FROM https://gist.github.com/abhinav-upadhyay/5300137 THANK YOU
class DateTimeEncoder(JSONEncoder):
    """ Instead of letting the default encoder convert datetime to string,
        convert datetime objects into a dict, which can be decoded by the
        DateTimeDecoder
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return {
                '__type__': 'datetime',
                'year': obj.year,
                'month': obj.month,
                'day': obj.day,
                'hour': obj.hour,
                'minute': obj.minute,
                'second': obj.second,
                'microsecond': obj.microsecond,
            }
        else:
            return JSONEncoder.default(self, obj)


# Updated from original gist.
# Added a failure return if the conversion was unsuccessful
class DateTimeDecoder(JSONDecoder):

    def __init__(self, *args, **kargs):
        JSONDecoder.__init__(self, object_hook=self.dict_to_object,
                             *args, **kargs)

    def dict_to_object(self, data):
        decode_failed = "failure"
        if '__type__' not in data:
            return decode_failed

        if isinstance(data, dict):
            type = data.pop('__type__', None)
            try:
                dateobj = datetime(**data)
                return dateobj
            except:
                data['__type__'] = type
                return decode_failed

        return decode_failed