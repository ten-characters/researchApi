__author__ = 'austin'

from requests import put, get, post, delete
from TESTING.testData import *
# base_url = 'https://api.truckpallet.com'  # production AH
# base_url = 'https://test.truckpallet.com/api'  # testing
# base_url = 'http://localhost:8000/api' # local testing
base_url = 'http://localhost:8000' # local
base_url_v1 = base_url + "/v1.0"
base_url_v1_1 = base_url + "/v1.1"

driver_files = {
    'insurance': open('insurance.jpg', 'rb'),
    'license': open('license.jpg', 'rb'),
    'truck': open('truck.jpg', 'rb'),
    'trailer': open('trailer.jpg', 'rb')
}

# Admin login
# admin_login = post(base_url + '/login', data=adminLoginData)
# testAdminEmail['email'] = json.loads(adminLoginData)['email']
# testAdminEmail['token'] = admin_login.json()['token']
# testAdminEmail = json.dumps(testAdminEmail)


responses = [
    # post(base_url_v1 + "/register/interest")
    # post(base_url_v1 + "/register/interest", data=newInterestData)
    # post(base_url_v1 + "/register/warehouse", data=newWarehouseData)
    # post(base_url_v1 + "/register/user/warehouse", data=newStartWarehouseManagerData)
    # post(base_url_v1 + "/register/user/warehouse", data=newEndWarehouseManagerData)
    # post(base_url_v1 + "/register/user/shipper", data=newShipperData)
    # post(base_url_v1 + "/apply/user/shipper", data=newShipperData)
    # put(base_url_v1 + "/apply/decision/558984eded98551813b3d17b", data=acceptApplicationData)
    # post(base_url + "/apply/user/driver", data=newDriverData, files=driver_files)
    # post(base_url_v1 + "/register/truck", data=newTruckData)
    # post(base_url_v1 + "/register/trailer", data=newTrailerData)
    # post(base_url_v1 + "/shipments/add", data=newShipmentData)
    # get(base_url_v1 + "/shipments/unaccepted")
    # put(base_url_v1 + '/shipments/respond', data=acceptShipmentRequest)
    # delete(base_url_v1 + "/account/delete/55785428e6fc8c1c9c55dad3", data=deleteRequest)
    # get(base_url_v1 + "/applications")
    # post(base_url_v1 + '/admin/shutdown'
    # get(base_url_v1 + "/drivers", data=getDriversData)
    # get(base_url_v1 + '/')
    # put(base_url_v1 + '/shipments/finish/5580768ce6fc8c405920311b')
    # get(base_url_v1 + '/me')
    # post(base_url + '/login', data=loginDataServe)
    # post(base_url_v1 + '/admin/add', data=newAdminData)
    # post(base_url + '/apply/user', data=newAdminData)
    # put(base_url_v1 + '/apply/decision/83839', data=testAuth)
    # get(base_url_v1 + '/shipments/get_mine', data=getMineData)
    # get(base_url_v1 + '/drivers', data=json.dumps({'rng': 200, 'location': [40.731225, -74.038707]}))
    # post(base_url_v1 + '/account/reset', data=testReset)

    # post(base_url_v1 + '/downloaded_user', data=testDownloaded),
    # get(base_url_v1 + '/downloaded_user/autin@gmail.com'),
    #
    # get(base_url_v1 + '/admin/downloaded_user_list/json', data=testAdminEmail),
    # post(base_url_v1 + '/admin/send_email_to', data=testAdminEmail)
    put(base_url_v1_1 + '/admin/mongo/update', data=adminPasswordData)
]


def create_mecca_drivers(start, end):
    for i in range(start, end+1):
        test_email = "mecca{num}@test.com".format(num=i)
        driver_data = newDriverData
        driver_data.update(email=test_email)
        request = post(base_url + "/apply/user", data=driver_data, files=driver_files)
        print("Worked? " + str(request.ok))
        if not request.ok:
            print(request.json())

from pprint import pprint

for r in responses:
    try:
        pprint(str(r.url) + ": " + str(r.json()))
        # downloaded = r.json()['downloaded_users']
    except ValueError:
        pprint(r)

# unique = []
# for u in downloaded:
#     u = json.loads(u)
#     if u['phone'] not in unique:
#         unique.append(u['phone'])
# print(len(unique))

create_mecca_drivers(1, 2)
