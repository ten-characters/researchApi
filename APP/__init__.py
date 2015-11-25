__author__ = 'austin'

import braintree
from datetime import timedelta
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_mongoengine import MongoEngine
from itsdangerous import URLSafeTimedSerializer

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
# server = 'https://api.serveraddress.com'
# base_api_ext = ''
# base_web_url = 'https://serveraddress.com'
# DEBUG = False
# S3_MEDIA_BUCKET = 'media.serveraddress.com'
#
# TESTING
server = 'https://test.serveraddress.com'
base_api_ext = '/api'
base_web_url = 'https://test.serveraddress.com'
DEBUG = True
S3_MEDIA_BUCKET = 'media.test.serveraddress.com'

# ROUTER LOCAL
# server = 'http://192.168.1.6'
# base_api_ext = '/api'
# base_web_url = 'http://localhost:8001'
# DEBUG = True
# S3_MEDIA_BUCKET = 'media.test.serveraddress.com'

# LOCAL
# server = 'http://localhost:8000'
# base_api_ext = ''
# base_web_url = 'http://localhost:8001'
# DEBUG = True
# S3_MEDIA_BUCKET = 'media.test.serveraddress.com'


SECRET_KEY = 'secret'
app.config["DEBUG"] = DEBUG
app.config["SECRET_KEY"] = SECRET_KEY
app.config['DEFAULT_PARSERS'] = [
    'flask.ext.api.parsers.JSONParser',
    'flask.ext.api.parsers.URLEncodedParser',
    'flask.ext.api.parsers.MultiPartParser'
]

app.config["MONGODB_SETTINGS"] = {
    'db': 'database',
    'username': 'admin',
    'password': 'password'
}

app.config['MAIL_SERVER'] = 'mail.serveraddress.com'
app.config['MAIL_PORT'] = 25
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'email@serveraddress.com'
app.config['MAIL_PASSWORD'] = 'password'

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
    merchant_master_id = 'masterid'
    braintree.Configuration.configure(
        braintree.Environment.Sandbox,
        merchant_id='merchant',
        public_key='public',
        private_key='private'
    )
    PALLET_PAYMENT_TOKEN = 'token'
else:
    # Production
    merchant_master_id = 'masterid'
    braintree.Configuration.configure(
        braintree.Environment.Production,
        merchant_id='merchant',
        public_key='public',
        private_key='private'
    )
    PALLET_PAYMENT_TOKEN = 'token'

DAYS_HELD_IN_ESCROW = 3

# ---- GLOBALS ---- #

# PARSE PUSH NOTIFICATIONS
if DEBUG:
    PARSE_MASTER = 'master'
    PARSE_APP_ID = 'app'
    PARSE_REST_KEY = 'rest'
else:
    PARSE_MASTER = 'master'
    PARSE_APP_ID = 'app'
    PARSE_REST_KEY = 'rest'


PALLET_OFFER_SHIPMENT_KEY = "offer_shipment"
PALLET_PHONE_NUMBER = '555-555-5555'
PALLET_EMAIL = 'email@serveraddress.com'

PALLET_SECRET_ADMIN_PASS = 'secret'

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
