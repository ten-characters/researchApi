import unittest

from TESTING.unittests.testApp import create_app, app

from APP import S3_MEDIA_BUCKET
from APP.models import ActiveUser, UserApplication
from APP.api.upload import hash_file_name_dep
from APP.utility import DateTimeDecoder

from mongoengine.errors import NotUniqueError

from flask import request
from flask_testing import LiveServerTestCase
import json
import requests

from werkzeug.datastructures import FileStorage

import boto3
from botocore.exceptions import ClientError
from boto3.s3.transfer import S3Transfer

import os
from PIL import Image

TEMP_MEDIA_FOLDER = os.path.dirname(os.path.realpath(__file__)) + '/temp'


def download(filepath):
    """
        Downloads from amazon s3 and then send back FileStorage
    :param filepath:
    :return:
    """
    s3_client = boto3.client('s3')
    transfer_client = S3Transfer(s3_client)
    transfer_client.download_file(S3_MEDIA_BUCKET, filepath, 'temp/tempdownload.jpg')
    return FileStorage(open('temp/tempdownload.jpg'))


def upload_thumbnails(doctype, filepath):
    """
        Will be given a filepath for its place in the s3 bucket
        First stores the file locally
        Then creates thumbnail
        Then upload it
        Then returns the new thumbnail filepath
    :param filepath:
    :return:
    """
#     First get the file from s3 bucket
    s3_client = boto3.client('s3')
    transfer_client = S3Transfer(s3_client)

    try:
        transfer_client.download_file(S3_MEDIA_BUCKET, filepath, 'temp/tempdownload.jpg')
    except ClientError:
        return None

    thumb_name = hash_file_name_dep("thumbnail", "tempdownload.jpg")

#     Then create the thumbnail
    thumb_image = Image.open('temp/tempdownload.jpg')
    os.remove('temp/tempdownload.jpg')

    thumb_image.thumbnail((120, 120))
    # Save the thumbnail in the temp upload directory
    thumb_image.save('temp/' + thumb_name, "JPEG")

    # Upload
    transfer_client.upload_file("temp/" + thumb_name, S3_MEDIA_BUCKET, thumb_name)

    # Now delete the file
    os.remove("temp/" + thumb_name)
    return thumb_name


@app.route("/shutdown", methods=['POST'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return json.dumps("we good")


class DbMigrationTest(LiveServerTestCase):
    def create_app(self):
        app = create_app()
        app.config['LIVESERVER_PORT'] = 8943
        return app

    def testUpdateSchemas(self):
        """
            This will update the schema from v1.0 to v1.1
            Mostly just marks things as changed, and create thumbnails
            for the images that need them
        :return:
        """
        # update both the ActiveUsers and the UserApplications
        users = list(ActiveUser.objects) + list(UserApplication.objects)
        for user in users:
            # Mark as changed
            user._mark_as_changed('location')
            user._mark_as_changed('first_name')
            user._mark_as_changed('last_name')
            user._mark_as_changed('phone')
            user._mark_as_changed('company')
            user._mark_as_changed('billing_info')

            if user.profile_picture_path != '':
                user.profile_picture_thumb_path = upload_thumbnails('profile_picture', user.profile_picture_path)

            if user.driver_info is not None:
                user.driver_info._mark_as_changed('license_number')
                user.driver_info._mark_as_changed('license_name')
                user.driver_info._mark_as_changed('dob')
                user.driver_info._mark_as_changed('ssn')
                user.driver_info._mark_as_changed('dot')
                user.driver_info._mark_as_changed('mc_number')
                user.driver_info._mark_as_changed('ifta_form_path')
                user.driver_info._mark_as_changed('irp_form_path')

                # Update their trucks and other photos that need a thumbnail
                for truck in user.driver_info.trucks:
                    if truck.photo_path is not None and truck.photo_thumb_path is None:
                        user.update(pull__driver_info__trucks=truck)
                        truck.photo_thumb_path = upload_thumbnails('truck', truck.photo_path)
                        user.update(push__driver_info__trucks=truck)

                for trailer in user.driver_info.trailers:
                    if trailer.photo_path is not None and trailer.photo_thumb_path is None:
                        user.update(pull__driver_info__trailers=trailer)
                        trailer.photo_thumb_path = upload_thumbnails('trailer', trailer.photo_path)
                        user.update(push__driver_info__trailers=trailer)
                
            # Accounts if people have weird dob info
            if isinstance(user.dob, dict):
                decoder = DateTimeDecoder()
                user.dob = decoder.dict_to_object(json.dumps(user.dob))

            if isinstance(user.dob, str):
                import ast
                decoder = DateTimeDecoder()
                user.dob = decoder.dict_to_object(ast.literal_eval(user.dob))

            user.save()

    def testConvertToActiveUser(self):
        """
            Once we have updated the schemas we will want to
            transfer everyone out of the UserApplication to a real user
        :return:
        """
        for application in UserApplication.objects:
            converted = application.to_active_user()

            try:
                converted.save()
                # Save it and then move on

                # Now we have to mark all their fields for approval
                converted.basic_init()
                converted.reload()
                self.assertFalse(converted.is_full_account)

                #
                for key in converted.fields_for_approval:
                    converted.fields_for_approval[key] = "pending_approval"

                converted.save()
                # Once everything is saved, delete the applications
                # So scary !
                application.delete()
                application.switch_collection('archived_applications')
                application.save()
            except NotUniqueError:
                # Only add those who have not already been converted
                pass

        assert len(UserApplication.objects) == 0

    def doCleanups(self):
        try:
            requests.post(self.get_server_url() + '/shutdown')
        except Exception:
            pass
        return super().doCleanups()

    def tearDown(self):
        print("Closing test!")


if __name__ == '__main__':
    unittest.main()
