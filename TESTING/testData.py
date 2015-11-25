__author__ = 'austin'

from datetime import datetime
import json
import random
from APP.utility import DateTimeEncoder

testPrice = json.dumps(
    {
        'start_addr': 'Jersey City, NJ',
        'end_addr': 'Washingtong, DC'
    }
)

newInterestData = json.dumps(
    {
        'name': 'name',
        'email': 'email@example.com',
        'account_type': 'driver',
        'interest_type': 'Test',
        'comment': 'pizza pizza'
    }
)

newShipperData = json.dumps(
    {
        'service': 'web',
        'first_name': 'John',
        'last_name': 'biggington',
        'email': 'austin.cawley@gmail.com',
        'password': 'austinrules',
        'phone': 8023569513,
        'billing_address': '1 Caster Lane',
        'billing_city': 'New Camden',
        'billing_state': 'Old Bright',
        'billing_country': 'The US of O',
        'billing_zip': '07059',
        'company': 'Jerry\'s Trucks',
        'location': (30.0, 45.6)
    }
)

newDriverData = {
        'type': 'driver',
        'service': 'web',
        'first_name': 'Mecca',
        'last_name': 'Tester',
        'email': 'mecca14@test.com',
        'password': 'mecca',
        'phone': 8023569513,
        'ext': 4,
        'billing_address': '560 Marin Boulevard',
        'billing_city': 'Jersey City',
        'billing_state': 'NJ',
        'billing_country': 'USA',
        'billing_zip': '07059',
        'current_street_address': '560 Marin Boulevard',
        'current_city': 'Jersey City',
        'current_state': 'NJ',
        'current_country': 'USA',
        'current_zip': '07059',
        'company': 'Mecca',
        'location': (30.0, 40.0),
        'license_number': '909',
        'license_name': 'trizout',
        'dob': '05/21/1995',
        'ssn': '734332960',
        'dot_number': '3453d',
        'mc_number': '3453dDS',
        'trailer_vin': 'XXXX',
        'trailer_plate': 'XXXX',
        'trailer_year': '1999',
        'trailer_size': '53ft',
        'trailer_model': 'Ford Focus',
        'trailer_model_type': 'Refer',
        'truck_vin': 'XXXX',
        'truck_plate': 'XXXX',
        'truck_year': '1949',
        'truck_model': 'Ford Entourage',
        'referral': ''
    }


newWarehouseData = json.dumps(
    {
        'manager_id': '5576ed6be6fc8c0bbd318dc8',
        'user_id': '5576ed6be6fc8c0bbd318dc8',
        'name': 'Killah Warehaus 3',
        'service': 'web',
        'location': (30.0, 45.6),
        'address': '1 Caster Lane',
        'city': 'New Camden',
        'state': 'Old Bright',
        'country': 'The US of O',
        'zip': '07059',
        'email': 'cheezwhiz@hotcracker.com'
    }
)

newStartWarehouseManagerData = json.dumps(
    {
        'service': 'web',
        'first_name': 'Timma',
        'last_name': 'biggington',
        'email': 'austin.cawley@gmail.com',
        'phone': 8023569513,
        'billing_address': '1 Caster Lane',
        'billing_city': 'New Camden',
        'billing_state': 'Old Bright',
        'billing_country': 'The US of O',
        'billing_zip': '07059',
        'company': 'Jerry\'s Trucks',
        'location': (30.0, 40.0),
        'name': 'Start Warehouse',
        'pickup_instructions': 'PickUP',
        'dropoff_instructions': 'DropOFF'
    }
)

newEndWarehouseManagerData = json.dumps(
    {
        'service': 'web',
        'first_name': 'Jimbob',
        'last_name': 'biggington',
        'email': 'jimmyboy@jimbo.com',
        'password': 'password',
        'phone': 8023569513,
        'billing_address': '1 Caster Lane',
        'billing_city': 'New Camden',
        'billing_state': 'Old Bright',
        'billing_country': 'The US of O',
        'billing_zip': '07059',
        'company': 'Jerry\'s Trucks',
        'location': (30.0, 40.0),
        'name': 'End Warehouse',
        'pickup_instructions': 'PickUP',
        'dropoff_instructions': 'DropOFF'
    }
)


newShipmentData = json.dumps(
    {
        'service': 'web',
        'shipper_id': '557f4b7de6fc8c4cd4e6614c',
        'price': 100.0,
        'name': str(random),
        'commodity': 'Texaco Stamps',
        'ship_class': 12,
        'weight': 400.0,
        'size': 'LTL',
        'start_name': 'Start Warehouse',
        'start_address': 'Start Addr',
        'start_city': 'East BumbleButt',
        'start_state': 'SoKrill',
        'start_country': 'supaKrill',
        'start_zip': '89403',
        'start_location': (30.0, 40.0),
        'start_email': 'thisismyemail@aim.com',
        'start_pickup_instructions': 'Just get the fucker',
        'end_name': 'end Warehouse',
        'end_address': 'end Addr',
        'end_city': 'East BumbleButt',
        'end_state': 'SoKrill',
        'end_country': 'supaKrill',
        'end_zip': '89403',
        'end_location': (30.0, 40.0),
        'end_email': 'thisismyemail2@aim.com',
        'company_ref': '909',
        'needs_jack': True,
        'pickup_time':  DateTimeEncoder().encode(datetime.now()),
        'dropoff_time': DateTimeEncoder().encode(datetime.now())
    }
)

acceptShipmentRequest = json.dumps(
    {
        'shipment_id': '55808921e6fc8c4b4f2934ad',
        'driver_id': '557f4b7de6fc8c4cd4e6614c',
        'response': True
    }
)

declineShipmentRequest = json.dumps(
    {
        'shipment_id': '55734a84e6fc8c28d96afaab',
        'driver_id': '55736a30e6fc8c3857ec10ab',
        'is_accepted': False
    }
)

deleteRequest = json.dumps(
    {
        'user_id': '5578539de6fc8c1c2f85ccf4',
        'reason': 'he was a douche',
        'service': 'web'
    }
)

newTruckData = json.dumps(
    {
        'driver_id': '557f0a07e6fc8c1bb5c4bb16',
        'registration': '9483',
        'vin': '431',
        'plate': 'EFO 803',
        'year': 2019,
        'model': 'MeccaBros'
    }
)

newTrailerData = json.dumps(
    {
        'driver_id': '55784ef6e6fc8c18d327b196',
        'registration': '9483',
        'vin': '431',
        'plate': 'EFO 8303',
        'year': 2019,
        'model': 'MeccaBros',
        'model_type': 'Flatbed',
        'size': '40'
    }
)

ratingData = json.dumps(
    {

    }
)

acceptApplicationData = json.dumps(
    {
        'email': 'teampallet@gmail.com',
        'token': '.eJyLVipJTcwtSMzJSS1xSM9NzMzRS87PVdJRMjIwNNU1MNM1Mg4xNLMysrAyMNMzNjMyNDPBkDQxhkoaGZkrxQIAuogUWg.CGsalg.e5ihEn7T75mWSnlYNGaClmhPIw0',
        'is_accepted': True
    }
)

getDriversData = json.dumps(
    {
        'rng': 5,
        'location': (30, 40)
    }
)

loginDataServe = json.dumps(
    {
        'email': 'teampallet@gmail.com',
        'password': 'password'
    }
)

loginDataLocal = json.dumps(
    {
        'email': 'austin.cawley@gmail.com',
        'password': 'password'
    }
)

newAdminData = json.dumps(
    {
        'type': 'admin',
        'address': '500 Hudson Street',
        'state': 'NJ',
        'city': 'Hoboken',
        'country': 'USA',
        'zip': '07030',
        'first_name': 'Fran',
        'last_name': 'Fran',
        'email': 'fran@truckpallet.com',
        'password': 'pork&11eelT',
        'service': 'web',
        'dob': '02/27/1996',
        'phone': '9144797368',
        'ext': '',
        'company': 'Pallet Technologies, Inc.',
        'location': [40.7309441, -74.0392467]
    }
)

testAuth = json.dumps(
    {
        'email': 'austin.cawley@gmail.com',
        'token': '.eJyLVkosLS7JzNNLTizPSa10SM9NzMzRS87PVdJRMjIwNNU1MNM1MgoxMLYyNbAyMNUzsDQxMDBAkzSxMjK1MjLRMzS3NDE2VIoFABUuFWM.CGkcMw.wSuF6z2ZDHO4CM6qxs1EfV3aK5Y'
    }
)

getMineData = json.dumps(
    {
        'email': 'austin.cawley@gmail.com'
    }
)

testReset = json.dumps(
    {
        'email': 'austin.cawley@gmail.com',
        'reset_hash': '$2a$12$avsyW.DwddGr7huiFe2AD.wwv9gR81Lxpk0LwbquxwaPMBV24b7zO',
        'new_password': 'pl31800Cagire'
    }
)

testDownloaded = json.dumps(
    {
        'email': 'austin.cawley@gmail.com',
        'phone': '8023569513'
    }
)

testAdminEmail = {
        'user_base': 'downloaded_users',
        'options': [],
        'message_header': 'Thanks for downloading Pallet',
        'message_body': ' We are greatly sorry for the broken link in our last email. Please use this instead.'
                        ' Sorry for the inconvenience.',
        'message_link_text': 'Click here to apply!',
        'message_link_url': 'https://truckpallet.com/register/driver'
    }


adminLoginData = json.dumps(
    {
        'email': 'austin.cawley@gmail.com',
        'password': 'pl31800Cagire'
    }
)

adminPasswordData = json.dumps(
    {
        'admin_password': 'pork&11eelT6'
    }
)


