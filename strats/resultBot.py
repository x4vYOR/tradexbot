# -*- coding: utf-8 -*-
import sqlite3 as sql


class resultBot:
    db_name = ""
    conn = None
    last_id = None

    def __init__(self):
        self.db_name = "./database/result.db"
        self.conn = sql.connect(self.db_name, check_same_thread=False)
        cur = self.conn.cursor()
        command = """CREATE TABLE IF NOT EXISTS RESULT (id integer primary key autoincrement, pair text, timeframe text, buy_price float, sell_price float, 
                                                        amount float, buy_cost float, sell_cost float, profit float)"""
        cur.execute(command)
        self.conn.commit()

    def insert(
        self,
        pair,
        timeframe,
        buy_price,
        sell_price,
        amount,
        buy_cost,
        sell_cost,
        profit,
    ):
        sql = f"""INSERT INTO RESULT (pair, timeframe, buy_price, sell_price, amount, buy_cost, sell_cost, profit) 
                    VALUES("{str(pair)}","{str(timeframe)}",{float(buy_price)},{float(sell_price)},{float(amount)},{float(buy_cost)},{float(sell_cost)},{float(profit)})"""
        cur = self.conn.cursor()
        cur.execute(sql)
        self.last_id = cur.lastrowid
        self.conn.commit()

