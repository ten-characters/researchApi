__author__ = 'austin'

import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from fuelCrawler.models import StateAvgFuelPrice
from fuelCrawler.resources import state_urls_to_crawl, avg_search_frequency, database_name


class AvgPrice:
    def __init__(self, price=None, state=None, time_recorded=None):
        if price is None:
            self.price = 0
        else:
            self.price = price
        if state is None:
            self.state = ""
        else:
            self.state = state
        if time_recorded is None:
            self.time_recorded = datetime.now()
        else:
            self.time_recorded = time_recorded


def fuel_price_spider():
    state_num = 1
    prices = []
    for state, state_url in state_urls_to_crawl.items():
        url = state_url + "/index.aspx?fuel=D"
        # print(str(state_num) + ' ' + url)
        source = requests.get(url)
        soup = BeautifulSoup(source.text, 'html.parser')
        avg_price = soup.find('div', {'id': 'divTicker'}).findNext('h2').text
        prices.append(AvgPrice(float(avg_price), state))
        state_num += 1
    return prices


def run():
    from pymongo import errors
    from mongoengine import connect, connection
    num_runs = 0
    while True:
        num_runs += 1
        to_write = fuel_price_spider()
        try:
            connect(database_name)
            for price in to_write:
                StateAvgFuelPrice(
                    price=price.price,
                    state=price.state,
                    time_recorded=price.time_recorded
                    ).save()

        except errors.AutoReconnect:
            print("Auto Reconnect Error!")
        except errors.ConnectionFailure:
            print("Failure to connect!")
        except connection.ConnectionError:
            print("Can't connect to database!")

        print("Finished saving run ", num_runs, " to database.")
        time.sleep(avg_search_frequency)


from fuelCrawler.decorators import async

@async
def run_async():
    run()
