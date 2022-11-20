# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 20:13:24 2022

@author: x4vyjm
"""
from strategies.Trade import Trade
import ast
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)
class IncrementalBuy:
    class PairStrategy:
        def __init__(self, pair, initial_capital, available_capital, timeframe,n_decimals, open_trades=[]):
            self.pair = pair
            self.timeframe = timeframe
            print("piar y timframe ")
            self.n_decimals = n_decimals
            print("n_decimal", n_decimals)
            self.initial_capital = initial_capital
            print("initial capital ")
            self.available_capital = available_capital
            print("available_capital ", self.available_capital)
            self.trades = open_trades
            print("trades ",self.trades)
            self.distance = 100
            self.n_candles = 0
            self.failed_buys = 0
            self.period = len(open_trades)
            print(f"len open_trades: {self.period}")
            self.avg_buy_price = 0.0
            self.invested_capital = 0.0
            self.total_quantity = 0.0
            for item in open_trades:
                print(f"there are open trades: {item}")
                self.avg_buy_price += item.entry_price*item.quantity
                self.total_quantity += item.quantity
                self.invested_capital += item.investment
            if(len(open_trades)>0):
                self.avg_buy_price /= self.total_quantity
            self.positioned = True if len(self.trades)>0 else False
            print("Pair strategy class variables initializados")

        def openTrade(self, trade):
            self.trades.append(trade)
        
        def closeTrades(self, sell_price, sell_date):
            for item in self.trades:
                item.close(sell_price, sell_date)
            # reinit this pair
            self.trades = []
            self.distance = 100
            self.n_candles = 0
            self.failed_buys = 0
            self.period = 0
            self.avg_buy_price = 0.0
            self.invested_capital = 0.0
            self.total_quantity = 0.0
            self.positioned = False
    # class objects
    conn = None #database conection
    exchange = None #exchange coneciont
    #Portfolio variables
    initial_capital = 1000
    current_capital = 1000
    invested_capital = 1000
    # strategy variables
    pairs = []
    timeframe = ""
    profit = 1.01
    stoploss = 0
    
    initial_divisor = 20
    max_n_buys = 12
    min_distance = 1    
    
    pair_strategy={}
    # data evolution varaibles
    total_capital_evolution = []
    invested_capital_evolution = []

    

    def __init__(self, config, conn, exchange):
        """
        Parameters
        ----------
        config : dictionary
            Dictionary with the values of strategie variables.
        conn : object
            Database sqlite connection object.
        exchange : object
            Binance connection object.
        Returns
        -------
        None.

        """
        self.pairs = config["pairs"]
        self.timeframe = config["timeframe"]
        self.initial_capital = float(config["initial_capital"]) * len(self.pairs)
        strategy_params = ast.literal_eval(config["strategy_parameters"])
        self.max_n_buys = int(strategy_params["backtest"]["backtest_initial_max"][0])
        self.initial_divisor = int(strategy_params["backtest"]["backtest_initial_max"][1])
        self.profit = float(strategy_params["target"]["target_profit"])
        self.min_distance = int(strategy_params["backtest"]["backtest_distance"])
        self.conn = conn
        self.exchange = exchange
        self.uuid = config["uuid"]
        print("Clase con variables inicializadas")
        # load trades in bot to respective pair (only oppened trades)
        for pair in self.pairs:
            print(f" Pair: {pair}")
            if(len(config["trades"])>0):
                opened_trades_pair = [Trade(item["entry_price"], item["quantity"], item["investment"], item["open_date"], item["close_candle"], item["order_id"], item["pair"], item["timeframe"], self.uuid, self.conn,new=False) for item in config["trades"] if item["closed"] == 0 and item["pair"]==pair]
            else:
                opened_trades_pair = []
            print(f"Openned trades pair: {len(opened_trades_pair)}")
            logger.info(f"The pair {pair} has {len(opened_trades_pair)} trades openned.")
            print("get decimal")
            aux_decimal = self.get_decimals(pair)
            print(f"aux decimal after return: {aux_decimal}")
            print(f"config[initial_capital] is: {config['initial_capital']} type: {type(config['initial_capital'])}")
            print(f"self.timeframe] is: {self.timeframe} type: {type(self.timeframe)}")
            print(f"aux_decimal is: {aux_decimal} type: {type(aux_decimal)}")
            print(f"opened_trades_pair is: {opened_trades_pair} type: {type(opened_trades_pair)}")
            print(f"capital_pair before is: {config['capital_pair']} type: {type(config['capital_pair'])}")
            objPair = self.PairStrategy(pair, float(config["initial_capital"]), config["capital_pair"][pair] ,self.timeframe, aux_decimal, open_trades=opened_trades_pair)
            print("objPair instanciado")
            #save in a dict pair: object
            logger.info("## Adding objPair to pair_strategy Dict")
            self.pair_strategy[pair] = objPair
            print("objPair añadifo a pairstrategy")
        print("cargaron trades pendientes de la bd")    

    def avgBuyPrice(self,avg_buy_price, total_quantity, price, qty):
        """
        Function to get the new buy price average.
        Parameters
        ----------
        price : float
            Price of new buy.
        qty : float
            Cuantity of new buy.

        Returns
        -------
        float
            New buy price average of current accumulation.

        """
        return (
            avg_buy_price * total_quantity + price * qty
        ) / (qty + total_quantity)

    def getDivisor(self, period):
        """
        Function to get the new capital divisor. Remember its a growing trading size amount

        Returns
        -------
        float
            New divisor of current capital to next order.

        """
        return float(
            self.initial_divisor * (1 - ((1 / self.max_n_buys) * period))
        )

    def process(self, data_dict):
        """
        Function to analize de last predicted data. Check if a buy or sell signal will triggered. After sell closeTrades function is called, wich close de Trades objects, save data and restart to initial values, ready to new accumulation process..
        Parameters
        ----------
        data_dict : list
            Last prediction in dict format to process. Format: [{"pair": "ETHBTC", "buy": false, "close": 0.001, "close_time":456131314565}]
        Returns
        -------
        None.
        """
        print(f"data_dict is: {str(data_dict)}")
        info_capital = {"portfolio": 0, "available": 0, "invested": 0, "close_time": data_dict[0]["close_time"]}
        for signal in data_dict:            
            print(f"signal is: {str(signal)}")
            if signal["buy"] == True:
                self.pair_strategy[signal["pair"]].n_candles += 1
                print(" BUY TRUE. The prev status of pairstrategy is: ")
                print(" period: ", self.pair_strategy[signal["pair"]].period)
                print(" max_n_buys: ", self.max_n_buys)
                print(" distance: ", self.pair_strategy[signal["pair"]].distance)
                print(" min_distance: ", self.min_distance)
                if (
                    self.pair_strategy[signal["pair"]].period < self.max_n_buys
                    and self.pair_strategy[signal["pair"]].distance >= self.min_distance
                ):
                    divisor = self.getDivisor(self.pair_strategy[signal["pair"]].period)
                    entry_amount = (self.pair_strategy[signal["pair"]].available_capital) / divisor
                    objTrade, buy_price, amount_invested, quantity = self.openTrade(self.pair_strategy[signal["pair"]].pair, entry_amount,self.pair_strategy[signal["pair"]].n_decimals, signal["close_time"])
                    if(objTrade != None):
                        # Si la compra fue un éxito
                        self.pair_strategy[signal["pair"]].period += 1
                        self.pair_strategy[signal["pair"]].avg_buy_price = self.avgBuyPrice(self.pair_strategy[signal["pair"]].avg_buy_price, self.pair_strategy[signal["pair"]].total_quantity, buy_price, quantity)
                        logger.info(f"### NUEVO PRECIO PROMEDIO: {self.pair_strategy[signal['pair']].avg_buy_price}")
                        logger.info(f"### NUEVO TARGET: {self.pair_strategy[signal['pair']].avg_buy_price * (1+self.profit)}")

                        self.pair_strategy[signal["pair"]].total_quantity += quantity
                        self.pair_strategy[signal["pair"]].invested_capital += amount_invested * 1.003
                        self.pair_strategy[signal["pair"]].available_capital -= amount_invested * 1.003
                        self.pair_strategy[signal["pair"]].positioned = True
                        self.pair_strategy[signal["pair"]].distance = 0
                        self.pair_strategy[signal["pair"]].openTrade(objTrade) #add the new trade object to list of trades in pair object
                        #Update available capital of pair in Database. Maybe the bot can be stopped accidentally
                        self.conn.updateBotCapitalPair({"uuid":self.uuid, "pair":signal["pair"], "available_capital": float(self.pair_strategy[signal["pair"]].available_capital)})
                else:
                    self.pair_strategy[signal["pair"]].distance += 1
                    self.pair_strategy[signal["pair"]].failed_buys += 1
            else:   
                print(f"no buy true")
                self.pair_strategy[signal["pair"]].distance += 1
                self.pair_strategy[signal["pair"]].n_candles += 1
                if self.pair_strategy[signal["pair"]].positioned:
                    print("si esta posicionada")
                    if (
                        float(signal["close"]) >= self.pair_strategy[signal["pair"]].avg_buy_price * 0.98 #(1+self.profit)
                    ):  # if data_dict["close"] >= self.avg_buy_price * self.profit:
                        # Ya que se logró el beneficio cierro los trades, vendiendo toda la cantidad acumulada
                        self.closeTrades(self.pair_strategy[signal["pair"]].pair)
            info_capital["invested"] += self.pair_strategy[signal["pair"]].invested_capital
            info_capital["available"] += self.pair_strategy[signal["pair"]].available_capital
            info_capital["portfolio"] += ( (self.pair_strategy[signal["pair"]].total_quantity * signal["close"] ) + self.pair_strategy[signal["pair"]].available_capital)
            logger.info("terminar de procesar")
        self.conn.saveCapital({"uuid": self.uuid,"capital":info_capital})
        print("info_capital saved")
    def openTrade(self, pair, entry_amount, n_decimals, close_candle):
        print("### Intentando nueva compra en par ", pair)
        print("symbol: ", pair)
        print("n_decimals: ", n_decimals)
        print("entry_amount: ", entry_amount)
        print("quoteOrderQty: ", round(entry_amount, n_decimals))
        order = self.exchange.order_market_buy(
            symbol=pair, quoteOrderQty=round(entry_amount, 7)
        )
        if order["status"] == "FILLED":
            logger.info(f"### Compra realizada en par {pair}")
            if len(order["fills"]) > 0:
                cantidad_fills = 0
                precio_x_cantidad_fills = 0
                for fill in order["fills"]:
                    cantidad_fills += float(fill["qty"])
                    precio_x_cantidad_fills += float(fill["qty"]) * float(fill["price"])
                avg_price_buy = precio_x_cantidad_fills / cantidad_fills
            newTrade = Trade(
                avg_price_buy,
                order["executedQty"],
                entry_amount,
                order["transactTime"],
                close_candle,
                order["orderId"],
                pair,
                self.timeframe,
                self.uuid,
                self.conn
            )
            return newTrade, avg_price_buy, precio_x_cantidad_fills, cantidad_fills
        logger.info(f"### Compra fallida")
        return None,0,0,0

    def closeTrades(self, pair):
        logger.info(f"### Intentando vender")
        print("self.pair_strategy[pair].total_quantity: ", self.pair_strategy[pair].total_quantity)
        order = self.exchange.order_market_sell(
            symbol=pair, quantity=round(self.pair_strategy[pair].total_quantity, self.pair_strategy[pair].n_decimals)
        )
        if order["status"] == "FILLED":
            logger.info(f"### Venta exitosa")
            logger.info(order)
            if len(order["fills"]) > 0:
                cantidad_fills = 0
                precio_x_cantidad_fills = 0
                for fill in order["fills"]:
                    cantidad_fills += float(fill["qty"])
                    precio_x_cantidad_fills += float(fill["qty"]) * float(fill["price"])
                avg_price_sell = precio_x_cantidad_fills / cantidad_fills
            # luego de vender, aumento el available capital en el valor de toda la venta
            self.pair_strategy[pair].available_capital += avg_price_sell * float(order["executedQty"])
            # llamo al metodo de pair strategy que reinicia sus variables y cierra sus trades.
            self.pair_strategy[pair].closeTrades(avg_price_sell, order["transactTime"])
            # Actualizo el capital disponible en la bd para tener persistencia, si acaso se detiene el bot, poder reiniciar con el mismo capital disponible
            self.conn.updateBotCapitalPair({"uuid":self.uuid, "pair":pair, "available_capital": float(self.pair_strategy[pair].available_capital)})
            return True
        return False

    def get_decimals(self, pair):
        print(f"getting decimal for : {pair}")
        info = self.exchange.get_symbol_info(pair)
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
        print(f"Decimal before return {decimal}")
        return decimal

    """
    def setOrderLimit(self):
        try:
            order = self.exchange.order_limit_sell(
                symbol=self.pair,
                quantity=round(self.total_quantity, self.n_decimals),
                price=round(self.avg_buy_price * self.profit, 8),
            )
            logger.info(order)
            logger.info("### Orden colocada con id: ", order["orderId"])
            return order["orderId"]
        except:
            return None

    def checkOrderLimit(self):
        try:
            order = self.exchange.get_order(symbol=self.pair, orderId=self.limit_order_id)
            logger.info(order)
            return order["status"]
        except:
            return "NET_FAILED"

    def cancelOrderLimit(self):
        try:
            order = self.exchange.cancel_order(symbol=self.pair, orderId=self.limit_order_id)
            logger.info(order)
            return order["status"]
        except:
            return "NET_FAILED"
    """
