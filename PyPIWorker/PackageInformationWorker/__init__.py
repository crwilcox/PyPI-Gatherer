import threading
import PackageInformationWorker.PyPIHistoricalScraper
import logging

logger = logging.getLogger()

class WorkerThread(threading.Thread):
    def run(self):
        while True:
            try:
                PyPIHistoricalScraper.main();
            except:
                logger.error("oops. try again")