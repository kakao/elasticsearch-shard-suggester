import requests
import traceback

from requests.auth import HTTPBasicAuth

class SearchTester():

    def __init__(self, url, index, username=None, password=None):

        self.url = url
        self.index = index
        self.query = {
            "query" : {
                "query_string": {
                    "query": "*"
                }
            }
        }

        self.username = username
        self.password = password

    def search(self):

        try:
            took_time = self._get()['took']

            # if took_time is 0 ms, it treated as False so it need to be 1.
            if not took_time:
                took_time = 1

            return took_time

        except:
            print traceback.print_exc()
            return False

    def _get(self):

        if self.username and self.password :
            return requests.get("{url}/{index}/_search?preference=_shards:0".format(url=self.url, index=self.index),
                                auth=HTTPBasicAuth(self.username, self.password),
                                json=self.query).json()
        else :
            return requests.get("{url}/{index}/_search?preference=_shards:0".format(url=self.url, index=self.index),
                                json=self.query).json()

