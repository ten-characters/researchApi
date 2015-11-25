__author__ = 'austin'

import json

from APP import app, base_api_ext, base_api_v1_ext, base_api_v1_1_ext, PALLET_PAYMENT_TOKEN, FIRST_MOVE_PROMO
from APP.models import ActiveUser, Transaction
from APP.utility import check_authentication, throw_error, log_error, make_gen_success
from APP.email import make_payment_method_approved_message, make_payment_method_declined_message, send_async_mail
from flask import request, abort, jsonify, Response, make_response
import braintree
from decimal import Decimal

FILE_TAG = __name__


@app.route(base_api_ext + '/braintree/client_token')
@app.route(base_api_v1_ext + '/braintree/client_token')
@app.route(base_api_v1_1_ext + '/braintree/client_token')
def get_client_token():
    """

    :return:
    """
    auth = check_authentication()
    if not auth[0]:
        abort(403)

    data = json.loads(request.data.decode('utf-8'))
    user = ActiveUser.objects.get_from_email(data['email'])

    if user is not None:
        to_return = braintree.ClientToken.generate({"customer_id": user.customer_id})

        try:
            return make_response(jsonify(result=to_return, new_token=auth[1]), 200)
        except IndexError:
            return make_response(jsonify(result=to_return), 200)
    throw_error("Couldn't find user by email: " + data['email'], 400, request, FILE_TAG)


def create_promo_transaction(driver):
    """
    This is called when a driver completes their first move!

    :param driver: Driver object
    :return:
    """
    transaction = Transaction(
                user_paid=driver,
                type="promo",
                amount=Decimal(FIRST_MOVE_PROMO),
                service_charge=Decimal(0.00)
    )

    result = None
    try:
        result = braintree.Transaction.sale(
            {
                "merchant_account_id": driver.customer_id,
                "amount": Decimal(FIRST_MOVE_PROMO),
                "payment_method_token": PALLET_PAYMENT_TOKEN,
                "service_fee_amount": Decimal(0.0),
                "options": {
                    "submit_for_settlement": True,
                    "hold_in_escrow": True
                },
                'custom_fields': {
                    'type': 'promo'
                }
            }
        )
    except braintree.exceptions.authorization_error.AuthorizationError as ex:
        # We will store this is their unpaid transactions if they still haven't got their thing!
        driver.update(inc__driver_info__unpaid_transactions=FIRST_MOVE_PROMO)
        # We will pay them when they are all there
        log_error("Can't authorize transaction!", FILE_TAG, exception=ex)

    if result is not None:
        if result.is_success:
            transaction.transaction_id = result.transaction.id
            transaction.save()
            # Add it to both user's list of transactions
            driver.update(push__transactions=transaction)
        else:
            transaction.save()
            # Add it to both user's list of transactions
            driver.update(push__transactions=transaction)
            # If the transaction was not successful, return the reason why
            result_transaction = result.transaction
            if result_transaction is None:
                log_error("Problem making promo transaction!", FILE_TAG)
            else:
                log_error("Problem making promo transaction: " + str(result.transaction.processor_response_text), FILE_TAG)
            return False

    return True


def create_shipment_transaction(shipment):
    """

    :param shipment:
    :return:
    """

    transaction = Transaction(
                user_paid=shipment.driver,
                user_charged=shipment.shipper,
                shipment=shipment,
                type="shipment",
                amount=round(Decimal(shipment.trucker_price), ndigits=2),
                service_charge=round(Decimal(shipment.price - shipment.trucker_price), ndigits=2)
    ).save()

    shipment.update(transaction=transaction)

    result = None
    try:
        result = braintree.Transaction.sale(
            {
                "merchant_account_id": shipment.driver.customer_id,
                "amount": round(Decimal(shipment.price), ndigits=2),
                "payment_method_nonce": shipment.payment_nonce,
                "service_fee_amount": round(Decimal(shipment.price - shipment.trucker_price), ndigits=2),
                "options": {
                    "submit_for_settlement": True,
                    "hold_in_escrow": True,
                    "store_in_vault": True
                },
                'custom_fields': {
                        'type': 'shipment_authorized'
                }
            }
        )
    except braintree.exceptions.authorization_error.AuthorizationError:
        # This means that the trucker is not yet approved to be a submerchant
        # What to do: keep the transaction going and keep trying to complete it,
        #   It will get finished when the trucker fiiiinally is accepted
        # Add it to both user's list of transactions
        shipment.shipper.update(push__transactions=transaction)
        shipment.driver.update(push__transactions=transaction, inc__driver_info__unpaid_transactions=round(shipment.trucker_price, ndigits=2))
        # If this fails then that means we have to pay us! Money has to go somewhere!
        try:
            result = braintree.Transaction.sale(
                {
                    "amount": round(Decimal(shipment.price), ndigits=2),
                    "payment_method_nonce": shipment.payment_nonce,
                    "options": {
                        "submit_for_settlement": True
                    },
                    'custom_fields': {
                        'type': 'shipment_unauthorized'
                    }
                }
            )

            print(dir(result))
        except Exception as ex:
            print(ex)

    if result is not None:
        if result.is_success:
            transaction.transaction_id = result.transaction.id
            # Add it to both user's list of transactions
            shipment.shipper.update(push__transactions=transaction)
            shipment.driver.update(push__transactions=transaction)
        else:
            # Add it to both user's list of transactions
            shipment.shipper.update(push__transactions=transaction)
            shipment.driver.update(push__transactions=transaction)
            # If the transaction was not successful, return the reason why
            return False, result.transaction.processor_response_text

    return True


# WEBHOOKS : Braintree notification service
@app.route(base_api_ext + '/braintree/submerchant_hook', methods=['GET', 'POST'])
@app.route(base_api_v1_ext + '/braintree/submerchant_hook', methods=['GET', 'POST'])
@app.route(base_api_v1_1_ext + '/braintree/submerchant_hook', methods=['GET', 'POST'])
def submerchant_hook():
    """
        This is hit when braintree clears drivers as a-ok to be sub-merchants!
    :return:
    """
    if request.method == "GET":
        return braintree.WebhookNotification.verify(request.args['bt_challenge'])

    # POST
    notification = braintree.WebhookNotification.parse(str(request.form['bt_signature']),
                                                       request.form['bt_payload'])

    bt_id = notification.merchant_account.id
    users = ActiveUser.objects(customer_id=bt_id, driver_info__exists=True)
    if len(users) != 1:
        throw_error("No Braintree driver with id: " + bt_id, 404, request, FILE_TAG)

    driver = users[0]

    if notification.kind == braintree.WebhookNotification.Kind.SubMerchantAccountApproved:
        # Todo:  mark it in the books
        # If they have an unpaid register, pay em!
        if driver.driver_info.unpaid_transactions > 0.0:
            result = braintree.Transaction.sale(
                    {
                        "merchant_account_id": bt_id,
                        "amount": round(driver.driver_info.unpaid_transactions, ndigits=2),
                        "payment_method_token": PALLET_PAYMENT_TOKEN,
                        "service_fee_amount": round(Decimal(0.0), ndigits=2),
                        "options": {
                            #"hold_in_escrow": True,
                            # We can only hold in escrow if we onboard ourselves as submerchants
                            # Might be a worthwhile thingeroo
                            "submit_for_settlement": True
                        },
                        'custom_fields': {
                            'type': 'unpaid_balance'
                        }
                    }
            )

            if result.is_success:
                users.update(driver_info__unpaid_transactions=0.00)
            # Todo! What if this fails? Why would it?

        message = make_payment_method_approved_message(driver)
        send_async_mail(message)

        driver.update(driver_info__payment_confirmed=True)
        driver.reload()
        driver.update_account_status()

    elif notification.kind == braintree.WebhookNotification.Kind.SubMerchantAccountDeclined:
        # Todo:  deactivate account?
        # Or just keep the account but mark as inactive
        reason = notification.message
        driver.fields_for_approval.braintree = reason
        driver.save()
        driver.reload()
        message = make_payment_method_declined_message(driver, reason)
        send_async_mail(message)

    return make_gen_success()
