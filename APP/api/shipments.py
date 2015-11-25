__author__ = 'austin'

import json
from datetime import timedelta, datetime

from APP import base_api_v1_ext, base_api_v1_1_ext, TRUCKER_PERCENTAGE, FIRST_MOVE_PROMO, SHIPMENT_HOURS_OFFER, DEBUG
from APP.models import Contact, Address, Shipment, Warehouse, Transaction
from APP.api.registration import register_warehouse_internally
from APP.utility import *
from APP.email import *
from APP.driverMatcher import start_driver_matcher
from APP.api.upload import upload_internally, delete_s3_file
from flask import jsonify, request, abort, make_response
from mongoengine import DoesNotExist, ValidationError, NotUniqueError
from pymongo.errors import DuplicateKeyError
from APP.api.braintreeEndpoints import create_shipment_transaction, create_promo_transaction

FILE_TAG = __name__

# ------------- SHIPMENTS ----------------- #
@app.route(base_api_v1_ext + '/shipments/unaccepted', methods=['GET', 'PUT'])
@app.route(base_api_v1_1_ext + '/shipments/unaccepted', methods=['GET', 'PUT'])
def get_unaccepted_shipments():
    """ GET UNACCEPTED SHIPMENT LIST
        REQUEST FORMAT:
            /shipments/unaccepted
         Just return a list of shipments:
         [
            {"shipment": {}},
         ]
    """
    auth = check_authentication(req_roles=['driver'])
    if not auth[0]:
        abort(403)

    data = loads(request.data.decode('utf-8'))

    max_returned = None
    try:
        max_returned = data['max_returned']
    except Exception:
        # Leave max_returned
        pass

    rng = None
    try:
        rng = data['rng']
        location = data['location']
    except Exception:
        # Also leave rng as none
        pass

    to_return = []

    if rng is None:
        shipments = Shipment.objects.get_all_unaccepted(max_returned=max_returned)
    else:
        shipments = Shipment.objects.get_unaccepted_in_rng_of(rng,
                                                               location,
                                                               max_returned=max_returned)

    for shipment in shipments:
        to_return.append(shipment.get_returnable_json())

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_response(jsonify(shipments=json.dumps(to_return), new_token=new_token), 200)


@app.route(base_api_v1_ext + '/shipments/add', methods=['POST'])
@app.route(base_api_v1_1_ext + '/shipments/add', methods=['POST'])
def add_shipment():
    """ ADD SHIPMENT
        REQUEST FORMAT:
            /shipments/add
         Just add new shipment
        requires:(request data)
            shipper_id
            start_id or warehouse info ( see @ Warehouse)
            end_id or warehouse info ( " " )
            pickup_time - encoded w/ our special stuff
            dropoff_time - " "
            created_by_service
            price
            commodity
            reference_numbers - (json encoded) dict
            weight
            is_full_truckload - bool
            num_pallets
            num_pieces_per_pallet
            delivery_order - file of appropriate type

            **optional**
            needs_liftgate - bool
            needs_jack jack - " "
            needs_lumper - " "
    """
    auth = check_authentication(form_data={'email': request.form['email'], 'token': request.form['token']})
    if not auth[0]:
        abort(403)
    data = request.form
    datatemp = {}
    try:
        datatemp.update({'start_location': (float(data['start_location_lat']), float(data['start_location_lon']))})
    except KeyError:
        # print('no new start location')
        pass
    try:
        datatemp.update({'end_location': (float(data['end_location_lat']), float(data['end_location_lon']))})
    except KeyError:
        # print('no new end location')
        pass

    shipper = ActiveUser.objects.get_from_email(data['email'])
    if shipper is None:
        throw_error('No shipper by this email: ' + data['email'], 400, request, FILE_TAG)

     # If the warehouse exists, use it! If it does not, register it!
    # Since we have the warehouse name, here is where we search for the warehouse in our database!
    # Attach warehouse object _id to the shipment
    # If no warehouse exists with that name, ok, fine, we won't attach a warehouse id

    # ---- START WAREHOUSE ---- #
    start_contacts_list = []
    # Start by checking if their is a contact included!
    if 'start_contact_name' in data:
        try:
            # Compile contact
            ext = None
            try:
                ext = data['start_contact_ext']
            except KeyError:
                pass

            start_contact = Contact(
                name=data['start_contact_name'],
                email=data['start_contact_email'],
                phone=data['start_contact_phone'],
                ext=ext
            )

            # This is gearing up for adding ?
            start_contacts_list.append(start_contact)
        except (ValidationError, KeyError, DuplicateKeyError, NotUniqueError) as ex:
            throw_error("Couldn't make the start contact!", 400, request, FILE_TAG, exception=ex)
    
    if 'start_id' in data and isinstance(data['start_id'], str):
        # Try to find the warehouse
        try:
            start_warehouse = Warehouse.objects.get(id=data['start_id'])
            
            try:
                start_contact = start_contacts_list[0]
                for contact in start_contacts_list:
                    is_new = True
                    for listed_contact in start_warehouse.contacts_list:
                        if contact.name.lower() == listed_contact.name.lower():
                            is_new = False
                    if is_new:
                        start_warehouse.update(push__contacts_list=contact)
            except IndexError:
                start_contact = start_warehouse.contacts_list[0]
            
        except DoesNotExist:
            throw_error('Trying to ship to a nonexistant warehouse with id: ' + data['start_id'],
                        400, request, FILE_TAG)
    else:
        # Try to compile the warehouse to register it internally
        try:
            # Compile Address
            start_address = Address(
                address=data['start_address'],
                city=data['start_city'],
                state=data['start_state'],
                country=data['start_country'],
                zip=data['start_zip']
            )
        except (ValidationError, KeyError, DuplicateKeyError, NotUniqueError) as ex:
            throw_error("Start address error.", 400, request, FILE_TAG, exception=ex)

        # OPTIONALS
        pickup_instructs = None; dropoff_instructs = None
        if 'start_pickup_instructions' in data and isinstance(data['start_pickup_instructions'], str):
            pickup_instructs = data['start_pickup_instructions']
        if 'start_dropoff_instructions' in data and isinstance(data['start_dropoff_instructions'], str):
            dropoff_instructs = data['start_dropoff_instructions']
        # Import the internal warehouse registration method. It is there for clarity. 
        # Make a compelling case on why its nicer somewhere else and we shall move it move it
        try:
            start_warehouse = register_warehouse_internally(
                data['service'],
                shipper,
                data['start_name'],
                datatemp['start_location'],
                start_address,
                [start_contact],
                pickup_instructions=pickup_instructs,
                dropoff_instructions=dropoff_instructs
            )
        except ValidationError as ex:
            throw_error("Start warehouse internally.", 400, request, FILE_TAG, exception=ex)
        except KeyError as ex:
            throw_error("Start warehouse internally.", 400, request, FILE_TAG, exception=ex)
        except DuplicateKeyError as ex:
            throw_error("Start warehouse internally.", 400, request, FILE_TAG, exception=ex)
        except NotUniqueError as ex:
            throw_error("Start warehouse internally.", 400, request, FILE_TAG, exception=ex)

    # ---- END WAREHOUSE ---- #
    # Now do that exact same thing but for the ending warehouse
    end_contacts_list = []
    if 'end_contact_name' in data:
        try:
            # Compile contact
            ext = None
            try:
                ext = data['end_contact_ext']
            except KeyError:
                pass

            end_contact = Contact(
                name=data['end_contact_name'],
                email=data['end_contact_email'],
                phone=data['end_contact_phone'],
                ext=ext
            )

            end_contacts_list.append(end_contact)

        except (ValidationError, KeyError, DuplicateKeyError, NotUniqueError) as ex:
            throw_error("Couldn't make the end contact!", 400, request, FILE_TAG, exception=ex)

    # Can still add contacts
    if 'end_id' in data and isinstance(data['end_id'], str):
        # Try to find the warehouse
        try:
            end_warehouse = Warehouse.objects.get(id=data['end_id'])
            
            try:
                end_contact = end_contacts_list[0]
                for contact in end_contacts_list:
                    is_new = True
                    for listed_contact in end_warehouse.contacts_list:
                        if contact.name.lower() == listed_contact.name.lower():
                            is_new = False
                    if is_new:
                        end_warehouse.update(push__contacts_list=contact)
            except IndexError:
                end_contact = end_warehouse.contacts_list[0]
                
        except DoesNotExist:
            throw_error('Trying to ship to a nonexistant warehouse with id: ' + data['end_id'],
                        400, request, FILE_TAG)
    else:
        # Try to compile the warehouse to register it internally
        try:
            end_address = Address(
                address=data['end_address'],
                city=data['end_city'],
                state=data['end_state'],
                country=data['end_country'],
                zip=data['end_zip']
            )
        except (ValidationError, KeyError, DuplicateKeyError, NotUniqueError) as ex:
            throw_error("Error while creating end address!", 400, request, FILE_TAG, exception=ex)

        # OPTIONALS
        pickup_instructs = None; dropoff_instructs = None
        # Make a compelling case on why its nicer somewhere else and we shall move it move it
        try:
            end_warehouse = register_warehouse_internally(
                data['service'],
                shipper,
                data['end_name'],
                datatemp['end_location'],
                end_address,
                [end_contact],
                pickup_instructions=pickup_instructs,
                dropoff_instructions=dropoff_instructs
            )
        except (ValidationError, KeyError, DuplicateKeyError, NotUniqueError) as ex:
            throw_error("Error while creating end address!", 400, request, FILE_TAG, exception=ex)

    # Finally we should have our two warehouses. If we don't we should not be here. Get out.

    # Decode the datetime from json and make sure it passed
    pickup_time = json.loads(data['pickup_time'], cls=DateTimeDecoder)
    pickup_time_end = json.loads(data['pickup_time_end'], cls=DateTimeDecoder)
    dropoff_time = json.loads(data['dropoff_time'], cls=DateTimeDecoder)
    dropoff_time_end = json.loads(data['dropoff_time_end'], cls=DateTimeDecoder)

    if pickup_time == "failure" or dropoff_time == "failure":
        abort(400)

    try:
        # Calculate the driver price!
        price = float(data['price'])
        trucker_price = price * TRUCKER_PERCENTAGE
    except TypeError:
        throw_error("Price isn't a float!", 400, request, FILE_TAG)

    try:
        is_full_truckload = (data['is_full_truckload'] == 'True')
    except KeyError:
        throw_error("Key error in full truckload!", 400, request, FILE_TAG)

    try:
        reference_numbers = json.loads(data['reference_numbers'])
    except Exception:
        throw_error("Couldn't parse reference numbers!", 400, request, FILE_TAG)

    # Upload and save the path of the delivery order!
    # Put as far down as possible, should be deleted if the shipment fails validation
    # Hopefully it won't fail after this without being caught
    delivery_order = upload_internally('delivery_order', request.files['delivery_order'])

    # OPTIONAL FIELDS
    liftgate = False; jack = False; lumper = False
    # Accessorial Charges
    try:
        liftgate = (data['needs_liftgate'] == 'True')
        jack = (data['needs_jack'] == 'True')
        lumper = (data['needs_lumper'] == 'True')
    except KeyError as ex:
        throw_error("Key error in accessorial charges!", 400, request, FILE_TAG, exception=ex)

    # Got everything we need! Gather and Go!
    try:
        # Todo: play with these time ranges. Right now it checks if there was a similar shipment in the last 10 minutes
        time_range_upper = pickup_time + timedelta(minutes=5)
        time_range_lower = pickup_time - timedelta(minutes=5)
        potential_duplicates = Shipment.objects(price=price,
                                                shipper=shipper,
                                                reference_numbers=reference_numbers,
                                                pickup_time__lte=time_range_upper,
                                                pickup_time__gte=time_range_lower)
        if len(potential_duplicates) != 0:
            delete_s3_file(delivery_order)
            raise ValidationError("Duplicates found!")

        if DEBUG:
            nonce = 'fake-valid-nonce'
        else:
            nonce = data['payment_nonce']

        shipment = Shipment(
            created_by_service=data['service'],
            price=price,
            trucker_price=trucker_price,
            commodity=data['commodity'],
            reference_numbers=reference_numbers,
            weight=float(data['weight']),
            is_full_truckload=is_full_truckload,
            num_pallets=data['num_pallets'],
            num_pieces_per_pallet=data['num_pieces_per_pallet'],
            start_warehouse=start_warehouse,
            start_contact=start_contact,
            end_warehouse=end_warehouse,
            end_contact=end_contact,
            shipper=shipper,
            payment_nonce=nonce,
            current_holder=start_warehouse,
            pickup_time=pickup_time,
            pickup_time_end=pickup_time_end,
            dropoff_time=dropoff_time,
            dropoff_time_end=dropoff_time_end,
            needs_liftgate=liftgate,
            needs_jack=jack,
            needs_lumper=lumper,
            delivery_order_path=delivery_order
        ).save()
    except ValidationError as ex:
        # Delete the DO!
        delete_s3_file(delivery_order)
        throw_error('ValidationError!', 400, request, FILE_TAG, exception=ex)
    except KeyError as ex:
        delete_s3_file(delivery_order)
        throw_error('KeyError!', 400, request, FILE_TAG, exception=ex)
    except DuplicateKeyError as ex:
        delete_s3_file(delivery_order)
        throw_error('DuplicateKeyError!', 400, request, FILE_TAG, exception=ex)
    except NotUniqueError as ex:
        delete_s3_file(delivery_order)
        throw_error('NotUniqueError!', 400, request, FILE_TAG, exception=ex)

    # We've got the shipper so why not just update them right here?! Whawho!
    shipper.update(push__shipments=shipment)

    # Add the shipment reference to all other parties involved here (cough the warehouses)
    # If the warehouses are currently unmanaged, add the shipments to the warehouse document itself
    # If managed, add to the warehouse manager
    if start_warehouse.manager is not None:
        # Push to managers info
        ActiveUser.objects(id__exact=start_warehouse.manager.id).update_one(push__shipments=shipment)
    start_warehouse.update(push__shipments=shipment)
    
    if end_warehouse.manager is not None:
        # Push to managers info
        ActiveUser.objects(id__exact=end_warehouse.manager.id).update_one(push__shipments=shipment)
    end_warehouse.update(push__shipments=shipment)

    # If we have gotten this far, we have successfully created a new shipment and need to find it a driver
    # Damn this shit is exciting!!!
    # Mr jangles just wanna jangle :(
    pickup_time_offset = shipment.pickup_time - estimate_time_taken_to_find_driver(shipment)
    log(" Pickup offset: " + str(pickup_time_offset) + ". Now: " + str(datetime.utcnow()), FILE_TAG)
    if pickup_time_offset < datetime.utcnow():
        # If we are within the window of the time estimate to find a driver, start offering immediately
        start_driver_matcher(shipment)
    # Otherwise just let the shipmentWatcher deal with it

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_response(jsonify(new_token=new_token, shipment_id=shipment))


@app.route(base_api_v1_ext + '/shipments/favorite/<shipment_id>', methods=['GET', 'PUT'])
@app.route(base_api_v1_1_ext + '/shipments/favorite/<shipment_id>', methods=['GET', 'PUT'])
def favorite(shipment_id):
    """

    :param shipment_id:
    :return:
    """
    auth = check_authentication(req_roles=['driver'])
    if not auth[0]:
            abort(403)
    data = json.loads(request.data.decode('utf-8'))

    driver = ActiveUser.objects.get_from_email(data['email'])
    if driver is None:
        throw_error('No driver by email: ' + data['email'], 404, request, FILE_TAG)
    shipment = Shipment.objects.get(id__exact=shipment_id)
    if shipment is None:
        throw_error('No shipment to favorite: ' + shipment_id, 404, request, FILE_TAG)
    # trolol
    if driver.driver_info:
        # Give the option to unfavorite
        # Just send to the same endpoint and it will be removed! No sass!
        if shipment in driver.driver_info.favorites:
            driver.update(pull__driver_info__favorites=shipment)
        else:
            driver.update(push__driver_info__favorites=shipment)
        driver.save()
    else:
        throw_error("Non Driver user trying to favorite a shipment?!", 404, request, FILE_TAG)

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_gen_success(new_token=new_token)


@app.route(base_api_v1_ext + '/shipments/respond', methods=['PUT'])
@app.route(base_api_v1_1_ext + '/shipments/respond', methods=['PUT'])
def respond_to_shipment_offer():
    """
        REQUEST FORMAT:
            /shipments/accept
            Just needs to mark the shipment as accepted if it is and then
        requires:(request data)
            shipment_id
    """
    auth = check_authentication(req_roles=['driver'])
    if not auth[0]:
        abort(403)
    data = json.loads(request.data.decode('utf-8'))

    if 'shipment_id' not in data or not isinstance(data['shipment_id'], str):
        abort(400)

    try:
        if isinstance(data['response'], bool):
            accept_response = data['response']
        else:
            accept_response = (data['response'] == 'True')
    except KeyError:
        throw_error("Key error in response!", 400, request, FILE_TAG)

    # Make sure the shipment exists and has not already been taken
    try:
        shipment = Shipment.objects.get(id__exact=data['shipment_id'])
    except DoesNotExist:
        throw_error('Trying to respond to an unregistered shipment: ' + data['shipment_id'],
                    400, request, FILE_TAG)

    if shipment.is_accepted:
        raise AlreadyAcceptedException(data['email']
                                       + " is trying to accept an already accepted shipment!")

    # Find the driver and make sure that they exist and are registered
    try:
        driver = ActiveUser.objects.get(email=data['email'], driver_info__exists=True)
        log(driver.email + " is responding to shipment " + str(shipment.id), FILE_TAG)
    except DoesNotExist:
        throw_error(
            'An unregistered driver trying to accept a shipment: ' + data['email'],
            400, request, FILE_TAG)

    if accept_response:
        # ACCEPTED
        # Record that the driver id in the shipment
        shipment.update(
            is_accepted=True,
            is_available=False,
            driver=driver,
            time_accepted=datetime.utcnow())
        shipment.reload()
        # Add the shipment to the drivers list of shipments as well!
        driver.update(push__shipments=shipment)
        # For now we will not offer more than one offer at a time
        driver.update(driver_info__is_active=False)
        driver.save()
        # Send a notification to the start warehouse and shipper, informing them with what they neeeeed

        send_async_mail(make_shipment_info_message(shipment, 'start'))
        send_async_mail(make_shipment_accept_message(shipment))

    else:
        # Add the driver the the rejected list
        shipment.update(push__drivers_rejected=driver)
        shipment.save()
        start_driver_matcher(shipment)

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_gen_success(new_token=new_token)


# Should be called in conjunction with an upload of the first bill of lading
@app.route(base_api_v1_ext + '/shipments/pickup/<string:shipment_id>', methods=['PUT', 'POST'])
@app.route(base_api_v1_1_ext + '/shipments/pickup/<string:shipment_id>', methods=['PUT', 'POST'])
def pickup_shipment(shipment_id):
    """

    :param shipment_id:
    :return:
    """
    data = json.loads(request.form['data'])

    auth = check_authentication(req_roles=['driver'], form_data=data)
    if not auth[0]:
        abort(403)


    shipment = Shipment.objects.get_from_id(shipment_id)
    if shipment is None:
        throw_error('No shipment to pickup: ' + shipment_id, 404, request, FILE_TAG)

    # Now save the bill of lading and save it!
    bol = upload_internally('bill_lading', request.files['file'])

    # Mark that the driver is now the holder of the shipment
    shipment.update(current_holder=shipment.driver)
    shipment.update(is_in_transit=True)
    shipment.update(bill_lading_path=bol)
    shipment.update(time_picked_up=datetime.utcnow())
    # Reloading, because apparently updating wasn't doin dat
    shipment.reload()
    shipment.save()
    # Notify the shipper and the ending warehouse
    send_async_mail(make_shipment_picked_up_message(shipment))
    send_async_mail(make_shipment_info_message(shipment, 'end'))

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_response(jsonify(file_path=bol, new_token=new_token), 200)


@app.route(base_api_v1_ext + '/shipments/finish/<string:shipment_id>', methods=['GET', 'PUT', 'POST'])
@app.route(base_api_v1_1_ext + '/shipments/finish/<string:shipment_id>', methods=['PUT', 'POST'])
def finish_shipment(shipment_id):
    """

    :param shipment_id:
    :return:
    """
    # Should be a multi-part form
    data = json.loads(request.form['data'])

    auth = check_authentication(req_roles=['driver'], form_data=data)
    if not auth[0]:
        abort(403)

    shipment = Shipment.objects.get_from_id(shipment_id)
    if shipment is None:
        throw_error('No shipment to finish: ' + shipment_id, 404, request, FILE_TAG)

    driver = ActiveUser.objects.get_from_id(shipment.driver.id)
    if shipment not in driver.shipments:
        throw_error('Driver does not have access to that shipment', 403, request, FILE_TAG)

    if 'signee_name' not in data:
        throw_error('No signee name in the dropoff request!', 400, request, FILE_TAG)

    if 'signature' not in request.files:
        throw_error('No signature file in the dropoff request!', 400, request, FILE_TAG)

    driver.update(inc__driver_info__total_moves=1)
    if driver.driver_info.total_moves == 1:
        driver.update(inc__driver_info__unpaid_transactions=FIRST_MOVE_PROMO)
        driver.save()

    # Timestamp the dood ! ~ !
    shipment.update(time_finished=datetime.utcnow())

    # Move the shipment from everyone current shipments to finished
    shipper = ActiveUser.objects.get(id__exact=shipment.shipper.id)
    start_warehouse = Warehouse.objects.get(id__exact=shipment.start_warehouse.id)
    end_warehouse = Warehouse.objects.get(id__exact=shipment.end_warehouse.id)

    rel_users = [driver, shipper, start_warehouse, end_warehouse]
    for user in rel_users:
        for i in range(0, len(user.shipments)):
            if user.shipments[i].id == shipment.id:
                user.update(pull__shipments=shipment)
                user.update(push__finished_shipments=shipment)

    # Re-upload the bill of lading with the signature
    # Create a custom pod from a signature image and a name
    try:
        pod = create_pod(shipment, request.files['signature'], data['signee_name'])
    except Exception as ex:
        log_error("Error while creating the pod!", FILE_TAG, exception=ex)

    # Mark that the end warehouse now holds the shipment
    shipment.update(current_holder=end_warehouse)
    # Move to finished_shipments collection
    shipment.update(is_in_transit=False)
    shipment.update(is_finished=True)
    shipment.update(proof_of_delivery_path=pod)
    shipment.update(time_delivered=datetime.utcnow())
    shipment.reload()
    # We can't really switch collections until mongoengine supports
    # querying from other collections as well
    # Todo: May be able to do this with Shipment.switch_collection on the Class object
    # shipment.switch_collection('shipments_finished')
    # shipment.save()
    # shipment.switch_collection('shipments_active')
    # shipment.delete()

    # Notify everyone
    send_async_mail(make_shipment_delivered_message(shipment))
    # '''
    # $$$$$$$$ pay/charge people $$$$$$$$$$ honey honey honey cant u c
    service_fee = shipment.price - shipment.trucker_price
    # print("Service fee is: " + str(service_fee))

    # A new way to charge peep
    try:
        create_shipment_transaction(shipment)
    except Exception as ex:
        # KNOWN BT ERRORS THAT OCCUR
        # Authorization error
        # If the transfer fails for any reason we should log that
        # the driver was not paid
        log_error("Payment transaction failed for: " + str(shipment.id) + "!", FILE_TAG, exception=ex)

    create_promo_transaction(driver)
    driver.reload()
    if len(driver.finished_shipments) == 1:
        # If the driver has just finished their first move, pay their referred user !
        log("The driver: " + driver.email + " has just completed their first move!", FILE_TAG)
        if driver.referral_user is not None:
            # print("Referred by another user!")
            create_promo_transaction(driver.referral_user)

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_gen_success(new_token=new_token)


@app.route(base_api_v1_ext + '/shipments/cancel/<string:shipment_id>', methods=['PUT', 'POST'])
@app.route(base_api_v1_1_ext + '/shipments/cancel/<string:shipment_id>', methods=['PUT', 'POST'])
def cancel_shipment(shipment_id):
    """
        :param data: should be sent in request.data
        :param reason: str, optional to be saved in database
        :param shipment_id: for the database, duh.
        :return:
    """
    auth = check_authentication()
    if not auth[0]:
        abort(403)

    shipper = ActiveUser.objects.get_from_email(json.loads(request.data.decode('utf-8'))['email'])
    shipment = Shipment.objects.get_from_id(shipment_id)

    data = json.loads(request.data.decode('utf-8'))
    reason = data['reason'] if not KeyError and len(data['reason']) < 255 else None

    if shipment is None:
        throw_error('No shipment to finish: ' + shipment_id, 404, request, FILE_TAG)

    # Only allow the shipment to be canceled if it is not already accepted
    # Todo: decide if we need to send an email to the shipper HERE or just
    if shipment.is_accepted:
        # Send speeeecial 600 status code back
        raise AlreadyAcceptedException

    if shipper is None or shipment is None:
        throw_error("Can't find the shipper or the shipment in database.", 404, request, FILE_TAG)

    # Send an email to the warehouse that the shipment was canceled through Pallet
    send_async_mail(make_shipment_canceled_message(shipment, 'shipper'))
    send_async_mail(make_shipment_canceled_message(shipment, 'warehouse'))

    shipment.archive_cancelled(reason=reason)

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_gen_success(new_token=new_token)


@app.route(base_api_v1_ext + '/shipments/get_mine', methods=['GET', 'PUT'])
@app.route(base_api_v1_1_ext + '/shipments/mine', methods=['GET', 'PUT'])
def get_my_shipments():
    """

    :return:
    """
    auth = check_authentication()
    if not auth[0]:
        abort(403)

    try:
        data = loads(request.data.decode('utf-8'))
    except Exception:
        throw_error("Couldn't parse json data!", 400, request, FILE_TAG)

    user = ActiveUser.objects.get_from_email(data['email'])
    shipments = user.shipments

    if 'max' in data and isinstance(data['max'], int):
        max = data['max']
    else:
        max = len(shipments)

    only_current = False
    if 'only_current' in data and isinstance(data['only_current'], bool):
        only_current = data['only_current']

    to_return = []

    for i in range(0, max):
        shipment = Shipment.objects.get_from_id(shipments[i].id)

        if not(only_current and shipment.is_finished):
            to_return.append(shipment.get_returnable_json())
        
    else:
        if max < len(shipments):
            max += 1

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_response(jsonify(result=to_return, new_token=new_token), 200)


@app.route(base_api_v1_ext + '/used_warehouses/get_mine', methods=['GET', 'PUT'])
@app.route(base_api_v1_1_ext + '/warehouse/mine', methods=['GET'])
def get_my_used_warehouses():
    auth = check_authentication()
    if not auth[0]:
        abort(403)

    try:
        data = loads(request.data.decode('utf-8'))
    except Exception:
        throw_error("Couldn't parse json data!", 400, request, FILE_TAG)

    user = ActiveUser.objects.get_from_email(data['email'])
    used_warehouses = user.used_warehouses
    to_return = []
    keys_to_delete = ('date_registered', 'registered_by_service', 'registered_by_user',
                       'manager', 'shipments', 'finished_shipments')
    for warehouse_id in used_warehouses:
        info = Warehouse.objects.get_from_id(warehouse_id)

        for key in keys_to_delete:
            del info[key]
        to_return.append(info)

    try:
        new_token = auth[1]
    except IndexError:
        new_token = None
    return make_response(jsonify(result=to_return, new_token=new_token), 200)




