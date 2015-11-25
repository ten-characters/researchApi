__author__ = 'austin'

from datetime import datetime

import warnings
import functools


def deprecated(in_version, reason=None):
    '''This is a decorator which can be used to mark functions
       as deprecated. It will result in a warning being emitted
       when the function is used.'''
    def dec(f):
        @functools.wraps(f)
        def new_func(*args, **kwargs):
            message = "Call to deprecated function {f}{args}. Dep in version: {version}."\
                            .format(version=str(in_version), f=f.__name__, args=str(args))
            if reason is not None:
                message += " Because: " + reason
            print(message, f.__name__)
            return f(*args, **kwargs)
        return new_func
    return dec


@deprecated('1', reason='it was dumb')
def format_string_to_date(datestring):
    formats = [
        '%m/%d/%Y-%H:%M:%S',
        '%m/%d/%Y',
        '%Y-%m-%d-%H:%M:%S',
        '%Y-%m-%d'
    ]

    date = None
    for form in formats:
        try:
            date = datetime.strptime(datestring, form)
            break
        except ValueError:
            pass

    return date

date = '1990-07-01-00:00:00'

date = format_string_to_date(date)
# print(date.day)

# from flask import Flask
# from flask_mongoengine import MongoEngine
#
# app = Flask(__name__)
# app.config["MONGODB_SETTINGS"] = {'DB': 'Test'}
# db = MongoEngine(app)


# class Reference(db.Document):
#     test = db.StringField()
#
#
# class Transaction(db.DynamicDocument):
#     meta = {'indexes':
#         [
#             'is_paid',
#             'date'
#         ]
#     }
#
#     date = db.DateTimeField(required=False, default=datetime.utcnow())
#     date_released_from_escrow = db.DateTimeField(required=False)
#     # Links to the two users !
#     user_paid = db.ReferenceField(Reference, required=False, default=None)
#     # When we are paying people, we should do it from an account made
#     # specifically for that
#     user_charged = db.ReferenceField(Reference, required=False, default=None)
#
#     shipment = db.ReferenceField(Reference, required=False, default=None)
#
#     transaction_record = db.StringField(required=False, default=None, max_length=255)
#
#     bt_message = db.StringField(required=False)
#
#     # Two types right now: shipment or promo
#     type = db.StringField(required=False)
#     amount = db.DecimalField(required=False, default=0.00, precision=3)
#     service_charge = db.DecimalField(required=False, default=0.00, precision=3)
#     is_paid = db.BooleanField(required=False, default=False)
#
# ref = Reference().save()
#
# trannie = Transaction(
#     user_paid=ref,
#     user_charged=ref,
#     shipment=ref
# )
# print(trannie.id is None)
# trannie.save()
# print(trannie.id)


# print(format_string_to_date('05/21/1995'))
#
# class DriverIssue(db.EmbeddedDocument):
#     location = db.PointField(required=True)
#     # Only needed if can still deliver
#
# issue = DriverIssue(location=[42.93, -73.4])
#
# from pygeocoder import Geocoder
#
# print(issue)
# geocoded = Geocoder.reverse_geocode(issue.location[0], issue.location[1])
# print(geocoded)