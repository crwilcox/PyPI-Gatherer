import threading
from WorkDiscovery.PyPIWatcher import PyPIWatcher
import traceback
import time
import logging

logger = logging.getLogger()

class WorkerThread(threading.Thread):
    def run(self):
        pypi_watcher = PyPIWatcher()
        while True:
            try:
                pypi_watcher.queue_new_updates_from_PyPI()
                time.sleep(60*10) # sleep for 10 minutes between updates from PyPI list     
            except Exception as e:
                logger.error("Failure in WorkDiscovery:{}".format(traceback.format_exc()))
                # after failure new up a Watcher
                pypi_watcher = PyPIWatcher()
