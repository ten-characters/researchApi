__author__ = 'austin'

from APP import DAYS_HELD_IN_ESCROW
from APP.models import Transaction
from APP.decorators import async
from APP.utility import log_error

import braintree

import time
from datetime import datetime, timedelta

FILE_TAG = __name__

"""
    Start this script at the start of every api launch
    Should run through all the transactions and finish them if they need that!
    We want to hold transactions for three days right now !
    Should run once an hour just for shits and giggles
"""
SLEEP_TIME = 1 * 60 * 60  # hours * minutes * seconds

def run():
    times_run = 0
    while True:
        print('running finisher for the ' + str(times_run) + 'th time. So cyclic. Ugh.')
        times_run += 1
        # Start by getting a list of all the unpaid transactions in our books
        transactions = Transaction.objects()
        for transaction in transactions:
            # Check to see if the date to be held until has passed
            if transaction.date + timedelta(days=DAYS_HELD_IN_ESCROW) < datetime.utcnow() \
                    and transaction.transaction_id is not None:
                # If it is, submit for removal from escrow !
                result = braintree.Transaction.release_from_escrow(transaction.transaction_id)
                if result.is_success:
                    transaction.update(date_released_from_escrow=datetime.utcnow(), is_paid=True)
                else:
                    log_error("Couldn't release transaction: " + transaction.id + " for this reason: "
                              + str(result.transaction.processor_response_text), FILE_TAG)

        time.sleep(SLEEP_TIME)


@async
def run_async():
    run()
