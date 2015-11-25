# coding=utf-8
__author__ = 'austin'

from datetime import datetime, timedelta

from APP import mongo, bcrypt, serializer
from APP.customQuerySets import ActiveUsersQuery, ShipmentsQuery, WarehouseQuery

db = mongo

FILE_TAG = __name__
TOKEN_EXPIRATION = timedelta(minutes=15)


# SECTION
# ---------- EMBEDDED DOCUMENTS --------- #
class Contact(db.DynamicEmbeddedDocument):
    """ Let's start documenting python like this ! ! !
        To be used in warehouses, like a list of contacts
    """
    name = db.StringField(required=True, max_length=255)
    email = db.StringField(required=True, max_length=40)
    phone = db.StringField(required=True, max_length=20)
    ext = db.StringField(required=False, max_length=10)


class Rating(db.DynamicEmbeddedDocument):
    shipment_id = db.ObjectIdField()
    rated_user_id = db.ObjectIdField()
    rating = db.FloatField(required=False)
    date = db.DateTimeField(default=datetime.utcnow(), required=False)


class Address(db.EmbeddedDocument):
    address = db.StringField(required=True, max_length=255)
    city = db.StringField(required=True, max_length=255)
    state = db.StringField(required=True, max_length=255)
    country = db.StringField(required=True, max_length=255)
    zip = db.StringField(required=True)


class Truck(db.DynamicEmbeddedDocument):
    # Not technically required since embedded
    # But may come back and register trucks in their own collections
    # So if that happens, def def keep this Reference
    # driver = db.ReferenceField('User', required=True)
    plate = db.StringField(required=True, max_length=255)
    year = db.IntField(required=True)
    model = db.StringField(required=True, max_length=255)
    photo_path = db.StringField(required=False, default='')
    photo_thumb_path = db.StringField(required=False, default='')


class Trailer(db.DynamicEmbeddedDocument):
    plate = db.StringField(required=True, max_length=255)
    year = db.IntField(required=True)
    # dry van, flatbed, refer
    # Should stick to dry van for now
    model = db.StringField(required=True, max_length=255)
    model_type = db.StringField(required=True, default="Dry Van")
    # size (53ft, 48, 40, 20)
    size = db.StringField(required=True)
    photo_path = db.StringField(required=False, default='')
    photo_thumb_path = db.StringField(required=False, default='')


class DriverIssue(db.DynamicEmbeddedDocument):
    time_reported = db.DateTimeField(required=False, default=datetime.utcnow())
    location = db.PointField(required=True)
    can_deliver = db.BooleanField(required=True)
    # Only needed if can still deliver
    estimated_delay_hours = db.DecimalField(required=False)


class DriverInfo(db.DynamicEmbeddedDocument):
    """
        How we differential from other accounts
    """
    # ADMIN
    # Add driver id to a collection of active drivers when True
    is_active = db.BooleanField(required=False, default=False)
    orientation = db.FloatField(required=False, default=0.0)
    velocity = db.FloatField(required=False, default=0.0)

    payment_confirmed = db.BooleanField(required=False, default=False)
    # USER ACCESSIBLE

    road_name = db.StringField(required=False, max_length=80, default='')

    dot_number = db.StringField(required=False)
    hut_number = db.StringField(required=False)
    mc_number = db.StringField(required=False)

    # All Documents Pictured and stored in separate collection
    insurance_form_path = db.StringField(required=False, default='')
    license_form_path = db.StringField(required=False, default='')

    # For storing transactions accrued while payment not confirmed
    unpaid_transactions = db.DecimalField(required=False, default=0.00, precision=3)

    # Just some quick stats
    drivers_signed_up = db.IntField(required=False, default=0)
    total_profit = db.FloatField()
    total_moves = db.IntField()

    # Favs
    favorites = db.ListField(db.ReferenceField('Shipment', name='favorites'), required=False)

    # Don't quite trust mongoengines EmbeddedDocumentListField yet
    trucks = db.ListField(db.EmbeddedDocumentField(Truck))
    trailers = db.ListField(db.EmbeddedDocumentField(Trailer))

    issues = db.EmbeddedDocumentListField(DriverIssue, default=[])


# SECTION
# ---------- USERS ------------ #
class User(db.DynamicDocument):
    """
        An overarching account type for everybody!
        Gets more specific as more information is added!

        To find applied users: is_full_account -> boolean
    """
    meta = {'allow_inheritance': True,
            'abstract': True,
            'indexes':
                # Since it's tough to switch and query collections,
                # we will just index the categories. For now
                [
                    'email',
                    'referral_key',
                    'is_full_account'
                ]
            }

    # ONLY FIELDS FOR ADMINS TO SEE
    is_full_account = db.BooleanField(default=False)
    last_login = db.DateTimeField(default=datetime.utcnow())
    last_request = db.DateTimeField(default=datetime.utcnow())
    date_registered = db.DateTimeField(default=datetime.utcnow())
    registered_by = db.StringField(required=True, max_length=255)
    approved_by = db.ReferenceField('User', required=False)

    location = db.PointField(required=False)

    ratings_received = db.EmbeddedDocumentListField(Rating, default=[])
    ratings_given = db.EmbeddedDocumentListField(Rating, default=[])

    shipments = db.ListField(db.ReferenceField('Shipment', name='shipments'), required=False)
    finished_shipments = db.ListField(db.ReferenceField('Shipment', name='finished_shipments'),
                                      required=False)
    # AUTHENTICATION
    email = db.EmailField(required=True, unique=True)
    password = db.StringField(max_length=255, required=True)
    auth_token = db.StringField(max_length=255, default="")
    roles = db.ListField(db.StringField(max_length=255), default=['base_user'])

    # For PUSH NOTIFICATIONS
    # Only for use in active users actually
    # Will be stored locally on the Android device and registered as a broadcast channel
    notification_key = db.StringField(required=False, max_length=80)

    # For password resetting
    reset_hash = db.StringField(required=False, default='')

    # BRAINTREE
    # Could also be used as their personal referral code number
    customer_id = db.StringField(max_length=20)

    # USER ACCESSIBLE
    first_name = db.StringField(required=False, max_length=80, default='')
    road_name = db.StringField(required=False, max_length=80, default='')
    last_name = db.StringField(required=False, max_length=80, default='')
    dob = db.DateTimeField(required=False, default=None)
    phone = db.StringField(required=False, default='')
    ext = db.StringField(required=False, default='')
    billing_info = db.EmbeddedDocumentField(Address, required=False)
    company = db.StringField(required=False, max_length=255, default='')
    # Set the default pictures to those found on the web
    profile_picture_path = db.StringField(required=False, default='default_propic')
    profile_picture_thumb_path = db.StringField(required=False, default='default_propic_thumb')

    # Referrals
    referral_code = db.StringField(required=False, max_length=8)
    referral_user = db.ReferenceField('ActiveUser', required=False)
    num_referred = db.IntField(required=False, default=0)
    users_referred = db.ListField(db.ReferenceField('ActiveUser'), required=False)

    # For linking multiple account types
    # Can check for existence
    driver_info = db.EmbeddedDocumentField(DriverInfo, required=False, default=None)
    # shipper_info = db.EmbeddedDocumentField(ShipperInfo, required=False)
    warehouses = db.ListField(db.ReferenceField('Warehouse'), required=False)
    used_warehouses = db.ListField(db.ReferenceField('Warehouse'), required=False)

    transactions = db.ListField(db.ReferenceField('Transaction'), required=False)

    fields_for_approval = db.DictField()

    # So we can tell if the user is deleted
    # todo: support logging in after deletion as a read-only SUCKA
    def is_active(self):
        return isinstance(self, ActiveUser)

    def is_user_full_account(self):
        return self.is_full_account

    def basic_init(self):
        field_keys = []

        if 'admin' in self.roles:
            field_keys += ['admin']

        if 'shipper' in self.roles:
            field_keys += ['background_check']

        if 'warehouse' in self.roles:
            field_keys += ['background_check']

        if 'driver' in self.roles:
            field_keys += ['license', 'insurance', 'mc_number', 'dot_number', 'braintree']

        #  Will in the future add in keys if they are applying as a warehouse!

        fields = {}
        for key in field_keys:
            fields[key] = "pending_upload"
        self.update(fields_for_approval=fields)
        self.save()

    def has_all_fields(self):
        '''
            Just returns if the user has all the mandatory fields needed for a full account
            :return:
        '''
        has_all = True
        for field in self.fields_for_approval:
            if self.fields_for_approval[field] != 'approved':
                has_all = False
                break
        return has_all

    def update_account_status(self):
        if self.has_all_fields():
            self.update(is_full_account=True)
        else:
            self.update(is_full_account=False)

    def get_id(self):
        return str(self.id)

    def get_roles(self):
        return self.roles

    def get_location(self):
        return self.location['coordinates']

    def get_rating(self):
        # Give them a 5 rating for shits and gigs if they have none
        if len(self.ratings_received) == 0:
            total_rating = 5.0
        else:
            total_rating = 0
            for rating in self.ratings_received:
                total_rating += rating.rating

            total_rating /= len(self.ratings_received)

        return total_rating

    # Get all of the users shipments while popping off vulnerable keys!
    def get_json_shipment_list(self, max=None, only_current=False, only_past=False):
        if max is None or max > (len(self.shipments) + len(self.finished_shipments)):
            max = len(self.shipments)
            max += len(self.finished_shipments)

        to_return = []
        for i in range(0, max):
            try:
                if only_past:
                    raise IndexError
                shipment = Shipment.objects.get_from_id(self.shipments[i].id)
            except IndexError:
                if only_current:
                    break
                # Todo: Should I start a new for loop here, and separate the max?
                # Only start adding finished shipments when all current shipments have been
                # depleted
                if only_past:
                    try:
                        shipment = Shipment.objects\
                            .get_from_id(self.finished_shipments[i].id)
                    except IndexError:
                        if only_past:
                            break
                else:
                    shipment = Shipment.objects\
                        .get_from_id(self.finished_shipments[i - len(self.shipments)].id)

            if shipment is not None:
                to_return.append(shipment.get_returnable_json())
        else:
            if max < len(self.shipments):
                max += 1

        return to_return

    def get_json_used_warehouses_list(self, max=None):
        import json

        if max is None:
            max = len(self.used_warehouses)

        to_return = []
        keys_to_delete = ('date_registered', 'registered_by_service', 'registered_by_user',
                          'shipments', 'finished_shipments')
        # This is silly, mongoengine stores these as references
        # Pretty sure we can just reference the object directly
        # not query again ... like so
        for i in range(0, max):
            info = json.loads(self.used_warehouses[i].to_json())
            for key in keys_to_delete:
                del info[key]

            to_return.append(info)

        # Todo: What does this do ? ? ?
        # Comments people !
        else:
            if max < len(self.used_warehouses):
                max += 1

        return to_return


class ActiveUser(User):
    meta = {'queryset_class': ActiveUsersQuery,
            'collection': 'users_active',
            'indexes':
                # Since it's tough to switch and query collections,
                # we will just index the categories. For now
                [
                    'notification_key'
                ]
            }

    def login(self, password):
        # Get the user object from mongoDB
        if bcrypt.check_password_hash(self.password, password):
            self.last_login = datetime.utcnow()
            # Create a token for them and store it
            self.auth_token = self.make_auth_token()
            self.save()
            return True, self.auth_token
        return False

    def make_auth_token(self):
        # Returns a serialized string containing:
        # Email
        # Last_login
        # An expiration time for the token
        expiration = datetime.utcnow() + TOKEN_EXPIRATION
        to_serialize = [self.email, self.last_login.isoformat(), expiration.isoformat()]
        token = serializer.dumps(to_serialize)
        return token

    def auth_with_token(self, token):
        # Checks against the last token set,
        # Then returns whether they are authenticated and either None or a new auth token
        # Checks to make sure that the auth_token is not the default empty string
        new_token = None
        if self.auth_token != "":
            if token == self.auth_token:
                from dateutil import parser
                # They must be authenticated, or have stolen the token within the last Expiration date
                # serialized data comes in the form [email, last_login, Expiration time]
                # Must decode from isoformat string
                token_data = serializer.loads(token)
                last_login = parser.parse(token_data[1])
                expiration = parser.parse(token_data[2])
                # Take milliseconds off, can be imprecise
                if token_data[0] == self.email and last_login.replace(microsecond=0) == self.last_login.replace(microsecond=0):
                    # Authenticated for sure!
                    self.update(last_request=datetime.utcnow())
                    if expiration < datetime.utcnow():
                        # Needs a new token
                        self.auth_token = self.make_auth_token()
                        self.save()
                    # Todo: Must create a fresh_login_required method to protect such things as updating data
                    return True, self.auth_token
        return False, new_token

# Deprecated 1.1
# class DeletedUser(User):
#     meta = {'collection': 'users_deleted'}
#
#     # Information to keep record of even after the account was deleted
#     # archive database and add these few extra fields dynamically
#     # crawl this collection regularly, deleting those who have been inactive for
#     # and extended period of time
#     date_deleted = db.DateTimeField(default=datetime.utcnow())
#     deleted_by = db.StringField(required=True, max_length=255)
#     reason_deleted = db.StringField(required=True)


# Deprecated 1.1
class UserApplication(User):
    meta = {'collection': 'users_applied'}

    def to_active_user(self):
        user = ActiveUser(
            date_applied=self.date_registered,
            registered_by=self.registered_by,
            location=self.location,
            first_name=self.first_name,
            last_name=self.last_name,
            phone=self.phone,
            ext=self.ext,
            email=self.email,
            password=self.password,
            roles=self.roles,
            billing_info=self.billing_info,
            company=self.company,
            referral_user=self.referral_user,
            driver_info=self.driver_info,
            warehouses=self.warehouses,
            used_warehouses=self.used_warehouses
        )
        return user


# Just for tracking shipments, consisting of a time stamp and location
class BreadcrumbLocation(db.EmbeddedDocument):
    time_stamp = db.DateTimeField(default=datetime.utcnow())
    location = db.PointField(required=True)


# SECTION
# --------- OTHER ---------- #
class Shipment(db.DynamicDocument):
    # Todo: regularly index each collection by most frequent query param
    # Should move active shipments to collection and inactive shipments to collection
    meta = {'queryset_class': ShipmentsQuery,
            'collection': 'shipments',
            'indexes':
                # Since it's tough to switch and query collections,
                # we will just index the categories. For now
                [
                    'is_finished',
                    'is_in_transit',
                    'is_accepted'
                ]
            }

    time_created = db.DateTimeField(required=True, default=datetime.utcnow())
    created_by_service = db.StringField(required=True, max_length=255)

    price = db.FloatField(required=True, min_value=0)
    trucker_price = db.FloatField(required=True, min_value=0)

    weight = db.FloatField(required=True)
    is_full_truckload = db.BooleanField(required=True)
    num_pallets = db.IntField(required=True)
    num_pieces_per_pallet = db.IntField(required=True)

    commodity = db.StringField(required=True, max_length=255)
    reference_numbers = db.DictField(required=True)

    pickup_time = db.DateTimeField(required=True)
    pickup_time_end = db.DateTimeField(required=True)
    dropoff_time = db.DateTimeField(required=True)
    dropoff_time_end = db.DateTimeField(required=True)

    start_warehouse = db.ReferenceField('Warehouse', required=True, default=None)
    start_contact = db.EmbeddedDocumentField(Contact, required=False)

    end_warehouse = db.ReferenceField('Warehouse', required=True, default=None)
    end_contact = db.EmbeddedDocumentField(Contact, required=False)

    # Attached Documents
    # These will be just the location of the files
    bill_lading_path = db.StringField(default="")
    delivery_order_path = db.StringField(default="")
    proof_of_delivery_path = db.StringField(default="")
    proof_of_delivery_number = db.SequenceField()

    # Accessorial Charges
    needs_liftgate = db.BooleanField(default=False)
    needs_jack = db.BooleanField(default=False)
    needs_lumper = db.BooleanField(default=False)

    # FOR OUR USE
    shipper = db.ReferenceField(ActiveUser, required=True)
    payment_nonce = db.StringField(required=True)
    # Must make sure this is only filled with either an ActiveUser or a Warehouse!
    current_holder = db.GenericReferenceField(required=False)
    drivers_rejected = db.ListField(db.ReferenceField(ActiveUser), default=[])

    # To track the shipments, its breadcrumbs yumm
    tracked_locations = db.ListField(db.EmbeddedDocumentField(BreadcrumbLocation), default=[])

    # All reported issues by the driver!
    issues = db.ListField(db.EmbeddedDocumentField(DriverIssue), required=False, default=[])

    # Upon acceptance
    time_accepted = db.DateTimeField(default=None)
    driver = db.ReferenceField(ActiveUser, default=None)

    # Upon finish
    time_finished = db.DateTimeField(default=None)

    # For categorization on the unaccepted shipments list
    is_being_offered = db.BooleanField(default=False)
    is_available = db.BooleanField(default=False)
    is_accepted = db.BooleanField(default=False)
    is_in_transit = db.BooleanField(default=False)
    is_finished = db.BooleanField(default=False)

    # This is only for use in the shipmentWatcher so we don't send multiple emails!
    has_been_warned = db.BooleanField(default=False)

    transaction = db.GenericReferenceField(required=False, default=None)

    def get_returnable_json(self):
        import json
        keys_to_delete = ('drivers_rejected', 'time_created', 'created_by_service',
                      'pickup_time', 'pickup_time_end', 'dropoff_time', 'dropoff_time_end', 'payment_nonce')

        info = json.loads(self.to_json())
        for key in keys_to_delete:
            del info[key]

        # Attach good stuff about the warehouses involved too
        # Todo: stop using json here, it is unnecessary. Look @ how shipper is handled

        pickup_warehouse_json = json.loads(self.start_warehouse.to_json())
        pickup_location = pickup_warehouse_json['location']['coordinates']
        pickup_name = pickup_warehouse_json['name']

        dropoff_warehouse_json = json.loads(self.end_warehouse.to_json())
        dropoff_location = dropoff_warehouse_json['location']['coordinates']
        dropoff_name = dropoff_warehouse_json['name']

        if self.driver:
            info['driver_location'] = self.driver['location']['coordinates']

        info['pickup_location'] = pickup_location
        info['pickup_address'] = pickup_warehouse_json['address']
        info['pickup_name'] = pickup_name
        info['pickup_time'] = self.pickup_time.isoformat()
        info['pickup_time_end'] = self.pickup_time_end.isoformat()
        info['pickup_rating'] = self.start_warehouse.get_rating()
        if self.time_finished:
            info['time_finished'] = self.time_finished.isoformat()
        if self.time_accepted:
            info['time_accepted'] = self.time_accepted.isoformat()

        info['dropoff_location'] = dropoff_location
        info['dropoff_address'] = dropoff_warehouse_json['address']
        info['dropoff_name'] = dropoff_name
        info['dropoff_time'] = self.dropoff_time.isoformat()
        info['dropoff_time_end'] = self.dropoff_time_end.isoformat()
        info['dropoff_rating'] = self.end_warehouse.get_rating()
        info['dropoff_phone'] = "8023569513"# self.end_warehouse.phone

        # fancy fancy greggie
        for i, crumb in enumerate(self.tracked_locations):
            info['tracked_locations'][i]['time_stamp'] = crumb['time_stamp'].isoformat()

        info['shipper_company'] = self.shipper.company
        info['shipper_name'] = self.shipper.last_name
        info['shipper_rating'] = self.shipper.get_rating()

        if self.driver is not None:
            info['driver_rating'] = self.driver.get_rating()

        # troubles pushing adding comment for git change also I like Cake

        # attach the current location
        if isinstance(self.current_holder, Warehouse):
            location = json.loads(Warehouse.objects.get_from_id(self.current_holder.id).to_json())
        else:
            location = json.loads(ActiveUser.objects.get_from_id(self.current_holder.id).to_json())
        location = location['location']['coordinates']

        info['location'] = location

        # timedelta_to_available = self.calc_time_to_available()
        # info['to_available_seconds'] = timedelta_to_available.total_seconds()
        # info['to_available_string'] = str(timedelta_to_available)

        return info

    def get_email_html(self):
        # Todo: in future, account for all possible reference numbers, with: "number" <br/> list
        html = self.get_primary_reference_string() + "<br/>" + \
                "Commodity: " + self.commodity + "<br/>" + \
               "# Pallets: " + str(self.num_pallets) + "<br/>" + \
               "# Piece per Pallet: " + str(self.num_pieces_per_pallet) + "<br/>"
        return html

    def get_primary_reference_string(self):
        return self.reference_numbers['Primary'] + " " + self.get_primary_reference()

    def get_primary_reference(self):
        return self.reference_numbers[self.reference_numbers['Primary']]

    # def calc_time_to_available(self):
    #     """
    #     :param shipment:
    #     :return: timedelta , representing the time until available
    #     """
    #     from APP import SHIPMENT_HOURS_AVAILABLE
    #     return (self.pickup_time - SHIPMENT_HOURS_AVAILABLE) - datetime.utcnow()

    @staticmethod
    def estimate_time_taken_to_find_driver(self):
        """
            If we later want to go and put in a more complicated,
            how much time we will need to offer the shipment
            Depends on the context, like how many drivers are in the area, their response rates, etc.

        :param shipment:
        :return: timedelta , representing an estimate of how many hours we need to find a driver
        """
        from APP import SHIPMENT_HOURS_OFFER
        return SHIPMENT_HOURS_OFFER

    def archive_cancelled(self, reason=None):
        '''

        :param reason:
        :return:
        '''
        self.delete()
        # Since this is a dynamic document we can do whatever the f we want
        self.reason_cancelled = reason
        self.switch_collection('canceled_shipments')
        self.save()

    def archive_unmatched(self):
        '''

        :return:
        '''
        self.delete()
        self.switch_collection('unmatched_shipments')
        self.save()


class Warehouse(db.DynamicDocument):
    """
        How warehouses are represented
    """
    meta = {'queryset_class': WarehouseQuery}
    # Need something to authenticate that this is truly someone's warehouse
    date_registered = db.DateTimeField(default=datetime.utcnow())
    registered_by_service = db.StringField(required=True)
    registered_by_user = db.ReferenceField(ActiveUser, required=True)

    name = db.StringField(required=True, max_length=255, unique=True)
    location = db.PointField(required=True)
    address = db.EmbeddedDocumentField(Address, required=True)

    primary_email = db.EmailField(required=True)

    contacts_list = db.EmbeddedDocumentListField(Contact, default=[])

    ratings_received = db.EmbeddedDocumentListField(Rating, default=[])
    ratings_given = db.EmbeddedDocumentListField(Rating, default=[])

    # OPTIONALS
    pickup_instructions = db.StringField(required=False, max_length=None)
    dropoff_instructions = db.StringField(required=False, max_length=None)
    # So that we can reference and use warehouses even if they aren't controlled by a user
    manager = db.ReferenceField(ActiveUser, required=False, default=None)
    # Only for use in un-linked Warehouses
    # Once linked to a manager, all emails should go through the reference
    shipments = db.ListField(db.ReferenceField(Shipment), required=False)
    finished_shipments = db.ListField(db.ReferenceField(Shipment))

    def get_rating(self):
        # Give them a 5 rating for shits and gigs if they have none
        if len(self.ratings_received) == 0:
            total_rating = 5
        else:
            total_rating = 0
            for rating in self.ratings_received:
                total_rating += rating.rating

            total_rating /= len(self.ratings_received)

        return total_rating

    def get_returnable_json(self):
        import json

        if max is None:
            max = len(self.used_warehouses)

        to_return = []
        keys_to_delete = ('date_registered', 'registered_by_service', 'registered_by_user',
                          'shipments', 'finished_shipments')

        info = json.loads(self.to_json())
        for key in keys_to_delete:
            del info[key]

        to_return.append(info)

        if max < len(self.used_warehouses):
            max += 1

        return to_return


class Transaction(db.DynamicDocument):
    """
        Stored in their own collection, gone through by a script to be taken out of escrow
    """
    meta = {
        'collection': 'transactions',
        'indexes':
        [
            'is_paid',
            'date'
        ]
    }

    date = db.DateTimeField(required=False, default=datetime.utcnow())
    date_released_from_escrow = db.DateTimeField(required=False)
    # Links to the two users !
    user_paid = db.GenericReferenceField(required=False, default=None)
    # When we are paying people, we should do it from an account made
    # specifically for that
    user_charged = db.GenericReferenceField(required=False, default=None)

    shipment = db.GenericReferenceField(required=False, default=None)

    transaction_id = db.StringField(required=False, default=None, max_length=255)

    bt_message = db.StringField(required=False)

    # Two types right now: shipment or promo
    type = db.StringField(required=False)
    amount = db.DecimalField(required=False, default=0.00, precision=3)
    service_charge = db.DecimalField(required=False, default=0.00, precision=3)
    is_paid = db.BooleanField(required=False, default=False)


class DownloadedUser(db.DynamicDocument):
    """
        When a user downloads Pallet and we take their number and email
    """
    meta = {
        'indexes': ['email']
    }
    downloaded_on = db.DateTimeField(required=False, default=datetime.utcnow())
    email = db.StringField(required=True, max_length=255)
    phone = db.StringField(required=True, max_length=255)
    has_been_emailed = db.BooleanField(default=False)


class Log(db.Document):
    """
        We output to the log file as well as storing a lil object
    """
    meta = {'allow_inheritance': True,
            'abstract': True,
            'indexes':
                # Since it's tough to switch and query collections,
                # we will just index the categories. For now
                [
                    'tag'
                ]
            }
    time_found = db.DateTimeField(required=False, default=datetime.utcnow())
    message = db.StringField(required=True)
    data = db.DictField(required=False)
    tag = db.StringField(required=False)


class Error(Log):
    """
        A specific log, when a request turns up a bad result
    """
    time_found = db.DateTimeField(required=False, default=datetime.utcnow())
    message = db.StringField(required=True)
    code = db.IntField(required=False)
    tag = db.StringField(required=False)
    exception = db.StringField(required=False)
    url_request = db.StringField(required=False)
    remote_addr = db.StringField(required=False)
    user_agent = db.StringField(required=False)



