# -*- coding: utf-8 -*-
from websocket import WebSocketApp
import pandas as pd
import datetime
import json
from dbmongo import DbBridge
from binance import Client
import os
import talib as ta
import numpy as np
from os import getenv

class saveData:

    pairs = []
    timeframe = ""
    binanceClient = Client(tld='us')    
    conn = DbBridge(password=getenv("MONGO_PASSWORD"), auth = True)
    start = "01-01-2017"
    end = "20-12-2023"
    sock_uri = ""
    pair_buffer = {}
    indicators = []
    #df.shift(1) df.loc[0] = new_row

    def __init__(self, ticks, timeframe = "15m", start = "01-01-2017", end = "20-12-2023", indicators = None):
        self.pairs = ticks
        self.timeframe = timeframe
        self.start = start
        self.end = end
        self.indicators = indicators

    def loadDB(self):
        #(open_time datetime primary key, open float, high float, low float, close float, volume double, close_time datetime)
        for pair in self.pairs:
            print(f"### Cargando data en {pair} {self.timeframe} ###")
            self.conn.clearData(pair, self.timeframe)
            df = self.getHistoricalData(pair)
            df1 = self.getLastMonthData(pair)
            df2 = self.getLastDayData(pair)
            df = pd.concat([df.head(-1), df1], axis=0)
            df = pd.concat([df.head(-1), df2.head(-1)], axis=0)
            df = df.set_index("open_time")
            df = df[~df.index.duplicated(keep="first")]
            df = df.reset_index()
            df = df.apply(pd.to_numeric, errors='ignore')
            df = self.addIndicators(df)
            self.conn.saveCandles(df.to_dict('records'), pair, self.timeframe)
            self.pair_buffer[pair] = df.tail(300)
            print("len inicial:  ",len(self.pair_buffer[pair]))
            df = df.iloc[0:0]

    def getHistoricalData(self, pair):
        print(f"### Obteniendo data historica {pair} {self.timeframe} ###")
        path = f"./data/ticks/{pair}{self.timeframe}.json"
        file_exists = os.path.exists(path)
        if not file_exists:
            klines = self.binanceClient.get_historical_klines(
                pair,
                interval=self.timeframe,
                start_str=self.start,
                end_str=self.end,
            )
            fi = open(path, "w")
            fi.write(json.dumps(klines))
            fi.close()
        print("### Leyendo datos de archivo: ", path)
        df = pd.read_json(path)
        df.columns = [
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "Quote asset volume",
            "Number of trades",
            "Taker buy base asset volume",
            "Taker buy quote asset volume",
            "ignore",
        ]
        df = df.drop(
            [
                "Quote asset volume",
                "Number of trades",
                "Taker buy base asset volume",
                "Taker buy quote asset volume",
                "ignore",
            ],
            axis=1,
        )
        return df

    def getLastMonthData(self, pair):
        print(f"### Obteniendo data del ultimo mes {pair} {self.timeframe}")
        start = datetime.date.today() - datetime.timedelta(days=30)
        df = pd.DataFrame(
            self.binanceClient.get_historical_klines(
                pair,
                interval=self.timeframe,
                start_str=str(start),
                end_str=str(datetime.date.today()),
            )
        )
        df.columns = [
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "Quote asset volume",
            "Number of trades",
            "Taker buy base asset volume",
            "Taker buy quote asset volume",
            "ignore",
        ]
        df = df.drop(
            [
                "Quote asset volume",
                "Number of trades",
                "Taker buy base asset volume",
                "Taker buy quote asset volume",
                "ignore",
            ],
            axis=1,
        )
        return df

    def getLastDayData(self, pair):
        print(f"### Obteniendo data del dia {pair} {self.timeframe}")
        df = pd.DataFrame(
            self.binanceClient.get_historical_klines(
                pair, self.timeframe, "1 day ago UTC"
            )
        )
        df.columns = [
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "Quote asset volume",
            "Number of trades",
            "Taker buy base asset volume",
            "Taker buy quote asset volume",
            "ignore",
        ]
        df = df.drop(
            [
                "Quote asset volume",
                "Number of trades",
                "Taker buy base asset volume",
                "Taker buy quote asset volume",
                "ignore",
            ],
            axis=1,
        )
        return df
    
    def getRecentData(self, pair):
        print(f"### Obteniendo data del dia {pair} {self.timeframe}")
        df = pd.DataFrame(
            self.binanceClient.get_historical_klines(
                pair, self.timeframe, "1 hour ago UTC"
            )
        )
        df.columns = [
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "Quote asset volume",
            "Number of trades",
            "Taker buy base asset volume",
            "Taker buy quote asset volume",
            "ignore",
        ]
        df = df.drop(
            [
                "Quote asset volume",
                "Number of trades",
                "Taker buy base asset volume",
                "Taker buy quote asset volume",
                "ignore",
            ],
            axis=1,
        )
        df = df.head(-1)
        return df

    def on_open(self,ws):
        print("open")

    def on_close(self, ws, close_status_code, close_msg):
        print("closed")

    def on_message(self, ws, message):
        json_message = json.loads(message) 
        candle = json_message['data']['k']  
        #print(candle["s"])
        is_candle_closed = candle['x']
        if is_candle_closed:
            self.refreshBuffer(self.toDataframe(candle),candle["s"])
    
    def toDataframe(self,msg):
        df = pd.DataFrame([msg])
        df = df.loc[:,['t','o','h','l','c','v','T']]
        df.columns = ["open_time", "open", "high", "low", "close", "volume", "close_time"]
        return df

    def refreshBuffer(self, df, pair):
        #print("###########################################")
        #obtengo las 6 ultimas velas (opentime) de la BD
        lastTimestamps = self.conn.getLastNTimestamp(pair,self.timeframe,15)
        # me quedo con los que no se repiten
        #print(lastTimestamps)
        #print(df["open_time"])
        #print(type(lastTimestamps[0]))
        #print("LEN antes")
        #print(len(df))
        df = df.drop(df[df["open_time"].isin(lastTimestamps)].index)
        #print("LEN despues")
        #print(len(df))
        #actualizo el buffer con esos datos no repetidos
        if(len(df)>0):
            #print("len buffer antes: ",len(self.pair_buffer[pair]))
            self.pair_buffer[pair] = self.pair_buffer[pair].shift(-len(df))
            #print("len buffer despues: ",len(self.pair_buffer[pair]))
            #print(self.pair_buffer[pair])
            #print("##### buffer")
            #print(self.pair_buffer[pair].iloc[-len(df):,0:7])
            #print("##### new data")
            #print(df)
            #print("len buffer antes unir con df nuevo: ",len(self.pair_buffer[pair]))
            self.pair_buffer[pair].iloc[-len(df):,0:7] = df
            #print("len buffer despues unir con df nuevo: ",len(self.pair_buffer[pair]))
            #añado indicadores sobre el buffer
            self.pair_buffer[pair] = self.addIndicators(self.pair_buffer[pair])
            #print("len buffer despues añadir indicadores: ",len(self.pair_buffer[pair]))
            # guardo los datos no repetidos desde el buffer hacia la base de datos
            if(len(df)==1):
                try:
                    #print("len buffer: ",len(self.pair_buffer[pair]))
                    #print("open_time inserted: ",df["open_time"])
                    #print("buffer iloc: ", self.pair_buffer[pair].iloc[-len(df):])
                    #print("Lo que se va giardar: ",self.pair_buffer[pair].iloc[-len(df):].to_dict('records'))
                    response = self.conn.saveCandle(self.pair_buffer[pair].iloc[-len(df):].to_dict('records'),pair,self.timeframe)
                    #print("solo unoooo")
                    #print(response)
                except Exception as e:
                    print(e)
            else:
                #print("open_time insertedes: ",df["open_time"])
                self.conn.saveCandles(self.pair_buffer[pair].iloc[-len(df):].to_dict('records'),pair,self.timeframe)
            

    def startWebSocket(self):
        sock_uri = "wss://stream.binance.com:9443/stream?streams="
        # iterar de nuevo sobre los pares obteniendo las velas de la ultima hora
        for index,pair in enumerate(self.pairs):
            df = self.getRecentData(pair)
            
            self.refreshBuffer(df,pair)
            #luego de iterar sobre todos, genero la cadena de conexion de ws
            # ethusdt@kline_1m/btcusdt@kline_1m/bnbusdt@kline_1m/ethbtc@kline_1m
            sock_uri += (pair.lower()+'@kline_'+self.timeframe) if index == 0 else ('/'+pair.lower()+'@kline_'+self.timeframe)
            #retorno la instancia de websocket
        print(sock_uri)
        ws = WebSocketApp(sock_uri, on_open=self.on_open,on_close=self.on_close, on_message=self.on_message)
        return ws

    def addIndicators(self,dataframe):
        print(f"### Añadiendo indicadores al dataset ###")
        dataframe = dataframe.apply(pd.to_numeric, errors='ignore')
        for indicator in self.indicators:
            if indicator == "rsi":
                dataframe["rsi"] = ta.RSI(dataframe["close"], timeperiod=14)
            elif indicator == "obv":
                dataframe["obv"] = ta.OBV(
                    dataframe["close"], dataframe["volume"]
                )
            elif indicator == "atr":
                dataframe["atr"] = ta.ATR(
                    dataframe["high"],
                    dataframe["low"],
                    dataframe["close"],
                    timeperiod=14,
                )
            elif indicator == "adx":
                dataframe["adx"] = ta.ADX(
                    dataframe["high"],
                    dataframe["low"],
                    dataframe["close"],
                    timeperiod=14,
                )
            elif indicator == "cci":
                dataframe["cci"] = ta.CCI(
                    dataframe["high"],
                    dataframe["low"],
                    dataframe["close"],
                    timeperiod=14,
                )
            elif indicator == "mfi":
                dataframe["mfi"] = ta.MFI(
                    dataframe["high"],
                    dataframe["low"],
                    dataframe["close"],
                    dataframe["volume"],
                    timeperiod=14,
                )
            elif indicator == "mom":
                dataframe["mom"] = ta.MOM(
                    dataframe["close"],
                    timeperiod=10,
                )
            elif indicator == "macd":
                (
                    dataframe["macd"],
                    dataframe["macd_signal"],
                    dataframe["macd_hist"],
                ) = ta.MACD(
                    dataframe["close"],
                    fastperiod=12,
                    slowperiod=26,
                    signalperiod=9,
                )
            elif indicator == "bbands":
                (
                    dataframe["upperband"],
                    dataframe["middleband"],
                    dataframe["lowerband"],
                ) = ta.BBANDS(
                    dataframe["close"],
                    timeperiod=5, nbdevup=2, nbdevdn=2, matype=0
                )
            
            elif indicator == "ema12":
                dataframe["ema12"] = ta.EMA(dataframe["close"], timeperiod=12)
            elif indicator == "ema9":
                dataframe["ema9"] = ta.EMA(dataframe["close"], timeperiod=9)
            elif indicator == "ema24":
                dataframe["ema24"] = ta.EMA(dataframe["close"], timeperiod=24)
            elif indicator == "ema21":
                dataframe["ema21"] = ta.EMA(dataframe["close"], timeperiod=21)
            elif indicator == "ema50":
                dataframe["ema50"] = ta.EMA(dataframe["close"], timeperiod=50)
            elif indicator == "ema100":
                dataframe["ema100"] = ta.EMA(
                    dataframe["close"], timeperiod=100
                )
            elif indicator == "ema200":
                dataframe["ema200"] = ta.EMA(
                    dataframe["close"], timeperiod=200
                )
            elif indicator == "ema400":
                dataframe["ema400"] = ta.EMA(
                    dataframe["close"], timeperiod=400
                )
            elif indicator == "change":
                dataframe["change"] = (
                    (dataframe["close"] - dataframe["open"])
                    / dataframe["open"]
                ) * 100
            elif indicator == "cambio":
                dataframe["cambio"] = (
                    (dataframe["close"] - dataframe["open"])
                    / dataframe["open"]
                ) * 100
        #dataframe = dataframe.dropna()
        return dataframe
