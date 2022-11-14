# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 20:13:24 2022

@author: x4vyjm
"""
from src.Trade import Trade
from src.resultBot import resultBot


class AcumulatorStrategy:
    capital = 1000
    profit = 1.01
    stoploss = 1.01
    precio_compra_promedio = 0
    divisor_inicial = 20
    maxima_n_compras = 12
    periodo = 0
    cantidad_total = 0
    monto_total = 0
    posicionado = 0
    min_distancia = 1
    distancia = 0
    conn = None
    accumulation_id = 0
    pair = ""
    timeframe = ""
    trades = []
    n_decimals = 0
    precio_venta = 0
    n_candles = 0
    sell_date = None
    monto_venta = 0
    failed_buys = 0
    bc = None
    objResult = None

    def __init__(self, config, pair, timeframe, conn, n_decimals, binanceClient):
        """
        Parameters
        ----------
        config : dictionary
            Dictionary with the values of strategie variables.
        pair : string
            Trading pair.
        timeframe : string
            Pair timeframe.
        conn : object
            Database sqlite connection object.
        n_decimals : integer
            Size of decimal part to round trading order quantity.
        binanceClient : object
            Binance connection object.

        Returns
        -------
        None.

        """
        self.pair = pair
        self.timeframe = timeframe
        self.capital = float(config["parameters"]["initial_capital"])
        self.maxima_n_compras = int(config["parameters"]["max_buys"])
        self.divisor_inicial = int(config["parameters"]["initial_divisor"])
        self.profit = float(config["parameters"]["profit"])
        self.stoploss = float(config["parameters"]["loss"])
        self.min_distancia = int(config["parameters"]["distance"])
        self.conn = conn
        self.n_decimals = int(n_decimals)
        self.bc = binanceClient
        self.objResult = resultBot()
        command = """CREATE TABLE IF NOT EXISTS ACCUMULATION (id integer primary key autoincrement, pair text, timeframe text, 
                                                        total_quantity float,sell_price float, avg_entry_price float, avg_stop_price float, 
                                                        total_inversion float, sell_amount float, n_candles integer, closed integer, target_price float, 
                                                        sell_date timestamp, open_date timestamp, close_date timestamp, failed_buys integer)"""
        cur = self.conn.cursor()
        cur.execute(command)
        self.conn.commit()
        if not (self.lastAccumulationOpened()):
            print("### Inicializando nueva estrategia")
            self.distancia = 100
            self.newAccumulation()

    def avgBuyPrice(self, precio, cantidad):
        """
        Function to get the new buy price average.
        Parameters
        ----------
        precio : float
            Price of new buy.
        cantidad : float
            Cuantity of new buy.

        Returns
        -------
        float
            New buy price average of current accumulation.

        """
        return (
            self.precio_compra_promedio * self.cantidad_total + precio * cantidad
        ) / (cantidad + self.cantidad_total)

    def getDivisor(self):
        """
        Function to get the new capital divisor. Remember its a growing trading size amount

        Returns
        -------
        float
            New divisor of current capital to next order.

        """
        return float(
            self.divisor_inicial * (1 - ((1 / self.maxima_n_compras) * self.periodo))
        )

    def process(self, row, exact_timeframe=False):
        """
        Function to analize de last row of data. Check if a buy or sell signal will triggered. After sell closeTrades function is called, wich close de Trades objects, save data and restart to initial values, ready to new accumulation process..
        Parameters
        ----------
        row : dataset
            Last row in dataframe format to process.
        exact_timeframe : boolean, optional
            There are two calls to this function. If "True" means is a call with the candle timeframe closed ("timeframe" defined interval). "False" means that is a real time call (1m interval).  The default is True.
        Returns
        -------
        None.
        """

        print("### Procesando nueva vela para comprar")
        if row["buy"].iloc[-1] == True:
            self.n_candles += 1
            print(" periodo: ", self.periodo)
            print(" maxima_n_compras: ", self.maxima_n_compras)
            print(" distancia: ", self.distancia)
            print(" min_distancia: ", self.min_distancia)
            if (
                self.periodo < self.maxima_n_compras
                and self.distancia >= self.min_distancia
            ):
                divisor = self.getDivisor()
                self.periodo += 1
                monto_entrada = self.capital / divisor
                self.precio_stop_loss = float(row["prev"]*self.stoploss)
                self.openTrade(monto_entrada)
            else:
                self.distancia += 1
                self.failed_buys += 1
        else:
            if exact_timeframe:
                if self.posicionado:
                    print("SI ESTA POSICIONADO-.....")
                    if(float(self.stoploss) > 0):
                        print("SI EL STOP LOSS ES MAYOR A CERO-.....")
                        if (float(row["close"]) <= self.precio_stop_loss):  # if row["close"] >= self.precio_compra_promedio * self.profit:
                            print("SI el CIERRE ES MENOR AL STOP LOSS CIERRO LOS TRADES.....")
                            self.closeTrades()
                self.distancia += 1
                self.n_candles += 1
            if self.posicionado:
                if (
                    float(row["close"]) >= self.precio_compra_promedio * self.profit
                ):  # if row["close"] >= self.precio_compra_promedio * self.profit:
                    self.closeTrades()

        print("terminar de procesar")

    def openTrade(self, monto_entrada):
        print("### Intentando nueva compra")
        print("symbol: ", self.pair)
        print("n_decimals: ", self.n_decimals)
        print("monto_entrada: ", monto_entrada)
        print("quoteOrderQty: ", round(monto_entrada, self.n_decimals))
        order = self.bc.order_market_buy(
            symbol=self.pair, quoteOrderQty=round(monto_entrada, 7)
        )
        if order["status"] == "FILLED":
            print(f"### Compra realizada")
            if len(order["fills"]) > 0:
                cantidad_fills = 0
                precio_x_cantidad_fills = 0
                for fill in order["fills"]:
                    cantidad_fills += float(fill["qty"])
                    precio_x_cantidad_fills += float(fill["qty"]) * float(fill["price"])
                avg_price_buy = precio_x_cantidad_fills / cantidad_fills
            newTrade = Trade(
                self.accumulation_id,
                avg_price_buy,
                order["executedQty"],
                monto_entrada,
                order["transactTime"],
                order["orderId"],
                self.conn,
            )
            self.trades.append(newTrade)

            self.precio_compra_promedio = self.avgBuyPrice(
                avg_price_buy, float(order["executedQty"])
            )
            print("### NUEVO PRECIO PROMEDIO: ", self.precio_compra_promedio)
            print("### NUEVO TARGET: ", self.precio_compra_promedio * self.profit)
            print("### STOP LOSS: ", self.precio_stop_loss)
            self.capital -= precio_x_cantidad_fills * 1.003
            self.cantidad_total += cantidad_fills
            self.monto_total += precio_x_cantidad_fills * 1.003
            self.posicionado = 1
            self.distancia = 0
            self.updateAccumulationAfterBuy()
            return True
        print(f"### Compra fallida")
        return False

    def closeTrades(self):
        print(f"### Intentando vender")
        print("self.cantidad_total: ", self.cantidad_total)
        order = self.bc.order_market_sell(
            symbol=self.pair, quantity=round(self.cantidad_total, self.n_decimals)
        )
        if order["status"] == "FILLED":
            print(f"### Venta exitosa")
            print(order)
            if len(order["fills"]) > 0:
                cantidad_fills = 0
                precio_x_cantidad_fills = 0
                for fill in order["fills"]:
                    cantidad_fills += float(fill["qty"])
                    precio_x_cantidad_fills += float(fill["qty"]) * float(fill["price"])
                avg_price_sell = precio_x_cantidad_fills / cantidad_fills
            self.closed = 1
            self.precio_venta = avg_price_sell
            self.posicionado = 0
            self.sell_date = order["transactTime"]
            self.monto_venta = float(order["executedQty"])
            self.sell_trades()
            self.capital += self.precio_venta * self.monto_venta
            self.updateAccumulationAfterSell()
            self.newAccumulation()
            return True
        return False

    def sell_trades(self):
        for item in self.trades:
            item.close(self.precio_venta, self.sell_date)
            cost_buy = float(float(item.entry_price) * float(item.quantity))
            cost_sell = float(float(self.precio_venta) * float(item.quantity))
            self.objResult.insert(
                self.pair,
                self.timeframe,
                item.entry_price,
                self.precio_venta,
                item.quantity,
                cost_buy,
                cost_sell,
                cost_sell - cost_buy,
            )

    def newAccumulation(self):
        print(f"### Registrando nueva acumulacion")
        sql = f"""INSERT INTO ACCUMULATION (pair, timeframe, total_inversion, closed, failed_buys) 
                VALUES("{str(self.pair)}","{str(self.timeframe)}",{float(0)},{int(0)},{int(0)})"""
        cur = self.conn.cursor()
        cur.execute(sql)
        self.accumulation_id = cur.lastrowid
        self.conn.commit()
        self.precio_compra_promedio = 0
        self.periodo = 0
        self.cantidad_total = 0
        self.monto_total = 0
        self.posicionado = 0
        self.distancia = 100
        self.precio_venta = 0
        self.n_candles = 0
        self.sell_date = None
        self.monto_venta = 0
        self.failed_buys = 0
        self.trades.clear()

    def lastAccumulationOpened(self):
        cur = self.conn.cursor()
        command = "SELECT * FROM ACCUMULATION WHERE (closed = 0 AND total_quantity IS NOT NULL) ORDER BY id DESC"
        cur.execute(command)
        rows = cur.fetchall()
        if len(rows) > 0:
            print(
                f"### Cargando estrategia abierta de la base de datos con id={str(rows[0][0])}"
            )
            cur = self.conn.cursor()
            command = "SELECT * FROM TRADE WHERE accumulation_id = " + str(rows[0][0])
            cur.execute(command)
            trades = cur.fetchall()
            self.accumulation_id = int(rows[0][0])
            self.loadTrades(trades)
            self.cantidad_total = float(rows[0][3])
            self.precio_compra_promedio = float(rows[0][5])
            self.precio_stop_loss = float(rows[0][6])
            self.monto_total = float(rows[0][7])
            self.capital -= self.monto_total
            self.periodo = len(trades)
            self.posicionado = 1
            self.distancia = int(self.min_distancia) / 2
            self.failed_buys = int(rows[0][15])
            return True
        else:
            return False

    def loadTrades(self, trades):
        for item in trades:
            trade = Trade(
                self.accumulation_id,
                item[2],
                item[4],
                item[5],
                item[7],
                item[9],
                self.conn,
                new=False,
                trade_id=int(item[0]),
            )
            self.trades.append(trade)

    def updateAccumulationAfterBuy(self):
        print(f"### Actualizando acumulacion despues de una compra")
        sql = f"""Update ACCUMULATION set total_quantity = {float(self.cantidad_total)}, avg_entry_price = {float(self.precio_compra_promedio)}, avg_stop_price = {float(self.precio_stop_loss)},
                total_inversion = {float(self.monto_total)}, target_price = {float(self.precio_compra_promedio*self.profit)}  where id = {int(self.accumulation_id)}"""
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()

    def updateAccumulationAfterSell(self):
        print(f"### Actualizando acumulacion despues de vender")
        sql = f"""Update ACCUMULATION set sell_price = {float(self.precio_venta)}, n_candles = {int(self.n_candles)}, 
                closed = 1, sell_date = {str(self.sell_date)}, sell_amount = {str(self.monto_venta)}, failed_buys = {int(self.failed_buys)} where id = {int(self.accumulation_id)}"""
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()

    """
    def setOrderLimit(self):
        try:
            order = self.bc.order_limit_sell(
                symbol=self.pair,
                quantity=round(self.cantidad_total, self.n_decimals),
                price=round(self.precio_compra_promedio * self.profit, 8),
            )
            print(order)
            print("### Orden colocada con id: ", order["orderId"])
            return order["orderId"]
        except:
            return None

    def checkOrderLimit(self):
        try:
            order = self.bc.get_order(symbol=self.pair, orderId=self.limit_order_id)
            print(order)
            return order["status"]
        except:
            return "NET_FAILED"

    def cancelOrderLimit(self):
        try:
            order = self.bc.cancel_order(symbol=self.pair, orderId=self.limit_order_id)
            print(order)
            return order["status"]
        except:
            return "NET_FAILED"
    """
