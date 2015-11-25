__author__ = 'austin'

import unittest
from pprint import pprint
from datetime import datetime

from TESTING.unittests.testApp import create_app, db

# FUNCTIONS TO TEST
from TESTING.unittests.testApp import app, bcrypt
from flask import request, abort, url_for
from flask_testing import LiveServerTestCase
from flask_mongoengine import DoesNotExist, ValidationError
from mongoengine import NotUniqueError
from pygeocoder import Geocoder, GeocoderError
import json
import requests


class DriverInfo(db.EmbeddedDocument):
    # ADMIN
    # Add driver id to a collection of active drivers when True
    is_active = db.BooleanField(required=False, default=False)
    orientation = db.FloatField(required=False, default=0.0)
    velocity = db.FloatField(required=False, default=0.0)

    payment_confirmed = db.BooleanField(required=False, default=False)
    # USER ACCESSIBLE

    road_name = db.StringField(required=False, max_length=80, default="")

    license_number = db.StringField(required=False, max_length=255)
    license_name = db.StringField(required=False, max_length=255)

    dot_number = db.StringField(required=False)
    hut_number = db.StringField(required=False)
    mc_number = db.StringField(required=False)

    # All Documents Pictured and stored in separate collection
    insurance_form_path = db.StringField(required=False, default='')
    license_form_path = db.StringField(required=False, default='')

    # For storing transactions accrued while payment not confirmed
    unpaid_transactions = db.DecimalField(required=False, default=0.00, precision=3)

    # Just some quick stats
    drivers_signed_up = db.IntField(required=False, default=0)
    total_profit = db.FloatField()
    total_moves = db.IntField()


class Address(db.EmbeddedDocument):
    address = db.StringField(required=True, max_length=255)
    city = db.StringField(required=True, max_length=255)
    state = db.StringField(required=True, max_length=255)
    country = db.StringField(required=True, max_length=255)
    zip = db.StringField(required=True)


class User(db.DynamicDocument):
    """
        Dynamic in case we need to add fields as we go,
        like driver info ?
    """
    meta = {'allow_inheritance': True,
            'abstract': True,
            'indexes':
                # Since it's tough to switch and query collections,
                # we will just index the categories. For now
                [
                    'email',
                    'referral_key',
                    'is_full_account'
                ]
            }

    # ONLY FIELDS FOR ADMINS TO SEE
    is_full_account = db.BooleanField(default=False)
    last_login = db.DateTimeField(default=datetime.utcnow())
    last_request = db.DateTimeField(default=datetime.utcnow())
    date_registered = db.DateTimeField(default=datetime.utcnow())
    registered_by = db.StringField(required=True, max_length=255)
    approved_by = db.ReferenceField('User', required=False)

    location = db.PointField(required=False)

    # AUTHENTICATION
    email = db.EmailField(required=True, unique=True)
    password = db.StringField(max_length=255, required=True)
    auth_token = db.StringField(max_length=255, default="")
    roles = db.ListField(db.StringField(max_length=255), default=[])

    # For PUSH NOTIFICATIONS
    # Only for use in active users actually
    # Will be stored locally on the Android device and registered as a broadcast channel
    notification_key = db.StringField(required=False, max_length=80)

    # BRAINTREE
    # Could also be used as their personal referral code number
    customer_id = db.StringField(max_length=20)

    # USER ACCESSIBLE
    first_name = db.StringField(required=False, max_length=80)
    road_name = db.StringField(required=False, max_length=80)
    last_name = db.StringField(required=False, max_length=80)
    dob = db.DateTimeField(required=False)
    phone = db.StringField(required=False)
    ext = db.StringField(required=False, default="")
    billing_info = db.EmbeddedDocumentField(Address, required=False)
    company = db.StringField(required=False, max_length=255)
    profile_picture_path = db.StringField(required=False, default="")

    # Referrals
    referral_code = db.StringField(required=False, max_length=8)
    referral_user = db.ReferenceField('User', required=False)
    num_referred = db.IntField(required=False, default=0)

    # For linking multiple account types
    # Can check for existence
    driver_info = db.EmbeddedDocumentField(DriverInfo, required=False, default=None)

    fields_for_approval = db.DictField()

    # So we can tell if the user is deleted
    # todo: support logging in after deletion as a read-only SUCKA
    def is_active(self):
        if isinstance(self, ActiveUser):
            return True
        return False

    def is_user_full_account(self):
        return self.is_full_account

    def basic_init(self):
        field_keys = []

        if 'admin' in self.roles:
            field_keys += ['admin']

        if 'shipper' in self.roles:
            field_keys += ['background_check']

        if 'warehouse' in self.roles:
            field_keys += ['background_check']

        if 'driver' in self.roles:
            field_keys += ['license', 'insurance', 'mc_number', 'dot_number']

        #  Will in the future add in keys if they are applying as a warehouse!

        fields = {}
        for key in field_keys:
            fields[key] = "pending_upload"
        self.update(fields_for_approval=fields)
        self.save()

    def has_all_fields(self):
        '''
            Just returns if the user has all the mandatory fields needed for a full account
            :return:
        '''
        has_all = True
        for field in self.fields_for_approval:
            if self.fields_for_approval[field] != 'approved':
                has_all = False
                break
        return has_all


class ActiveUser(User):
    meta = {'collection': 'users_active',
            'indexes':
                # Since it's tough to switch and query collections,
                # we will just index the categories. For now
                [
                    'notification_key'
                ]
            }


@app.route('/test')
def test():
    return json.dumps({"code":"success"})

@app.route('/user/me/<string:email>')
def get_me(email):
    user = ActiveUser.objects.get(email=email)
    return json.dumps(user.to_json())


@app.route('/apply/user', methods=['POST'])
def apply():
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
            print("Duplicates")
            abort(400)

        pass_hash = bcrypt.generate_password_hash(data['password'])

        referral_code_hash = ''
        while referral_code_hash == '' or len(ActiveUser.objects(referral_code=referral_code_hash)) != 0:
            referral_code_hash = "123456"

        # We really only want their email and password so they can have a temporary login
        # Can only be registered by the web right now

        # Must assign roles!
        roles = [data['type']]

        if data['type'] == 'driver':
            referral_user = None
            try:
                referral_user = ActiveUser.objects.get(referral_code=data['referral_code'])
                referral_user.update(inc__num_referred=1)
            except (DoesNotExist, KeyError):
                # Todo: just pass for now
                # might do something cool l8r
                pass

            driver_info = DriverInfo()
            new_user = ActiveUser(
                email=data['email'],
                password=pass_hash,
                registered_by='web',
                driver_info=driver_info,
                referral_user=referral_user,
                roles=roles
            ).save()
        elif data['type'] == 'shipper' or data['type'] == 'warehouse':
            # May differentiate shipper/warehouse later on but for now
            # They have the same information
            # Takes all information necessary from application

            # Gather billing information
            billing_info = Address(
                address=data['address'].capitalize(),
                state=data['state'].upper(),
                city=data['city'].capitalize(),
                country=data['country'].upper(),
                zip=data['zip']
            )

            location = (Geocoder.geocode(billing_info.address + "," + billing_info.city + "," + billing_info.state))[0].coordinates

            new_user = ActiveUser(
                email=data['email'],
                password=pass_hash,
                registered_by='web',
                billing_info=billing_info,
                location=location,
                roles=roles
            ).save()
        elif data['type'] == 'admin':
            new_user = ActiveUser(
                email=data['email'],
                password=pass_hash,
                registered_by='web',
                roles=roles
            ).save()
        else:
            abort(400)

        # This will set the basic fields for approval
        new_user.basic_init()

    except ValidationError as ex:
        print(ex)
        abort(400)
    except KeyError as ex:
        print(ex)
        abort(400)
    except NotUniqueError as ex:
        print(ex)
        abort(400)
    except GeocoderError as ex:
        print(ex)
        abort(400)

    return json.dumps({'code': 'success'})


@app.route('/user/apply/decision/<string:app_id>', methods=['POST', 'PUT'])
def application_decision(app_id):
    """
        For each individual piece of a users application, at least for drivers,
        we need to individually approve their information

        New process:
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

    data = json.loads(request.data.decode('utf-8'))

    # Load the admin user so we can reference

    # Find in database
    try:
        user = ActiveUser.objects.get(id__exact=app_id)
    except DoesNotExist as ex:
        print(ex)
        abort(400)

    try:
        # For admins
        # If the user is an admin, the approving admin must send along a secret password
        # to verify that they truly has
        if 'admin' in user.roles:
            # Check the password
            if not data['admin_password'] == "secret_pass":
                print("Admin password no match")
                abort(403)

        user.update(fields_for_approval=data['fields_for_approval'])
        user.reload()
    except KeyError as ex:
        print(ex)
        abort(400)

    # Check if user has completed all the fields and if they have, give em a full account!
    if user.has_all_fields():
        user.update(is_full_account=True)
        #  Give them a notification key now that we know their cool
        notif_key_hash = 'notif_key'
        # Pop off all special character that could be in an email address
        email_without_special_chars = 'testemail'

        notif_key_hash += email_without_special_chars

        user.update(notification_key=notif_key_hash,
                    customer_id="customer_id")

    else:
        # Todo!
        pass

    return json.dumps({'code': 'success'})


class ApplicationTest(LiveServerTestCase):
    def create_app(self):
        app = create_app()
        app.config['LIVESERVER_PORT'] = 8943

        return app

    def testApplyDriver(self):
        print("Apply Driver Test")
        server = self.get_server_url()
        driver_app_data = {
            'email': 'test@test.com',
            'password': 'test',
            'type': 'driver'
        }
        # Now try to test the application!
        app_request = requests.post(server + '/apply/user', data=json.dumps(driver_app_data))
        assert app_request.ok
        repeat_request = requests.post(server + '/apply/user', data=json.dumps(driver_app_data))
        self.assertFalse(repeat_request.ok)

    def testApplyShipper(self):
        print("Apply Shipper Test")
        server = self.get_server_url()
        shipper_app_data = {
            'email': 'test@test.com',
            'password': 'test',
            'type': 'shipper',
            'address': '1 Castle Point Terrace',
            'state': 'NJ',
            'city': 'hoboken',
            'country': 'usa',
            'zip': '07030'
        }
        # Now try to test the application!
        app_request = requests.post(server + '/apply/user', data=json.dumps(shipper_app_data))
        assert app_request.ok
        repeat_request = requests.post(server + '/apply/user', data=json.dumps(shipper_app_data))
        self.assertFalse(repeat_request.ok)

    def testAcceptShipper(self):
        print("Accept shipper test")
        server = self.get_server_url()
        self.testApplyDriver()

        user_request = requests.get(server + '/user/me/test@test.com')
        assert user_request.ok

        user = json.loads(user_request.json())
        id = user['_id']['$oid']

        # Now make sure its defaulted correctly
        self.assertFalse(user['is_full_account'])

        # Now try to reject them!
        updated_fields = user['fields_for_approval']
        for key in updated_fields:
            updated_fields[key] = 'Rejected because you suck at being accepted.'
        accept_request = requests.put(server + '/user/apply/decision/' + id, data=json.dumps(
            {
                'fields_for_approval': updated_fields
            }
        ))
        assert accept_request.ok

        # Now try to accept them!
        user_request = requests.get(server + '/user/me/test@test.com')
        user = json.loads(user_request.json())

        self.assertFalse(user['is_full_account'])

        updated_fields = user['fields_for_approval']
        for key in updated_fields:
            updated_fields[key] = 'approved'
        accept_request = requests.put(server + '/user/apply/decision/' + id, data=json.dumps(
            {
                'fields_for_approval': updated_fields
            }
        ))
        assert accept_request.ok

        # Reload and check again
        user_request = requests.get(server + '/user/me/test@test.com')
        user = json.loads(user_request.json())

        assert user['is_full_account']


    def doCleanups(self):
        try:
            (ActiveUser.objects.get(email="test@test.com")).delete()
        except Exception:
            pass
        return super().doCleanups()

    def tearDown(self):
        print("Closing test!")


if __name__ == '__main__':
    unittest.main()
