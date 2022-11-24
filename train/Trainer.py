# -*- coding: utf-8 -*-
"""
Created on Mon Apr 11 16:49:57 2022

@author: x4vyjm
"""
import pandas as pd
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn import svm
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import plot_roc_curve, f1_score, roc_auc_score
from sklearn.metrics import accuracy_score, classification_report
from sklearn.metrics import (
    confusion_matrix,
    plot_confusion_matrix,
    ConfusionMatrixDisplay,
)
import xgboost as xgb
import joblib
import train.backtestStrategies as bs
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime
import json
import ast
import os
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

class Trainer:
    dataset = None
    backtest_dataset = None
    models = []
    backtest = []
    scaler = None
    trained_models = []
    x_columns = []
    x_columns_except_price = []
    y_column = ""
    only_oversell = True
    test_size = 0.2
    below_rsi = 28
    random_state = 0
    X_train = None
    X_test = None
    y_train = None
    y_test = None
    db_name = ""
    conn = None
    train_id = 0
    train_model = ""
    pair = ""
    timeframe = ""
    configuration = []
    sql_file = None
    all = False
    model = None

    def __init__(self, configuration, dataset, train_columns, backtest_dataset,conn, checksum, y_columns="target"):
        self.conf = configuration
        self.dataset = self.addTarget(configuration, dataset)
        self.backtest_dataset = backtest_dataset
        self.train_columns= train_columns
        self.y_columns = y_columns
        self.splitData()
        self.conn = conn
        self.checksum = checksum
    
    def addTarget(self,config, dataset):
        rules = config["strategy"]["rules"]
        strategy_parameters = config["strategy"]["strategy_parameters"]
        dataset["target"] = True
        """ 
        Precedencia : 
            1 - rules
                    Sirve para definir las zonas o puntos de compra/venta basado en las condiciones refinidas.
            2 - strategy_parameters["target"]
                    Sirven para marcar puntos de compra basado en los rendimientos esperados. Por ejemplo: si nosotros compramos cuando el precio rompe al alza la ema200, para marcarlo 
                    como punto de compra exitoso debemos evaluar que, si comprando en esa señal obtenemos el beneficio definido, tambien descartamos si sobrepasa el stop loss definido.
            3 - strategy_parameters["filter"]
                    Son parametros que definen los filtros sobre dataset de entrenamiento. Es decir, se removeran los datos que no cumplan la restriccion.

        """
        print("######## APPLY RULES ###########")

        for rule in rules:
            if rule["condition"]["name"] in ["Below","Minor"]:
                if(rule["second_indicator"]["name"] != "value"):
                    dataset["target"] = dataset["target"] & np.where(dataset[rule["first_indicator"]["name"]] < dataset[rule["second_indicator"]["name"]], True, False)
                else:
                    dataset["target"] = dataset["target"] & np.where(dataset[rule["first_indicator"]["name"]] < rule["value"], True, False)

            elif rule["condition"]["name"] == "Crosses Up":
                if(rule["second_indicator"]["name"] != "value"):
                    dataset["target"] = dataset["target"] & np.where(
                        (
                            (dataset[rule["first_indicator"]["name"]].shift(1) < dataset[rule["second_indicator"]["name"]].shift(1)) &
                            (dataset[rule["first_indicator"]["name"]] > dataset[rule["second_indicator"]["name"]]) 
                        )
                        , True, False)
                else:
                    dataset["target"] = dataset["target"] & np.where(
                        (
                            (dataset[rule["first_indicator"]["name"]].shift(1) < rule["value"]) &
                            (dataset[rule["first_indicator"]["name"]] > rule["value"])
                        )    
                        , True, False)
                            
            elif rule["condition"]["name"] in ["Above","Major"]:
                if(rule["second_indicator"]["name"] != "value"):
                    dataset["target"] = dataset["target"] & np.where(dataset[rule["first_indicator"]["name"]] > dataset[rule["second_indicator"]["name"]], True, False)
                else:
                    dataset["target"] = dataset["target"] & np.where(dataset[rule["first_indicator"]["name"]] > rule["value"], True, False)

            elif rule["condition"]["name"] == "Crosses Down":
                if(rule["second_indicator"]["name"] != "value"):
                    dataset["target"] = dataset["target"] & np.where(
                        (
                            (dataset[rule["first_indicator"]["name"]].shift(1) > dataset[rule["second_indicator"]["name"]].shift(1)) &
                            (dataset[rule["first_indicator"]["name"]] < dataset[rule["second_indicator"]["name"]]) 
                        )
                        , True, False)
                else:
                    dataset["target"] = dataset["target"] & np.where(
                        (
                            (dataset[rule["first_indicator"]["name"]].shift(1) > rule["value"]) &
                            (dataset[rule["first_indicator"]["name"]] < rule["value"])
                        )    
                        , True, False)

            elif rule["condition"]["name"] == "Equal":
                if(rule["second_indicator"]["name"] != "value"):
                    dataset["target"] = dataset["target"] & np.where(dataset[rule["first_indicator"]["name"]] == dataset[rule["second_indicator"]["name"]], True, False)
                else:
                    dataset["target"] = dataset["target"] & np.where(dataset[rule["first_indicator"]["name"]] == rule["value"], True, False)

            elif rule["condition"]["name"] == "Distinct":
                if(rule["second_indicator"]["name"] != "value"):
                    dataset["target"] = dataset["target"] & np.where(dataset[rule["first_indicator"]["name"]] != dataset[rule["second_indicator"]["name"]], True, False)
                else:
                    dataset["target"] = dataset["target"] & np.where(dataset[rule["first_indicator"]["name"]] != rule["value"], True, False)

            elif rule["condition"]["name"] == "Reached":
                if(rule["second_indicator"]["name"] != "value"):
                    dataset["target"] = dataset["target"] & np.where(
                        (
                            (dataset[rule["first_indicator"]["name"]].shift(1) < dataset[rule["second_indicator"]["name"]].shift(1)) &
                            (dataset[rule["first_indicator"]["name"]] >= dataset[rule["second_indicator"]["name"]]) 
                        )
                        , True, False)
                else:
                    dataset["target"] = dataset["target"] & np.where(
                        (
                            (dataset[rule["first_indicator"]["name"]].shift(1) < rule["value"]) &
                            (dataset[rule["first_indicator"]["name"]] >= rule["value"])
                        )    
                        , True, False)

        print("####  CREANDO COLUMNA OBJETIVO CON PROFIT Y STOP EN N VELAS ####")
        # ¿dentro de las 6 siguientes velas, si comprara en precio de cierre, alcanza un "beneficio"% de ganancia?
        datasetclose = pd.DataFrame()
        datasetclose["close"] = dataset["close"]
        datasetclose["high"] = dataset["high"]
        datasetclose["result1"] = False
        for n in range(int(strategy_parameters["target"]["target_profit_candles"])):
            datasetclose["aux"] = datasetclose["high"].shift(-1 * (n + 1))
            datasetclose["result1"] = datasetclose["result1"] | (
                np.where(
                    datasetclose["aux"]
                    >= datasetclose["close"] * (1 + strategy_parameters["target"]["target_profit"]),
                    True,
                    False,
                )
            )

        # ¿dentro de las "n_riesgo" siguientes velas, si comprara en precio de cierre, perderé "riesgo"% ?
        datasetclose["result2"] = True
        for n in range(int(strategy_parameters["target"]["target_risk_candles"])):
            datasetclose["aux"] = datasetclose["close"].shift(-1 * (n + 1))
            datasetclose["result2"] = datasetclose["result2"] & (
                np.where(
                    datasetclose["aux"]
                    <= datasetclose["close"] * (1 - float(strategy_parameters["target"]["target_risk"])),
                    False,
                    True,
                )
            )
        dataset["target"] = dataset["target"] & (
            datasetclose["result1"]
            & datasetclose["result2"]
        )

        #if not self.target["use_histogram_reverse"]:
        #dataset["open_time"] = pd.to_datetime(
        #    dataset["open_time"], unit="ms"
        #)
        #dataset["close_time"] = pd.to_datetime(
         #   dataset["close_time"], unit="ms"
        #)
        #dataset.set_index("open_time")
        #print("###### Columnas despues de poner target: ", self.dataframe.columns)
        #print(self.dataframe)
        #self.showGraph()
        print("######## SUCCESSFUL TARGET ADDED ###########")
        return dataset

    def splitData(self):
        print("####### SPLIT DATA: ",float(self.conf["training_detail"]["data_split"])/100)
        print(self.train_columns)
        print(self.dataset.info())
        X_Cols = self.dataset[self.train_columns]
        print("X_Cols: ")
        print(X_Cols)
        Y_Cols = self.dataset[self.y_columns]
        print("Y_Cols: ")
        print(Y_Cols)
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X_Cols, Y_Cols, test_size=float(self.conf["training_detail"]["data_split"])/100, random_state=0
        )
        print("x_train: ")
        print(self.X_train)
        print("X_test: ")
        print(self.X_test)
        print("y_train: ")
        print(self.y_train)
        print("y_test: ")
        print(self.y_test)
        self.scaler = StandardScaler()
        self.X_train = self.scaler.fit_transform(self.X_train)
        self.X_test = self.scaler.transform(self.X_test)
        print("### success splitted")

    def predictModel(self, model, dataset, escalado=False):
        if escalado:
            dataset = self.scaler.transform(dataset)
        y_pred = model.predict(dataset)
        return y_pred

    def train(self):
        #self.conf = configuration
        # self.trained_models = []
        response = []
        aux_response = {}
        self.nombre_scaler = (
            "./ml/models/scalers/"
            + "_"
            + str(self.conf["id"])
            + "_"
            + datetime.now().strftime("%d%m%Y%I%M%S%p")
            + ".joblib"
        )
        
        print("--------- ENTRENAMIENTO ---------")
        # nombre_modelos = []
        for mod in self.conf["training_detail"]["algorithm_details"]:
            status_train = self.conn.getTrainStatus(self.checksum)
            print(status_train)
            if status_train["status"] == "stopped":
                print("status is stopped")
                return []
            aux_response["scaler"] = self.nombre_scaler
            aux_response["train_columns"] = self.train_columns
            if mod["algorithm"]["name"] == "RandomForest":
                self.model, best_params, nombre_modelo = self.entrenarRF(mod)
            elif mod["algorithm"]["name"]  == "KNN":
                self.model, best_params, nombre_modelo = self.entrenarKNN(mod)
            elif mod["algorithm"]["name"]  == "SVM":
                self.model, best_params, nombre_modelo = self.entrenarSVM(mod)
            elif mod["algorithm"]["name"]  == "XGBoost":
                self.model, best_params, nombre_modelo = self.entrenarXGB(mod)
            self.y_pred = self.predictModel(self.model, self.X_test)
            status_train = self.conn.getTrainStatus(self.checksum)
            print(status_train)
            if status_train["status"] == "stopped":
                print("status is stopped")
                return []
            accu, prec, rec, spec, f1, roc, tn, tp, fn, fp = self.metrics(
                self.y_test, self.y_pred
            )
            aux_response["model"] = {
                "name": mod["algorithm"]["name"], 
                "file": nombre_modelo, 
                "metrics": [
                    {"name": "F1-score", "value": f1},
                    {"name": "ROC", "value": roc},
                    {"name": "Specificity", "value": spec},
                    {"name": "Accuracy", "value": accu},
                    {"name": "Recall", "value": rec},
                    {"name": "Precision", "value": prec},
                    {"name": "TP", "value": tp},
                    {"name": "TN", "value": tn},
                    {"name": "FP", "value": fp},
                    {"name": "FN", "value": fn}
                ],
                "model_best_parameters": best_params
            }
            backtest_response = []
            for backtest_data in self.backtest_dataset:
                status_train = self.conn.getTrainStatus(self.checksum)
                print(status_train)
                if status_train["status"] == "stopped":
                    print("status is stopped")
                    return []
                backtest_data["data"] = self.addTarget(self.conf, backtest_data["data"])
                y_pred = self.predictModel(self.model, backtest_data["data"][self.train_columns], True) 
                backtest_data["data"]["predicted"] = y_pred
                chart_funds, chart_candles,backtest_name,backtest_conf,profit,n_buys,n_buysacum,maxdowndraw = self.backtest(backtest_data["data"], mod["algorithm"]["name"]+'_'+backtest_data["pair"], self.conf["strategy"])
                backtest_response.append({"pair": backtest_data["pair"], "chart_candles": chart_candles, "chart_funds": chart_funds, 
                    "metrics":  [
                        {"name": "% Profit", "value": profit},
                        {"name": "Max Drawdown", "value": maxdowndraw},
                        {"name": "N Buys", "value": n_buys},
                        {"name": "N BuysAcum", "value": n_buysacum}
                    ]
                })
            aux_response["backtest"] = backtest_response
            response.append(aux_response)
            aux_response = {}
        
        joblib.dump(self.scaler, self.nombre_scaler, 3)
        """
        # eliminar el modelo entrenado para ahorrar espacio
        if os.path.exists(nombre_modelo):
            os.remove(nombre_modelo)
        if os.path.exists(nombre_modelo):
            os.remove(nombre_modelo)
        if escalador_usado == 0:
            # eliminar el escalador para ahorrar espacio
            if os.path.exists(nombre_scaler):
                os.remove(nombre_scaler)
        """
        print(response)
        status_train = self.conn.getTrainStatus(self.checksum)
        print(status_train)
        if status_train["status"] == "stopped":
            print("status is stopped")
            return []
        return response   
        

    def backtest(self, dataset, model_name, strat):
        if strat["buy_strategy"]["name"] == "reverse_ratio_0_5":
            strategy = bs.Reverse_ratio_0_5(
                strat["parameters"]["initial_capital"],
                strat["parameters"]["profit"],
                strat["parameters"]["loss"],
                strat["parameters"]["amount_per_trade"],
                strat["parameters"]["distance"],
            )
            strategy.procesarDataset(dataset[["predicted", "close", "high", "low"]])
            dataset["buy"] = strategy.lista_buys
            dataset["sell"] = strategy.lista_sells
            dataset["capital"] = strategy.lista_fondos
            titulo = self.train_name + "_" + model_name + "_" + strat["name"]
            name_evol = (
                "./train/backtest/fondos_"
                + datetime.now().strftime("%d%m%Y%I%M%S%p")
                + ".html"
            )
            name_chart = (
                "./train/backtest/chart_"
                + datetime.now().strftime("%d%m%Y%I%M%S%p")
                + ".html"
            )
            self.chartBacktesting(dataset, name_chart, titulo)
            self.chartEvolution(
                dataset.loc[:, ["close_time", "capital"]],
                "close_time",
                "capital",
                "Capital " + titulo,
                name_evol,
            )

        if strat["buy_strategy"]["name"] == "Incremental Buys":
            strat_params = strat["strategy_parameters"]
            print(strat_params)
            print(strat_params["backtest"]["backtest_initial_max"][0])
            strategy = bs.Promedio_creciente(
                self.conf["trading_setup"]["capital"],
                strat_params["backtest"]["backtest_initial_max"][0],
                strat_params["backtest"]["backtest_initial_max"][1],
                strat_params["target"]["target_profit"],
                strat_params["backtest"]["backtest_distance"],
            )
            strategy.procesarDataset(dataset[["predicted", "close", "high"]])
            dataset["buy"] = strategy.lista_buys
            dataset["sell"] = strategy.lista_sells
            dataset["capital"] = strategy.lista_fondos
            dataset["invertido"] = strategy.lista_invertido
            titulo = model_name + "_" + strat["buy_strategy"]["name"].replace(" ","_")
            name_evol = (
                "./train/backtest/fondos_"
                + datetime.now().strftime("%d%m%Y%I%M%S%p")
                + ".html"
            )
            name_chart = (
                "./train/backtest/chart_"
                + datetime.now().strftime("%d%m%Y%I%M%S%p")
                + ".html"
            )
            print("Evaluando profit: ", strategy.lista_fondos[-1])
            #if (
            #    strategy.lista_fondos[-1]
            #    > float(strat["parameters"]["initial_capital"]) * 1.01
            #):
            self.chartBacktesting(dataset, name_chart, titulo)
            self.chartEvolution(
                dataset.loc[:, ["close_time", "capital"]],
                "close_time",
                "capital",
                "Capital " + titulo,
                name_evol,
            )
            maxdowndraw = self.calc_MDD(dataset["capital"])
            return (
                name_evol,
                name_chart,
                strat["buy_strategy"]["name"],
                strat,
                strategy.lista_fondos[-1],
                strategy.lista_buys.count(True),
                max(strategy.lista_periodos) if len(strategy.lista_periodos)>0 else 0,
                maxdowndraw["mdd"].values[-1]
            )

        if strat["buy_strategy"]["name"] == "promedio_creciente_dos":
            strategy = bs.Promedio_creciente_dos(
                strat["parameters"]["initial_capital"],
                strat["parameters"]["max_buys"],
                strat["parameters"]["initial_divisor"],
                strat["parameters"]["profit"],
                strat["parameters"]["distance"],
            )
            strategy.procesarDataset(dataset[["predicted", "close", "high"]])
            dataset["buy"] = strategy.lista_buys
            dataset["sell"] = strategy.lista_sells
            dataset["capital"] = strategy.lista_fondos
            dataset["invertido"] = strategy.lista_invertido
            titulo = self.train_name + "_" + model_name + "_" + strat["name"]
            name_evol = (
                "./train/backtest/fondos_"
                + datetime.now().strftime("%d%m%Y%I%M%S%p")
                + ".html"
            )
            name_chart = (
                "./train/backtest/chart_"
                + datetime.now().strftime("%d%m%Y%I%M%S%p")
                + ".html"
            )
            self.chartBacktesting(dataset, name_chart, titulo)
            self.chartEvolution(
                dataset.loc[:, ["close_time", "capital"]],
                "close_time",
                "capital",
                "Capital " + titulo,
                name_evol,
            )

            return (
                name_evol,
                name_chart,
                strat["name"],
                strat,
                strategy.lista_fondos[-1],
                strategy.lista_buys.count(True),
                max(strategy.lista_periodos),
            )

        if strat["buy_strategy"]["name"] == "promedio_creciente_tres":
                strategy = bs.Promedio_creciente_tres(
                    strat["parameters"]["initial_capital"],
                    strat["parameters"]["max_buys"],
                    strat["parameters"]["initial_divisor"],
                    strat["parameters"]["profit"],
                    strat["parameters"]["distance"],
                )
                strategy.procesarDataset(dataset[["predicted", "close", "high"]])
                dataset["buy"] = strategy.lista_buys
                dataset["sell"] = strategy.lista_sells
                dataset["capital"] = strategy.lista_fondos
                dataset["invertido"] = strategy.lista_invertido
                titulo = self.train_name + "_" + model_name + "_" + strat["name"]
                name_evol = (
                    "./train/backtest/fondos_"
                    + datetime.now().strftime("%d%m%Y%I%M%S%p")
                    + ".html"
                )
                name_chart = (
                    "./train/backtest/chart_"
                    + datetime.now().strftime("%d%m%Y%I%M%S%p")
                    + ".html"
                )
                self.chartBacktesting(dataset, name_chart, titulo)
                self.chartEvolution(
                    dataset.loc[:, ["close_time", "capital"]],
                    "close_time",
                    "capital",
                    "Capital " + titulo,
                    name_evol,
                )

                return (
                    name_evol,
                    name_chart,
                    strat["name"],
                    strat,
                    strategy.lista_fondos[-1],
                    strategy.lista_buys.count(True),
                    max(strategy.lista_periodos),
                )

    def chartBacktesting(self, dataset, nombre, titulo):
        """
        Recibe un dataset con data completa lista para generar el gráfico de velas
        y las marcas de compras y ventas.
        """
        # dataset1 = dataset2.loc['2022-1-1':'2022-1-30']
        print("#### IMPRIMIENDO GRÁFICA  ", titulo, " ####")
        dataset = dataset.reset_index()
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.01,
            row_width=[0.2, 0.1, 0.5],
        )

        fig.add_trace(
            go.Candlestick(
                x=dataset["open_time"],
                open=dataset["open"],
                high=dataset["high"],
                low=dataset["low"],
                close=dataset["close"],
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=dataset["open_time"], y=dataset["rsi"]), row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=dataset["open_time"], y=dataset["capital"]), row=3, col=1
        )
        fig.add_trace(
            go.Scatter(x=dataset["open_time"], y=dataset["invertido"]), row=3, col=1
        )

        for i in range(len(dataset["predicted"])):
            buys = dataset.loc[i:i, "buy"].values[0]
            sells = dataset.loc[i:i, "sell"].values[0]
            res = dataset.loc[i:i, "target"].values[0]
            if buys == True:
                fig.add_annotation(
                    x=dataset.loc[i, "open_time"],
                    y=dataset.loc[i, "close"],
                    text="▲",
                    showarrow=False,
                    font=dict(size=16, color="blue"),
                )
            if res == True:
                fig.add_annotation(
                    x=dataset.loc[i, "open_time"],
                    y=dataset.loc[i, "close"],
                    text="◀",
                    showarrow=False,
                    font=dict(size=16, color="green"),
                )
            if sells == True:
                fig.add_annotation(
                    x=dataset.loc[i, "open_time"],
                    y=dataset.loc[i, "close"],
                    text="▲",
                    showarrow=False,
                    font=dict(size=16, color="red"),
                )
        fig.update_layout(
            xaxis_rangeslider_visible=False, showlegend=False, title=titulo
        )
        fig.write_html(nombre)
        # fig.show()

    def chartEvolution(self, dataset, x_name, y_name, titulo, nombre, todo=False):
        if not (todo):
            print("#### IMPRIMIENDO  ", titulo, " ####")
            fig = px.line(dataset, x=x_name, y=y_name, title=titulo)
            fig.write_html(nombre)
            # fig.show()
        else:
            print("#### IMPRIMIENDO  ", titulo, " TODO ####")
            df = pd.DataFrame()
            df["close_time"] = dataset[0]["close_time"]
            df["capital"] = 0.04
            df["invertido"] = 0
            for ds in dataset:
                df["invertido"] += ds["invertido"]
                df["capital"] += ds["capital"] - 0.02
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02
            )
            fig.add_trace(go.Scatter(x=df[x_name], y=df[y_name[0]]), row=1, col=1)
            fig.add_trace(go.Scatter(x=df[x_name], y=df[y_name[1]]), row=2, col=1)
            fig.update_layout(
                xaxis_rangeslider_visible=False, showlegend=True, title=titulo
            )
            fig.write_html(nombre)
            # fig.show()

    def metrics(self, y_test, y_pred):
        rf_matrix = confusion_matrix(y_test, y_pred)

        true_negatives = rf_matrix[0][0]
        false_negatives = rf_matrix[1][0]
        true_positives = rf_matrix[1][1]
        false_positives = rf_matrix[0][1]
        accuracy = ((true_negatives + true_positives) / (true_negatives + true_positives + false_negatives + false_positives)) if (true_negatives + true_positives + false_negatives + false_positives) != 0  else 0
        precision = (true_positives / (true_positives + false_positives)) if (true_positives + false_positives)!=0 else 0
        recall = (true_positives / (true_positives + false_negatives)) if (true_positives + false_negatives)!=0 else 0
        specificity = (true_negatives / (true_negatives + false_positives)) if (true_negatives + false_positives)!=0 else 0
        print("Verdaderos Positivos: ", true_positives)
        print("Falsos Positivos: ", false_positives)
        print("Verdaderos Negativos: ", true_negatives)
        print("Falsos Negativos: ", false_negatives)
        # print("Exactitud: {}".format(float(accuracy)))
        print("Precisión: {}".format(float(precision)))
        print("Sensibilidad: {}".format(float(recall)))
        # print("Especificidad: {}".format(float(specificity)))
        print(classification_report(y_test, y_pred))
        roc_value = roc_auc_score(y_test, y_pred)
        f1_value = f1_score(y_test, y_pred)
        print("\n\nF1 Value: ", f1_value)
        print("\n\nROC Value: ", roc_value)

        return (
            accuracy,
            precision,
            recall,
            specificity,
            f1_value,
            roc_value,
            true_negatives,
            true_positives,
            false_negatives,
            false_positives,
        )

    def entrenarRF(self, conf):
        """
        X: dataset con las variables independientes
        y: dataset con la variable dependiende
        modelo: cadena con el nombre del modelo preentrenado en la carpeta del proyecto
        """
        parameters = ast.literal_eval(conf["parameters"])
        nombre_modelo = (
            "./ml/models/"
            + conf["algorithm"]["name"]
            + "_"
            + datetime.now().strftime("%d%m%Y%I%M%S%p")
            + ".joblib"
        )
        print("#### ENTRENANDO RANDOM FOREST CON GRIDSEARCH y CV ####")
        param_grid = {
            "n_estimators": list(ast.literal_eval(parameters["n_stimators"])),
            "random_state": [ast.literal_eval(parameters["random_state"])],
            "min_samples_split": list(ast.literal_eval(parameters["min_samples_split"])),
        }
        rf = RandomForestClassifier()
        rf_RandomGrid = GridSearchCV(
            estimator=rf,
            param_grid=param_grid,
            cv=int(parameters["cv"]),
            scoring="f1",
            n_jobs=2,
        )
        print(self.X_train)
        print(self.y_train)
        rf_RandomGrid.fit(self.X_train, self.y_train)
        print("#### cv_result f1 ####")
        print(rf_RandomGrid.cv_results_["mean_test_score"])
        print("#### Best paramters ####")
        print(rf_RandomGrid.best_params_)
        print(
            f"Train Accuracy - : {rf_RandomGrid.score(self.X_train,self.y_train):.3f}"
        )
        best_model = rf_RandomGrid.best_estimator_
        best_model.fit(self.X_train, self.y_train)
        joblib.dump(best_model, nombre_modelo, 4)
        return best_model, rf_RandomGrid.best_params_, nombre_modelo

    def entrenarKNN(self, conf):
        parameters = ast.literal_eval(conf["parameters"])
        nombre_modelo = (
            "./ml/models/"
            + conf["algorithm"]["name"]
            + "_"
            + datetime.now().strftime("%d%m%Y%I%M%S%p")
            + ".joblib"
        )
        print("#### ENTRENANDO KNN CON GRIDSEARCH y CV ####")
        param_grid = {
            "n_neighbors": ast.literal_eval(parameters["n_neighbors"]),
            "metric": ast.literal_eval(parameters["metric"]),
        }
        grid_knn = KNeighborsClassifier()
        knn_RandomGrid = GridSearchCV(
            estimator=grid_knn,
            param_grid=param_grid,
            cv=int(parameters["cv"]),
            scoring="f1",
            n_jobs=2,
        )
        knn_RandomGrid.fit(self.X_train, self.y_train)
        print("#### cv_result f1 ####")
        print(knn_RandomGrid.cv_results_["mean_test_score"])
        print("#### Best paramters ####")
        print(knn_RandomGrid.best_params_)
        print(
            f"Train Accuracy - : {knn_RandomGrid.score(self.X_train,self.y_train):.3f}"
        )
        best_model = knn_RandomGrid.best_estimator_
        best_model.fit(self.X_train, self.y_train)
        joblib.dump(best_model, nombre_modelo, 4)
        return best_model, knn_RandomGrid.best_params_, nombre_modelo

    def entrenarXGB(self, conf):
        parameters = ast.literal_eval(conf["parameters"])
        nombre_modelo = (
            "./ml/models/"
            + conf["algorithm"]["name"]
            + "_"
            + datetime.now().strftime("%d%m%Y%I%M%S%p")
            + ".joblib"
        )
        print("#### ENTRENANDO XGBOOST CON GRIDSEARCH y CV ####")
        param_grid = {
            "n_estimators": ast.literal_eval(parameters["n_estimators"]),
            "learning_rate": ast.literal_eval(parameters["learning_rate"]),
            "objective": ast.literal_eval(parameters["objective"]),
            "random_state": [ast.literal_eval(parameters["random_state"])],
        }
        grid_xgb = xgb.XGBClassifier(
            verbosity=0, silent=True, use_label_encoder=False
        )
        xgb_RandomGrid = GridSearchCV(
            estimator=grid_xgb,
            param_grid=param_grid,
            cv=int(parameters["cv"]),
            scoring="f1",
            n_jobs=2,
        )
        xgb_RandomGrid.fit(self.X_train, self.y_train)
        print("#### cv_result f1 ####")
        print(xgb_RandomGrid.cv_results_["mean_test_score"])
        print("#### Best paramters ####")
        print(xgb_RandomGrid.best_params_)
        print(
            f"Train Accuracy - : {xgb_RandomGrid.score(self.X_train,self.y_train):.3f}"
        )
        best_model = xgb_RandomGrid.best_estimator_
        best_model.fit(self.X_train, self.y_train)
        joblib.dump(best_model, nombre_modelo, 4)
        return best_model, xgb_RandomGrid.best_params_, nombre_modelo

    def entrenarSVM(self, conf):
        parameters = ast.literal_eval(conf["parameters"])
        nombre_modelo = (
            "./ml/models/"
            + conf["parameters"]["name"]
            + "_"
            + datetime.now().strftime("%d%m%Y%I%M%S%p")
            + ".joblib"
        )
        print("#### ENTRENANDO SVM CON GRIDSEARCH y CV ####")
        param_grid = {
            "kernel": ast.literal_eval(parameters["kernel"]),
            "random_state": [ast.literal_eval(parameters["random_state"])],
        }
        grid_svm = svm.SVC()
        svm_RandomGrid = GridSearchCV(
            estimator=grid_svm,
            param_grid=param_grid,
            cv=int(parameters["cv"]),
            scoring="f1",
            n_jobs=2,
        )
        svm_RandomGrid.fit(self.X_train, self.y_train)
        print("#### cv_result f1 ####")
        print(svm_RandomGrid.cv_results_["mean_test_score"])
        print("#### Best paramters ####")
        print(svm_RandomGrid.best_params_)
        print(
            f"Train Accuracy - : {svm_RandomGrid.score(self.X_train,self.y_train):.3f}"
        )
        best_model = svm_RandomGrid.best_estimator_
        best_model.fit(self.X_train, self.y_train)
        joblib.dump(best_model, nombre_modelo, 4)
        return best_model, svm_RandomGrid.best_params_, nombre_modelo


    def deleteTraineds(self, column="profit"):
        n_delete = 4  # len(self.configurations)*len(self.models)
        cur = self.conn.cursor()
        cur.execute(
            f"SELECT * FROM MODEL ORDER BY " + str(column) + f" ASC LIMIT {n_delete}"
        )
        rows = cur.fetchall()
        for row in rows:
            if "All" in str(rows[0][2]):
                for mod in ast.literal_eval(str(rows[0][3])):
                    if os.path.exists(mod):
                        os.remove(mod)
            else:
                if os.path.exists(rows[0][3]):
                    os.remove(rows[0][3])

        cur = self.conn.cursor()
        ide = str(rows[0][0])
        cur.execute(f"DELETE FROM MODEL WHERE id = {ide}")
        self.conn.commit()

    def calc_MDD(self,networth):
        df = pd.Series(networth, name="nw").to_frame()

        max_peaks_idx = df.nw.expanding(min_periods=1).apply(lambda x: x.argmax()).fillna(0).astype(int)
        df['max_peaks_idx'] = pd.Series(max_peaks_idx).to_frame()

        nw_peaks = pd.Series(df.nw.iloc[max_peaks_idx.values].values, index=df.nw.index)

        df['dd'] = ((df.nw-nw_peaks)/nw_peaks)
        df['mdd'] = df.groupby('max_peaks_idx').dd.apply(lambda x: x.expanding(min_periods=1).apply(lambda y: y.min())).fillna(0)

        return df