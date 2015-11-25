__author__ = 'austin'

from mongoengine import QuerySet, DoesNotExist


# ToDo: copy format from drivers in range of
class ShipmentsQuery(QuerySet):
    def get_from_id(self, id):
        return self.filter(id__exact=id).first()

    # RANGE IS IN METERS
    def get_unaccepted_in_rng_of(self, rng, location, max_returned=None):
        from APP.models import Warehouse
        # Since all shipments start in a warehouse, just query for the nearby warehouses
        # and then check their shipments
        warehouses = Warehouse.objects(location__near=location, location__max_distance=rng)
        shipments = []
        for warehouse in warehouses:
            ws = warehouse['shipments']
            for shipment in ws:
                if not shipment['is_accepted']:
                    shipments.append(shipment)
                    if max_returned is not None:
                        # Only allow the max returned number to be added to list
                        if len(shipments) >= max_returned:
                            break
        return shipments

    def get_all_unaccepted(self, max_returned=None):
        shipments = self.filter(is_accepted=False, is_being_offered=False)
        to_return = []

        if max_returned is None:
            # If none supplied, return em all!
            max_returned = len(shipments)

        for i in range(0, max_returned):
            to_return.append(shipments[i])

        return to_return


class ActiveUsersQuery(QuerySet):
    def get_from_id(self, id):
        try:
            return self.filter(id__exact=id).first()
        except (DoesNotExist, AttributeError):
            return None

    def get_from_email(self, email):
        try:
            user = self.filter(email=email.lower()).first()
            return user
        except (DoesNotExist, AttributeError):
            return None

    '''
        Given both a range and a location and sifts through.
        Rng - (int, float) IN METERS
        Location - (list, tuple) of floats or ints LAT/LNG Coordinates
    '''
    def get_drivers_in_rng_of(self, rng, location):
        from APP.utility import miles_to_meters
        from pymongo import errors
        try:
            drivers = self.filter(driver_info__exists=True, driver_info__is_active=True,
                              location__near=location, location__max_distance=miles_to_meters(rng))
        except errors.OperationFailure:
            return []

        truckers = []
        for driver in drivers:
            truckers.append(driver)
        return truckers

    def get_all_available(self):
        return self.filter(driver_info__exists=True, driver_info__is_active=True)

    def get_all_drivers(self):
        drivers = self.filter(driver_info__exists=True)
        return drivers

    # Todo:
    def get_drivers_by_rating(self):

        return None

        # Todo: create stats queries for admin analysis


class WarehouseQuery(QuerySet):
    def get_from_id(self, id):
        try:
            return self.filter(id__exact=id).first()
        except DoesNotExist:
            return None

    def get_from_email(self, email):
        try:
            return self.filter(email=email.lower()).first()
        except DoesNotExist:
            return None
