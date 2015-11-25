__author__ = 'craig'

from APP.driverMatcher import find_driver_for_shipment
from APP.utility import estimate_time_taken_to_find_driver
from APP.models import Shipment
from APP.decorators import async
from APP.email import send_async_mail, make_no_drivers_message, make_no_local_drivers_warning_message
from datetime import datetime
import time


SLEEP_TIME = 300  # 5 * 60 aka 5 mins !


'''
    General Notes:
        According to Jerry it takes about 2.5 hours for a large company to come and pick up a shipment. So if we cannot
        find a driver before that time, we should let the customer know, alerting them to two options:
            - Cancel it on the web portal
                Potentially we could even provide a quick link to do this
                Jk. Fuckem.
            - Leave it be, let the time run out, cancel it at any time
                If the time runs out, we should close the shipment (?) and archive it in a new collection

    Why not just comb through the database?
    It provides almost the same functionality as the csv file?
        If just for performance, are the collection indexes not sufficient?

    Problems:
        - The csv makes it hard to push with Git, way too easy to overwrite the entire watched shipments list
        - Todo: For some reason or other, we can't send emails. Apparently there is no context in which to send them
            from. Thoroughly confused.
    Solutions:
        - No more csv
'''


# Night gathers, and now my watch begins.
# It shall not end until my death.
# I shall take no wife, hold no lands, father no children.
# I shall wear no crowns and win no glory.
# I shall live and die at my post.
# I am the sword in the darkness.
# I am the watcher on the walls.
# I am the shield that guards the realms of men.
# I pledge my life and honor to the Night's Watch, for this night and all the nights to come.
def watch_shipments():
    """
        The main goal with this guy is to make sure we continue to try to find drivers for shipments. Always. Well, every 5 minutes.
    :return:
    """
    print('Watch started!')
    times_run = 0
    while True:
        print('Running watch for the ' + str(times_run) + 'th time. Hi Craig.')
        if times_run == 42:
            print("Hooli is coming for you @Greg @Fran.")

        shipments_to_check = Shipment.objects(is_accepted=False)
        for shipment in shipments_to_check:
            # if shipment.pickup_time - SHIPMENT_HOURS_AVAILABLE < datetime.utcnow():
                # shipment.update(is_available=True)
                if shipment.pickup_time - estimate_time_taken_to_find_driver(shipment) < datetime.utcnow():
                    # Try to find it a driver all the way until the pickup time has passed
                    # If no drivers are in the area, this will be done incredibly quickly and should
                    # repost to the unaccepted without hiccups
                    if not shipment.is_being_offered:
                        find_driver_for_shipment(shipment)

                # if shipment.pickup_time - SHIPMENT_HOURS_BEFORE_ALERTING_CUSTOMER < datetime.utcnow() \
                #         and not shipment.has_been_warned:
                #     # Just send out a notice if we are within a few hours before the shipment
                #     # is supposed to be picked up
                #     # We want to be as transparent as possible about our limitations
                #     shipment.update(has_been_warned=True)
                #     try:
                #         send_async_mail(make_no_local_drivers_warning_message(shipment))
                #     except Exception as ex:
                #         print("Oh no, we had an exception of type " + str(type(ex)) + " in the shipmentWatcher")
                elif shipment.pickup_time_end < datetime.utcnow():
                    # This is sad, we could not find a driver
                    # Archive it and send an email
                    shipment.archive_unmatched()
                    try:
                        send_async_mail(make_no_drivers_message(shipment))
                    except Exception as ex:
                        print("Oh no, we had an exception of type " + str(type(ex)) + " in the shipmentWatcher")

        times_run += 1
        time.sleep(SLEEP_TIME)


@async
def run_async():
    watch_shipments()


def run():
    watch_shipments()
