#!/bin/usr/env python3
# -*- coding:utf-8 -*-
# ===============================================================================
# LIBRARIES
# ===============================================================================

from datetime import datetime, timedelta
from dbCon import mysql_con
from Synthesize_VOL import VIX_index,linearSpineLine_X_days_vol

# ===============================================================================
# Class Reader
# ===============================================================================

def calculate_vix_into_db(startTime,endTime):
    connn = mysql_con('CALCULATED_VIX')
    start_time = datetime.strptime(startTime,'%Y-%m-%d %H:%M:%S')


    while start_time.strftime('%Y-%m-%d %H:%M:%S') < endTime:
        ts = start_time.strftime('%Y-%m-%d %H:%M:%S')

        if ts[-8:] > '16:20:00':
            start_time += timedelta(1)
            start_time = datetime.strptime(start_time.strftime('%Y-%m-%d') + ' 09:40:00', '%Y-%m-%d %H:%M:%S')
            continue

        if start_time.weekday() == 6 or start_time.weekday() == 5:
            start_time += timedelta(1)
            continue
        start_time += timedelta(1 / 24)

        print('calculating:', ts)
        try:
            vol_x = VIX_index(ts)
            dic = {
                '30_VOL':float(vol_x['vol_blend']),
                '30_AVE_P/C_ratio' : float(vol_x['back_p/c_Ratio'] + vol_x['front_p/c_Ratio'])/2,
                'RECORD_TS':vol_x['Record_TS'],
                'QUOT_TS':vol_x['Quato_TS'],
                'CREATED_TIME':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'UPDATED_TIME':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            query = (
                "INSERT INTO `VIX_TERM_STRUCTURE` (30_VOL, `30_AVE_P/C_ratio`, RECORD_TS, QUOT_TS, CREATED_TIME,UPDATED_TIME) "
                "VALUES (%(30_VOL)s, %(30_AVE_P/C_ratio)s, %(RECORD_TS)s, %(QUOT_TS)s, %(CREATED_TIME)s,%(UPDATED_TIME)s)"
                " ON DUPLICATE KEY UPDATE "
                "30_VOL = (%(30_VOL)s), `30_AVE_P/C_ratio` = (%(30_AVE_P/C_ratio)s),"
                " QUOT_TS = (%(QUOT_TS)s),UPDATED_TIME = (%(UPDATED_TIME)s);"
            )
            connn.curA.execute(query,dic)
            connn.cnx.commit()

            for span_length in [62,93,124,155,186,279,365]:
                vol_x = linearSpineLine_X_days_vol(span_length,ts)
                dic = {
                    str(span_length) + '_VOL': float(vol_x['vol_blend']),
                    str(span_length) + '_AVE_P/C_ratio': float(vol_x['back_p/c_Ratio'] + vol_x['front_p/c_Ratio'])/2,
                    'RECORD_TS': vol_x['Record_TS'],
                    'QUOT_TS': vol_x['Quato_TS'],
                    'CREATED_TIME': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'UPDATED_TIME': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'UND_PRICE': float(vol_x['UndPrice'])
                }
                query = (
                    "INSERT INTO `VIX_TERM_STRUCTURE` (" + str(span_length) + "_VOL, `" + str(span_length) + "_AVE_P/C_ratio`,"
                    " RECORD_TS, QUOT_TS, CREATED_TIME,UPDATED_TIME,UND_PRICE) "
                    "VALUES (%(" + str(span_length) + "_VOL)s, %(" + str(span_length) + "_AVE_P/C_ratio)s, %(RECORD_TS)s, %(QUOT_TS)s,"
                    " %(CREATED_TIME)s,%(UPDATED_TIME)s,%(UND_PRICE)s)"
                    " ON DUPLICATE KEY UPDATE "
                    + str(span_length) + "_VOL = (%(" + str(span_length) + "_VOL)s), `" + str(span_length) + "_AVE_P/C_ratio` = (%(" + str(span_length) + "_AVE_P/C_ratio)s),"
                    " QUOT_TS = (%(QUOT_TS)s),UPDATED_TIME = (%(UPDATED_TIME)s),UND_PRICE = (%(UND_PRICE)s);"
                )
                connn.curA.execute(query, dic)
                connn.cnx.commit()
        except Exception as e:
            f = open('Log.txt','a')
            f.write('calculating :' + ts + '\n' + str(e) + '\n\n')
            continue




if __name__=='__main__':
    calculate_vix_into_db('2016-01-04 09:40:00','2016-02-01 09:30:00')