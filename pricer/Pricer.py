__author__ = 'austin'

# from __future__ import division

from pricer import STATE_FUEL_AVG_DICT, PRICE_DATA_DICT, ACCESSORIALS_DICT
from pricer import RATE_KEY, SHORT_HAUL_EXPONENT, SHORT_HAUL_MIN_RATE
from pricer import get_miles_per_gallon
from pricer.directions import get_route, get_route_states
from pricer.regionize import regionize, find_next_closest_zip

from pygeocoder import Geocoder

'''
    The main functionality of this ALGORITHM
    Use case:
        get_price_from("Steamboat Springs, CO", "Jersey City, NJ", weight=30000, is_truckload=True, num_pallets=5)
        get_price_from("Steamboat Springs, CO", "Jersey City, NJ", weight=30000, is_truckload=False, num_pallets=5)
'''


def get_mile_rate_from_list(start_zips, end_zips, trip_miles):
    """
    Will raise KeyError if there are no records of zips by that name
    Todo: play with short haul rates compared to how long the trip is

    Let's experiment with the constant / trip_miles + short_rate

    Should get weighted price from a list of dicts (closest start zips and end zips along with their weights)
    start_zips = [
        {
            zip: '03039',
            weight: .8
        },
        ...
        {
            zip: '04039',
            weight: .1
        }
    ] # Sum of all weights should == 1

    For every start / end combo
    price * start_weight * end_weight

    :param start_zips: [string] (will be used as a dict key)
    :param end_zips: " "
    :param trip_miles: float
    :return:
    """

    price_per_mile = 0.0

    # We need to handle the cases where there is only one near hotspot and is traveling in the same region
    # I really want to stray away from this way of doing things. I am still in favor of creating a nice lil equation
    # looking like: constant / miles + base_rate
    if len(start_zips) == 1 and len(end_zips) == 1 and start_zips[0] == end_zips[0]:
        constant = PRICE_DATA_DICT[start_zips[0]['zip']][end_zips[0]['zip']][RATE_KEY] ** SHORT_HAUL_EXPONENT
        price_per_mile = constant / trip_miles + SHORT_HAUL_MIN_RATE
        return price_per_mile

    for start in start_zips:
        for end in end_zips:
            try:
                if start['zip'] != end['zip']:
                    # Ignore when the start and end are the same, as that could drive the prices crazy high!
                    zip_to_zip_rate = PRICE_DATA_DICT[start['zip']][end['zip']][RATE_KEY]
                    price_per_mile += zip_to_zip_rate * start['weight'] * end['weight']
            except KeyError:
                print("Problem going from " + start['zip'] + " to " + end['zip'])

    return price_per_mile


def get_price(start_lat, start_lng, end_lat, end_lng,
              weight=None, commodity=None, is_truckload=True, num_pallets=None, accessorials=None):

    """

    :param start_lat: float
    :param start_lng: float
    :param end_lat: float
    :param end_lng: float
    :param weight: float
    :param commodity: float
    :param is_truckload: bool
    :param num_pallets: int
    :param accessorials: list ( of keys )
    :return: (price, is_truckload)
    """
    # Default all the mutable params
    if accessorials is None:
        accessorials = []

    from datetime import datetime
    start_time = datetime.utcnow()

    # Default the kwarg optional parameters
    if weight is None:
        # If none provided, give em the heaviest, oops
        weight = 50000

    if commodity is None:
        commodity = 'tacos'

    task_start = datetime.utcnow()
    print("Getting route!")
    # First get the google route for the trip
    route = get_route(start_lat, start_lng, end_lat, end_lng)
    print("Took: " + str((datetime.utcnow() - task_start).seconds))
    # Store the total miles because that will be useful a bunch o' places
    total_trip_miles = str((route['routes'][0]['legs'][0]['distance']['text'])).replace(" mi", "")
    total_trip_miles = total_trip_miles.replace(" ft", "")
    total_trip_miles = total_trip_miles.replace(",", "")
    total_trip_miles = float(total_trip_miles)

    # The fuel price
    avg_fuel_price_per_gallon = 0.0
    print("Getting states passed through!")
    task_start = datetime.utcnow()
    states_passed_through = get_route_states(route)
    print("Took: " + str((datetime.utcnow() - task_start).seconds))
    print("Compiling the fuel price!")
    task_start = datetime.utcnow()

    avg_fuel_prices = []

    for state in states_passed_through:
        # The average gas price is a weighted compilation of all the states in the trip and the mileage in each
        avg_fuel_price_per_gallon += ((state['miles'] / total_trip_miles) * STATE_FUEL_AVG_DICT[state['state']])
        avg_fuel_prices.append(STATE_FUEL_AVG_DICT[state['state']])

    print("Took: " + str((datetime.utcnow() - task_start).seconds))
    # Convert into dollars
    fuel_price = (avg_fuel_price_per_gallon / get_miles_per_gallon(weight)) * total_trip_miles

    # The base price for Truckloads
    # Find regions and lookup in dict
    regions = regionize(start_lat, start_lng, end_lat, end_lng)
    start_regions = regions[0]
    end_regions = regions[1]

    base_price_per_mile = get_mile_rate_from_list(start_regions, end_regions, total_trip_miles)

    base_price = base_price_per_mile * total_trip_miles

    # Check if the base price is less than the lowest move price, aka the inter-region price
    if base_price < PRICE_DATA_DICT[start_regions[0]['zip']][end_regions[0]['zip']][RATE_KEY]:
        base_price = PRICE_DATA_DICT[start_regions[0]['zip']][end_regions[0]['zip']][RATE_KEY]

    print("Truckload price: " + str(base_price))

    if not is_truckload:
        # The Pallet(ized) rating system
        #

        """
        Base price:
        # Pallets:
        1 : $100
        2 : + $75
        3 ... Truckload : +$50

        Miles:
        Cumulative
        m <= 100 : Base Rate
        100 < m <= 200 : ^ 10%
        200 < m <= 300 : ^ 5%
        300 < m (every 100 miles) : ^ 3%

        :param: num_pallets : int
        :param: miles : float, int
        :return: price : float
        """

        # Start by computing the base price:
        palletized_base_price = 0
        base_rate = 100
        for i in range(0, num_pallets):
            palletized_base_price += base_rate
            if i < 2:
                base_rate -= 25

        # Now compute the mileage adjustment
        mileage_adjuster = 0
        mileage_percent_rate = .10
        # Minus one because it's exclusive every 100
        for i in range(0, (int((total_trip_miles-1) / 100))):
            mileage_adjuster += mileage_percent_rate
            if i < 2:
                mileage_percent_rate *= .5
                mileage_percent_rate = round(mileage_percent_rate, 2)

        # Add the addition from the mileage adjuster
        palletized_base_price += (palletized_base_price * mileage_adjuster)

        # If the palletized price is more expensive than as a truckload, charge as a truckload!
        # Otherwise, the palletized base price should be the one we go with!
        print("Palletized price: " + str(palletized_base_price))
        if palletized_base_price < base_price:
            base_price = palletized_base_price
        else:
            is_truckload = True

    # Gather Accessorial Charges
    accessorial_price = 0.0
    for extra in accessorials:
        accessorial_price += ACCESSORIALS_DICT[extra]

    the_price = round(float(base_price + fuel_price + accessorial_price), 2)

    # Just some stats
    print("STATS\n")
    print("Num closest to start: " + str(len(start_regions)))
    print("Num closest to end: " + str(len(end_regions)))
    print("Total miles: " + str(total_trip_miles))
    print("Base rate per mile: " + str(base_price / total_trip_miles))
    print("Base price: " + str(base_price))
    print("Average fuel surcharge per mile: " + str((sum(avg_fuel_prices) / len(avg_fuel_prices)) / get_miles_per_gallon(weight)))
    print("Fuel price: " + str(round(fuel_price, ndigits=2)))
    print("MPG: " + str(get_miles_per_gallon(weight)))
    print("Accessorials: " + str(accessorials))
    print("Accessorial price: " + str(accessorial_price))
    print("Price: " + str(the_price))
    print("Total time (seconds): " + str((datetime.utcnow() - start_time).seconds))

    return the_price, is_truckload


def get_price_from(start_address, end_address,
                   weight=None, commodity=None, is_truckload=True, num_pallets=None, accessorials=None):
    """
    ex: get_price_from("Jersey City, NJ", "Sante Fe, NM")
    :param start_address:
    :param end_address:
    :param weight:
    :param commodity:
    :param is_truckload:
    :param num_pallets:
    :param accessorials:
    :return:
    """

    if accessorials is None:
        accessorials = []

    start_geo = Geocoder.geocode(start_address)
    end_geo = Geocoder.geocode(end_address)
    return get_price(
        start_geo.latitude, start_geo.longitude,
        end_geo.latitude, end_geo.longitude,
        weight=weight, commodity=commodity,
        is_truckload=is_truckload, num_pallets=num_pallets, accessorials=accessorials
    )


get_price_from("Steamboat Springs, CO", "Montrose, CO",
               weight=30000, is_truckload=True, num_pallets=5, accessorials=['liftgate'])
# get_price_from("Woodmoor, CO", "Aurora, CO", weight=30000, is_truckload=True, num_pallets=5)
# get_price_from("Steamboat Springs, CO", "Jersey City, NJ", weight=30000, is_truckload=True, num_pallets=5)
# get_price_from("Tampa Bay, FL", "Jersey City, NJ", weight=30000, is_truckload=True, num_pallets=5)
# get_price_from("Newark, NJ", "Denver, CO", weight=30000, is_truckload=True, num_pallets=5)
