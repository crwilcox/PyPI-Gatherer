import tempfile
import os
import logging
import logging.handlers
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Log to console as well
logger.addHandler(logging.StreamHandler())
# Create a file log that rotates every hour and keeps 72 hours of history
logpath = os.path.join(tempfile.gettempdir(), "PyPIWorkerLog")
rotating_handler = logging.handlers.TimedRotatingFileHandler(logpath, 'h', 1, 72)
logger.addHandler(rotating_handler)

# Start the workers for discovery and work
logger.info("Starting Discovery Thread")
import WorkDiscovery
WorkDiscovery.WorkerThread().start()

import PackageInformationWorker
worker_count = 10
logger.info("Starting Workers. Count={}".format(worker_count))
for i in range(worker_count):
    logger.info("Starting Worker Thread: {}".format(i))
    PackageInformationWorker.WorkerThread().start()

import time
while True:
    time.sleep(30)