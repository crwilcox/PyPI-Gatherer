import azure.storage.queue as queue
import concurrent.futures
import config
import json
from multiprocessing import Pool
import requests
import time
import xml.etree.ElementTree as ET
import datetime
import dateutil
import threading
import traceback
import logging

logger = logging.getLogger()

class PyPIWatcher(object):
    """Watch PyPI for new packages coming in"""

    def __init__(self):
        self.qs = queue.QueueService(config.STORAGE_ACCOUNT_NAME, config.STORAGE_ACCOUNT_KEY)
        self.qs.create_queue(config.PACKAGE_QUEUE_NAME)
        self._background_queue_all_packages = None
        self._needs_background_scan = False

    def queue_new_updates_from_PyPI(self):
        # get the last checked time and update it.  There is a chance we duplicate
        # searches on the edges but no worries. I would rather not miss them right now
        last_checked_pypi = config.get_last_checked_pypi()
        time_of_search_start = datetime.datetime.utcnow()
        
        # look at the rss feed for new packages (https://pypi.python.org/pypi?%3Aaction=packages_rss) 
        new_packages_url = "https://pypi.python.org/pypi?%3Aaction=packages_rss"
        found_old_packages = self._queue_updates_from_rss(new_packages_url, last_checked_pypi)

        # look at the rss feed for updated packages (https://pypi.python.org/pypi?%3Aaction=rss)
        updated_packages_url = "https://pypi.python.org/pypi?%3Aaction=rss"
        found_old_updates = self._queue_updates_from_rss(updated_packages_url, last_checked_pypi)
        
        if self._needs_background_scan or not found_old_packages or not found_old_updates:
            # We have a scheduled scan, or didn't find old packages. 
            # Better queue an update of everything. If we are actively running a scan
            # just queue one for after.
            # unset the background scan needed
            self._needs_background_scan = False
            if not self._background_queue_all_packages or not self._background_queue_all_packages.isAlive():
                self._background_queue_all_packages = threading.Thread(target=self.queue_all_packages_on_pypi)
                self._background_queue_all_packages.start()        
            else:
                # we don't want to stop the thread.  Let's just make sure when this one ends
                # we get around to scheduling a new worker
                self._needs_background_scan = True
             
            # since we are starting an update from here, we can move the search
            # ahead to now.  This will be true since we will get from now (and 
            # some future) queued.
            time_of_search_start = datetime.datetime.utcnow() 

         # update the last checked pypi time   
        config.set_last_checked_pypi(time_of_search_start)

    def queue_all_packages_on_pypi(self):
        try:
            logger.info("Queuing all Packages from PyPI")
            max_coroutines = 10
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_coroutines) as executor:
                for p in PyPIWatcher._get_all_packages_on_pypi():
                    # approximate size of queue (qsize isn't reliable)
                    while executor._work_queue.qsize() > max_coroutines:
                        time.sleep(1)
                    executor.submit(self._add_versions_to_queue, p)
        except Exception:
            logger.error("Failed Queuing All Packages from PyPI", traceback.format_exc())

    def _add_versions_to_queue(self, package):
        start = time.time()
        versions = PyPIWatcher._get_package_versions(package)
        if versions:
            for version in versions:
                self._queue_package_for_update(package, version)
        end = time.time()
        logger.info("Added To Queue:{} Time:{}".format(package, end - start))

    def _queue_updates_from_rss(self, url, last_checked_pypi):
        '''
            url (str):
                url to the rss feed
            last_checked_pypi (datetime):
                date we last checked pypi. So we don't double queue stuff unnecessarily
            returns True if the list had packages that were old.
        '''
        old_packages_in_list = False

        request = requests.get(url)
        if request.status_code != 200:
            raise Exception('Failed to properly get RSS Updates:{}'.format(url))

        root = ET.fromstring(request.text)
        for item in root.iter('item'):
            # get the package name from url
            package_url = item.find('link').text
            package_name = PyPIWatcher._get_package_name(package_url)
            publish_date_text = item.find('pubDate').text
            publish_date = dateutil.parser.parse(publish_date_text)

            if not last_checked_pypi or last_checked_pypi < publish_date:
                self._add_versions_to_queue(package_name)
            else:
                # there were old packages. when we return we can say that we didn't have a gap
                old_packages_in_list = True

        return old_packages_in_list
    
    def _get_package_name(url):
        # urls are in the form pypi/{package-name}/{version}
        short_package_url = url[len('http://pypi.python.org/pypi/'):]
        package_name = short_package_url.split('/')[0]
        return package_name

    def _get_package_versions(package_name):
        package_url = "http://pypi.python.org/pypi/{}/json".format(package_name)
        request = requests.get(package_url)
        if request.status_code != 200:
            logger.error('Failed to properly get package json:{} status_code:{}'.format(package_url, request.status_code))
            return None

        json = request.json()

        package_versions = []
        for i in json['releases']:
            package_versions.append(i.strip())
        return package_versions

    def _queue_package_for_update(self, package, version):
        message = { "package":package, "version":version}
        self.qs.put_message(config.PACKAGE_QUEUE_NAME, json.dumps(message))

    def _get_all_packages_on_pypi():
        try:
            r = requests.get('http://pypi.python.org/simple')
            if r.status_code != 200:
                r = requests.get('http://pypi.python.org/simple')

            root = ET.fromstring(r.text)
        except:
            # if we fail here just continue with nothing. We can process what we figured out.
            # most likely thing is we had an invalid result.
            logger.error("Failed to get all packages:", traceback.format_exc())
            return None

        for a in root.iter('a'):
            yield a.attrib['href']
    