# -*- coding: utf-8 -*-
"""
Created on Wed Apr 20 19:36:14 2022

@author: x4vyjm
"""
from src.prepareData import PrepareData
from strategies.Strategies import AcumulatorStrategy
import joblib
import datetime
import ast
import requests
import json
import numpy as np
import pandas as pd
from pandas import json_normalize


class Trader:
    """
    Main Class thqt
    """

    models = []
    scalers = []
    dataset = None
    conn = None
    bc = None
    timeframe = ""
    pair = ""
    objData = None
    configuration = None
    scaler = None
    n_decimals = 0
    nomodel = False
    all = False

    def __init__(self, BinanceClient, timeframe, pair, configuration, all=False):
        """
        Parameters
        ----------
        BinanceClient : object
            Binance client object.
        timeframe : string
            Timeframe for tick.
        pair : string
            Ticker or symbol for trade
        configuration : object
            Configuration object.
        Returns
        -------
        None.
        """
        self.bc = BinanceClient
        self.timeframe = timeframe
        self.pair = pair
        self.configuration = configuration
        self.all = all
        if(all):
            self.objData = []
            self.conn = []
            for tick in self.pair:
                self.objData.append(PrepareData(
                    tick,
                    timeframe,
                    configuration.indicators,
                    limit=True,
                    target_dict=configuration.target,
                ))
                print("############### dataset #################")
                print(self.objData[0].getXColumnsExceptPrice())
                self.conn.append(self.objData[-1].conn)
        else:
            self.objData = PrepareData(
                pair,
                timeframe,
                configuration.indicators,
                limit=True,
                target_dict=configuration.target,
            )
            print("############### dataset #################")
            print(self.objData.getXColumnsExceptPrice())
            self.conn = self.objData.conn
        if not self.configuration.target["use_histogram_reverse"] and not self.configuration.bot["one_model_all_ticks"]:
            self.getBestResult()

        self.check_decimals()
        
        if(self.all):
            self.objStrategy = []
            for i in range(len(self.pair)):
                self.objStrategy.append(AcumulatorStrategy(
                    self.configuration.backtests[0],
                    self.pair[i],
                    self.timeframe,
                    self.conn[i],
                    self.n_decimals[i],
                    self.bc,
                ))   
        else:
            self.objStrategy = AcumulatorStrategy(
                self.configuration.backtests[0],
                self.pair,
                self.timeframe,
                self.conn,
                self.n_decimals,
                self.bc,
            )

    def getBestResult(self, column="profit"):
        """
        Parameters
        ----------
        column : string, optional
            Get the best train by "column" (ie. 'profit', 'f1' or 'roc'). The default is "profit".
            Then loads the trained models in an array (models) also load the scaler (scaler) used for training.
        Returns
        -------
        None.

        """
        cur = self.conn.cursor()
        command = "SELECT * FROM MODEL ORDER BY " + str(column) + " DESC LIMIT 1"
        cur.execute(command)
        rows = cur.fetchall()
        self.models = []
        self.scalers = []
        # if "All" in str(rows[0][2]):
        #    for mod in ast.literal_eval(str(rows[0][3])):
        #        print(mod)
        #        self.models.append(joblib.load(mod))
        # else:
        for row in rows:
            self.models.append(joblib.load(row[12]))
            self.scalers.append(joblib.load(row[13]))
        # self.scaler = joblib.load(rows[0][4])

        self.configuration.backtests[0] = ast.literal_eval(str(rows[0][8]))
        self.configuration.target = ast.literal_eval(str(rows[0][9]))
        self.configuration.indicators = ast.literal_eval(str(rows[0][23]))

    def checkLastCandle(self):
        """
        Returns
        -------
        ds : dataset
            last row dataframe with buy signal.
        """
        print("### Revisar ultima vela")
        now = datetime.datetime.now()
        time_divisor = {
            "5m": 5,
            "30m": 30,
            "15m": 15,
            "1h": 60,
            "4h": 240
        }
        exact_timeframe = now.minute % time_divisor[self.timeframe] == 0
        if exact_timeframe:
            print("### Revisar ultima vela: llamada cada timeframe")
            if(self.all):
                for obj in self.objData:                    
                    obj.loadDataset(True)
                    print("############### dataset #################")
                    print(obj.getXColumnsExceptPrice())
            else:
                self.objData.loadDataset(True)
            if self.configuration.target["use_histogram_reverse"]:
                self.objData.addTarget()
            if(self.all):
                lr = pd.DataFrame()
                for obj in self.objData:
                    lr = pd.concat([lr,self.objData.getLastRow()])
                print("df de ultimas velas en conjunto: ",lr)
            else:
                lr = self.objData.getLastRow()
            lr["open_time"] = pd.to_datetime(lr["open_time"], unit="ms")
            lr["close_time"] = pd.to_datetime(lr["close_time"], unit="ms")
            lr = lr.set_index("open_time")
            if(self.all):
                X_col = lr[self.objData[0].getXColumnsExceptPrice()]
            else:
                X_col = lr[self.objData.getXColumnsExceptPrice()]
            print("######### dataset ##########")
            print(X_col)
            aux1 = None
            if self.all:
                aux1 = self.callModelAPI(X_col)
                lr["buy"] = aux1["buy"]
            else:
                if not (self.configuration.target["use_histogram_reverse"]):
                    flag = 0
                    index = 0
                    for model in self.models:
                        ds = self.scalers[index].transform(X_col)
                        print("############### dataset #################")
                        print(ds)
                        pred = model.predict(ds)
                        aux = np.where(pred == True, 1, 0)
                        if flag == 0:
                            aux1 = aux
                            flag = 1
                        else:
                            aux1 += aux
                        index += 1
                else:
                    aux1 = np.where(lr["resultado"] == True, 10, 0)
                lr["buy"] = np.where(aux1 >= 1, True, False)
        else:
            print("### Revisar ultima vela: llamada cada minuto")
            candles = self.bc.get_klines(symbol=self.pair, interval="1m", limit=1)
            lr = pd.DataFrame(candles)
            lr.columns = [
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
            lr = lr[["close"]]
            lr["buy"] = False
        if(self.all):
            for i in range(len(self.objStrategy)):
                self.objStrategy[i].process(lr.iloc[i], exact_timeframe)
        else:
            self.objStrategy.process(lr, exact_timeframe)

    def check_decimals(self):
        print("### Obteniendo informacion de decimales")
        if(self.all):
            self.n_decimals = []
            for tick in self.pair:
                info = self.bc.get_symbol_info(tick)
                val = info["filters"][2]["stepSize"]
                decimal = 0
                is_dec = False
                for c in val:
                    if is_dec is True:
                        decimal += 1
                    if c == "1":
                        break
                    if c == ".":
                        is_dec = True
                self.n_decimals.append(decimal)
        else:
            info = self.bc.get_symbol_info(self.pair)
            val = info["filters"][2]["stepSize"]
            decimal = 0
            is_dec = False
            for c in val:
                if is_dec is True:
                    decimal += 1
                if c == "1":
                    break
                if c == ".":
                    is_dec = True
            self.n_decimals = decimal
    def callModelAPI(self,df):
        parsed = json.loads(df.to_json(orient="records"))
        print("Parsed: ",parsed)
        # sending post request and saving response as response object
        res = requests.post(url = self.configuration.bot["host_model"], json = parsed)
        print("response: ",res)
        df = json_normalize(res.json())
        print("df devuelto: ",df)
        return df
        

