__author__ = 'austin'
# Crawls gasbuddy websites and concatenates gas prices from their crazy system of divs
# Future Updates:
# Allow to only get top x numberof prices
# Will write a mirror crawler that only crawls for the average prices

import time
from datetime import datetime, timedelta

from fuelCrawler.resources import state_urls_to_crawl, lowest_search_frequency

class Price():
    """
        Price : Float
        Station : {Name : string, Address: string}
        Location : {State: string, Area: string}
        Time Recorded: datetime
    """
    def __init__(self, price=None, station=None, location=None, time_recorded=None):
        if price is None:
            self.price = 0
        else:
            self.price = price
        if station is None:
            self.station = {"Name": "", "Address": ""}
        else:
            self.station = station
        if location is None:
            self.location = {"State": "", "Area": ""}
        else:
            self.location = location
        if time_recorded is None:
            self.time_recorded = datetime.now()
        else:
            self.time_recorded = time_recorded


def buildPrice(price_div):
    new_price = 0
    multiplier = 1
    for word in price_div:
        if str(word) == '<div class="p1"></div>':
            new_price += 1 * multiplier
        elif str(word) == '<div class="p2"></div>':
            new_price += 2 * multiplier
        elif str(word) == '<div class="p3"></div>':
            new_price += 3 * multiplier
        elif str(word) == '<div class="p4"></div>':
            new_price += 4 * multiplier
        elif str(word) == '<div class="p5"></div>':
            new_price += 5 * multiplier
        elif str(word) == '<div class="p6"></div>':
            new_price += 6 * multiplier
        elif str(word) == '<div class="p7"></div>':
            new_price += 7 * multiplier
        elif str(word) == '<div class="p8"></div>':
            new_price += 8 * multiplier
        elif str(word) == '<div class="p9"></div>':
            new_price += 9 * multiplier
        elif str(word) == '<div class="p0"></div>':
            new_price += 0 * multiplier
        # with each level of div inside the price, number moves a decimal further to the right
        # print("Moving down a level!")
        if str(word) != '<div class="pd"></div>':
            multiplier *= .1

    return round(new_price, 4)


def separateStations(station_divs):
    """
    Stores station names and addresses and returns an list of small dictionaries
    """
    stations = []
    for tag in station_divs:
        name = tag.findNext('a').text
        address = tag.findNext('dd').text
        stations.append({"Name": name, "Address": address})
    return stations


def separateTimes(time_divs):
    """
        Could run a slightly more complex parser to store the exact hh:mm
            but we do not really need that specific of information
        Might consider a less loopy way but the overall load shouldn't be too great
            as the times are never more than 20 characters long,
            especially if we update often so that each update contains less information to parse through

        TODO:
            Account for different time zones once we branch out of the US east coast
    """
    times = []
    for tag in time_divs:
        parsed_num = []
        for char in tag.text:
            try:
                parsed_num.append(int(char))
            except ValueError:
                pass
                # Not a number so don't add!
                # Important not to use pass when trying a large amount of code
                # Potentially opens up to a hack if they can time an exception in the try block
                # Lol @ austin 2k15 ^

        delta_time = 0
        for i in range(1, len(parsed_num) + 1):
            delta_time += ((10 ** (len(parsed_num) - i)) * parsed_num[i-1])

        ''' for say num [1,4] with len = 2 should = 14
         => add (10 ^ (len-i)) * num[i-1]
            example loop:
                i = 1 => add 10^(2-1) * num[1-1] = 10 * 1 = 10
                i = 2 => add 10^(2-2) * num[2-1] = 1 * 4 = 4
                => 10 + 4 = 14

            should never go past 10^0
         '''

        if "hour" in tag.text or "hours" in tag.text:
            times.append(datetime.now() - timedelta(hours=delta_time))
        else:
            times.append(datetime.now() - timedelta(minutes=delta_time))

    return times

# Takes a time limit (in hours) and pulls all prices from New Jersey, New York, and Pennsylvania
def fuelPriceSpider(time_range):
    import requests
    from bs4 import BeautifulSoup
    prices = []
    for state, state_url in state_urls_to_crawl.items():
        url = state_url \
              + "/GasPriceSearch.aspx?typ=adv&fuel=D&srch=0&area=All%20Areas&tme_limit=" \
              + str(time_range)

        # Pulls source code from the url and then hands it over to Beautiful Soup for analysis
        source = requests.get(url)
        soup = BeautifulSoup(source.text, 'html.parser')
        # Sort through the soup
        price_divs = soup.findAll('div', {'class': 'sp_p'})
        areas = soup.findAll('a', {'class': 'p_area'})
        stations = separateStations(soup.findAll('dl', {'class': 'address'}))
        times = separateTimes(soup.findAll('div', {'class': 'tm'}))

        for price_line, area, station, price_time in zip(price_divs, areas, stations, times):
            # Creates new Price object
            new_price_object = Price()
            new_price_object.price = buildPrice(price_line)
            new_price_object.location = {"Area": area.text, "State": state}
            new_price_object.station = station
            new_price_object.time_recorded = price_time
            prices.append(new_price_object)

    return prices

# Main Program
if __name__ == '__main__':
    from fuelCrawler.models import LowestPrice
    from pygeocoder import Geocoder, GeocoderError
    from pymongo import errors
    from mongoengine import connect, connection
    # Must make sure there are no problems with only connecting once while script
    # runs continuously for days / months on end
    num_runs = 0
    while True:
        num_runs += 1
        prices_to_write = fuelPriceSpider(lowest_search_frequency)
        # print("Made it out of the spider...ALIVE")
        # print("Num prices to write: ", len(prices_to_write))
        # print("Sleep seconds between saves: ", lowest_search_frequency/len(prices_to_write))

        # Write to remote database
        '''
        collection_name = 'Fuel'
        mongo_usr = 'cralwer'
        mongo_pwd = 'crawler'
        mongo_uri = 'mongodb://admin:ubuntu@mongo.truckpallet.com/test'
        connect(
            name=collection_name,
            username=mongo_usr,
            password=mongo_pwd,
            host=mongo_uri
        ) '''

        # OR assume that the script is running on a mongo server: What we will assume for now
        # Could write directly from the spider instead of passing arrays to be written here
        # Needs to sleep for a certain amount of time to avoid OVER_QUERY_LIMIT problem with Google
        # In our case, we will split the time evenly between the length of the search frequency and hope that is enough
        # Ensures every price gets written as well as spaces out resource consumption
        try:
            connect('fuel-prices')
            for price in prices_to_write:
                try:
                    price_latlng = Geocoder.geocode(price.location["Area"] + "," + price.location["State"]).coordinates
                    LowestPrice(
                        price=price.price,
                        station=price.station,
                        location=price.location,
                        latlng=price_latlng,
                        time_recorded=price.time_recorded,
                        isLowest=True
                        ).save()
                    time.sleep(lowest_search_frequency/len(prices_to_write))
                except GeocoderError:
                    print("Caught geocoder error!")
        except errors.AutoReconnect:
            print("Auto Reconnect Error!")
        except errors.ConnectionFailure:
            print("Failure to connect!")
        except connection.ConnectionError:
            print("Can't connect to database!")

        # The time delay should be greater or equal to the time limit crawled for
        # Could cause repeat prices if not the case
        # Normally sleeping an entire program is not best practice, but here there is only one task
        print("Finished saving run ", num_runs, " to database.")
        time.sleep(lowest_search_frequency)


