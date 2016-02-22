import requests
import traceback
import logging

logger = logging.getLogger()

class PyPIPackageInformation(object):
    """Methods to get information from PyPi"""

    def get_package_specific_version_info(package_name, version):
        try:
            package = { 'name':package_name, 'version':version, 'uploaded':None, 'downloads':None, 'classifiers':None}
            package_specific_version_url = "http://pypi.python.org/pypi/{}/{}/json".format(package_name, version)
        
            request = requests.get(package_specific_version_url)
            
            if request.status_code != 200:
                logger.error('Failed to properly get package:{} version:{} status_code:{}. Fall back to package json'.format(package_name, version, request.status_code))
                package__url = "http://pypi.python.org/pypi/{}/json".format(package_name)
                # Try just on the root json for the package.  Won't get classifier data unfortunately.
                request = requests.get(package__url)
                if request != 200:
                    # if after retrying it is still a bad result, just continue along.  We will skip this. 
                    # One of our periodic sweeps of all packages should find this.
                    return None
            try:
                js = request.json()
            except:
                # some packages have versions like '..' that go terribly when put into a URL.  Just return None if we fail to decode JSON from the json endpoints.
                return None

            if not version in js['releases'].keys():
                # the release we are looking for wasn't found.  If this happens, just return None.
                return None

            if len(js['releases'][version]) > 0:
                package['uploaded'] = js['releases'][version][0]['upload_time']
                package['downloads'] = js['releases'][version][0]['downloads']
            else:
                package['uploaded'] = None
                package['downloads'] = 0
            
            if js['info']['version'] == version:
                # if the version is the same we can get the classifier info from here.
                # if it isn't equal we probably had to fall back to the summary listing on pypi
                package['classifiers'] = js['info']['classifiers']

            return package
        except Exception as e:
            # we need to rethrow this so that it bubbles up and we don't continue along
            # if we were to continue along we could end up removing things from the work queue.
            logger.error(traceback.format_exc())
            raise e