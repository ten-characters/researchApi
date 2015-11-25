"""
    Deals with all of our files
"""
__author__ = 'austin'

from APP import app, TEMP_MEDIA_FOLDER, base_api_v1_ext, base_api_v1_1_ext, S3_MEDIA_BUCKET
from APP.models import Shipment, ActiveUser
from APP.utility import throw_error, check_authentication, log
from APP.decorators import deprecated

from flask import request, send_from_directory, abort, jsonify, make_response
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from mongoengine import DoesNotExist
import json
from datetime import datetime
import os
import zipfile
import hashlib

import boto3
from botocore.exceptions import ClientError
from boto3.s3.transfer import S3Transfer

from PIL import Image

FILE_TAG = __name__

ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'])

USER_FILES = set(['profile_picture'])
# Need to weed out where we put drivers_license --> so silly, so problem causing, so non  explicit
DRIVER_FILES = set(['insurance', 'drivers_license', 'license', 'truck', 'trailer'])
USER_FILES = set(['profile_picture'])
SHIPMENT_FILES = set(['delivery_order', 'bill_lading', 'proof_of_delivery', 'signature'])

THUMB_SIZE = 120, 120


def allowed_file(doc_type, filename):
    """
        Allowed file
        This is not an end point it is simply a function that makes sure the file extention is a type we can handle

        :param doc_type:
        :param filename:
        :return:
    """
    good_extension = '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

    # Must be any of these three types
    is_user_file = doc_type in USER_FILES
    is_driver_file = doc_type in DRIVER_FILES
    is_shipment_file = doc_type in SHIPMENT_FILES
    return good_extension and (is_user_file or is_driver_file or is_shipment_file)


@deprecated('1.1')
@app.route(base_api_v1_ext + '/upload/<string:doc_type>', methods=['POST'])
def upload_document_dep(doc_type):
    """ Upload document
        REQUEST FORMAT:
            /upload/document type
            the request must be a multipart/form and contain a "file" in the files part of the request
            it will return success or fail
        requires:
            document type:(one of)
                w9
                insurance
                valid_authority
                ifta
                irp
                drivers_licence
                delivery_order
                bill_lading
                proof_of_delivery
            a document in 'files'
            user credentials :
                email
                token

        :param doc_type:
        :return:
    """
    file = request.files['file']
    # A hackaround method to get form data from Android and still support
    # Requests from python request lib used in web app
    try:
        data = json.loads(request.form['data'])
        print("From loads!")
        # todo: why are there two Trues?
        form_data = True
    except KeyError:
        data = {'email': request.form['email'], 'token': request.form['token'], 'shipment_id': request.form['shipment_id']}
        form_data = True
    except KeyError:
        throw_error('Key Error!', 400, request, FILE_TAG)

    print("File:")
    print(file)
    if file:
        print("Has file! : " + file.filename)

        if allowed_file(doc_type, file.filename) or is_zip(file.filename):
            print("Allowed file!")
            if form_data:
                auth = check_authentication(form_data=data)
            else:
                auth = check_authentication()

            if not auth[0]:
                abort(403)

            # dealing with compressed zip images from Android devices
            if is_zip(file.filename):
                print("It's a zip file!")
                filename = upload_zip_dep(doc_type, file)
            else:
                # Upload the file and then we'll figure our where it goes
                print("It's a not zip file!")
                filename = upload_internally(doc_type, file)

            print("Doctype: " + doc_type)
            if doc_type in DRIVER_FILES:
                try:
                    user = ActiveUser.objects.get(email=data['email'].lower(), driver_info__exists=True)
                except DoesNotExist:
                    throw_error('Trying to find a user that does not exist: ' + data['email'], 400, request, FILE_TAG)

                # Find the driver's info
                driver_info = user.driver_info
                # Make sure that we delete the old file before re-writing its location
                if doc_type == 'profile_picture':
                    if user.profile_picture_path != "":
                        delete_s3_file(user.profile_picture_path)
                    user.profile_picture_path = filename
                    driver_info.save()
                elif doc_type == 'insurance':
                    if driver_info.insurance_form_path != "":
                        delete_s3_file(driver_info.insurance_form_path)
                    driver_info.insurance_form_path = filename
                    driver_info.save()
                elif doc_type == 'drivers_license':
                    if driver_info.license_form_path != "":
                        delete_s3_file(driver_info.license_form_path)
                    driver_info.license_form_path = filename
                    driver_info.save()

                else:
                    throw_error('Invalid form upload', 400, request, FILE_TAG)
                try:
                    new_token = auth[1]
                except IndexError:
                    new_token = None
                return make_response(jsonify(message="Great Success",
                                             new_token=new_token,
                                             file_path=filename), 200)

            # --- USER FILES --- #
            # These are applicable to all users, doi
            elif doc_type in USER_FILES:
                user = ActiveUser.objects.get(email=data['email'].lower())
                if doc_type == 'profile_picture':
                    if user.profile_picture_path != "":
                        delete_s3_file(user.profile_picture_path)
                    user.profile_picture_path = filename
                    user.save()

                try:
                    new_token = auth[1]
                except IndexError:
                    new_token = None
                return make_response(jsonify(message="Great Success",
                                             new_token=new_token,
                                             file_path=filename), 200)

            elif doc_type in SHIPMENT_FILES:
                try:
                    # Todo: make sure the shipment id is one of the users shipments
                    shipment = Shipment.objects.get(id__exact=data['shipment_id'])
                except DoesNotExist:
                    throw_error('Trying to find a shipment that does not exist: ' + data['shipment_id'],
                                400, request, FILE_TAG)

                if doc_type == 'bill_lading':
                    if shipment.bill_lading_path != "":
                        delete_s3_file(shipment.bill_lading_path)
                    shipment.update(bill_lading_path=filename)
                elif doc_type == 'delivery_order':
                    if shipment.delivery_order_path != "":
                        delete_s3_file(shipment.delivery_order_path)
                    shipment.update(delivery_order_path=filename)
                else:
                    throw_error('invalid form upload', 400, request, FILE_TAG)
                try:
                    new_token = auth[1]
                except IndexError:
                    new_token = None
                return make_response(jsonify(message="Great Success",
                                             new_token=new_token,
                                             file_path=filename), 200)
    return throw_error("No file!", 400, request, FILE_TAG)


# Todo! Could return a tuple of file keys if we want to do a thumbnail and do it all in one swoop
def upload_internally(doc_type, file, want_thumb=False, src_folder=TEMP_MEDIA_FOLDER, is_local=False):
    """
        Transferring over to using amazon s3 buckets!
        Will upload the file straight from here!
        We will keep the same schema, but the filenames now will be keys
        for the s3 bucket

        Boto3 Documentation:
        http://boto3.readthedocs.org/en/latest/reference/customizations/s3.html

    :param doc_type: str, from one of our supported documents above ^
    :param file: file, upload this shit. Can be a zip file if ya want.
    :keyword want_thumb:
    :type want_thumb: bool
    :default want_thumb: False
    :keyword src_folder:
    :type src_folder: str
    :default src_folder: TEMP_MEDIA_FOLDER
    :keyword is_local:
    :type is_local: bool
    :default is_local: False
    :return: string
    """
    files_to_upload = []

    if isinstance(file, str):
        # Support for sending a filename in place of a file
        file = FileStorage(open(src_folder + "/" + file))

    # First check if we need to unzip the file:
    if is_zip(file.filename):

        # Need to deal with deleting this file after use !
        file = FileStorage(unzip_file(file))
        log("Unzipped file: " + file.filename + "!", FILE_TAG)
        # file comes back in a different format than Flask stores it as
    elif not is_local:
        # Always save a copy of the file to the local temp directory
        # Makes it much easier to manipulate and work with as a FileStorage
        filename = file.filename
        new_filename = hash_file_name(filename)
        file.save(src_folder + "/" + new_filename)
        file = FileStorage(open(src_folder + "/" + new_filename))

    files_to_upload.append(file)
    filename = os.path.basename(file.filename)

    if want_thumb:
        files_to_upload.append(create_thumb(file))

    if allowed_file(doc_type, filename):
        # Connect to the s3 bucket
        try:
            # Upload potentially both the full size and the thumbnail
            uploaded_file_names = []
            for file in files_to_upload:
                upload_filename = os.path.basename(file.filename)
                upload_key = hash_file_name(upload_filename)
                s3_client = boto3.client('s3')
                transfer_client = S3Transfer(s3_client)
                # Upload
                transfer_client.upload_file(src_folder + "/" + upload_filename, S3_MEDIA_BUCKET, upload_key)
                # Delete
                delete_local_file(src_folder + "/" + upload_filename)
                uploaded_file_names.append(upload_key)
            # For now return list of names if thumb uploaded, just str if not
            if len(uploaded_file_names) == 1:
                return uploaded_file_names[0]
            else:
                return uploaded_file_names
        except UnicodeDecodeError as ex:
            throw_error("UnicodeDecodeError when uploading file!", 400, request, FILE_TAG, exception=ex)
        except ClientError as ex:
            throw_error("Client error in boto upload!", 500, request, FILE_TAG, exception=ex)

    ex = Exception("Not an allowed filetype!")
    throw_error("Not an allowed filetype!", 400, request, FILE_TAG, exception=ex)


def create_thumb(file, local_src=None, dest_folder=None):
    """
        Given FileStorage object
        In kwargs, given two options.
            Can specify the local path where the file is saved
            Can specify a specific folder to save the image to
    :param file:
    :type file: werkzeug.datastructures.FileStorage
    :param local_src:
    :type local_src: str
    :param dest_folder:
    :type dest_folder: str
    :return FileStorage:
    """
    # Gives the options of creating from a local store
    if local_src is not None:
        file = FileStorage(local_src)

    if dest_folder is None:
        dest_folder = TEMP_MEDIA_FOLDER

    new_thumb_filename = hash_file_name_dep('thumbnail', file.filename)
    thumb_image = Image.open(file.filename)

    thumb_image.thumbnail(THUMB_SIZE)
    # Save the thumbnail in the temp upload directory
    thumb_image.save(dest_folder + '/' + new_thumb_filename, "JPEG")
    return FileStorage(open(dest_folder + '/' + new_thumb_filename))


def unzip_file(file):
    """
        Basically exactly what it says it does
        Unzips the file, stores it temporarily, and then gives it back
    :param file:
    :type file:
    :return IOWrapper:
    """
    zipped_file = zipfile.ZipFile(file)
    if len(zipped_file.namelist()) != 0:
        file_to_unzip_name = zipped_file.namelist()[0]
        filename = hash_file_name(file_to_unzip_name)
        zipped_file.extract(file_to_unzip_name, path=TEMP_MEDIA_FOLDER)
        os.rename(TEMP_MEDIA_FOLDER + "/" + file_to_unzip_name, TEMP_MEDIA_FOLDER + "/" + filename)
        return open(TEMP_MEDIA_FOLDER + "/" + filename)
    else:
        # It's not zipped you dingus!
        return file


@deprecated('1.1')
def upload_zip_dep(doc_type, file):
    """

    :param doc_type:
    :param file:
    :return:
    """
    zipped_file = zipfile.ZipFile(file)
    if len(zipped_file.namelist()) != 0:
        zipped_filename = zipped_file.namelist()[0]
        if allowed_file(doc_type, zipped_filename):
            # basically try to do the same as an upload, storing the filename
            # and rename it in the correct folder
            filename = hash_file_name_dep(doc_type, zipped_filename)
            zipped_file.extract(zipped_filename, path=TEMP_MEDIA_FOLDER)
            os.rename(TEMP_MEDIA_FOLDER + "/" + zipped_filename,
                      TEMP_MEDIA_FOLDER + "/" + filename)

            # Keep this old system of extracting, then upload to s3
            # Buuut then remove the file
            s3_client = boto3.client('s3')
            transfer_client = S3Transfer(s3_client)
            # Upload
            transfer_client.upload_file(TEMP_MEDIA_FOLDER + "/" + filename, S3_MEDIA_BUCKET, filename)
            # Delete
            delete_local_file(TEMP_MEDIA_FOLDER + "/" + filename)
            return filename
        else:
            throw_error("Bad File Name!", 400, request, FILE_TAG)
    else:
        throw_error("No files in zip!", 400, request, FILE_TAG)


def hash_file_name(filename):
    """

    :param filename:
    :return:
    """
    name, ext = os.path.splitext(filename)
    name = secure_filename(hashlib.md5((datetime.utcnow().isoformat()).encode('utf-8')).hexdigest())
    return name + ext


@deprecated("1.1.1", reason="Doc Type is unnecessary")
def hash_file_name_dep(doc_type, filename):
    """

    :param doc_type:
    :param filename:
    :return:
    """
    new_filename = secure_filename(
            hashlib.md5((doc_type + datetime.utcnow().isoformat())
                        .encode('utf-8'))
                        .hexdigest() + "." + filename.rsplit('.', 1)[1])
    return new_filename


def is_zip(filename):
    """
        Just checks if we have a .zip extension on the file.
        Would use the zipfile.is_zipfile() but I am almost positive
        that just checks if it is a zipfile object ( jk it messes with the file )
        which upload files are not
        so mega lame
        :param filename:
        :return:
    """
    try:
        name, ext = os.path.splitext(filename)
        if ext == '.zip':
            return True
    except Exception:
        pass
    return False


def download_s3_to_local(filename, dest=TEMP_MEDIA_FOLDER):
    """

    :param filename:
    :param dest:
    :raises FileNotFoundException:
    :return: Path to the locally stored file
    """
    now = str(datetime.now())  # get milliseconds to append on the file name to avoid duplicates
    now = now.rsplit('.')[1]
    temp_filename = now + filename
    temp_file = open(TEMP_MEDIA_FOLDER + '/' + temp_filename, 'w')
    temp_file.close()

    s3_client = boto3.client('s3')
    transfer_client = S3Transfer(s3_client)
    try:
        transfer_client.download_file(S3_MEDIA_BUCKET, filename, dest + '/' + temp_filename)
    except ClientError:
        raise FileNotFoundError()

    return dest + '/' + temp_filename


# Could make this return a boolean if successful or not?
def delete_s3_file(*args):
    """
    Deletes a file from our s3 bucket
    :param args: list of keys stored in the s3 bucket
    :return: bool, the success of the operation
    """
    try:
        for filename in args:
            s3 = boto3.resource('s3')
            uploaded = s3.Object(S3_MEDIA_BUCKET, filename)
            uploaded.delete()
        return True
    except Exception as ex:
        # Anything that goes wrong, we wanna know
        return False


def delete_local_file(*args, quiet=False):
    """

    :param args: file paths
    :type args: str, list of str
    :raises: FileNotFoundException
    :return:
    """
    for filepath in args:
        try:
            os.remove(filepath)
        except FileNotFoundError as ex:
            if not quiet:
                raise ex
    return True


@app.route(base_api_v1_ext + '/download/<string:filename>')
@app.route(base_api_v1_1_ext + '/file/<string:filename>')
def download_document(filename):
    """ Download document
        REQUEST FORMAT:
        /file/filename
        returns the file with that name
    requires:
        the name of the file in the url

        :param filename:
        :return:
    """
    # We will assume right now that if they have the filename they must have
    # been authenticated to get that information
    # This assumption should change, soon,

    # Could potentially create a script that goes and renames all files and changes
    # Their path in users database
    # Or potentially not. Who knows how anal secretive we'll get

    # auth = check_authentication()
    # if auth[0]:
        # On a user basis, or if they have permission for a shipment
    # return send_from_directory(TEMP_MEDIA_FOLDER, filename)

    now = str(datetime.now())  # get milliseconds to append on the file name to avoid duplicates
    now = now.rsplit('.')[1]
    temp_filename = now + filename
    temp_file = open(TEMP_MEDIA_FOLDER + '/' + temp_filename, 'w')
    temp_file.close()
    found_error = False
    try:
        s3_client = boto3.client('s3')
        transfer_client = S3Transfer(s3_client)
        transfer_client.download_file(S3_MEDIA_BUCKET, filename, TEMP_MEDIA_FOLDER + '/' + temp_filename)
        return send_from_directory(TEMP_MEDIA_FOLDER, temp_filename)
    except ClientError as ex:
        found_error = True
        exception = ex
    finally:
        # Always remove the locally stored file
        delete_local_file(TEMP_MEDIA_FOLDER + '/' + temp_filename)
        if found_error:
            return throw_error("Can't find the file to download!", 404, request, FILE_TAG, exception=exception)


