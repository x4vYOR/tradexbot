# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 22:03:22 2022

@author: x4vyjm
"""

class Trade:
    entry_price = None
    close_price = None
    quantity = None
    investment = None
    closed = 0
    open_date = ""
    close_date = ""
    order_id = ""
    period = 1
    uuid = ""
    pair = ""
    timeframe = ""
    conn = None
    trade_id = None

    def __init__(
        self,
        entry_price,
        quantity,
        investment,
        open_date,
        close_candle,
        order_id,
        pair,
        timeframe,
        uuid,
        conn,
        new=True,
        trade_id=None,
    ):
        self.entry_price = entry_price
        self.quantity = quantity
        self.pair = pair
        self.timeframe = timeframe
        self.investment = investment
        self.open_date = open_date
        self.close_candle = close_candle
        self.order_id = order_id
        self.conn = conn
        self.uuid = uuid
        if new:
            data = {"entry_price": float(self.entry_price), "close_price": float(0), "close_candle": str(self.close_candle), "quantity": float(self.quantity), "pair": self.pair, "timeframe": self.timeframe, 
                    "investment": float(self.investment), "closed": int(self.closed), "open_date": str(self.open_date), "close_date": "", "order_id": str(self.order_id) }
            res = conn.saveTrade({'uuid': self.uuid,'trade':data})
            if(res):
                print("### Trade nuevo creado")

    def close(self, close_price, close_date):
        print("### Cierre de trade")
        self.closed = 1
        self.close_date = close_date
        self.close_price = close_price
        data = {"close_date": str(close_date), "close_price": float(close_price),"pair":self.pair,"order_id": self.order_id}
        res = self.conn.closeTrade({'uuid':self.uuid, 'trade': data})
        if(res):
                print("### Trade cerrado order_id=",self.order_id)

    def isClosed(self):
        print(f"### Obteniendo informacion si el trade es cerrado")
        return self.closed

