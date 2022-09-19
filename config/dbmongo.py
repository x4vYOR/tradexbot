from pymongo import MongoClient

class DbBridge():
    
    def __init__(self, host="localhost", port="27017",user = "root", password = None, auth=False):
        if not (auth):
            uri = f"mongodb://{host}:{port}/"
        else:
            uri = f"mongodb://{user}:{password}@{host}:{port}/admin?authSource=admin&authMechanism=SCRAM-SHA-1"
        self.client = MongoClient(uri)
        print("CONEXION EXITOSA A BD")
    
    def saveCandle(self, candle, pair, timeframe):
        try:
            res = self.client[pair][timeframe].insert_one(candle[0])
            print("row insertado")
            return res.inserted_id
        except Exception as e:
            print(e)

    def saveCandles(self, candles, pair, timeframe):
        res = self.client[pair][timeframe].insert_many(candles)
        return res.inserted_ids

    def clearData(self, pair, timeframe):
        try:
            self.client[pair][timeframe].drop()
            return True
        except Exception as e:
            return False

    def hasData(self, pair, timeframe):
        if(self.client[pair][timeframe].find().limit(1).count()>0):
            return True
        return False

    def getLastCandle(self, pair, timeframe):
        res = self.client[pair][timeframe].find().limit(1)
        return res
        
    async def getLastTimestamp(self, pair, timeframe):
        res = self.client[pair][timeframe].find().limit(1)
        return res["open_time"]

    async def getLastNTimestamp(self, pair, timeframe, N):
        res = self.client[pair][timeframe].find().sort("_id", -1).limit(N)
        return [item["open_time"] for item in res]
    
    async def getLastCandleByOpenTime(self, pair, timeframe, openTime):
        return self.client[pair][timeframe].find({"open_time": openTime})[0]

    def getHistoricalCandles(self, pair, timeframe, start, end):
        return self.client[pair][timeframe].find({'open_time':{'$gte':start,'$lt':end}})
