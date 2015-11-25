__author__ = 'austin'

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_mongoengine import MongoEngine

app = Flask(__name__)
app.config['TESTING'] = True
app.config['DEBUG'] = True

app.config["MONGODB_SETTINGS"] = {
    'db': 'UnitTesting'
}

# app.config["MONGODB_SETTINGS"] = {
#     'db': '',
#     'username': '',
#     'password': ''
# }
db = MongoEngine(app)

bcrypt = Bcrypt(app)


def create_app():
    return app
