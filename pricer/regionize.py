__author__ = 'masterFran'

from pricer import HOTSPOT_MILEAGE_THRESHOLD

from geopy import distance
from geopy import Point

from operator import itemgetter


# Built using the handy dandy tool in test.py!
points = [
    {'point': Point(41.37, -75.68, 0.0), 'zip': '18501'},
    {'point': Point(40.2631879, -77.17152279999999, 0.0), 'zip': '17013'},
    {'point': Point(42.6322463, -73.7654367, 0.0), 'zip': '12202'},
    {'point': Point(43.0481645, -76.1473156, 0.0), 'zip': '13202'},
    {'point': Point(41.77210609999999, -72.70380469999999, 0.0), 'zip': '06105'},
    {'point': Point(39.2081349, -75.45777749999999, 0.0), 'zip': '19901'},
    {'point': Point(38.3517112, -81.63364740000002, 0.0), 'zip': '25301'},
    {'point': Point(35.9989632, -78.5887951, 0.0), 'zip': '27587'},
    {'point': Point(33.912446, -80.6992633, 0.0), 'zip': '29044'},
    {'point': Point(33.45, -112.07, 0.0), 'zip': '85001'},
    {'point': Point(41.2819478, -96.2482149, 0.0), 'zip': '68022'},
    {'point': Point(39.36, -74.42999999999999, 0.0), 'zip': '08404'},
    {'point': Point(40.22, -74.74, 0.0), 'zip': '08601'},
    {'point': Point(35.0720392, -106.6466306, 0.0), 'zip': '87101'},
    {'point': Point(35.2045402, -101.8407065, 0.0), 'zip': '79101'},
    {'point': Point(40.7984796, -77.899604, 0.0), 'zip': '16803'},
    {'point': Point(30.4305062, -84.25421949999999, 0.0), 'zip': '32301'},
    {'point': Point(32.2907734, -90.18462170000001, 0.0), 'zip': '39201'},
    {'point': Point(44.14003109999999, -103.1971067, 0.0), 'zip': '57701'},
    {'point': Point(43.6833235, -85.49941919999999, 0.0), 'zip': '49307'},
    {'point': Point(33.76, -84.39, 0.0), 'zip': '30301'},
    {'point': Point(39.42052959999999, -76.79135579999999, 0.0), 'zip': '21117'},
    {'point': Point(33.52, -86.8, 0.0), 'zip': '35201'},
    {'point': Point(42.3548561, -71.0661193, 0.0), 'zip': '02108'},
    {'point': Point(42.89676739999999, -78.8863847, 0.0), 'zip': '14201'},
    {'point': Point(35.0457994, -85.3065281, 0.0), 'zip': '37401'},
    {'point': Point(41.85, -87.64999999999999, 0.0), 'zip': '60290'},
    {'point': Point(39.10663539999999, -84.53632259999999, 0.0), 'zip': '45201'},
    {'point': Point(41.4908027, -81.6726759, 0.0), 'zip': '44101'},
    {'point': Point(39.9705786, -83.03210969999999, 0.0), 'zip': '43216'},
    {'point': Point(32.78, -96.8, 0.0), 'zip': '75260'},
    {'point': Point(41.521107, -90.57188839999999, 0.0), 'zip': '52801'},
    {'point': Point(39.7541032, -105.0002242, 0.0), 'zip': '80202'},
    {'point': Point(42.348495, -83.0602998, 0.0), 'zip': '48201'},
    {'point': Point(29.77, -95.36999999999999, 0.0), 'zip': '77001'},
    {'point': Point(39.7774501, -86.1090119, 0.0), 'zip': '46201'},
    {'point': Point(30.3420008, -81.7691318, 0.0), 'zip': '32099'},
    {'point': Point(39.1041725, -94.5998517, 0.0), 'zip': '64101'},
    {'point': Point(34.7499657, -92.28520139999999, 0.0), 'zip': '72201'},
    {'point': Point(34.0578814, -118.3096648, 0.0), 'zip': '90005'},
    {'point': Point(38.23999999999999, -85.75999999999999, 0.0), 'zip': '40201'},
    {'point': Point(35.0035156, -89.93773089999999, 0.0), 'zip': '37501'},
    {'point': Point(25.7783254, -80.1990136, 0.0), 'zip': '33101'},
    {'point': Point(43.0439776, -87.8991514, 0.0), 'zip': '53202'},
    {'point': Point(44.9836543, -93.2693572, 0.0), 'zip': '55401'},
    {'point': Point(30.69595, -88.04373, 0.0), 'zip': '36601'},
    {'point': Point(36.2722491, -86.7114545, 0.0), 'zip': '37115'},
    {'point': Point(29.95957689999999, -90.0770127, 0.0), 'zip': '70112'},
    {'point': Point(40.73053729999999, -74.1730762, 0.0), 'zip': '07101'},
    {'point': Point(35.47, -97.52, 0.0), 'zip': '73101'},
    {'point': Point(40.6852029, -89.5961698, 0.0), 'zip': '61601'},
    {'point': Point(39.95, -75.17999999999999, 0.0), 'zip': '19092'},
    {'point': Point(40.4737114, -79.9612368, 0.0), 'zip': '15201'},
    {'point': Point(45.505603, -122.6882145, 0.0), 'zip': '97201'},
    {'point': Point(37.56, -77.45, 0.0), 'zip': '23218'},
    {'point': Point(38.58, -121.49, 0.0), 'zip': '94203'},
    {'point': Point(40.7563925, -111.8985922, 0.0), 'zip': '84101'},
    {'point': Point(29.46357, -98.5226706, 0.0), 'zip': '78201'},
    {'point': Point(32.88435520000001, -117.2338066, 0.0), 'zip': '92093'},
    {'point': Point(58.298671, 22.6918273, 0.0), 'zip': '94101'},
    {'point': Point(32.081259, -81.0809848, 0.0), 'zip': '31401'},
    {'point': Point(47.6084921, -122.336407, 0.0), 'zip': '98101'},
    {'point': Point(38.6305392, -90.19282160000002, 0.0), 'zip': '63101'},
    {'point': Point(27.94, -82.45, 0.0), 'zip': '33601'},
    {'point': Point(41.6411077, -83.54366259999999, 0.0), 'zip': '43601'},
    {'point': Point(36.1510884, -95.9945809, 0.0), 'zip': '74101'},
    {'point': Point(36.851849, -76.28013349999999, 0.0), 'zip': '23501'},
    {'point': Point(38.912068, -77.0190228, 0.0), 'zip': '20001'},
    {'point': Point(37.6966286, -97.34132120000001, 0.0), 'zip': '67201'},
    {'point': Point(42.26, -71.8, 0.0), 'zip': '01601'}
]


def closestPoints(point):
    """
    :param point: central point
    :return: the zip of the closest point
    """
    print("Getting closest point!")

    # For finding one point!

    # minDistance = distance.distance(points[0]['point'], point)
    # minIndex = 0
    # for i in range(1, len(points)):
    #     thisDistance = distance.distance(points[i]['point'], point)
    #     if thisDistance.miles < minDistance.miles:
    #         minDistance = thisDistance
    #         minIndex = i
    # return points[minIndex]['zip']

    # For finding multiple!

    # Could add distance straight to the list ^
    points_by_distance = []
    for p in points:
        p.update(distance=(distance.distance(p['point'], point)).miles)
        points_by_distance.append(p)

    # Or we could just use the built in python sorter ...
    sorted_by_distance = sorted(points, key=itemgetter('distance'))

    num_closest_points = 1
    # Find how many points are within x miles
    for i in range(0, len(sorted_by_distance)):
        if sorted_by_distance[i]['distance'] < HOTSPOT_MILEAGE_THRESHOLD:
            # Always have at least one closest point
            if i != 0:
                num_closest_points += 1
        else:
            break

    # Now lets take the top n points and add the weights to make them
    closest_zips = []

    # To find the weight of each point:
    # 1. Sum total distance
    # 2. Flip each point by subtracting individual distance from total
    # 3. Find each percentage of flipped nodes by dividing by the sum of flipped distances
    #       ( (num_closest_points - 1) * total distance)

    # Marginally faster to load into list before summing. The Trade-off: marginally more memory used
    total_distance = sum( [sorted_by_distance[i]['distance'] for i in range(0, num_closest_points)] )

    for i in range(0, num_closest_points):
        p = sorted_by_distance[i]
        if num_closest_points == 1:
            weight = 1
        else:
            weight = (total_distance - p['distance']) / ((num_closest_points - 1) * total_distance)
        closest_zips.append({'zip': p['zip'], 'weight': weight})

    return closest_zips


def regionize(start_lat, start_lng, end_lat, end_lng, num_hotspots=None):
    """
    # How to use regionize:
        regionize(Starting Point, Ending Point)
        Ex: regionize(41.6411077,  -83.54366259999999, 32.081259,  -81.0809848)
        Ex: regionize(41.6411077,  -83.54366259999999, 32.081259,  -81.0809848, num_hotspots=3)

    Should return a list of the n closest hot-spots for both the start and end locations
    Should also return the weight of each hot-spot in determining the price

    We need a list of n points along with weights :)
    aka :
    points = [
        {
            point: Point,
            weight: .8
        },
        ...
        {
            point: Point,
            weight: .1
        }
    ]

    :param start_lat: float
    :param start_lng: float
    :param end_lat: float
    :param end_lng: float
    :return: [[{closest zip to start, weight}, ...], [{closest zip to end, weight}, ...]]
    """

    return [
        closestPoints(Point(start_lat, start_lng)),
        closestPoints(Point(end_lat, end_lng))
    ]


def find_next_closest_zip(current_closest_zip):
    point = None
    for p in points:
        if p['zip'] == current_closest_zip:
            point = p['point']

    if point is None:
        return current_closest_zip

    minDistance = distance.distance(points[0]['point'], point)
    minIndex = 0
    for i in range(1, len(points)):
        thisDistance = distance.distance(points[i]['point'], point)
        # If this is the next closest with
        if thisDistance.miles < minDistance.miles and points[i]['zip'] != current_closest_zip:
            minDistance = thisDistance
            minIndex = i
    return points[minIndex]['zip']



