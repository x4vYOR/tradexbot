from ast import Try
from .celery import worker
from config.dbmongo import DbBridge
from ml.model import MlModel

conn = DbBridge(host="localhost", port=27017, auth=False)

@worker.task(
    ignore_result=True
)
def runTrader(self, bot_config):

    try:
        mlmodel = MlModel()
        # load de model and scaler

        # load strategy object and send db conection to save trades 
        
        #  forever search database for last item, and when it arrives, predict item
        

        # send the pairs and signal dataframe to strategy

        return True
    except Exception as e:
        pass

    finally:
        #change the status of bot
        pass
