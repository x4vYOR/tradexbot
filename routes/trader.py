from fastapi import APIRouter, UploadFile, File, WebSocket
from celery import Celery
from fastapi.responses import JSONResponse
from middlewares.verify_token_route import VerifyTokenRoute
from ml.model import MlModel
from models.model import *
from models.bot import NewBot, UpdateBot, ActionBot, TradesBot, MetricsBot, TaskTicket
from squemas.data import datasEntity
import pandas as pd
from config.dbmongo import DbBridge
import aiofiles
from worker.task import runTrader
from celery.task.control import revoke
from celery.result import AsyncResult



trader_routes = APIRouter(route_class=VerifyTokenRoute)
mlmodel = MlModel()
conn = DbBridge(host="localhost", port=27017, auth=False)

@trader_routes.post("/reload")
async def reload(data:ReloadModel):
    try:
        result = await mlmodel.load_model(data)
        if(result):
            return JSONResponse(content={"message":"Reloading Successed"},status_code=200)
        else:
            return JSONResponse(content={"message":"Reloading Failed"},status_code=200)
    except Exception as e:
        print(e)
        return JSONResponse(content={"message":"Reloading Error"}, status_code=401)

@trader_routes.post("/upload")
async def upload_file(file: UploadFile=File(...)):
    try:
        async with aiofiles.open(f"./ml/{file.filename}", 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
            out_file.close()
        return JSONResponse(content={"message":"Success Upload", "filename":file.filename},status_code=200)
    except Exception as e:
        return JSONResponse(content={"message":"Upload Error", "error":e},status_code=401)

@trader_routes.websocket("/signal")
async def websocket_endpoint(websocket: WebSocket, timeframe: str, pairs:str):
    pairs_list = pairs.split(",")
    last_timestamp = (await conn.getLastNTimestamp(pairs_list[0], timeframe, 1))[0]
    print('Accepting client connection...')
    await websocket.accept()
    while True:
        try:
            # Get the last candles in every pair from databases
            lastPairsCandle = [await conn.getLastCandleByOpenTime(item,timeframe, last_timestamp) for item in pairs_list]
            #print(type(lastPairsCandle))
            #print(mlmodel.columns)
            # Convert above data to dataframe and add column pair
            data_to_df = await datasEntity(lastPairsCandle,mlmodel.columns)
            #print(data_to_df)
            #print(type(data_to_df))
            df = pd.DataFrame(data_to_df)
            df["pair"] = pairs_list
            # send dataset to predict function and receive a list of dicts with "pairs" and "buy" keys
            res = await mlmodel.predict(df) # return dict
            await websocket.send_json(res)
        except Exception as e:
            print('error:', e)
            break
    print('Bye..')

@trader_routes.post("/new/bot")
async def new_bot(bot: NewBot):
    try:
        # if not exist register it in database
        new_bot = conn.saveBot(bot)
        conn.saveBot(bot)
        return JSONResponse(content={"message":"Success", "uuid": new_bot.uuid},status_code=200)
    except Exception as e:
        return JSONResponse(content={"message":"Error", "error":e},status_code=401)

@trader_routes.post("/update/bot")
async def update_bot(bot: UpdateBot):
    try:
        if(conn.existBot(bot.uuid)):
            conn.updateBot(bot)
            edited_bot = conn.getBot(bot.uuid)
            return JSONResponse(content={"message":"Success", "bot": edited_bot},status_code=200)
        else:
            return JSONResponse(content={"message":"Error", "error": "Not Found"},status_code=200)    
    except Exception as e:
        return JSONResponse(content={"message":"Error", "error":e},status_code=401)

@trader_routes.post("/run/bot", response_model=TaskTicket)
async def run_bot(bot: ActionBot):
    try:
        if(conn.existBot(bot.uuid)):
            bot_item = conn.getBot(bot.uuid)
            #start bot
            task_id = runTrader.delay(bot_item)

            return JSONResponse(content={"message":"Success", "status": task_id},status_code=200)
        else:
            return JSONResponse(content={"message":"Error", "error": "Not Found"},status_code=200)    
    except Exception as e:
        return JSONResponse(content={"message":"Error", "error":e},status_code=401)

@trader_routes.post("/stop/bot")
async def stop_bot(bot: ActionBot):
    try:
        if(conn.existBot(bot.uuid)):
            #stop bot
            revoke(bot.task_id, terminate=True)
            return JSONResponse(content={"message":"Success", "status": "stopped"},status_code=200)
        else:
            return JSONResponse(content={"message":"Error", "error": "Not Found"},status_code=200)    
    except Exception as e:
        return JSONResponse(content={"message":"Error", "error":e},status_code=401)

        
@trader_routes.post("/status/bot")
async def status_bot(bot: ActionBot):
    try:
        if(conn.existBot(bot.uuid)):
            #stop bot
            result = AsyncResult(bot.task_id)
            return JSONResponse(content={"message":"Success", "status": result.state},status_code=200)
        else:
            return JSONResponse(content={"message":"Error", "error": "Not Found"},status_code=200)    
    except Exception as e:
        return JSONResponse(content={"message":"Error", "error":e},status_code=401)

@trader_routes.post("/trades/bot")
async def trades_bot(bot: TradesBot):
    try:
        if(conn.existBot(bot.uuid)):
            trades = conn.getTradesBot(bot)
            return JSONResponse(content={"message":"Success", "trades": trades},status_code=200)
        else:
            return JSONResponse(content={"message":"Error", "error": "Not Found"},status_code=200)    
    except Exception as e:
        return JSONResponse(content={"message":"Error", "error":e},status_code=401)

@trader_routes.post("/metrics/bot")
async def metrics_bot(item: MetricsBot):
    try:
        if(conn.existBot(item.uuid)):
            bot = conn.getBot(item.uuid)

            # generate metrics

            metrics = ""

            return JSONResponse(content={"message":"Success", "metrics": metrics},status_code=200)
        else:
            return JSONResponse(content={"message":"Error", "error": "Not Found"},status_code=200)    
    except Exception as e:
        return JSONResponse(content={"message":"Error", "error":e},status_code=401)

