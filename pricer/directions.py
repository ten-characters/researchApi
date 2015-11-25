__author__ = 'austin'

from pricer import STATE_GEOCODE_MILEAGE_THRESHOLD

from requests import get
import geocoder
from geopy import distance, Point


def get_route(start_lat, start_lng, end_lat, end_lng):
    start_string = "origin=" + str(start_lat) + "," + str(start_lng)
    end_string = "destination=" + str(end_lat) + "," + str(end_lng)

    sensor = "sensor=false"

    params = start_string + "&" + end_string + "&" + sensor
    output_format = "json"

    route_url = "https://maps.googleapis.com/maps/api/directions/" + output_format + "?" + params

    route_resp = get(route_url)

    return route_resp.json()


def get_route_states(route):
    """
    Need to cut down on reverse geocoding requests, as this is what is slowing our algorithm down tremendously
    ~Be wary of hacks~
    We could do this either by finding some module out there that categorizes a latlng into a state without the interwebs,
    orrr we could only geocode to find the state if the next latlng in the route is outside a certain threshold

    :param route: a json dict from the Google Maps api
    :return: list of dict of states by two letter code along with the miles in each
    """
    states_passed_through = []

    steps = route['routes'][0]['legs'][0]['steps']

    last_geocoded_point = None
    last_state_passed = None
    num_geocoded = 0

    for step in steps:
        latlng = (step['start_location']['lat'], step['start_location']['lng'])

        # Normalize the distance into miles
        distance_text = str(step['distance']['text'])
        if 'ft' in distance_text:
            distance_text = distance_text.replace("ft", "")
            distance_miles = float(distance_text) / 5280
        else:
            distance_miles = float(distance_text.replace("mi", ""))

        if last_geocoded_point is not None \
                and distance.distance(Point(latlng[0], latlng[1]), last_geocoded_point).miles \
                        < STATE_GEOCODE_MILEAGE_THRESHOLD:
            # Trying to cut down on how often we geocode states, so long trips will be calculated
            # as quickly as possible
            if last_state_passed is not None:
                states_passed_through.append({'state': last_state_passed, 'miles': distance_miles})
        else:
            state = (geocoder.google([latlng[0], latlng[1]], method='reverse')).state
            last_geocoded_point = Point(latlng[0], latlng[1])
            last_state_passed = state
            num_geocoded += 1

            if state is None:
                print("Failed to geocode:" + str(latlng) + " in getting states passed!")
                if last_state_passed is not None:
                    states_passed_through.append({'state': last_state_passed, 'miles': distance_miles})
            else:
                states_passed_through.append({'state': state, 'miles': distance_miles})

    print("Number of state geocodes: " + str(num_geocoded))
    return states_passed_through


