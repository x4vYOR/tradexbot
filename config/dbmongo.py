from pymongo import MongoClient
from uuid import uuid4

class DbBridge():
    
    def __init__(self, host="localhost", port="27017",user = "root", password = None, auth=False):
        if not (auth):
            uri = f"mongodb://{host}:{port}/"
        else:
            uri = f"mongodb://{user}:{password}@{host}:{port}/admin?authSource=admin&authMechanism=SCRAM-SHA-1"
        self.client = MongoClient(host=uri,uuidRepresentation='standard')
        print("CONEXION EXITOSA A BD")
    
    def saveCandle(self, candle, pair, timeframe):
        try:
            res = self.client[pair][timeframe].insert_one(candle[0])
            print("row insertado")
            return res.inserted_id
        except Exception as e:
            print(e)

    def getBot(self, uuid):
        try:
            res = self.client["autotrade"]["bot"].find({"uuid": uuid}).limit(1)
            return res
        except Exception as e:
            print(e)
    def getTradesBot(self, data):
        try:
            bot = self.client["autotrade"]["bot"].find({"uuid": data.uuid}).limit(1)
            return [trade for trade in bot.trades if (trade.pair in data.pairs)]
        except Exception as e:
            print(e)
    def saveBot(self, data):
        try:
            data["uuid"] = uuid4()
            data["status"] = "stopped"
            saved = self.client["autotrade"]["bot"].insert_one(data)
            print("bot insertado")
            res = self.client["autotrade"]["bot"].find({"_id": saved.inserted_id})
            return res
        except Exception as e:
            print(e)
    def updateBot(self, data):
        try:
            saved = self.client["autotrade"]["bot"].update_one(
                {"uuid": data.uuid}, {"$set": data}
            )
            print("bot actualizado")
            if(saved.modified_count>0):
                return True
            else:
                return False
        except Exception as e:
            print(e)
    def setBotStatus(self, data):
        try:
            saved = self.client["autotrade"]["bot"].update_one(
                {"uuid": data.uuid}, {"$set": {'status':data.status}}
            )
            print("status modificado a ",data.status)
            if(saved.modified_count>0):
                return True
            else:
                return False
        except Exception as e:
            print(e)
    
    def getBotStatus(self, uuid):
        try:
            bot = self.client["autotrade"]["bot"].find({"uuid":uuid}).limit(1)
            return bot.status
        except Exception as e:
            print(e)
    def existBot(self, uuid):
        try:
            if(self.client["autotrade"]["bot"].find({"uuid":uuid}).limit(1).count()>0):
                return True
            return False
        except Exception as e:
            print(e)

    def saveTrade(self, data):
        try:
            saved = self.client["autotrade"]["bot"].update_one(
                {"uuid": data.uuid}, {"$push": {'trades':data.trade}}
            )
            print("trade agregado")
            if(saved.modified_count>0):
                return True
            else:
                return False
        except Exception as e:
            print(e)
    def closeTrade(self,data):
        try:
            saved = self.client["autotrade"]["bot"].updateOne(
                {
                    'uuid': data.uuid,
                    'trades': { '$elemMatch': { 'pair': data.trade.pair, 'order_id': data.trade.order_id } }
                },
                { '$set': { "trades.$.closed" : 1, "trades.$.close_price": data.trade.close_price, "trades.$.close_date": data.trade.close_date } }
            )
            if(saved.modified_count>0):
                return True
            else:
                return False
        except Exception as e:
            print(e)
    
    def updateBotCapitalPair(self,data):
        try:
            saved = self.client["autotrade"]["bot"].updateOne(
                {
                    'uuid': data.uuid,
                    'capital_pair': { '$elemMatch': { 'pair': data.pair } }
                },
                { '$set': { "capital_pair.$.available_capital": data.available_capital } }
            )
            if(saved.modified_count>0):
                return True
            else:
                return False
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
