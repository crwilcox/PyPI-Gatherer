# Fill in these values fora  storage account and key of your own
STORAGE_ACCOUNT_NAME = ''
STORAGE_ACCOUNT_KEY = ''

PACKAGE_VERSION_DATA_TABLENAME = "packageversiondata" # table to more or less mirror pypi versions
PACKAGE_SUMMARY_TABLENAME = "packagesummarydata" # table that is a highlevel summary of the table
PACKAGE_QUEUE_NAME = "packagestoscan" # queue that is used to track work that needs doing.
CONFIG_TABLENAME = "config" # table used to store variable configs that exist across runners and runs.

### BELOW ARE NOT EDITED CONFIGS ###
from azure import storage
import dateutil
def get_last_checked_pypi():
    table_service = storage.CloudStorageAccount(STORAGE_ACCOUNT_NAME, STORAGE_ACCOUNT_KEY).create_table_service()
    table_service.create_table(CONFIG_TABLENAME)
    
    last_checked_pypi = table_service.query_entities(CONFIG_TABLENAME, "PartitionKey eq 'last_checked_pypi'")
    if not len(last_checked_pypi):
        return None
    else:
        return last_checked_pypi[0].value
def set_last_checked_pypi(value):
    table_service = storage.CloudStorageAccount(STORAGE_ACCOUNT_NAME, STORAGE_ACCOUNT_KEY).create_table_service()
    table_service.create_table(CONFIG_TABLENAME)
    table_service.insert_or_replace_entity(CONFIG_TABLENAME, 'last_checked_pypi', 'ROWKEY', { 'value': value })