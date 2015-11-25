__author__ = 'austin'

'''
    THE Algorithm

    Some things that have gone into v1.1:
        - Preliminary Palletized pricing
        - Weighting multiple close hotspots within a certain distance
        - Accounting for weight in the miles per gallon of fuel approximation
        - Less geocoding from state to state, just if the next step is more than x miles from the last
        - Added a whole bunch o' stats

'''


import csv
import os
from datetime import datetime

# Keys as denoted by DAT
MILEAGE_KEY = 'PC-Miler Practical Mileage'
RATE_AVG_KEY = 'Spot Avg Linehaul Rate'
RATE_LOW_KEY = 'Spot Low Linehaul Rate'
RATE_HIGH_KEY = 'Spot High Linehaul Rate'
RATE_FUEL_KEY = 'Spot Fuel Surcharge'
ZIP_ORIG_KEY = 'Orig Postal Code'
ZIP_DEST_KEY = 'Dest Postal Code'

# The Key we are using
DAT_RATE_KEY = RATE_AVG_KEY

# Our own data keys
RATE_KEY = 'rate'

SHORT_HAUL_MIN_RATE = 2.5
SHORT_HAUL_EXPONENT = 1.2

HOTSPOT_MILEAGE_THRESHOLD = 150

STATE_GEOCODE_MILEAGE_THRESHOLD = 10

ACCESSORIALS_DICT = {
    'liftgate': 100,
    'lumper': 125,
    'jack': 50,
}

# This will be used as the constant in the short haul calculation function
# SHORT_HAUL_NUMERATOR_CONSTANT

PRICE_DATA_DICT = {}

"""
    Load into a easily readable and sortable structure .. a dict!
    Each origin zip should have the rate to every other zip, plus extras:
        - Short haul price, determined by average # Nixed for now : (

    Schema:
        Data {
            Origin: {
                Dest: {
                    rate: .43,
                    miles: 1002
                },
                Dest: {
                    rate: .52,
                    miles: 500
                }, ...
                Short: 3.6
            }

        }
"""
load_start = datetime.utcnow()

for prices_file in os.listdir(os.path.dirname(os.path.realpath(__file__)) + '/PriceData'):
    with open(os.path.dirname(os.path.realpath(__file__)) + '/PriceData/' + prices_file) as csvfile:
        reader = csv.DictReader(csvfile)
        rate = None
        for row in reader:

            # Some zips are cut off if they start with zero
            # thanks excel
            new_origin_zip = row[ZIP_ORIG_KEY]
            if len(new_origin_zip) == 4:
                    new_origin_zip = '0' + new_origin_zip

            new_dest_zip = row[ZIP_DEST_KEY]
            if len(new_dest_zip) == 4:
                    new_dest_zip = '0' + new_dest_zip

            # When the column names come around, don't try to make sense of em
            if new_origin_zip != "":
                try:
                    PRICE_DATA_DICT[new_origin_zip]
                except KeyError:
                    # If this is the first time this postal code has been seen make sure
                    # the DATA knows it will become a dict
                    PRICE_DATA_DICT[new_origin_zip] = {}

                try:
                    # Everything that will go into the end point dict aka : rate and miles
                    PRICE_DATA_DICT[new_origin_zip][new_dest_zip]
                except KeyError:
                    PRICE_DATA_DICT[new_origin_zip][new_dest_zip] = {}

                PRICE_DATA_DICT[new_origin_zip][new_dest_zip][RATE_KEY] = float(row[DAT_RATE_KEY])
                PRICE_DATA_DICT[new_origin_zip][new_dest_zip][MILEAGE_KEY] = int(row[MILEAGE_KEY])


print("Microseconds to load price dict: " + str((datetime.utcnow() - load_start).microseconds))

# Also pull the days average gas prices from the mongo database and store them here ! Fun !
from pricer.models import StateAvgFuelPrice
from pricer.decorators import async
from mongoengine import connect
from datetime import datetime, timedelta

STATE_FUEL_AVG_DICT = {}


# Todo: Probably want to make this query on a per case basis !
def update_average_prices():
    connect('fuel-prices')
    STATE_FUEL_AVG_DICT.clear()
    # Query the database for all in the last day
    last_prices_time = datetime.utcnow()
    prices = []
    while len(prices) == 0 and len(StateAvgFuelPrice.objects()) != 0:
        last_prices_time -= timedelta(days=1)
        prices = StateAvgFuelPrice.objects(time_recorded__gte=last_prices_time)

    for price in prices:
        STATE_FUEL_AVG_DICT[price.state] = price.price


def get_miles_per_gallon(weight):
    """
    A basic function to account for weight
    Linear for now as we have no great data:
        0 lbs load => 7 mpg
        50,000 lbs load => 4.5 mpg
    :param weight: float, int, whatever number
    :return: float ( miles per gallon of fuel)
    """
    return 7 - (weight * .00005)  # 5 * 10^-5

update_average_prices()
