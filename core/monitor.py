import multiprocessing
import datetime
import time
import base64

from core.search_tester import SearchTester
from core.elasticsearch import ElasticSearch

class Monitor(multiprocessing.Process):

    def __init__(self, cluster, logger, invoke_hour, query_interval):

        multiprocessing.Process.__init__(self)

        self.name = cluster['url']
        self.url = "{protocol}://{url}:{port}".\
                    format(protocol=cluster['protocol'], \
                           url=cluster['url'], \
                           port=cluster['port'])

        try:
            self.username = cluster['username']
            self.password = cluster['password']
        except KeyError:
            self.username = None
            self.password = None

        try:
            self.basis = cluster['basis']
        except KeyError:
            self.basis = "today"

        try:
            self.mode = cluster['mode']
        except KeyError:
            self.mode = "run"

        try:
            self.shrink = cluster['shrink']
        except KeyError:
            self.shrink = False

        if self.username and self.password:
            self.elasticsearch = ElasticSearch(self.url, cluster['timestring'], logger, self.basis, self.username, base64.b64decode(self.password))
        else :
            self.elasticsearch = ElasticSearch(self.url, cluster['timestring'], logger, self.basis)

        self.threshold = cluster['threshold']
        self.replicas = cluster['replicas']

        self.invoke_hour = invoke_hour
        self.invoked = False
        self.query_interval = query_interval

        self.optimal_shard_size = {}

        self.logger = logger

    def run(self):

        while True :

            self._init_for_new_day()

            indices = self.elasticsearch.get_index_of_today()

            make_tomorrow_index = False

            if self._check_invoke_hour(self.invoke_hour) and not self.invoked :
                make_tomorrow_index = True
                self.invoked = True

            for index in indices:
                if self.username and self.password:
                    search_tester = SearchTester(self.url, index['index'],
                                                 self.username, base64.b64decode(self.password))
                else:
                    search_tester = SearchTester(self.url, index['index'])
                took_time = search_tester.search()

                if took_time:

                    try:
                        ratio = float(self.threshold) / float(took_time)
                    except ZeroDivisionError:
                        ratio = self.threshold

                    current_shard_size = self.elasticsearch.get_shard_size_of_index(index['index'])

                    self.optimal_shard_size[index['index']] = current_shard_size * ratio
                    self.logger.info("[monitor][run] [{url}] [{index_name}] search performance : {took_time}, current shards size : {current_shard_size}, optimal shards size : {optimal_shard_size} bytes".\
                                     format(url=self.url, index_name=index['index'], took_time=took_time, current_shard_size=current_shard_size, optimal_shard_size=self.optimal_shard_size[index['index']]))

                    if make_tomorrow_index:

                        index_name_of_tomorrow = self.elasticsearch.get_index_name_of_tomorrow(index['name'])

                        payload = {
                            "settings": self._make_setting(index['index'], self.optimal_shard_size[index['index']], index_name_of_tomorrow),
                            "mappings": self.elasticsearch.get_mappings(index['index'])
                        }

                        if self.mode == "run":

                            if not self.elasticsearch.create_index(index_name_of_tomorrow, payload) :
                                self.logger.info("[monitor][run] [{url}] [{index_name_of_tomorrow}] creating index is failed". \
                                                        format(url=self.url, index_name_of_tomorrow=index_name_of_tomorrow))
                            else :
                                self.logger.info("[monitor][run] [{url}] [{index_name_of_tomorrow}] creating index is succeeded". \
                                                 format(url=self.url, index_name_of_tomorrow=index_name_of_tomorrow))

            time.sleep(self.query_interval)

    def _make_setting(self, index_name, took_time, index_name_of_tomorrow):

        settings = {
            "index": {
                "number_of_shards": 0,
                "number_of_replicas": self.replicas
            }
        }

        routing_allocation = self._has_routing_allocation(index_name)

        settings['index']['number_of_shards'] = self._get_number_of_shards(
                                                    self.elasticsearch.get_index_size(index_name),
                                                    self.optimal_shard_size[index_name],
                                                    routing_allocation
                                                )

        self.logger.info("[monitor][_make_setting] [{url}] [{index_name}] adjusted primary shards : {number_of_shards}".\
                    format(url=self.url, index_name=index_name_of_tomorrow, took_time=took_time, number_of_shards=settings['index']['number_of_shards']))

        return settings

    def _has_routing_allocation(self, index_name):

        settings = self.elasticsearch.get_settings(index_name)

        try:
            return settings['index']['routing']['allocation']['require']
        except KeyError:
            return False

    def _get_number_of_shards(self, index_size, optimal_shard_size, routing_allocation):

        number_of_shards = int(index_size) / int(optimal_shard_size)

        if routing_allocation:
            number_of_data_nodes = self.elasticsearch.num_of_data_nodes_routing_allocation(routing_allocation)
        else:
            number_of_data_nodes = self.elasticsearch.num_of_data_nodes()

        if number_of_shards < number_of_data_nodes and not self.shrink:
            number_of_shards = number_of_data_nodes

        if number_of_shards < 1:
            number_of_shards = 1

        return number_of_shards

    def _init_for_new_day(self):

        if datetime.datetime.now().strftime("%H") == "00":
            self.invoked = False

    def _check_invoke_hour(self, invoke_hour):

        timestamp = datetime.datetime.now().strftime("%H")

        if timestamp == invoke_hour:
            return True

        return False





