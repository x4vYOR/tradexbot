# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 20:13:24 2022

@author: x4vyjm
"""
from strategies.Trade import Trade
import ast
import logging
logging.basicConfig(filename='strategy.log', encoding='utf-8', level=logging.DEBUG)

class IncrementalBuy:
    class PairStrategy:
        def __init__(self, pair, initial_capital, available_capital, timeframe,n_decimals, open_trades=[]):
            self.pair = pair
            self.timeframe = timeframe
            self.n_decimals = n_decimals
            self.initial_capital = initial_capital
            self.available_capital = available_capital
            self.trades = open_trades
            self.distance = 100
            self.n_candles = 0
            self.failed_buys = 0
            self.period = len(open_trades)
            self.avg_buy_price, self.invested_capital, self.total_quantity = float(0)
            for item in open_trades:
                self.avg_buy_price += item.entry_price*item.quantity 
                self.total_quantity += item.quantity
                self.invested_capital += item.investment

            self.avg_buy_price /= self.total_quantity
            self.positioned = True if len(self.trades)>0 else False

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
            self.avg_buy_price, self.invested_capital, self.total_quantity = float(0)
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
        self.pairs = config.pairs
        self.timeframe = config.timeframe
        self.initial_capital = float(config.initial_capital) * len(self.pairs)
        strategy_params = ast.literal_eval(config.strategy_parameters)
        self.max_n_buys = int(strategy_params["backtest"]["backtest_initial_max"][0])
        self.initial_divisor = int(strategy_params["backtest"]["backtest_initial_max"][1])
        self.profit = float(strategy_params["target"]["target_profit"])
        self.min_distance = int(strategy_params["backtest"]["backtest_distance"])
        self.conn = conn
        self.exchange = exchange
        self.uuid = config.uuid

        # load trades in bot to respective pair (only oppened trades)
        for pair in self.pairs:
            opened_trades_pair = [Trade(item.entry_price, item.quantity, item.investment, item.open_date, item.order_id, item.pair, item.timeframe, config.uuid, self.conn,new=False) for item in config.trades if item.closed == 0 and item.pair==pair]
            logging.info(f"The pair {pair} has {len(opened_trades_pair)} trades openned.")
            objPair = self.PairStrategy(pair, config.initial_capital, config.capital_pair["pair"] ,self.timeframe, self.get_decimals(pair), open_trades=opened_trades_pair)
            #save in a dict pair: object
            logging.info("## Adding objPair to pair_strategy Dict")
            self.pair_strategy[pair] = objPair
            

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
            Last prediction in dict format to process. Format: [{"pair": "ETHBTC", "buy": false, "close": 0.001}]
        Returns
        -------
        None.
        """
        for signal in data_dict:
            if signal["buy"] == True:
                self.pair_strategy[signal["pair"]].n_candles += 1
                logging.info(" BUY TRUE. The prev status of pairstrategy is: ")
                logging.info(" period: ", self.pair_strategy[signal["pair"]].period)
                logging.info(" max_n_buys: ", self.max_n_buys)
                logging.info(" distance: ", self.pair_strategy[signal["pair"]].distance)
                logging.info(" min_distance: ", self.min_distance)
                if (
                    self.pair_strategy[signal["pair"]].period < self.max_n_buys
                    and self.pair_strategy[signal["pair"]].distance >= self.min_distance
                ):
                    divisor = self.getDivisor(self.pair_strategy[signal["pair"]].period)
                    entry_amount = (self.pair_strategy[signal["pair"]].available_capital) / divisor
                    objTrade, buy_price, amount_invested, quantity = self.openTrade(self.pair_strategy[signal["pair"]].pair, entry_amount,self.pair_strategy[signal["pair"]].n_decimals)
                    if(objTrade != None):
                        # Si la compra fue un éxito
                        self.pair_strategy[signal["pair"]].period += 1
                        self.pair_strategy[signal["pair"]].avg_buy_price = self.avgBuyPrice(self.pair_strategy[signal["pair"]].avg_buy_price, self.pair_strategy[signal["pair"]].total_quantity, buy_price, quantity)
                        logging.info("### NUEVO PRECIO PROMEDIO: ", self.pair_strategy[signal["pair"]].avg_buy_price)
                        logging.info("### NUEVO TARGET: ", self.pair_strategy[signal["pair"]].avg_buy_price * self.profit)

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
                self.pair_strategy[signal["pair"]].distance += 1
                self.pair_strategy[signal["pair"]].n_candles += 1
                if self.pair_strategy[signal["pair"]].positioned:
                    if (
                        float(signal["close"]) >= self.pair_strategy[signal["pair"]].avg_buy_price * self.profit
                    ):  # if data_dict["close"] >= self.avg_buy_price * self.profit:
                        # Ya que se logró el beneficio cierro los trades, vendiendo toda la cantidad acumulada
                        self.closeTrades(self.pair_strategy[signal["pair"]].pair)

            logging.info("terminar de procesar")

    def openTrade(self, pair, entry_amount, n_decimals):
        logging.info("### Intentando nueva compra en par ", pair)
        logging.info("symbol: ", pair)
        logging.info("n_decimals: ", n_decimals)
        logging.info("entry_amount: ", entry_amount)
        logging.info("quoteOrderQty: ", round(entry_amount, n_decimals))
        order = self.exchange.order_market_buy(
            symbol=pair, quoteOrderQty=round(entry_amount, 7)
        )
        if order["status"] == "FILLED":
            logging.info(f"### Compra realizada en par {pair}")
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
                order["orderId"],
                pair,
                self.timeframe,
                self.uuid,
                self.conn
            )
            return newTrade, avg_price_buy, precio_x_cantidad_fills, cantidad_fills
        logging.info(f"### Compra fallida")
        return None,0,0,0

    def closeTrades(self, pair):
        logging.info(f"### Intentando vender")
        logging.info("self.pair_strategy[pair].total_quantity: ", self.pair_strategy[pair].total_quantity)
        order = self.exchange.order_market_sell(
            symbol=pair, quantity=round(self.pair_strategy[pair].total_quantity, self.pair_strategy[pair].n_decimals)
        )
        if order["status"] == "FILLED":
            logging.info(f"### Venta exitosa")
            logging.info(order)
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
        return decimal

    """
    def setOrderLimit(self):
        try:
            order = self.exchange.order_limit_sell(
                symbol=self.pair,
                quantity=round(self.total_quantity, self.n_decimals),
                price=round(self.avg_buy_price * self.profit, 8),
            )
            logging.info(order)
            logging.info("### Orden colocada con id: ", order["orderId"])
            return order["orderId"]
        except:
            return None

    def checkOrderLimit(self):
        try:
            order = self.exchange.get_order(symbol=self.pair, orderId=self.limit_order_id)
            logging.info(order)
            return order["status"]
        except:
            return "NET_FAILED"

    def cancelOrderLimit(self):
        try:
            order = self.exchange.cancel_order(symbol=self.pair, orderId=self.limit_order_id)
            logging.info(order)
            return order["status"]
        except:
            return "NET_FAILED"
    """
