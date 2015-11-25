__author__ = 'austin'

from APP import PARSE_APP_ID, PARSE_REST_KEY
from APP.models import ActiveUser
from APP.utility import miles_to_meters, log_error
# from APP.email import send_async_mail, make_no_local_drivers_message
# from APP.decorators import multiprocess

from datetime import timedelta, datetime
from mongoengine.errors import DoesNotExist
import requests
import time
import json

FILE_TAG = __name__

MAX_RANGE = 30
TIME_LIMIT = timedelta(minutes=2)


# @multiprocess
def find_driver_for_shipment(shipment, search_range_miles=5):
    """

    :param shipment:
    :type shipment: Shipment
    :param search_range_miles:
    :type search_range_miles: int
    :return:
    """
    shipment.update(is_available=False)
    shipment.update(is_being_offered=True)
    while True:
        rng = miles_to_meters(search_range_miles)
        # Get the shipments location
        current_holder = shipment.current_holder
        current_holder_json = json.loads(current_holder.to_json())
        location = current_holder_json['location']['coordinates']

        # Get drivers within the shipments location
        closest_drivers = ActiveUser.objects.get_drivers_in_rng_of(rng, location)
        driver_to_offer = None
        # Check through the list of available drivers
        # They will be ordered by distance so the first found is the best!
        i = 0
        while driver_to_offer is None and i < len(closest_drivers):
            if closest_drivers[i] not in shipment.drivers_rejected:
                driver_to_offer = closest_drivers[i]
            i += 1

        if driver_to_offer is None:
            # Could send an email to the shipper saying there are no drivers in the local area
            # todo: play with range, maybe up it every time the list is depleted?
            # Ex: Must make sure not infinite, so we implement a maximum distance to search for
            if search_range_miles >= MAX_RANGE:
                shipment.update(is_being_offered=False)
                shipment.update(is_available=True)
                # shipper = ActiveUser.objects.get_from_id(shipment.shipper.id)
                # send_async_mail(make_no_local_drivers_message(shipper, shipment))
                break
        else:
            # We will send push notifications to drivers notification keys
            # Who knows if this is actually how you're supposed to use channels
            channels = []
            notif_key = driver_to_offer.notification_key
            # Append KEY to the beginning of the channel because Parse Channels have to start with
            channels.append("KEY" + notif_key)

            message = make_shipment_offer_notif(shipment)


            print('sending offer to: ' + driver_to_offer.email)
            offer_response = requests.post('https://api.parse.com/1/push',
                                           data=json.dumps({
                                               "channels": channels,
                                               "data": message
                                           }),
                                           headers={
                                               "X-Parse-Application-Id": PARSE_APP_ID,
                                               "X-Parse-REST-API-Key": PARSE_REST_KEY,
                                               "Content-Type": "application/json"
                                           })
            if not offer_response.ok:
                log_error("Failed to offer a push notification to " +
                          str(channels) + " with response: " + offer_response.text,
                          FILE_TAG)
            # import httplib2
            # connection = httplib2.HTTPSConnectionWithTimeout('api.parse.com', 443)
            # connection.connect()
            # connection.request('POST', '/1/push', json.dumps({
            #    "channels": channels,
            #    "data": message
            #  }), {
            #    "X-Parse-Application-Id": PARSE_APP_ID,
            #    "X-Parse-REST-API-Key": PARSE_REST_KEY,
            #    "Content-Type": "application/json"
            #  })

            # Give a buffer to account for slow internet connections
            # if someone accepts but takes 7 seconds to get here then ehhhh
            time.sleep(TIME_LIMIT.seconds + 7)

            # Must reload to pull current data
            try:
                shipment.reload()
            except DoesNotExist:
                # When a shipment has already been completed. Would be nutso in real
                # situations buuut whatever
                break
            if shipment.is_accepted or driver_to_offer.id in shipment.drivers_rejected:
                # Exit the method if the driver responded while the script was in sleep-ville
                # Also exits if the offered driver was added to the list of rejections whilst asleep
                # This prevents spawning craazy amount of processes being spawned when we call a new
                # driver_matcher upon explicit rejection of a shipment
                break
            shipment.update(push__drivers_rejected=driver_to_offer)

        search_range_miles += 5
    return


def make_shipment_offer_notif(shipment):
    """

    :param shipment:
    :type shipment: Shipment
    :return: dict
    """
    from APP import PALLET_OFFER_SHIPMENT_KEY

    expiration = (datetime.utcnow() + TIME_LIMIT).isoformat()
    # Then build the shipment
    # Just pop it in
    notification = {
        'type': PALLET_OFFER_SHIPMENT_KEY,
        'offer_data':
            {
                'shipment': shipment.get_returnable_json(),
                'expiration': expiration,
                # Temporary, while we work on UTCtime conversion
                'expiration_secs': TIME_LIMIT.seconds
            }
    }
    return notification

# Could be converted to a wrapper
import multiprocessing
def start_driver_matcher(shipment, search_range=5):
    """

    :param shipment:
    :param search_range:
    :return:
    """
    p = multiprocessing.Process(target=find_driver_for_shipment, args=(shipment, search_range, ))
    p.start()