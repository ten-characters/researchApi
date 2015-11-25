import json
import requests
from datetime import datetime
from flask import make_response, request
from flask_testing import LiveServerTestCase
# FUNCTIONS TO TEST
from APP.utility import create_pod
from APP.models import Shipment, ActiveUser, Warehouse, Address

import unittest
from TESTING.unittests.testApp import create_app, app


@app.route('/')
def hello_world():
    return "Hello World"


@app.route('/pod', methods=['GET', 'POST'])
def make_pod():
    data = json.loads(request.form['data'])
    # Find the shipment
    shipment = Shipment.objects.get(data['shipment_id'])
    name = create_pod(shipment, request.files['signature'], data['signee_name'])
    return name


@app.route("/shutdown", methods=['POST'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return json.dumps("we good")


class PodTest(unittest.TestCase):
    def create_app(self):
        app = create_app()
        # app.config['LIVESERVER_PORT'] = 8943
        app.run(port=8943)
        return app

    def createPOD(self):
        # server = self.get_server_url()
        # Need a shipper and two warehouses for shipment creation
        shipper = ActiveUser(
            email='shipper@test.com',
            password='password',
            registered_by='unittest',
            roles=['base_user', 'shipper']
        ).save()
        shipper.reload()

        pickup_address = Address(
            address='',
            city='',
            state='NJ',
            country='USA',
            zip=''
        )
        pickup = Warehouse(
            registered_by_service='unittest',
            registered_by_user=shipper,
            name='',
            location=(42.0, -73.4),
            address=pickup_address,
            primary_email='pickup@test.com'
        ).save()
        
        dropoff_address = Address(
            address='1 Castle Point Terrace',
            city='Hoboken',
            state='NJ',
            country='USA',
            zip='07030'
        )
        dropoff = Warehouse(
            registered_by_service='unittest',
            registered_by_user=shipper,
            name='Stevens',
            location=(42.0, -73.4),
            address=dropoff_address,
            primary_email='dropoff@test.com'
        ).save()

        # Create a shipment
        ref_numbers = {
            'Primary': 'Booking',
            'Booking': '39dosO',
            'Reference': 'JDiOS3'
        }
        shipment = Shipment(
            created_by_service='unittest',
            shipper=shipper,
            price=800,
            trucker_price=600,
            weight=20000,
            is_full_truckload=False,
            num_pallets=10,
            num_pieces_per_pallet=5,
            reference_numbers=ref_numbers,
            pickup_time=datetime.utcnow(),
            pickup_time_end=datetime.utcnow(),
            dropoff_time=datetime.utcnow(),
            dropoff_time_end=datetime.utcnow(),
            start_warehouse=pickup,
            end_warehouse=dropoff,
            payment_nonce='fake-valid-nonce'
        ).save()
        shipment.reload()

        # 
        data = {
            'shipment_id': shipment.id,
            'signee_name': 'Michael Mecca'
        }
        files = {
            'signature': open('images/signature.jpg', 'rb')
        }

        create_pod(shipment, files['signature'], 'Michael Mecca')

        # req = requests.post(server + '/pod', data=data, files=files)

        # assert req.ok

    def doCleanups(self):
        (ActiveUser.objects.get(email='shipper@test.com')).delete()
        (Warehouse.objects.get(primary_email='shipper@test.com')).delete()
        (Warehouse.objects.get(primary_email='shipper@test.com')).delete()
        requests.post(self.get_server_url() + '/shutdown')
        return super().doCleanups()

    def tearDown(self):
        print("Closing test!")


if __name__ == '__main__':
    unittest.main()

'''
def createPOD():
        # server = self.get_server_url()
        # Need a shipper and two warehouses for shipment creation


        pickup_address = Address(
            address='',
            city='',
            state='NJ',
            country='USA',
            zip=''
        )

        shipper = ActiveUser(
            email='shipper3@test.com',
            password='password',
            registered_by='unittest',
            roles=['base_user', 'shipper'],
            billing_info=pickup_address
        ).save()
        shipper.reload()

        pickup = Warehouse(
            registered_by_service='unittest',
            registered_by_user=shipper,
            name='',
            location=(42.0, -73.4),
            address=pickup_address,
            primary_email='pickup3@test.com'
        ).save()

        dropoff_address = Address(
            address='1 Castle Point Terrace',
            city='Hoboken',
            state='NJ',
            country='USA',
            zip='07030'
        )
        dropoff = Warehouse(
            registered_by_service='unittest',
            registered_by_user=shipper,
            name='Stevens3',
            location=(42.0, -73.4),
            address=dropoff_address,
            primary_email='dropoff3@test.com'
        ).save()

        # Create a shipment
        ref_numbers = {
            'Primary': 'Booking',
            'Booking': '39dosO',
            'Reference': 'JDiOS3'
        }
        shipment = Shipment(
            created_by_service='unittest',
            commodity="Cheese",
            shipper=shipper,
            price=800,
            trucker_price=600,
            weight=20000,
            is_full_truckload=False,
            num_pallets=10,
            num_pieces_per_pallet=5,
            reference_numbers=ref_numbers,
            pickup_time=datetime.utcnow(),
            pickup_time_end=datetime.utcnow(),
            dropoff_time=datetime.utcnow(),
            dropoff_time_end=datetime.utcnow(),
            start_warehouse=pickup,
            end_warehouse=dropoff,
            payment_nonce='fake-valid-nonce'
        ).save()
        shipment.reload()

        #
        data = {
            'shipment_id': shipment.id,
            'signee_name': 'Michael Mecca'
        }
        files = {
            'signature': open('images/signature.jpg', 'rb')
        }

        create_pod(shipment, files['signature'], 'Michael Mecca')
createPOD()
'''

# from APP.utility import create_pod
# from APP.models import Warehouse, Shipment, Address, Contact
# @app.route('/test')
# def pod_test():
#     try:
#         (ActiveUser.objects.get(email='shipper@test.com')).delete()
#     except Exception:
#         pass
#     try:
#         (Warehouse.objects.get(primary_email='pickup@test.com')).delete()
#     except Exception:
#         pass
#     try:
#         (Warehouse.objects.get(primary_email='dropoff@test.com')).delete()
#     except Exception:
#         pass
#     try:
#         (Shipment.objects.get(created_by_service='unittest')).delete()
#     except Exception:
#         pass
#
#     # Need a shipper and two warehouses for shipment creation
#     shipper_address = Address(
#         address='846 Fletcher Hill Road',
#         city='Jersey City',
#         state='NJ',
#         country='USA',
#         zip='07310'
#     )
#     shipper = ActiveUser(
#         email='shipper@test.com',
#         password='password',
#         company="Austin's Logistics",
#         phone="8023569513",
#         registered_by='unittest',
#         roles=['base_user', 'shipper'],
#         billing_info=shipper_address
#     ).save()
#     shipper.reload()
#
#     pickup_address = Address(
#         address=' ',
#         city='',
#         state='NJ',
#         country='USA',
#         zip=''
#     )
#     pickup = Warehouse(
#         registered_by_service='unittest',
#         registered_by_user=shipper,
#         name='',
#         location=(42.0, -73.4),
#         address=pickup_address,
#         primary_email='pickup@test.com'
#     ).save()
#
#     pickup_contact = Contact(
#         name='Billy Joe',
#         email='billy@joe.com',
#         phone='8023841913',
#         ext='123'
#     )
#
#     dropoff_address = Address(
#         address='1 Castle Point Terrace',
#         city='Hoboken',
#         state='NJ',
#         country='USA',
#         zip='07030'
#     )
#     dropoff = Warehouse(
#         registered_by_service='unittest',
#         registered_by_user=shipper,
#         name='Stevens',
#         location=(42.0, -73.4),
#         address=dropoff_address,
#         primary_email='dropoff@test.com'
#     ).save()
#
#     dropoff_contact = Contact(
#         name='Joe Billy',
#         email='joe@billy.com',
#         phone='4578361123',
#         ext='123'
#     )
#
#
#     # Create a shipment
#     ref_numbers = {
#         'Primary': 'Booking',
#         'Booking': '39dosO',
#         'Reference': 'JDiOS3',
#         'Pickup': 'SIOCSO',
#         'Dropoff': 'SJDIOj'
#     }
#     shipment = Shipment(
#         created_by_service='unittest',
#         shipper=shipper,
#         price=800,
#         trucker_price=600,
#         commodity="Coffee",
#         weight=20000,
#         is_full_truckload=False,
#         num_pallets=10,
#         num_pieces_per_pallet=5,
#         reference_numbers=ref_numbers,
#         pickup_time=datetime.utcnow(),
#         pickup_time_end=datetime.utcnow(),
#         start_contact=pickup_contact,
#         dropoff_time=datetime.utcnow(),
#         dropoff_time_end=datetime.utcnow(),
#         end_contact=dropoff_contact,
#         start_warehouse=pickup,
#         end_warehouse=dropoff,
#         payment_nonce='fake-valid-nonce'
#     ).save()
#     shipment.reload()
#
#     #
#     data = {
#         'shipment_id': shipment.id,
#         'signee_name': ''
#     }
#     files = {
#         'signature': open('/home/austin/GitRepo/api/APP/temp/signature.jpg', 'rb')
#     }
#
#     new_name = create_pod(shipment, files['signature'], '')
#
#     return make_gen_success()