__author__ = 'austin'

import unittest

from TESTING.unittests.testApp import create_app, app

from APP.models import ActiveUser
# FUNCTIONS TO TEST
from APP.api.login import login
from APP.api.manageAccounts import update_user, delete_account
from APP.api.registration import register_truck, register_trailer, apply

from flask import make_response
from flask_testing import LiveServerTestCase
import json
import requests


@app.route('/user/register', methods=['POST'])
def a():
    response = apply()
    if response.status_code != 400 and response.status_code != 500:
        return make_response("Cool", 200)
    else:
        return response


@app.route('/user/update', methods=['PUT', 'POST'])
def update():
    return update_user()


@app.route('/user', methods=['DELETE'])
def delete():
    return delete_account()


@app.route('/login', methods=['PUT', 'POST'])
def log():
    # For some reason this gets called a bizzillion times
    # During that thyme the token changes -> need to look into why
    # The 15 minute timer no work
    resp = login()
    process_response(json.loads(resp.data.decode('utf-8')))
    return resp


def store_login(email, token):
    globals().update(email=email)
    globals().update(token=token)


def append_login(login_dict):
    login_dict['email'] = globals().get('email')
    login_dict['token'] = globals().get('token')


def process_response(response_json):
    if 'new_token' in response_json:
        store_login('test@test.com', response_json['new_token'])
    elif 'token' in response_json:
        store_login('test@test.com', response_json['token'])


class UserUpdateTest(LiveServerTestCase):
    def create_app(self):
        app = create_app()
        app.config['LIVESERVER_PORT'] = 8943
        return app

    def testApplyDriver(self):
        server = self.get_server_url()

        # Made a basic user
        driver_app_data = {
            'email': 'test@test.com',
            'password': 'test',
            'type': 'driver'
        }
        # Now try to test the application!
        app_request = requests.post(server + '/user/register', data=json.dumps(driver_app_data))
        assert app_request.ok

        # Try to get an instance of our new lil guy through mongo
        user = ActiveUser.objects.get(email='test@test.com')

        # Now sign in
        login_data = {
            'email': 'test@test.com',
            'password': 'test'
        }
        login_req = requests.put(server + '/login', data=json.dumps(login_data))
        assert login_req.ok
        # If ok, store login
        process_response(login_req.json())

        # Basic info
        basic_info = {
            'company': "Trucking 101",
            'billing_info': json.dumps({
                'address': '1 Castle Point Terrace',
                'city': 'Hoboken',
                'state': 'NJ',
                'country': 'USA',
                'zip': '07030'
            }),
            'phone': '8023569513'
        }
        append_login(basic_info)
    #     First try to update with a set of basic info
        basic_req = requests.put(server + '/user/update', data=json.dumps(basic_info))
        assert basic_req.ok
        process_response(basic_req.json())

        user.reload()
        self.assertEqual(user.company, basic_info['company'])

    #     OK so our first update has worked
    #     Now check for the more sensative stuff
    #     Do it in separate chunks to simulate a reeeel time scenario
    #     Flatten the dict into its str
        first_half_data = {
            'driver_info': json.dumps({'mc_number': '11029203'})
        }
        first_half_files = {
            'insurance':  open('images/insurance.jpg', 'rb')
        }
        # Make sure it opens correctly
        # im = Image.open(open('images/insurance.jpg', 'rb'))
        # im.show()
        append_login(first_half_data)
        first_half_req = requests.post(server + '/user/update', data=first_half_data, files=first_half_files)
        # post(base_url + "/apply/user", data=driver_data, files=driver_files)
        assert first_half_req.ok
        process_response(first_half_req)

        # Now check everyting is there
        user.reload()
        self.assertEqual(user.driver_info.mc_number, '11029203')

        # For the second part, let's try to send a zip file,
        # Just so we know everything is a-ok on all fronts
        second_half_data = {
            'driver_info': json.dumps({
                'dot_number': '1119203'
            })
        }
        second_half_files = {
            'license':  open('images/richie.jpg.zip', 'rb')
        }

        append_login(second_half_data)
        second_half_req = requests.post(server + '/user/update', data=second_half_data, files=second_half_files)
        assert second_half_req.ok
        process_response(second_half_req)

        user.reload()
        self.assertEqual(user.driver_info.dot_number, '1119203')

    #    And finally, make sure uploading a propic works and saves two images, a thumbnail and a real photo
    #     We will try with both a zip and not with a zip
        propic_data = {}
        append_login(propic_data)
        propic_files = {
            'profile_picture': open('images/richie.jpg.zip', 'rb')
        }
        propic_req = requests.post(server + '/user/update', data=propic_data, files=propic_files)
        assert propic_req.ok
        process_response(propic_req)

        propic_data = {}
        append_login(propic_data)
        propic_files = {
            'profile_picture': open('images/insurance.jpg', 'rb')
        }
        propic_req = requests.post(server + '/user/update', data=propic_data, files=propic_files)
        assert propic_req.ok

        user.delete()

    def doCleanups(self):
        try:
            ActiveUser.objects.get(email="test@test.com").delete()
        except Exception:
            pass
        return super().doCleanups()

    def tearDown(self):
        print("Closing test!")


if __name__ == '__main__':
    unittest.main()
