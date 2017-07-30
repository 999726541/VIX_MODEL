#!/bin/usr/env python3
# -*- coding:utf-8 -*-
# ===============================================================================
# LIBRARIES
# ===============================================================================
import sys
sys.path.append('/home/leo-gwise/PycharmProjects/IbPy/DataLoader/')
import pandas as pd
from time import sleep
import mysql.connector
# ===============================================================================
# Class IB_API
# ===============================================================================
DB_HOST = 'xxxx'
USERNAME = 'xxxx'
PASSWORD = 'xxxx'
PORT = 3306

class mysql_con():

    def __init__(self,DB_DB,DB_HOST=DB_HOST):
        # Establish Connection

        print('Connecting to DB...')
        self.cnx = mysql.connector.connect(user=USERNAME,
                                           password=PASSWORD,
                                           host=DB_HOST,
                                           database=DB_DB,
                                           port=PORT
                                           )
        self.cursor = self.cnx.cursor(buffered=True)
        self.curA = self.cnx.cursor(buffered=True)
        self.curB = self.cnx.cursor(buffered=True)

        print('Connecting successed')
        sleep(2)

    def createTable(self,TABLE):

        print('Creating table... ')
        self.cursor.execute(TABLE)
        print('Creating table succeeded')

    def add2Greek(self,tableName,dic):
        add_greek = ("INSERT INTO `" + tableName + "` "
                        "(delta, impliedVolatility, optPrice, pvDividend, gamma, vega, theta, undPrice, Symbol, B_A, Record_TS) "
                        "VALUES (%(delta)s, %(impliedVolatility)s, %(optPrice)s, %(pvDividend)s, %(gamma)s, %(vega)s,"
                                                   " %(theta)s, %(undPrice)s, %(Symbol)s, %(B_A)s, %(Record_TS)s)"
                     "on duplicate key update"
                     " delta = delta,undPrice = undPrice")

        self.curA.execute(add_greek,dic)
        self.cnx.commit()


    def add2spx_OptMany(self,dic,tableName):
        add_ = ("INSERT INTO `" + tableName + "`"+
                " (OPT_ASK, OPT_BID, SYMBOL, RECORD_TS, STRIKE, TRADE_VOLUME, DELTA, IV, GAMMA, VEGA, THETA, UND_PRICE, CREATED_TIME, UPDATED_TIME) "
                "VALUES (%(OPT_ASK)s, %(OPT_BID)s, %(SYMBOL)s, %(RECORD_TS)s, %(STRIKE)s, %(TRADE_VOLUME)s,"
                " %(DELTA)s, %(IV)s, %(GAMMA)s, %(VEGA)s, %(THETA)s, %(UND_PRICE)s, %(CREATED_TIME)s, %(UPDATED_TIME)s)"
                " on DUPLICATE key update"
                " OPT_ASK=VALUES(OPT_ASK), OPT_BID=VALUES (OPT_BID), DELTA=VALUES (DELTA), "
                "IV=VALUES (IV), GAMMA=VALUES (GAMMA), VEGA=VALUES (VEGA), THETA=VALUES (THETA),"
                " UND_PRICE = VALUES (UND_PRICE), UPDATED_TIME = VALUES (UPDATED_TIME), RECORD_TS = VALUES(RECORD_TS)"
                )

        self.curA.executemany(add_,dic)
        self.cnx.commit()


    def add2bidask(self, tableName, dic):
        # print(dic)
        add_bidask = ("INSERT INTO `" + tableName +
                      "` (B_A_C , P, Symbol, Record_TS) " +
                      "VALUES (%(B_A_C)s, %(P)s, %(Symbol)s, %(Record_TS)s)"
                      "on duplicate key update"
                      " P = P")


        self.curB.execute(add_bidask, dic)
        self.cnx.commit()

    def add2bidaskMany(self, tableName, dic):
        # print(dic)
        add_bidask = ("INSERT INTO `" + tableName +
                      "` (B_A_C , P, Symbol, Record_TS) " +
                      "VALUES (%(B_A_C)s, %(P)s, %(Symbol)s, %(Record_TS)s)"
                      "on duplicate key update"
                      " P = P")

        self.curB.executemany(add_bidask, dic)
        self.cnx.commit()

    def if_exist(self,name):
        ask = ("SHOW TABLES LIKE '" + name + "'")
        self.cursor.execute(ask)
        # print(str(self.cursor.fetchone()))
        if name in str(self.cursor.fetchone()):
            return 1
        else:
            return 0

    def query(self,_query):
        self.cursor.execute(_query)
        return self.cursor

    def add_open_high_low_close(self,tableName,dic):
        add_bidask = ("INSERT INTO `" + tableName +
                      "` (open_P , high_P, low_P, close_P, Record_TS, volume, WAP) " +
                      "VALUES (%(open_P)s, %(high_P)s, %(low_P)s,%(close_P)s, %(Record_TS)s, %(volume)s, %(WAP)s)" +
                      "on duplicate key update open_P=open_P")
        self.curB.execute(add_bidask, dic)
        self.cnx.commit()

    def get_data_by_pandas(self,_query):
        return pd.read_sql(_query,self.cnx)

if __name__=='__main__':
    zz = mysql_con()
    # rr = zz.get_data_by_pandas("select * from `SPX   170421C02200000_bidask` ORDER BY `Record_TS`")
    kk = zz.get_data_by_pandas('select * from `SPX   170519C02250000_bidask` where B_A_C="ask" order by Record_TS desc limit 1')
    print(kk)
    # for i in zz.query("select * from `SPX   170421C02200000_greeks` ORDER BY `Record_TS`"):
