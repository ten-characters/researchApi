__author__ = 'austin'

from flask import Flask
from flask_mongoengine import MongoEngine
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer

from datetime import timedelta

import braintree

# APP
app = Flask(__name__)

'''
    Things to remember:
    When pushing to MASTER:
        - Make sure the servers are configured correctly below
        - Make sure the scripts are started (transactionFinisher, fuelCrawler, shipmentWatcher)
'''

# Configure

# PRODUCTION
# server = 'https://api.truckpallet.com'
# base_api_ext = ''
# base_web_url = 'https://truckpallet.com'
# DEBUG = False
# S3_MEDIA_BUCKET = 'media.truckpallet.com'
#
# TESTING
server = 'https://test.truckpallet.com'
base_api_ext = '/api'
base_web_url = 'https://test.truckpallet.com'
DEBUG = True
S3_MEDIA_BUCKET = 'media.test.truckpallet.com'

# ROUTER LOCAL
# server = 'http://192.168.1.6'
# base_api_ext = '/api'
# base_web_url = 'http://localhost:8001'
# DEBUG = True
# S3_MEDIA_BUCKET = 'media.test.truckpallet.com'

# LOCAL
# server = 'http://localhost:8000'
# base_api_ext = ''
# base_web_url = 'http://localhost:8001'
# DEBUG = True
# S3_MEDIA_BUCKET = 'media.test.truckpallet.com'


SECRET_KEY = 'asdjfupk'
app.config["DEBUG"] = DEBUG
app.config["SECRET_KEY"] = SECRET_KEY
app.config['DEFAULT_PARSERS'] = [
    'flask.ext.api.parsers.JSONParser',
    'flask.ext.api.parsers.URLEncodedParser',
    'flask.ext.api.parsers.MultiPartParser'
]

app.config["MONGODB_SETTINGS"] = {
    'db': 'Pallet',
    'username': 'API',
    'password': 'pork&11eelT6'
}

app.config['MAIL_SERVER'] = 'mail.truckpallet.com'
app.config['MAIL_PORT'] = 25
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'pallet@truckpallet.com'
app.config['MAIL_PASSWORD'] = 'pork&11eelT'

app.config['ACTIVE_DRIVER_THRESHOLD'] = timedelta(hours=3)

# INITIALIZE THE GOODIES
# MONGO
mongo = MongoEngine(app)

# FOR HASHING / ENCRYPTING
serializer = URLSafeTimedSerializer(app.secret_key)
bcrypt = Bcrypt(app)

# EMAIL for some notifications
mail = Mail(app)


# BRAINTREE
if DEBUG:
    # Sandbox
    merchant_master_id = 'pallettechnologies'
    braintree.Configuration.configure(
        braintree.Environment.Sandbox,
        merchant_id='gvkw62s2533kbsb8',
        public_key='wdv8q6zvkt9m4k85',
        private_key='ef639623cfbd21b1f3782d32d017761e'
    )
    PALLET_PAYMENT_TOKEN = '4knzmr'
else:
    # Production
    merchant_master_id = 'PalletTechnologilses_marketplace'
    braintree.Configuration.configure(
        braintree.Environment.Production,
        merchant_id='yw58frb322bb3rck',
        public_key='f9wxr5rms9zwrbjf',
        private_key='e184672b1c9405dea2c19e3f866890eb'
    )
    PALLET_PAYMENT_TOKEN = '4knzmr'

DAYS_HELD_IN_ESCROW = 3

# ---- GLOBALS ---- #

# PARSE PUSH NOTIFICATIONS
if DEBUG:
    PARSE_MASTER = 'ev3sjvFeMRUxMEBwbJxa4srcAKONY4n9BMlWbYpI'
    PARSE_APP_ID = '6Uggb7M4Mz5Hqk2mXoSEy0CIEZwNBFx3beiA1elb'
    PARSE_REST_KEY = '6LtRGPnNMSJ7AspVDyfCckiF7OrokknhmX8x80W6'
else:
    PARSE_MASTER = 'f3dDAZzLf9DMzrr64jwFYGDXe3M6yQh0HdtezxUL'
    PARSE_APP_ID = 'k9ZfmNoqvfqARweaRKYJJbuPz9rPFM3aSp0o4Iye'
    PARSE_REST_KEY = 'ms5FQ2rRUWx0hOjrJvzj7u7piyhKP5R75NWfp0ir'


PALLET_OFFER_SHIPMENT_KEY = "offer_shipment"
PALLET_PHONE_NUMBER = '201-820-8945'
PALLET_EMAIL = 'Pallet@truckpallet.com'

PALLET_SECRET_ADMIN_PASS = 'pork&11eelT6'

# Shipment offer times
# SHIPMENT_HOURS_AVAILABLE = timedelta(hours=7)
#  hours before the pickup window drivers will be allowed to accept the shipment
SHIPMENT_HOURS_OFFER = timedelta(hours=4)
# hours before the pickup window the shipment will go into active offering
# SHIPMENT_HOURS_BEFORE_ALERTING_CUSTOMER = timedelta(hours=4)
# hours before the pickup window the shipment will go into active offering

# Some constants
TRUCKER_PERCENTAGE = .85
FIRST_MOVE_PROMO = 25

# An easy place to keep our versions
# FOR TESTING on the one server, use the /api path to get to the api, separating it from /web

# VERSION-ING !
base_api_v1_ext = base_api_ext + '/v1.0'
base_api_v1_1_ext = base_api_ext + '/v1.1'

import os

# Make sure that file file uploads area exists!
try:
    os.mkdir(os.path.dirname(os.path.realpath(__file__)) + '/temp')
except FileExistsError:
    pass
root = os.path.dirname(os.path.realpath(__file__))

TEMP_MEDIA_FOLDER = root + '/temp'
STATIC_FOLDER = root + '/static'


# Import all the api files
from APP.api import admin, main, manageAccounts, \
    ratings, registration, shipments, upload, login,\
    braintreeEndpoints, github, drivers, errors, users

# The startup scripts!
from APP import transactionFinisher, shipmentWatcher
from fuelCrawler import averagePriceCrawler


@app.before_first_request
def run_on_start():
    print('Starting Scripts!')
    # Run all the starting scripts before running the app !
    averagePriceCrawler.run_async()
    transactionFinisher.run_async()
    shipmentWatcher.run_async()

# --- For Analytics

from flask import g
from datetime import datetime


@app.before_request
def init_request():
    g.start = datetime.utcnow()


@app.after_request
def track_request(response):
    """
        Takes the response thrown back by Flask
        This is here to add tracking
        Could potentially also add statistics to the the API response content
    :param response:
    :return:
    """


    request_time = datetime.utcnow() - g.start
    return response
