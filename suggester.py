"""
elasticsearch-shard-suggester main module
"""
import logging
import time
import yaml

from core.monitor import Monitor

CONFIG_PATH = "conf/elasticsearch-shard-suggester.yml"

CONFIG = yaml.load(file(CONFIG_PATH, 'r'))

"""
main function
"""
def main():

    logging.basicConfig(filename=CONFIG['logging']['logfile'],
                        filemode="a",
                        level=CONFIG['logging']['loglevel'],
                        format=CONFIG['logging']['format'])
    logger = logging.getLogger("elasticsearch-suggester")

    monitors = []

    while True:

        # Make Elasticsearch Monitor
        for cluster in CONFIG['clusters']:

            if not _is_already_started_process(cluster['url'], monitors):

                monitor = Monitor(
                    cluster,
                    logger,
                    CONFIG['application']['invoke_hour'],
                    CONFIG['application']['query_interval']
                )
                monitor.start()
                monitors.append(monitor)
                logger.info("start to monitor {cluster}".format(cluster=cluster))

        time.sleep(1)

"""
check monitor process 
"""
def _is_already_started_process(name, process_list):

    for process in process_list:
        if not process.is_alive():
            process_list.remove(process)

    for process in process_list:
        if process.name == name:
            return True

    return False


if __name__ == "__main__":
    main()
