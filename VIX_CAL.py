#!/bin/usr/env python3
# -*- coding:utf-8 -*-
# ===============================================================================
# LIBRARIES
# ===============================================================================

from datetime import datetime, timedelta
from dbCon import mysql_con
from VOL_MODEL_MAIN import VIX_index,VIX_future


# ===============================================================================
# Class Reader
# ===============================================================================

def calculate_vix_into_db(startTime,endTime):
    con = mysql_con('CALCULATED_VIX')

    start_time = datetime.strptime(startTime,'%Y-%m-%d %H:%M:%S')

    query = ("INSERT INTO `VIX_INTRINSIC`"+
            " (VIX, VIX_NEAR_WEIGHT, VIX_NEXT_WEIGHT, "
            "VIX_NEAR_SKEW, VIX_NEXT_SKEW, UND_PRICE, CREATED_TIME, UPDATED_TIME, "

            "VIX_FIRST, VIX_FIRST_SKEW, FIRST_FUTURE_EXPIRATION, FIRST_OPTION_EXPIRATION, "

            "VIX_SECOND, VIX_SECOND_SKEW, SECOND_FUTURE_EXPIRATION, SECOND_OPTION_EXPIRATION, "

            "VIX_THIRD, VIX_THIRD_SKEW, THIRD_FUTURE_EXPIRATION, THIRD_OPTION_EXPIRATION, "
            "TS) "
            "VALUES (%(VIX)s, %(VIX_NEAR_WEIGHT)s, %(VIX_NEXT_WEIGHT)s, %(VIX_NEAR_SKEW)s, %(VIX_NEXT_SKEW)s, %(UND_PRICE)s, %(CREATED_TIME)s, %(UPDATED_TIME)s, "
            "%(VIX_FIRST)s, %(VIX_FIRST_SKEW)s, %(FIRST_FUTURE_EXPIRATION)s, %(FIRST_OPTION_EXPIRATION)s, "
            "%(VIX_SECOND)s, %(VIX_SECOND_SKEW)s, %(SECOND_FUTURE_EXPIRATION)s, %(SECOND_OPTION_EXPIRATION)s, "
            "%(VIX_THIRD)s, %(VIX_THIRD_SKEW)s, %(THIRD_FUTURE_EXPIRATION)s, %(THIRD_OPTION_EXPIRATION)s, "
            "%(TS)s)"
            " on DUPLICATE key update"
            " VIX=VALUES(VIX), VIX_NEAR_WEIGHT=VALUES (VIX_NEAR_WEIGHT), VIX_NEXT_WEIGHT=VALUES (VIX_NEXT_WEIGHT), "
            "VIX_NEAR_SKEW=VALUES (VIX_NEAR_SKEW), VIX_NEXT_SKEW=VALUES (VIX_NEXT_SKEW), UND_PRICE=VALUES (UND_PRICE), UPDATED_TIME=VALUES (UPDATED_TIME),"
            " VIX_FIRST = VALUES (VIX_FIRST), VIX_FIRST_SKEW = VALUES (VIX_FIRST_SKEW), FIRST_FUTURE_EXPIRATION = VALUES(FIRST_FUTURE_EXPIRATION), FIRST_OPTION_EXPIRATION = VALUES(FIRST_OPTION_EXPIRATION),"
            " VIX_SECOND = VALUES (VIX_SECOND), VIX_SECOND_SKEW = VALUES (VIX_SECOND_SKEW), SECOND_FUTURE_EXPIRATION = VALUES(SECOND_FUTURE_EXPIRATION), SECOND_OPTION_EXPIRATION = VALUES(SECOND_OPTION_EXPIRATION),"
            " VIX_THIRD = VALUES (VIX_THIRD), VIX_THIRD_SKEW = VALUES (VIX_THIRD_SKEW), THIRD_FUTURE_EXPIRATION = VALUES(THIRD_FUTURE_EXPIRATION), THIRD_OPTION_EXPIRATION = VALUES(THIRD_OPTION_EXPIRATION),"
            " TS = VALUES (TS)"
            )


    while start_time.strftime('%Y-%m-%d %H:%M:%S') < endTime:
        ts = start_time.strftime('%Y-%m-%d %H:%M:%S')

        if ts[-8:] > '16:20:00':
            start_time += timedelta(1)
            start_time = datetime.strptime(start_time.strftime('%Y-%m-%d') + ' 09:40:00', '%Y-%m-%d %H:%M:%S')
            continue

        if start_time.weekday() == 6 or start_time.weekday() == 5:
            start_time += timedelta(1)
            continue
        start_time += timedelta(1 / 24 / 60)

        print('calculating:', ts)

        spot = VIX_index(ts)
        dic = {}
        dic['VIX_NEAR_WEIGHT'] = -1
        dic['VIX_NEXT_WEIGHT'] = -1

        dic['VIX_NEAR_SKEW'] = -1
        dic['VIX_NEXT_SKEW'] = -1
        dic['VIX'] = -1

        if len(spot) != 0:
            dic['VIX'] = round(spot['Price'].item(),3)
            if '_near_weight' in spot.columns:
                dic['VIX_NEAR_WEIGHT'] = spot['_near_weight'].item()
                dic['VIX_NEXT_WEIGHT'] = spot['_next_weight'].item()

                dic['VIX_NEAR_SKEW'] = spot['nearTerm_skew'].item()
                dic['VIX_NEXT_SKEW'] = spot['nextTerm_skew'].item()
            else:
                dic['VIX_NEAR_WEIGHT'] = 1
                dic['VIX_NEXT_WEIGHT'] = 0

                dic['VIX_NEAR_SKEW'] = spot['skewness'].item()
                dic['VIX_NEXT_SKEW'] = 0


        dic['CREATED_TIME'] = datetime.now().strftime('%Y-%m-%d %T')
        dic['UPDATED_TIME'] = datetime.now().strftime('%Y-%m-%d %T')


        vix_1 = VIX_future(1,ts)
        # check if there is data return
        if 'Price' not in vix_1.columns: continue
        dic['VIX_FIRST'] = round(vix_1['Price'].item(),3)
        dic['VIX_FIRST_SKEW'] = vix_1['skewness'].item()
        dic['FIRST_FUTURE_EXPIRATION'] = vix_1['Future_expiration'].item()
        dic['FIRST_OPTION_EXPIRATION'] = vix_1['OptionExpiration'].item()
        dic['UND_PRICE'] = vix_1['UndPrice'].item()


        vix_2 = VIX_future(2, ts)
        if 'Price' not in vix_2.columns: continue
        dic['VIX_SECOND'] = round(vix_2['Price'].item(),3)
        dic['VIX_SECOND_SKEW'] = vix_2['skewness'].item()
        dic['SECOND_FUTURE_EXPIRATION'] = vix_2['Future_expiration'].item()
        dic['SECOND_OPTION_EXPIRATION'] = vix_2['OptionExpiration'].item()


        vix_3 = VIX_future(3, ts)
        if 'Price' not in vix_3.columns: continue
        dic['VIX_THIRD'] = vix_3['Price'].item()
        dic['VIX_THIRD_SKEW'] = vix_3['skewness'].item()
        dic['THIRD_FUTURE_EXPIRATION'] = vix_3['Future_expiration'].item()
        dic['THIRD_OPTION_EXPIRATION'] = vix_3['OptionExpiration'].item()

        dic['TS'] = ts

        print(dic)
        # print(query)
        # con.curA.execute(query,dic)
        # con.cnx.commit()

        # except Exception as e:
        #    print(e)
        #    ii = open('log.txt','w')
        #    ii.write('\n' + str(e))

if __name__=='__main__':
    #@TODO
    calculate_vix_into_db('2017-07-17 09:40:00','2017-09-01 09:30:00')
    # calculate_vix_into_db('2016-05-01 09:30:00', '2016-06-01 09:30:00')
    # calculate_vix_into_db('2016-01-02 09:30:00', '2016-02-01 09:30:00')