# PyPI-Gatherer
A Python Azure Cloud Service that gathers data from PyPI and uploads it to Azure Table Storage.

This was created to do some research on Python 3 support levels. If you want to read my take on things you can
read the [blog on Microsoft Python Engineering](http://aka.ms/py3winning).

## Using the Collected Data
The easiest way to use the collected data from my service is to view 
the [Jupyter Notebook on Cortana Analytics Gallery](http://aka.ms/py3winningnb).

If you would rather run it locally though, you can download the [Azure SDK from PyPI](http://pypi.python.org/pypi/azure)
and use the following code:

```python
from azure.storage.table import TableService

account_name='pypidata'
config_sas='se=2030-01-01&sp=r&sv=2014-02-14&sig=cbluw1yeoAnmXSGtMbUM9dOmDgndoFnjSpeTAoz5Zls%3D&tn=config'
packagesummarydata_sas='se=2030-01-01&sp=r&sv=2014-02-14&sig=JbQiFfxRRqJqUn7lyyoY8ek2fC3r7%2Bb9rndXlGBvhwI%3D&tn=packagesummarydata'
packageversiondata_sas='se=2030-01-01&sp=r&sv=2014-02-14&sig=OpQRTKCCr7Bp%2BoFv%2BpElQ%2BF/fhA3HEiLHQfFb7bJy5o%3D&tn=packageversiondata'

config_table_service = TableService(account_name, sas_token=config_sas)
packagesummarydata_table_service = TableService(account_name, sas_token=packagesummarydata_sas)
packageversiondata_table_service = TableService(account_name, sas_token=packageversiondata_sas)
```


## Collecting the Data
If you prefer to collect the data yourself you will need an Azure subscription.
1) Create a storage account on Azure
2) Input the storage account info to the variables `STORAGE_ACCOUNT_NAME` and `STORAGE_ACCOUNT_KEY` in `config.py`
3) Deploy the cloud service to your account.

That should allow you to collect the data yourself.
