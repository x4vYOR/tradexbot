from .celery import worker
from config.dbmongo import DbBridge
from ml.model import MlModel
from squemas.data import datasEntity
import pandas as pd
from binance import Client
from time import sleep
from celery.utils.log import get_task_logger
from celery.contrib.abortable import AbortableTask  
#import sys

logger = get_task_logger(__name__)

@worker.task(bind=True,base=AbortableTask)
def runTrader(self,bot_config):
    #old_outs = sys.stdout, sys.stderr
    #rlevel = worker.conf.worker_redirect_stdouts_level
    try:
        print("HELLO")
        #worker.log.redirect_stdouts_to_logger(logger, rlevel)
        # load de model and scaler
        print(str(bot_config))
        mlmodel = MlModel()
        conn = DbBridge(host="localhost", port=27017, auth=False)
        exchange = Client(bot_config["api_key"], bot_config["api_secret"])
        print("### model, conn and exchange Objects where loaded")
        result = mlmodel.load_model(bot_config)
        aux_columns = ['close','open_time','close_time']+mlmodel.columns
        print("### model was configured nad loaded")
        # load strategy object and send db conection to save trades 
        strategy = None
        print(f"strategy: {bot_config['strategy']}")
        if(bot_config["strategy"] == "Incremental Buys"):
            from strats.strategies import IncrementalBuy
            print("## Instanciando IncrementalBuy")
            strategy = IncrementalBuy(bot_config, conn, exchange)
            logger.info("### Incremental Buy  Strategy loaded")
        elif(bot_config["strategy"] == "DCA"):
            pass
        else:
            pass
        
        #  forever search database for last item, and when it arrives, predict item
        last_timestamp = conn.getLastNTimestamp(bot_config["pairs"][0], bot_config["timeframe"], 1)[0]
        print(f"last_timestamp loaded: {last_timestamp}")
        conn.setBotStatus({"uuid":bot_config["uuid"], "status":"running"})
        logger.info(f"### the bot status to RUNNING was changed")
        while True:            
            aux_timestamp = conn.getLastNTimestamp(bot_config["pairs"][0], bot_config["timeframe"], 1)[0]
            print(f"aux_timestamp loaded: {aux_timestamp}")
            # only if aux_timestamp is diferent we can make prediction
            if(last_timestamp != aux_timestamp):
                logger.info("### there is a new timestamp")
                # Get the last candles in every pair from databases
                lastPairsCandle = [conn.getLastCandleByOpenTime(item,bot_config["timeframe"], last_timestamp) for item in bot_config["pairs"]]
                print(f"last_pairsCandle: {type(lastPairsCandle)}, {lastPairsCandle} ")
                #logger.info(mlmodel.columns)
                # Convert above data to dataframe and add column pair
                print(f"mlmodel.columns: {mlmodel.columns} type: {type(mlmodel.columns)}")
                print(f"aux_columns: {aux_columns} type: {type(aux_columns)}")
                data_to_df = datasEntity(lastPairsCandle,aux_columns)
                print("data to df: ",data_to_df)
                #logger.info(data_to_df)
                #logger.info(type(data_to_df))
                df = pd.DataFrame(data_to_df)
                print(f"data_to_df converted to df: {df}")
                df["pair"] = bot_config["pairs"]
                print("column pair added to df")
                # send dataset to predict function and receive a list of dicts with "pairs" and "buy" keys
                predicted_dict = mlmodel.predict(df) # return dict
                logger.info(f"### the model prediction is: {str(predicted_dict)}")                
                # send the pairs and signal dataframe to strategy
                #it has the format [{"pair": "ETHBTC", "buy": false, "close": 0.001}, {"pair": "DOTBTC", "buy": false, "close": 0.001}, {"pair": "SOLBTC", "buy": false, "close": 0.001}]
                logger.info("### the prediction was send to strategy")
                strategy.process(predicted_dict)
                logger.info("### the prediction was processed")
                # refresh the bot status
                #conn.setBotStatus({"uuid":bot_config["uuid"], "status":"running"})
                
                # refresh last_timestamp to aux_timestamp
                last_timestamp = aux_timestamp
                
            else:
                sleep(2)
            if conn.getBotStatus(bot_config["uuid"]) == "stopped":
                    # respect aborted state, and terminate gracefully.
                    logger.info('Task aborted')
                    return
    except Exception as e:
        logger.info(str(e))
    finally:
        conn.setBotStatus({"uuid":bot_config["uuid"], "status":"stopped"})
        #sys.stdout, sys.stderr = old_outs
