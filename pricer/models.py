__author__ = 'austin'
from mongoengine import *
import datetime


class StateAvgFuelPrice(Document):
    meta = {
        'indexes': [
            'price',
            'time_recorded'
        ]
    }
    price = FloatField(min_value=0, required=True)
    state = StringField(required=True)
    time_recorded = DateTimeField(default=datetime.datetime.now)

