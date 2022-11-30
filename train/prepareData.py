# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 20:13:24 2022

@author: x4vyjm
"""
import pandas as pd
import numpy as np
from train.helpers import extract_indicators
from squemas.data import datasEntity
import requests
from datetime import datetime
import json
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)
class PrepareData:
    """
    Clase con la cual se agregarán indicadores al dataset del tick dado.
    además se agregara la columna target. Esta clase devolverá el dataset listo para el entrenamiento
    """

    target = []
    dataframe = None
    tick = ""
    timeframe = "5m"
    start = "01-01-2017"
    end = "31-12-2022"
    split = "01-11-2021"
    target = {}
    x_columns = ["open_time","close_time", "high", "close", "open", "low","volume"]
    train_columns = ["volume"]
    train_dataset = pd.DataFrame()
    backtest_dataset = []
    headers = {}
    conn = None

    def __init__(self, configuration, conn):
        self.x_columns = ["open_time","close_time", "high", "close", "open", "low","volume"]
        self.train_columns = ["volume"]
        self.pairs = []
        print(configuration["train_indicators"])
        print(configuration["strategy"]["rules"])
        for item in extract_indicators(configuration["train_indicators"],configuration["strategy"]["rules"]):
            self.x_columns.append(item)
            self.train_columns.append(item)
        self.pairs = [item["pair"]["name"] for item in configuration["strategy"]["strategy_pairs"]]
        self.start = configuration["train_data_start"]
        self.end = configuration["backtest_data_end"]
        self.split = configuration["backtest_data_start"]
        self.timeframe = configuration["timeframe"]
        self.conn = conn
        self.loadDataset()
        
    
    def loadDataset(self):
        for pair in self.pairs:
            startdate = datetime.strptime(self.start, "%d/%m/%Y").timestamp()*1000
            enddate = datetime.strptime(self.end, "%d/%m/%Y").timestamp()*1000
            # devuelve una lista con todos los datos entre fechas para cada tick
            print(f"Get historical data: {pair}, {self.timeframe}, {startdate}, {enddate}")
            datos = self.conn.getHistoricalCandles(pair, self.timeframe, startdate, enddate)      
            dataset = datasEntity(datos, self.x_columns)
            #return JSONResponse(content={"data":json.dumps(dataset)},status_code=200)
            #print(r)
            #print(r.json()["data"])
            #print("$$$$$$$$$$")
            df = pd.DataFrame.from_dict(dataset)
            #print("### df before dropna")
            #print(df.tail(3))
            #print(df.info())
            df = df.set_index("open_time")
            df = df.dropna()
            #print("### df after dropna")
            #print(df)
            #print(df.info())
            #print(f"dateconverted start {self.dateconvert(self.start)}")
            #print(f"dateconverted split {self.dateconvert(self.split)}")
            #print("### Dataframe between: ")
            #print(df.loc[datetime.strptime(self.start, "%d/%m/%Y").timestamp()*1000 : datetime.strptime(self.split, "%d/%m/%Y").timestamp()*1000])
            self.train_dataset = pd.concat([self.train_dataset, df.loc[datetime.strptime(self.start, "%d/%m/%Y").timestamp()*1000 : datetime.strptime(self.split, "%d/%m/%Y").timestamp()*1000]], axis=0)
            #print(self.train_dataset.info())
            aux_df = df.loc[datetime.strptime(self.split, "%d/%m/%Y").timestamp()*1000 : datetime.strptime(self.end, "%d/%m/%Y").timestamp()*1000].reset_index()
            aux_df["open_time"] = pd.to_datetime(aux_df["open_time"], unit="ms")
            aux_df["close_time"] = pd.to_datetime(aux_df["close_time"], unit="ms")
            self.backtest_dataset.append({"pair":pair, "data": aux_df})
        self.train_dataset = self.train_dataset.reset_index()
        self.train_dataset["open_time"] = pd.to_datetime(self.train_dataset["open_time"], unit="ms")
        self.train_dataset["close_time"] = pd.to_datetime(self.train_dataset["close_time"], unit="ms")
        #print(self.train_dataset.info())
        #print(self.train_dataset.tail(5))
        print("######## SUCCESSFUL DATASET LOADER ##########")
    def dateconvert(self,date):
        aux = date.split("/")
        return aux[2]+"-"+aux[1]+"-"+aux[0]
    """
    
    def showGraph(self):
        print(f"### Imprimiendo grafico del dataset")
        dataset1 = self.dataframe.loc[self.graph_start : self.graph_end]
        dataset1 = dataset1.reset_index()
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02)
        fig.add_trace(
            go.Candlestick(
                x=dataset1["open_time"],
                open=dataset1["open"],
                high=dataset1["high"],
                low=dataset1["low"],
                close=dataset1["close"],
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=dataset1["open_time"], y=dataset1["rsi"]), row=2, col=1
        )
        win = 0
        for i in range(len(dataset1["resultado"])):
            temp = dataset1.loc[i:i, "resultado"].values[0]
            # temp1 = dataset1.loc[i:i,'Rsi'].values[0]
            if temp == True:
                fig.add_annotation(
                    x=dataset1.loc[i, "open_time"],
                    y=dataset1.loc[i, "close"],
                    text="▲",
                    showarrow=False,
                    font=dict(size=16, color="blue"),
                )
                win += 1
            # if temp1<target['min_rsi']:
            #    fig.add_annotation(x=dataset1.loc[i,'Open time'], y=dataset1.loc[i,'Close'], text="▲", showarrow=False, font=dict(size=12, color='green'))
        fig.update_layout(xaxis_rangeslider_visible=False, showlegend=True)
        fig.write_html(f"./data/graphs/grafico_data_{self.tick}.html")
        fig.show()

    """
