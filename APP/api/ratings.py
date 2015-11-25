__author__ = 'austin'

import json

from APP import app, base_api_v1_ext, base_api_v1_1_ext
from APP.models import ActiveUser, Rating, Shipment, Warehouse
from APP.utility import throw_error, make_gen_success, check_authentication
from flask import request, abort
from mongoengine import DoesNotExist

FILE_TAG = __name__


def rate(rating_user, rated_user, rating, shipment):
    # (person) rates (person) with (rating)
    rating_doc = Rating(
        rated_user_id=rated_user.id,
        shipment_id=shipment.id,
        rating=rating
    )
    rating_user.update(push__ratings_given=rating_doc)
    rated_user.update(push__ratings_received=rating_doc)



@app.route(base_api_v1_ext + '/rate/<string:shipment_id>', methods=['POST'])
@app.route(base_api_v1_1_ext + '/rate/<string:shipment_id>', methods=['POST'])
def rate_user(shipment_id):
    """Rate user
    REQUEST FORMAT:
        /rate/<string:shipment_id>
        adds a rating to a users ratings

        # Requires either Group 1 or Group 2

        {
         'shipment_id': 4958, # required
         'shipper_rating': (rating),   # Optional Group 1
         'consignee_rating': (rating), # Optional Group 1
         'trucker_rating': (rating)    # Optional Group 2
        }
    """
    auth = check_authentication()
    if not auth[0]:
        abort(403)
    try:
        data = json.loads(request.data.decode('utf-8'))
    except ValueError:
        data = request.form

    try:
        # There should be three values here!
        shipment = Shipment.objects.get(id__exact=shipment_id)
    except DoesNotExist:
        throw_error('Shipment does not exist!', 400, request, FILE_TAG)

    try:
        # Two options, either the trucker is rating or the customer is
        if 'trucker_rating' in data:
            # Customer is rating!
            # Find the trucker
            customer = ActiveUser.objects.get(id__exact=shipment.shipper.id)
            trucker = ActiveUser.objects.get(id__exact=shipment.driver.id)

            rate(customer, trucker, data['trucker_rating'], shipment)

        elif 'shipper_rating' in data and 'consignee_rating' in data:
            # Trucker is rating, get the shipper and consignee
            trucker = ActiveUser.objects.get(id__exact=shipment.driver.id)

            start_warehouse = Warehouse.objects.get(id__exact=shipment.start_warehouse.id)
            rate(trucker, start_warehouse, data['shipper_rating'], shipment)

            end_warehouse = Warehouse.objects.get(id__exact=shipment.end_warehouse.id)
            rate(trucker, end_warehouse, data['consignee_rating'], shipment)

    except DoesNotExist:
        throw_error('Does not exist!', 400, request, FILE_TAG)
    # except KeyError:
    #     make_error('Key error!', 400, request, FILE_TAG)

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_gen_success(new_token=new_token)
