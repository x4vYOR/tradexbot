from fastapi import APIRouter
from fastapi.responses import JSONResponse
from middlewares.verify_token_route import VerifyTokenRoute
from models.data import ReqDataset
from squemas.data import datasEntity
from config.dbmongo import DbBridge
import datetime
import json

data_routes = APIRouter(route_class=VerifyTokenRoute)

conn = DbBridge(host="localhost", port=27017, auth=False)

@data_routes.post("/data")
async def getData(data: ReqDataset):
    try:
        startdate = datetime.datetime.strptime(data.ini, "%d/%m/%Y").timestamp()*1000
        enddate = datetime.datetime.strptime(data.end, "%d/%m/%Y").timestamp()*1000
        # devuelve una lista con todos los datos entre fechas para cada tick
        datos = conn.getHistoricalCandles(data.pair, data.timeframe, startdate, enddate)      
        dataset = datasEntity(datos, data.indicators)
        return JSONResponse(content={"data":json.dumps(dataset)},status_code=200)
    except Exception as e:
        print(e)
        return JSONResponse(content={"message":"Error retrieving data"}, status_code=401)


"""
def getData(data: ReqDataset):
    try:
        dataAllTicks = {}
        if(data["last"]):
            for tick in data["tick"]:
                # devuelve la ultima fila de cada tick
                dataAllTicks[tick] = dataEntity(conn.ticks[tick].find().sort([('opentime', -1)]).limit(1))
        else:
            startdate = datetime.datetime.strptime(data["ini"],"%d/%m/%Y %H:%M:%S")
            enddate = datetime.datetime.strptime(data["end"],"%d/%m/%Y %H:%M:%S")
            for tick in data["tick"]:
                # devuelve una lista con todos los datos entre fechas para cada tick
                dataAllTicks[tick] = datasEntity(conn.ticks[tick].find({'opentime':{'$gte':startdate,'$lt':enddate}}))
        if data["predict"]:
            for tick in data["tick"]:
                dataAllTicks[tick] = predict(dataAllTicks[tick])
        return JSONResponse(content=dataAllTicks,status_code=200)
    except:
        return JSONResponse(content={"message":"Error retrieving data"}, status_code=401)
"""