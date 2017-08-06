#!/bin/usr/env python3
# -*- coding:utf-8 -*-
# ===============================================================================
# LIBRARIES
# ===============================================================================
from dbCon import mysql_con
import pandas as pd
import numpy as np
import copy
from datetime import datetime
ANNUL_RATE = 1.006
# ===============================================================================
# Class Reader
# ===============================================================================
global_conn = mysql_con('OPTION_DATA')

def get_spx_opt_data(term_date_list,nearest_timestamp=datetime.today().strftime("%Y-%m-%d %T"),whole_table=None):

    '''
    near_term: e.g '170623'
    next_term: '170623'
    '''

    if nearest_timestamp[-8:] >= '16:15:00':
        nearest_timestamp = nearest_timestamp[:10]+' 16:15:00'
    print('The timestamp you looking @: ',nearest_timestamp, 'for option ',term_date_list)

    all_data = pd.DataFrame({})
    und_price = 0

    # table name e.g SPX1601
    tableName = 'SPX'+ nearest_timestamp[2:7].replace('-','')

    for date_ in term_date_list:
        query = (
            "SELECT * FROM " + tableName + " " +
            "WHERE (SYMBOL, RECORD_TS) "
            "IN  "
            "("
            "SELECT SYMBOL,MAX(RECORD_TS) "
            "FROM " + tableName + " " +
            "WHERE (SYMBOL LIKE '%" + date_ +"%') "
            "AND (STR_TO_DATE(RECORD_TS,'%Y-%m-%d %T') - STR_TO_DATE('"+ nearest_timestamp+"','%Y-%m-%d %T')) <= 0 "
            "AND (record_ts > '" + nearest_timestamp[:10] + "')"
            "GROUP BY SYMBOL"
            ")"
            "ORDER BY SYMBOL ASC"
        )

        if whole_table is not None:
            # This function is for speeding up the calculation
            ts_symbol = whole_table[
                (whole_table['SYMBOL'].str.contains(date_)) & (whole_table['RECORD_TS'] <= nearest_timestamp) & (whole_table['RECORD_TS'] > nearest_timestamp[:10])
            ].groupby(['SYMBOL']).agg({'RECORD_TS': 'max'})
            ts_symbol.reset_index(inplace=True)
            opt_data = pd.merge(whole_table, ts_symbol, on=['RECORD_TS', 'SYMBOL'], how='inner')

        else:
            opt_data = global_conn.get_data_by_pandas(query)
            assert len(opt_data) > 0, ValueError('Option data Error, it might be due to that day'
                                                 ' is a holiday,so no data existing'
                                                 'in database please'
                                                 'check following query in mySQL' +
                                                 '\n' + query)
            assert len(opt_data[opt_data['OPT_ASK']==0]) < len(opt_data)*0.4, \
                ValueError('Option data Error, Getting all zero option chain,'
                           ' please check following query in mySQL' + '\n' + query)
        # get call data
        call_data = opt_data[opt_data['SYMBOL'].str.contains(date_ + 'C')]
        # print(call_data)
        call_data = call_data.rename(columns={
            'OPT_ASK': 'C_ask',
            'OPT_BID': 'C_bid',
            'SYMBOL': 'C_symbol',
            'RECORD_TS': 'C_TS'
        })
        call_data = call_data[['C_ask', 'C_bid', 'C_symbol', 'C_TS', 'STRIKE']]
        # get put data
        put_data = opt_data[opt_data['SYMBOL'].str.contains(date_ + 'P')]
        put_data = put_data.rename(columns={
            'OPT_ASK': 'P_ask',
            'OPT_BID': 'P_bid',
            'SYMBOL': 'P_symbol',
            'RECORD_TS': 'P_TS',
        })

        put_data = put_data[['P_ask', 'P_bid', 'P_symbol', 'P_TS', 'STRIKE']]

        # merge into what likes in IB
        all_data = pd.concat([all_data, call_data.merge(put_data, left_on='STRIKE', right_on='STRIKE', how='outer')],
                             axis=0)
        und_price += opt_data['UND_PRICE'].mean()

    # change bid price into 0 (-1 in database), all in str format
    all_data['P_bid'] = all_data['P_bid'].astype(float)
    all_data.loc[all_data['P_bid'] == -1, 'P_bid'] = 0

    all_data['P_ask'] = all_data['P_ask'].astype(float)
    all_data.loc[all_data['P_ask'] == -1, 'P_ask'] = 0

    all_data['C_bid'] = all_data['C_bid'].astype(float)
    all_data.loc[all_data['C_bid'] == -1, 'C_bid'] = 0

    all_data['C_ask'] = all_data['C_ask'].astype(float)
    all_data.loc[all_data['C_ask'] == -1, 'C_ask'] = 0
    # return all data and average price of underlying price
    # print(all_data)
    return all_data,round(und_price/len(term_date_list),3)


def get_existing_month_contract(nearest_timestamp,whole_table = None):
    '''
    Return a list of existing monthly options date
    E.g
    {'dates':
    ['160819', '160916', '161021', '161118', '161216', '170120', '170317', '170616', '171215', '180615', '181221']
    }
    '''

    tableName = 'SPX' + nearest_timestamp[2:7].replace('-', '')

    query = (
        "SELECT SYMBOL,MAX(RECORD_TS) FROM " + tableName +
        " WHERE (SYMBOL LIKE '%P0%') "
        "AND (STR_TO_DATE(RECORD_TS,'%Y-%m-%d %T') - STR_TO_DATE('"+nearest_timestamp+"','%Y-%m-%d %T')) <= 0 "
        "AND (strike='2000') AND (record_ts > '" + nearest_timestamp[:10] + "')GROUP BY SYMBOL;"
    )

    if whole_table is not None:

        all_options = whole_table[(whole_table['SYMBOL'].str.contains('P0')) & (whole_table['RECORD_TS'] <= nearest_timestamp) & (
            whole_table['RECORD_TS'] > nearest_timestamp[:10]) & (whole_table['STRIKE'] == 2000)].groupby(['SYMBOL']).agg({'RECORD_TS': 'max'})
        all_options.reset_index(inplace=True)

    else:
        all_options = global_conn.get_data_by_pandas(query)
        assert len(all_options) != 0,ValueError('Option data Error, it might be due to that day'
                                                 ' is a holiday,so no data existing'
                                                 'in database please'
                                                 'check following query in mySQL' +
                                                 '\n' + query)

    return [i[6:12] for i in all_options[all_options['SYMBOL'].str.contains('SPX ')]['SYMBOL']]


def get_whole_table(tableName):

    query = (
        "select * from `" + tableName + "` where symbol like '%SPX %';"
    )

    return global_conn.get_data_by_pandas(query)


def get_vix_daliy_all():
    vix_future_con = mysql_con('vix_future')
    return vix_future_con.get_data_by_pandas('select * from vix_spread_data order by vix_date desc')
if __name__=='__main__':
    print('start')
    dd = get_vix_daliy_all()
    dd['CD'] = dd['CD'].astype(int)
    month_1 = []
    month_2 = []
    month_3 = []
    month_4 = []
    record_ts = []
    VIX = []
    for iidex, content in dd.groupby(['vix_date']):
        for content in content:
            try:
                month_1.append(content[(content['CD'] < 21) & (content['CD'] > 0)]['back_f_price'].item())
            except:
                month_1.append(-1)
            try:
                month_2.append(content[(content['CD'] < 46) & (content['CD'] >= 21)]['back_f_price'].item())
            except:
                month_2.append(-1)
            try:
                month_3.append(content[(content['CD'] < 66) & (content['CD'] >= 46)]['back_f_price'].item())
            except:
                month_3.append(-1)
            try:
                month_4.append(content[(content['CD'] < 46) & (content['CD'] >= 86)]['back_f_price'].item())
            except:
                month_4.append(-1)
        record_ts.append(iidex)
        VIX.append(content[0:1]['vix_open'].item())