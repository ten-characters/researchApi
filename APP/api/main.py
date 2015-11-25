""" GENERAL NOTES
    The Pallet RESTful API using Flask
    we go old school
    truck yeah
    *cringe here*
    #craig
    Donny, whatta wise guy

    All data is sent in the 'data' header,
    or in multipart requests, the form
    Files (like photos) are sent in file headers

    Goals for the future:
        RESTful design structures:
            Only use nouns in endpoints, and reuse them in different HTTP contexts for logical actions.
                Ex: the get_price endpoint should be changed to just price, then filtered by the request method
"""
__author__ = 'austin'

from APP import app, base_api_ext, base_api_v1_ext, base_api_v1_1_ext
from APP.models import ActiveUser, Warehouse
from APP.utility import throw_error, check_authentication, make_gen_success

from flask import jsonify, request, abort, make_response
import json
from datetime import datetime

FILE_TAG = __name__

# General todos:
# Todo: Create an archive database to store all deleted users and unaccepted applications
# Todo: Start asking for forgiveness rather than validating all this data


# --------------------------- api VERSION 1.0 -------------------------------- #
@app.route(base_api_ext + '/')
@app.route(base_api_v1_ext + '/')
@app.route(base_api_v1_1_ext + '/')
def index():
    """

    :return:
    """
    return jsonify(response="Welcome to the Pallet api. Treat the world kindly.")


@app.route(base_api_ext + '/truck_on')
@app.route(base_api_v1_1_ext + '/truck_on')
def health():
    """
        Just returns a 200 status if we are up
    :return:
    """
    return make_response(jsonify(health="Truck on"), 200)


@app.route(base_api_ext + '/get_price', methods=['GET', 'PUT'])
@app.route(base_api_v1_ext + '/get_price', methods=['GET', 'PUT'])
@app.route(base_api_v1_1_ext + '/price', methods=['GET', 'PUT'])
def generate_price():
    """
    THE ALGORITHM ooOOoo

    :param: weight : (lbs) string/float
    :param: commodity : string
    :param: is_truckload: boolean
    :param: num_pallets: int
    :param: accessorials : [str]

    # OPTION 1
    :param: start_addr : string (Anything that can be geocoded is a-ok)
    :param: end_addr : " "
    # OPTION 2
    :param: start_lat : args can be either string or float
    :param: start_lng : " "
    :param: end_lat : " "
    :param: end_lng : " "
    :return:
    """
    try:
        data = json.loads(request.data.decode('utf-8'))
    except ValueError:
        data = request.form

    # Default all the values if not in data
    # I think this is cleaner than 4 try/except statements, others may disagree
    weight = None; commodity = None; is_truckload = True
    num_pallets = None; assessorials = None
    if 'weight' in data:
        weight = data['weight']
    if 'commodity' in data:
        commodity = data['commodity']
    if 'is_truckload' in data:
        is_truckload = data['is_truckload']
    if 'num_pallets' in data:
        num_pallets = data['num_pallets']

    from pricer import Pricer

    # Which method are they using huh huh??
    try:
        price = Pricer.get_price_from(data['start_addr'], data['end_addr'],
                                      weight=weight,
                                      commodity=commodity,
                                      is_truckload=is_truckload,
                                      num_pallets=num_pallets)
    except KeyError:
        price = Pricer.get_price(data['start_lat'], data['start_lng'], data['end_lat'], data['end_lng'],
                                      weight=weight,
                                      commodity=commodity,
                                      is_truckload=is_truckload,
                                      num_pallets=num_pallets)

    return make_response(jsonify(witty_response='nice try Donny, you wise guy',
                                 price=price[0],
                                 is_truckload=price[1]))


@app.route(base_api_v1_ext + '/warehouses', methods=['GET'])
@app.route(base_api_v1_1_ext + '/warehouses', methods=['GET'])
def get_warehouses():
    """

    :return:
    """
    auth = check_authentication()
    if not auth[0]:
            abort(403)
    # Todo: think about if theres something we want to keep hidden
    warehouses = []
    for w in Warehouse.objects:
        warehouses.append(w)

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None

    return jsonify(result=warehouses, new_token=new_token)


