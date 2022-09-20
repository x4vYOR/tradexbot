from asyncio import current_task
from time import sleep, time_ns
from fastapi import APIRouter, UploadFile, File, WebSocket
from fastapi.responses import JSONResponse
from middlewares.verify_token_route import VerifyTokenRoute
from ml.model import MlModel
from models.model import *
from models.data import ReqWsData
from squemas.data import datasEntity
import pandas as pd
from config.dbmongo import DbBridge
import aiofiles

model_routes = APIRouter(route_class=VerifyTokenRoute)
mlmodel = MlModel()
conn = DbBridge(host="localhost", port=27017, auth=False)

"""
@model_routes.post("/predict")
def predict(data: DataPredict):
    try:
        print(data)
        df = json_normalize(data.dict()) 
        print(df)
        return JSONResponse(content=model_pipeline(df),status_code=200)
    except:
        return JSONResponse(content={"message":"Predict Error"}, status_code=401)
"""
@model_routes.post("/reload")
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

@model_routes.post("/upload")
async def upload_file(file: UploadFile=File(...)):
    try:
        async with aiofiles.open(f"./ml/{file.filename}", 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
            out_file.close()
        return JSONResponse(content={"message":"Success Upload", "filename":file.filename},status_code=200)
    except Exception as e:
        return JSONResponse(content={"message":"Upload Error", "error":e},status_code=401)

@model_routes.websocket("/signal")
async def websocket_endpoint(websocket: WebSocket, timeframe: str, pairs:str):
    pairs_list = pairs.split(",")
    last_timestamp = (await conn.getLastNTimestamp(pairs_list[0], timeframe, 1))[0]
    print('Accepting client connection...')
    await websocket.accept()
    while True:
        try:
            aux_timestamp = (await conn.getLastNTimestamp(pairs_list[0], timeframe, 1))[0]
            print("New timstamp: ",aux_timestamp)
            # Get the last candles in every pair from databases
            if(last_timestamp != aux_timestamp):
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
                last_timestamp = aux_timestamp
            else:
                sleep(10)
        except Exception as e:
            print('error:', e)
            break
    print('Bye..')