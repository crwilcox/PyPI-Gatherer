import requests
import config
from azure import storage
from PackageInformationWorker.PyPIPackageInformation import PyPIPackageInformation
import json
import azure.storage.queue as queue
import traceback
import urllib
import logging

logger = logging.getLogger()
account_name = config.STORAGE_ACCOUNT_NAME
account_key = config.STORAGE_ACCOUNT_KEY
STATIC_ROW_KEY = 'ROWKEY'
table_service = storage.CloudStorageAccount(account_name, account_key).create_table_service()
table_service.create_table(config.PACKAGE_VERSION_DATA_TABLENAME)
table_service.create_table(config.PACKAGE_SUMMARY_TABLENAME)

def main():
    # package, version = ('azure', '1.0.0')
    # get a package to look at
    # check that package and version.
    # version data just gets filled in
    # summary trickier.
    # summary -> name,
    #               first_published (might be different than python2_start if
    #               not using trove classifier)
    #               python2_start (change if we find earlier),
    #               python2_end (change if we find earlier, remove if package
    #               after this come in and has python2),
    #               python3_start (change if we find earlier)
    try:
        qs = queue.QueueService(config.STORAGE_ACCOUNT_NAME, config.STORAGE_ACCOUNT_KEY)
        messages_in_batch = 5

        while True:
            messages = qs.get_messages(config.PACKAGE_QUEUE_NAME,numofmessages=messages_in_batch, visibilitytimeout=messages_in_batch*60)
            for message in messages:
                entity = json.loads(message.message_text)
                _process_one_package(entity["package"], entity["version"])
                # once completed delete the message
                qs.delete_message(config.PACKAGE_QUEUE_NAME, message.message_id, message.pop_receipt)
    except Exception as e:
        # swallow exception here. we will just reprocess and delete the message.
        # known failures:
        # - connection aborted by get_messages sometimes.  this happens with a connectionreseterror (10054)
        # - Random json errors. Could add retry.  
        logger.error(traceback.format_exc())
          
def _process_one_package(package_name, version):
    logger.info("Worker: Package:{} Version:{}".format(package_name, version))
    if not package_name or not version:
        logger.warn("Package_name or version was empty. Moving on as the queue had bad data")
        return

    # .6684 seconds to run.  74577 total packages
    package_info = PyPIPackageInformation.get_package_specific_version_info(package_name, version)
    if not package_info:
        logger.error("Worker: Package:{} Version:{} failed to get package info".format(package_name, version))
        return

    supports_python_2 = len([x for x in package_info['classifiers'] if x.startswith('Programming Language :: Python :: 2')]) > 0
    supports_python_3 = len([x for x in package_info['classifiers'] if x.startswith('Programming Language :: Python :: 3')]) > 0
    uploaded = package_info['uploaded']

    try:
        summary_entity = table_service.get_entity(config.PACKAGE_SUMMARY_TABLENAME, package_name, STATIC_ROW_KEY)
    except:
        # we don't have a summary for this entry.
        summary_entity = { 
            'PartitionKey':package_name, 'RowKey':STATIC_ROW_KEY, 'First_Published':None, 
            'Python2_Start':None, 'Python2_End':None, 'Python3_Start':None
            }
        table_service.insert_or_replace_entity(config.PACKAGE_SUMMARY_TABLENAME, package_name, STATIC_ROW_KEY, summary_entity)
        summary_entity = table_service.get_entity(config.PACKAGE_SUMMARY_TABLENAME, package_name, STATIC_ROW_KEY)

    # set fields using upload. Upload is none if the version has never been uploaded
    # Basically just filter out packages that never have content from our records.
    if uploaded is not None:
        if not hasattr(summary_entity, 'First_Published') or summary_entity.First_Published is None or summary_entity.First_Published > uploaded:
            # if the published date is empty or later than the current release we
            # are viewing update
            summary_entity.First_Published = uploaded

        if supports_python_2 and \
            (not hasattr(summary_entity, 'Python2_Start') or summary_entity.Python2_Start is None or summary_entity.Python2_Start > uploaded):
            # if the published date is empty or later than the date and it supports
            # python 2
            summary_entity.Python2_Start = uploaded
    
        if supports_python_2 and hasattr(summary_entity, 'Python2_End') and summary_entity.Python2_End is not None and summary_entity.Python2_End < uploaded:
            # we support python2 but it is after the date we thought python 2
            # support ended we must not have really ended
            summary_entity.Python2_End = None    
        elif hasattr(summary_entity, 'Python2_Start') and hasattr(summary_entity, 'Python2_End') and \
            summary_entity.Python2_Start is not None and summary_entity.Python2_End is not None and \
            (summary_entity.Python2_End > uploaded and summary_entity.Python2_Start < uploaded):
            # if we don't support python2, and we have started supporting python2
            # at some point
            # and if the date we are saying we ended is after the start
            summary_entity.Python2_End = uploaded

        if supports_python_3 and \
            (not hasattr(summary_entity, 'Python3_Start') or summary_entity.Python3_Start is None or summary_entity.Python3_Start > uploaded):
            # if the published date is empty or later than the current release we
            # are viewing update
            summary_entity.Python3_Start = uploaded

    version_entity = _insert_entity_to_package_version_table(package_name, version, supports_python_2, supports_python_3, package_info['downloads'], uploaded)
    summary_entity = table_service.insert_or_replace_entity(config.PACKAGE_SUMMARY_TABLENAME, package_name, STATIC_ROW_KEY, summary_entity)

def _insert_entity_to_package_version_table(package, version, python2, python3, downloads, upload_time):
    # TODO: issue with python azure storage.  Version can't have '~' in it. https://github.com/Azure/azure-storage-python/issues/76
    package_sanitized = urllib.parse.quote_plus(package)
    version_sanitized = urllib.parse.quote_plus(version)

    try:
        result =  table_service.insert_or_replace_entity(config.PACKAGE_VERSION_DATA_TABLENAME, package_sanitized, version_sanitized,
                                    {'PartitionKey' : package_sanitized,
                                     'RowKey': version_sanitized, 
                                     'Python2': python2, 
                                     'Python3': python3,
                                     'Downloads': downloads,
                                     'UploadTime': upload_time})

        return result
    except Exception as e:
        logger.error("Failed to insert Package:{} Version:{} Python2:{} Python3:{} Downloads:{} UploadTime:{} Exception:{}".format(
            package, version, python2, python3, downloads, upload_time, traceback.format_exc()))
        raise e