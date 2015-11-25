__author__ = 'austin'

from APP import app, mail, TEMP_MEDIA_FOLDER, base_web_url, PALLET_PHONE_NUMBER, PALLET_EMAIL
from APP.decorators import async
from APP.utility import log_error
from APP.api.upload import download_s3_to_local, delete_local_file

from flask import render_template
from flask_mail import Message

import os

FILE_TAG = __name__


@async
def send_async_mail(message):
    """ Sends the message in the background from our teampallet@gmail.com account! Whopdedooda!
        Builds from Master Fran's email templates found in
    """
    with app.app_context():
        mail.send(message)

# ---- ADMIN STUFF ---- #


def make_generic_email(recipients, header, body, link_text=None, link_url=None):
    """

    :param recipients:
    :param header:
    :param body:
    :param link_text:
    :param link_url:
    :return:
    """
    message = Message(
        header,
        sender=PALLET_EMAIL,
        recipients=recipients)
    message.html = render_template('baseEmail.html', header=header, message_body=body,
                                   button_text=link_text, button_link=link_url)
    return message


def make_admin_error_email(error_header, error_code, error_message, url, data):
    """

    :param error_header:
    :param error_code:
    :param error_message:
    :param url:
    :param data:
    :return:
    """
    message = Message(
        error_header,
        sender=PALLET_EMAIL,
        recipients=['devteam@truckpallet.com'])

    message_body = "We got an error: {error_code}. It came with this message: {error_message}. It " \
                   "came from this endpoint: {url}. It had this data: {data}. Either we fucked up or they " \
                   "fucked up. Either way peeple, let's fix it. " \
                   "Sincerely," \
                   "Api".format(error_code=error_code, error_message=error_message, url=url, data=data)
    message.html = render_template('baseEmail.html', name="Dev", header='ALERT ALERT ALERT', message_body=message_body)
    return message


# ---- NOT ADMIN STUFF ---- #
def make_application_approved_message(user_obj):
    """ To send when an application is accepted
        General Form:
            Hi there [name],
                Your Pallet account has been activated. Head to [either app or website]
                to start moving.

            Keep moving,

            Team Pallet
            www.truckpallet.com
    """
    redirect = "http://www.truckpallet.com"
    if 'driver_info' in user_obj:
        redirect = "http://play.google.com/store/apps/details?id=com.truckpallet.pallet"
    message = Message(
        'Pallet Approved!',
        sender=PALLET_EMAIL,
        recipients=[user_obj.email])

    header = 'Welcome to Pallet'
    message_body = "Thanks for your application, it has been approved and your Pallet account has been activated."
    button_text = "Start Moving"

    message.html = render_template('baseEmail.html', name=user_obj.first_name, header=header, message_body=message_body, button_link=redirect, button_text=button_text)

    return message


def make_application_rejected_message(user_obj, reason):
    """ To send when an application is rejected
        General Form:
            Hi there [name],
                We are sorry to say that your Pallet application wasn't accepted, for now.
                We will let you know if our policies change, and please reply if we have
                made a mistake. Or just to talk. Our number is:
                [Reason]

            Best,

            Team Pallet
            www.truckpallet.com

        :param user_obj:
        :param reason:
        :return:
    """
    from APP import PALLET_PHONE_NUMBER
    message = Message(
        'Pallet Response',
        sender=PALLET_EMAIL,
        recipients=[user_obj.email])
    message_body = " We are sorry to say that your Pallet application was not accepted, for now." \
                   " The reason being {reason}." \
                   " We will let you know if our policies change, and please reply if we have" \
                   " made a mistake. Or just to talk. Our number is: {pallet_number}" .format(reason=reason,
                                                                              pallet_number=PALLET_PHONE_NUMBER)

    message.html = render_template('baseEmail.html', name=user_obj.first_name, message_body=message_body)

    return message


def make_application_thankyou_message(user_app_obj):
    """

    :param user_app_obj:
    :return:
    """
    message = Message(
        'Thank you for your application!',
        sender=PALLET_EMAIL,
        recipients=[user_app_obj.email])

    message_body = "We received your application and are processing it now. We will " \
                   "be in touch as soon as we are ready for freight!"

    message.html = render_template('baseEmail.html', name="", message_body=message_body)

    return message


def make_no_local_drivers_warning_message(shipment):
    """

    :param shipment:
    :return:
    """
    from APP import PALLET_PHONE_NUMBER
    from APP.models import ActiveUser
    shipper = ActiveUser.objects.get_from_id(shipment.shipper.id)
    message = Message(
        "Can't find local drivers for " + shipment.get_primary_reference_string(),
        sender=PALLET_EMAIL,
        recipients=[shipper.email]
    )
    message_body = " This is a notice about your shipment {shipment_ref}." \
                   " We are actively looking for a driver, but want to be absolutely transparent as we approach the pickup time." \
                   " We will notify you immediately if we find one. " \
                   " Thank you for using Pallet the way freight is moving. " \
                   " Our number is: {pallet_number}".format(shipment_ref=shipment.get_primary_reference_string(),
                                                                              pallet_number=PALLET_PHONE_NUMBER)

    message.html = render_template('baseEmail.html', name=shipper.first_name, message_body=message_body)

    return message


def make_no_drivers_message(shipment):
    """

    :param shipment:
    :return:
    """
    from APP import PALLET_PHONE_NUMBER
    from APP.models import ActiveUser
    shipper = ActiveUser.objects.get_from_id(shipment.shipper.id)
    message = Message(
        "Can't find local drivers for " + shipment.get_primary_reference_string(),
        sender=PALLET_EMAIL,
        recipients=[shipper.email]
    )
    message_body = " We couldn't find any drivers to take your shipment {shipment_ref}." \
                   " We are greatly sorry for any inconvenience, please let us know what we can do better next time. " \
                   " We hope you understand that we are new and still growing, but we are growing quickly to provide the best for you." \
                   " Thank you for using Pallet, the way freight is moving. " \
                   "Our number is: {pallet_number}".format(shipment_ref=shipment.get_primary_reference_string(),
                                                                              pallet_number=PALLET_PHONE_NUMBER)

    message.html = render_template('baseEmail.html', name=shipper.first_name, message_body=message_body)

    return message


# SECTION #
# SHIPMENT STATUS UPDATES
def make_shipment_info_message(shipment, recipient):
    """ Create and return a simple html email message
        To be sent to the starting warehouse for them to create the Bill of Lading
        General Form:
            Hey [Warehouse name],
                [Shipper name] has listed a shipment from your warehouse.
                Shipment:
                [Shipment info]
                [Driver Last Name] is on route to pick up at [Pickup Time]
    
                This shipment was coordinated through Pallet. Sign up for Pallet and
                we will give you free money. 3% of every transaction to be exact.
    
            Keep moving,
    
            The Pallet Team
            www.truckpallet.com

        :param shipment:
        :param recipient:
        :return:
    """
    from APP.models import Warehouse, ActiveUser
    # Get the warehouses email:
    if recipient == 'start':
        warehouse = Warehouse.objects.get(id__exact=shipment.start_warehouse.id)
        arrival_time = shipment.pickup_time

        try:
            delivery_order_file = open(download_s3_to_local(shipment.delivery_order_path))
        except FileNotFoundError as ex:
            log_error("Can't find delivery order with path: " + shipment.delivery_order_path, FILE_TAG, exception=ex)
            delivery_order_file = None
    else:
        warehouse = Warehouse.objects.get(id__exact=shipment.end_warehouse.id)
        arrival_time = shipment.dropoff_time
    # Get the shipments new driver

    driver = ActiveUser.objects.get(id__exact=shipment.driver.id)
    shipper = ActiveUser.objects.get(id__exact=shipment.shipper.id)

    shipper_name = shipper.first_name + ' ' + shipper.last_name

    message = Message(
        'New Shipment',
        sender=PALLET_EMAIL,
        recipients=[warehouse.primary_email])

    # Compile the shipment info
    shipment_html = shipment.get_email_html()

    if shipment.needs_liftgate:
        shipment_html += "Needs a lift gate. "
    if shipment.needs_jack:
        shipment_html += "Needs a jack. "
    if shipment.needs_lumper:
        shipment_html += "Needs a lumper. "

    text = "{shipper_name} has listed a shipment from your warehouse." \
           + shipment_html + \
           " {driver_name} is on route to arrive at {arrival_time}. "

    message_body = text.format(warehouse_name=warehouse.name, shipper_name=shipper_name, driver_name=driver.last_name, arrival_time=arrival_time)

    message.html = render_template('baseEmail.html', name=shipper.first_name, message_body=message_body, header="New Shipment")

    if recipient == 'start' and delivery_order_file is not None:
        # Need to split the extension off so the email gets through aight
        name, ext = os.path.splitext(delivery_order_file.name)
        message.attach(delivery_order_file.name, 'image/' + ext, delivery_order_file.read())
        # Todo: Are these files deleted when read? Can we delete them after attaching?
        # delete_local_file(delivery_order_file.name, quiet=True)

    return message


def make_shipment_accept_message(shipment):
    """
        Create and return a simple html email message
        To be sent to the Shipper upon their freight being accepted
        General Form:
            Hi there [Shipper name],
                [Driver Last Name] is on route to pick up at [Pickup Time]

            Keep moving,

            Team Pallet
            www.truckpallet.com

    :param shipment:
    :return:
    """
    # Get the shipments new driver
    driver = shipment.driver
    shipper = shipment.shipper
    shipper_name = shipper.first_name + '' + shipper.last_name
    message = Message(
        'Shipment Accepted',
        sender=PALLET_EMAIL,
        recipients=[shipper.email])

    message_body = '{driver_name} is on route to pick up {shipment_ref} at {pickup_time}.'.format(shipper_name=shipper_name,
                                                                              driver_name=driver.last_name,
                                                                              shipment_ref=shipment.get_primary_reference_string(),
                                                                              pickup_time=shipment.pickup_time)

    message.html = render_template('baseEmail.html', name=shipper_name, message_body=message_body, header="Shipment Accepted")

    return message


def make_shipment_canceled_message(shipment, recipient):
    """

    :param shipment:
    :param recipient:
    :return:
    """
    if recipient == 'shipper':
        from APP.models import ActiveUser
        user = ActiveUser.objects.get(id__exact=shipment.shipper.id)
        name = user.first_name
        email = user.email
        update = " The shipment {shipment_ref} has been canceled in the Pallet system by the shipper." \
                 " They may still be in touch with you, but the shipment can no longer be monitored by us.".format(shipment_ref=shipment.get_primary_reference_string())
    else:
        from APP.models import Warehouse
        user = Warehouse.objects.get(id__exact=shipment.start_warehouse.id)
        name = user.name
        email = user.primary_email
        update = " The shipment {shipment_ref} has been canceled in the Pallet system by the shipper." \
                 " Thank you for using our system, give us a call or email if we can do it better.".format(shipment_ref=shipment.get_primary_reference_string())

    message = Message(
        'Shipment Canceled',
        sender=PALLET_EMAIL,
        recipients=[email]
    )

    message_body = " {update}  Our number is: {pallet_number}".format(update=update,  pallet_number=PALLET_PHONE_NUMBER)

    message.html = render_template('baseEmail.html', name=name, message_body=message_body, header="Shipment Canceled")

    return message


def make_shipment_picked_up_message(shipment):
    """

    :param shipment:
    :return:
    """
    from APP import PALLET_PHONE_NUMBER
    from APP.models import ActiveUser
    shipper = ActiveUser.objects.get(id__exact=shipment.shipper.id)

    message = Message(
        'Shipment Picked Up!',
        sender=PALLET_EMAIL,
        recipients=[shipper.email]
    )

    message_body = " The shipment {shipment_ref} has been picked up!" \
                   " Thank you for using our system, the way freight is moving. " \
                   "Our number is: {pallet_number}. Feel free to call, email, anything. ".format(shipment_ref=shipment.get_primary_reference_string(),
                                                                              pallet_number=PALLET_PHONE_NUMBER)

    message.html = render_template('baseEmail.html', name=shipper.first_name, message_body=message_body, header="Shipment Picked Up")

    return message


def make_shipment_delivered_message(shipment):
    """

    :param shipment:
    :return:
    """
    from APP.models import Warehouse, ActiveUser
    shipper = ActiveUser.objects.get(id__exact=shipment.shipper.id)
    start_warehouse = Warehouse.objects.get(id__exact=shipment.start_warehouse.id)
    
    message = Message(
        'Shipment Delivered!',
        sender=PALLET_EMAIL,
        recipients=[shipper.email, start_warehouse.primary_email]
    )
    
    message_body = " The shipment {shipment_ref} has been delivered! " \
                   " You will now be charged, but your funds will be held for three days. If there is a problem, " \
                   "please get in contact and we will resolve it immediately. " \
                   " Thank you for using our system, the way freight is moving. " \
                   "Our number is: {pallet_number}. Feel free to call, email, anything. ".format(shipment_ref=shipment.get_primary_reference_string(),
                                                                              pallet_number=PALLET_PHONE_NUMBER)

    message.html = render_template('baseEmail.html', name=shipper.first_name, message_body=message_body, header="Shipment Delivered")
    return message


# SECTION
# ISSUES
def make_issue_message(shipment, issue, notify_us=False):
    """

    :param shipment:
    :param issue:
    :param notify_us:
    :return:
    """
    from pygeocoder import Geocoder, GeocoderError

    # Compile necessary info
    customer = shipment.shipper

    if shipment.is_in_transit:
        warehouse = shipment.end_warehouse
    else:
        warehouse = shipment.start_warehouse

    try:
        address_geocoded = Geocoder.reverse_geocode(
            issue.location[0], issue.location[1]
        )
        print(address_geocoded)
        address = address_geocoded.formatted_address
    except Exception as ex:
        address = str(issue.location)

    if notify_us:
        recipients = [customer.email, warehouse.primary_email, PALLET_EMAIL]
    else:
        recipients = [customer.email, warehouse.primary_email]
    message = Message(
        'Issue with ' + shipment.get_primary_reference_string(),
        sender='Application',
        recipients=recipients
    )

    extra = None
    if not shipment.is_in_transit:
        extra = " We are attempting to find you a new driver immediately. "

    if issue.can_deliver:
        message_body = " There has been an issue reported in transit for the shipment: " \
                       " {extra} " \
                       "  {shipment} " \
                       " Your freight is currently at: {address} " \
                       " The trucker estimates a delay of {delay} hours. " \
                       " You can log onto the website to view the location anytime." \
                       "Our number is: {pallet_number}. Feel free to call, email, anything. ".format(shipment=shipment.get_primary_reference_string(),
                                                                                                     extra=extra,
                                                                                                     address=address,
                                                                                                      delay=issue.estimated_delay_hours,
                                                                                                      pallet_number=PALLET_PHONE_NUMBER)
    else:
        message_body = " There has been an issue reported in transit for the shipment: " \
                   "  {shipment} " \
                   " Your freight is currently at: {address} " \
                   " The trucker reports that he can not still deliver today. " \
                   " We greatly apologize and are working to reroute your shipment," \
                   " please call us if you would like a different course of action. " \
                   " Our number is: {pallet_number}. ".format(shipment=shipment.get_primary_reference_string(),
                                                                              address=address,
                                                                              delay=issue.estimated_delay_hours,
                                                                              pallet_number=PALLET_PHONE_NUMBER)

    message.html = render_template('baseEmail.html', name=customer.first_name, message_body=message_body, header="Issue with Shipment")

    return message


# SECTION #
# PAYMENTS #
def make_payment_method_approved_message(user):
    """

    :param user:
    :return:
    """
    message = Message(
        'Payment Approved!',
        sender=PALLET_EMAIL,
        recipients=[user.email]
    )
    header = 'Payment Approved'
    message_body = "Your payment method has been approved! You're good to start moving! Thanks for using our system, " \
                   "the way freight is moving. Our number is: {pallet_number}. " \
                   "Feel free to call, email, anything.".format(pallet_number=PALLET_PHONE_NUMBER)

    message.html = render_template('baseEmail.html', name=user.first_name, header=header, message_body=message_body)

    return message


def make_payment_method_declined_message(user, reason):
    """

    :param user:
    :param reason:
    :return:
    """
    message = Message(
        'Payment Declined',
        sender=PALLET_EMAIL,
        recipients=[user.email]
    )

    header = 'Payment Declined'
    message_body = "Unfortunately, your payment method has been declined. The reason supplied by our payment processor is {reason}." \
                   " We'd love to have you fix it and enter it again when ready. " \
                   "Our number is: {pallet_number}. Feel free to call, email, anything.".format(reason=reason, pallet_number=PALLET_PHONE_NUMBER)

    message.html = render_template('baseEmail.html', name=user.first_name, header=header, message_body=message_body)

    return message


def make_password_reset_message(user, reset_hash):
    """

    :param user:
    :param reset_hash:
    :return:
    """
    message = Message(
        'Reset Password',
        sender=PALLET_EMAIL,
        recipients=[user.email]
    )

    web_reset_url = base_web_url + '/reset?hash=' + reset_hash

    header = 'Password Reset'
    message_body = "You've requested a password change. Please click the button to reset it. If you did " \
                   "not mean to request a change, please ignore this, you're password will not change."

    message.html = render_template('baseEmail.html', name=user.first_name, header=header, message_body=message_body,
                                   button_link=web_reset_url, button_text='Reset')

    return message


def make_password_reset_success(user):
    """

    :param user:
    :return:
    """
    message = Message(
        'Reset Password',
        sender=PALLET_EMAIL,
        recipients=[user.email]
    )

    header = 'Password Reset Success'
    message_body = "You've successfully changed your password. If this was not you're doing, please contact us."

    message.html = render_template('baseEmail.html', name=user.first_name, header=header, message_body=message_body)

    return message