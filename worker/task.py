from .celery import worker
from config.dbmongo import DbBridge
from ml.model import MlModel
from squemas.data import datasEntity
import pandas as pd
from binance import Client
from time import sleep
import logging

logging.basicConfig(filename='task.log', level=logging.DEBUG)


@worker.task(
    ignore_result=True
)
async def runTrader(bot_config):
    try:
        # load de model and scaler
        logging.info(str(bot_config))
        mlmodel = MlModel()
        conn = DbBridge(host="localhost", port=27017, auth=False)
        exchange = Client(bot_config.api_key, bot_config.api_secret)
        logging.info("### model, conn and exchange Objects where loaded")
        result = await mlmodel.load_model(bot_config)
        logging.info("### model was configured nad loaded")
        # load strategy object and send db conection to save trades 
        strategy = None
        if(bot_config.strategy == "Incremental Buy"):
            from strategies.strategies import IncrementalBuy
            strategy = IncrementalBuy(bot_config, conn, exchange)
            logging.info("### Incremental Buy  Strategy loaded")
        elif(bot_config.strategy == "DCA"):
            pass
        else:
            pass
        
        #  forever search database for last item, and when it arrives, predict item
        last_timestamp = (await conn.getLastNTimestamp(bot_config.pairs, bot_config.timeframe, 1))[0]
        
        while True:
            aux_timestamp = (await conn.getLastNTimestamp(bot_config.pairs[0], bot_config.timeframe, 1))[0]
            # only if aux_timestamp is diferent we can make prediction
            if(last_timestamp != aux_timestamp):
                logging.info("### there is a new timestamp")
                # Get the last candles in every pair from databases
                lastPairsCandle = [await conn.getLastCandleByOpenTime(item,bot_config.timeframe, last_timestamp) for item in bot_config.pairs]
                #logging.info(type(lastPairsCandle))
                #logging.info(mlmodel.columns)
                # Convert above data to dataframe and add column pair
                data_to_df = await datasEntity(lastPairsCandle,mlmodel.columns)
                #logging.info(data_to_df)
                #logging.info(type(data_to_df))
                df = pd.DataFrame(data_to_df)
                df["pair"] = bot_config.pairs
                # send dataset to predict function and receive a list of dicts with "pairs" and "buy" keys
                predicted_dict = await mlmodel.predict(df) # return dict
                logging.info(f"### the model prediction is: {str(predicted_dict)}")                
                # send the pairs and signal dataframe to strategy
                #it has the format [{"pair": "ETHBTC", "buy": false, "close": 0.001}, {"pair": "DOTBTC", "buy": false, "close": 0.001}, {"pair": "SOLBTC", "buy": false, "close": 0.001}]
                logging.info("### the prediction was send to strategy")
                strategy.process(predicted_dict)
                logging.info("### the prediction was processed")
                # refresh the bot status
                conn.setBotStatus({"uuid":bot_config.uuid, "status":"running"})
                logging.info(f"### the bot status to RUNNING was changed")
                # refresh last_timestamp to aux_timestamp
                last_timestamp = aux_timestamp
            else:
                sleep(1)
    except Exception as e:
        logging.error(str(e))
    finally:
        conn.setBotStatus({"uuid":bot_config.uuid, "status":"stopped"})
        logging.info(f"### the bot status to STOPPED was changed")
