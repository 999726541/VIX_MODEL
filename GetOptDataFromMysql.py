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


def get_spx_opt_data(term_date_list,nearest_timestamp=datetime.today().strftime("%Y-%m-%d %T")):

    '''
    near_term: e.g '170623'
    next_term: '170623'
    '''

    if nearest_timestamp[-8:] >= '16:00:00':
        nearest_timestamp = nearest_timestamp[:10]+' 16:00:00'
    print('The timestamp you looking @: ',nearest_timestamp)
    conn = mysql_con('OPTION_DATA')
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
            "GROUP BY SYMBOL"
            ")"
            "ORDER BY SYMBOL ASC"
        )

        opt_data = conn.get_data_by_pandas(query)
        if len(opt_data) == 0:
            return pd.DataFrame({}),''




        # print(opt_data)
        # if len(opt_data) == 0: raise 'NO '+date_+' DATA IN DATABASE'

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


if __name__=='__main__':
    print(get_spx_opt_data(['160129','160205'],'2016-01-05 10:34:23'))