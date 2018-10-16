import requests
import datetime

from requests.auth import HTTPBasicAuth

class ElasticSearch():

    def __init__(self, url, timestring, logger, basis="today", username=None, password=None):

        self.url = url
        self.timestring = timestring
        self.logger = logger

        self.username = username
        self.password = password
        self.basis = basis

    def create_index(self, index_name, payload):

        response = self._put("{index_name}".format(index_name=index_name), payload)

        if response.status_code != 200 :
            self.logger.info("[elasticsearch][create_index] [{url}] status_code {status_code} reason {text}".\
                             format(url=self.url, status_code=response.status_code, text=response.text))
            return False

        return True

    def get_index_name_of_tomorrow(self, index_name):

        if self.basis == "yesterday":
            tommorrow_timestamp = (datetime.date.today()).strftime(self.timestring)
        else :
            tommorrow_timestamp = ( datetime.date.today() + datetime.timedelta(1)).strftime(self.timestring)

        return "{index_name}-{tommorrow_timestamp}".format(index_name=index_name, tommorrow_timestamp=tommorrow_timestamp)

    def get_index_of_today(self):

        if self.basis == "yesterday":
            today_timestamp = ( datetime.date.today() - datetime.timedelta(1)).strftime(self.timestring)
        else :
            today_timestamp = datetime.date.today().strftime(self.timestring)
        indices = self._get_indices()
        today_indices = []

        for index in indices:

            if str(index['index']).find(today_timestamp) != -1 :
                index['name'] = self._extract_index_name(index['index'], today_timestamp)
                today_indices.append(index)

        return today_indices

    def num_of_data_nodes_routing_allocation(self, routing_allocation):

        attr, value = routing_allocation.items()[0]

        count = 0
        for node in self._get("_cat/nodeattrs?format=json"):
            if node['attr'] == attr and node['value'] == value:
                count += 1

        return count

    def num_of_data_nodes(self):

        count = 0
        for node in self._get("_cat/nodes?h=id,node.role&format=json") :
            if node['node.role'].find("d") != -1:
                count += 1

        return count

    def get_mappings(self, index_name):

        return self._get("{index_name}/_mappings".format(index_name=index_name))[index_name]['mappings']

    def get_settings(self, index_name):

        return self._get("{index_name}/_settings".format(index_name=index_name))[index_name]['settings']

    def get_index_size(self, index_name):

        store_size = self._get("_cat/indices/{index_name}?format=json".format(index_name=index_name))[0]['pri.store.size']

        return self._transform_store_size_to_bytes(store_size)

    def get_primary_shards_of_index(self, index_name):

        return int(self._get("{index_name}/_settings".format(index_name=index_name))[index_name]['settings']['index']['number_of_shards'])

    def get_shard_size_of_index(self, index_name):

        for shard in self._get_shards(index_name):
            return self._transform_store_size_to_bytes(shard['store'])

    def _extract_index_name(self, index_name, timestamp):

        return index_name.split("-{timestamp}".format(timestamp=timestamp))[0]

    def _transform_store_size_to_bytes(self, store_size):

        if store_size.find("kb") != -1:
            return float(store_size.split("kb")[0]) * 1024
        elif store_size.find("mb") != -1 :
            return float(store_size.split("mb")[0]) * 1024 * 1024
        elif store_size.find("gb") != -1 :
            return float(store_size.split("gb")[0]) * 1024 * 1024 * 1024
        elif store_size.find("tb") != -1 :
            return float(store_size.split("tb")[0]) * 1024 * 1024 * 1024 * 1024
        else :
            return float(store_size.split("b")[0])

    def _get_shards(self, index_name):

        return self._get("_cat/shards/{index_name}?h=shard,store&format=json".format(index_name=index_name))

    def _get_indices(self):

        response = []

        for _ in self._get("_cat/indices?h=index&format=json") :
            if not str(_['index']).startswith(".") :
                response.append(_)

        return response

    def _get(self, api):

        if self.username and self.password :
            return requests.get("{url}/{api}".format(url=self.url, api=api), auth=HTTPBasicAuth(self.username, self.password), timeout=120).json()
        else :
            return requests.get("{url}/{api}".format(url=self.url, api=api), timeout=120).json()

    def _put(self, api, payload):

        if self.username and self.password :
            return requests.put("{url}/{api}".format(url=self.url, api=api), auth=HTTPBasicAuth(self.username, self.password), timeout=120, json=payload)
        else :
            return requests.put("{url}/{api}".format(url=self.url, api=api), timeout=120, json=payload)