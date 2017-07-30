#!/bin/usr/env python3
# -*- coding:utf-8 -*-
# ===============================================================================
# LIBRARIES
# ===============================================================================
from dbCon import mysql_con
import pandas as pd
import numpy as np
import copy
from datetime import datetime,timedelta
from GetOptDataFromMysql import get_spx_opt_data,get_existing_month_contract
ANNUL_RATE = 1.006
# ===============================================================================
# Class Reader
# ===============================================================================


def find_which_two_options(days=30,calculating = False,cur_date = datetime.today().strftime("%Y-%m-%d %T")):
    front = days-7
    back = days +7
    _front_days = 0
    front_date = None
    back_date = None
    cur_date = datetime.strptime(cur_date,"%Y-%m-%d %H:%M:%S")
    for i in range(front+1,back):
        if (cur_date+timedelta(i)).weekday() == 4:
            front_date = cur_date + timedelta(i)
            _front_days = i
            # check if it is the third friday
            if ( front_date.date().weekday() == 4) and (14 < front_date.day <22) and (calculating==False):
                front_date = front_date - timedelta(1)
            break

    for j in range(_front_days+1,back):
        if (cur_date + timedelta(j)).weekday() == 4:
            back_date = cur_date + timedelta(j)
            # check if it is the third friday
            if ( back_date.date().weekday() == 4) and (14 < back_date.day <22) and (calculating==False):
                back_date = back_date - timedelta(1)
            break

    # print(front_date,back_date)
    return front_date,back_date



def find_how_many_mins_left(df,present_time):
    '''
    Return how many mins left before expiration date
    return:
    Minutes left
    datetime of expiration date
    '''

    # Transfer into datetime format
    expire_date = df[0:1]['P_symbol'].item().replace('SPX','').replace('W','').replace(' ','').replace(' ','')[:6]
    year = '20'+expire_date[:2]
    month = expire_date[2:4]
    days = expire_date[4:]
    _date = datetime.strptime(year + '-' + month + '-' + days, '%Y-%m-%d')

    # minutes from midnight until 8:30 a.m. for “standard” SPX expirations; or minutes
    # from midnight until 3:00 p.m. for “weekly” SPX expirations
    if _date.weekday() == 4 and 14 < _date.day < 22:
        M_Settleday = 510
    else:
        M_Settleday = 900

    #  minutes remaining until expiration date, date of expiration is e.g 2017-05-19 00:00:00
    now = datetime.strptime(present_time,'%Y-%m-%d %H:%M:%S')

    M_CurrentDay = (_date - now).total_seconds()/60

    # T = {M_Currentday + M_Settlement day } / Minutes in a year
    _T = (M_Settleday + M_CurrentDay) / 525600
    mins_left = M_Settleday + M_CurrentDay

    return _T, _date, mins_left


def find_out_atm_option(df):
    # Put mid price minus Call price
    # In the money Put has higher spx price, so it should be below the ATM option
    # Put > Call, in the bottom
    alldata = copy.deepcopy(df)
    alldata = alldata[(alldata['P_bid'] != 0) & (alldata['C_bid']!=0)]
    diff = ((alldata['P_ask'].astype(float) + alldata['P_bid'].astype(float)) / 2 -
            (alldata['C_ask'].astype(float) + alldata['C_bid'].astype(float)) / 2)
    alldata.loc[:,'bid_ask_diff'] = diff

    # Sort by put - call value
    alldata.sort_values('bid_ask_diff', inplace=True)
    alldata.reset_index(inplace=True, drop=True)

    # find smallest index
    try:
        index_smallest_value = abs(alldata['bid_ask_diff']).sort_values(0).index[0]
    except:
        ValueError('Option data error')

    # get put option
    # out_of_money_put = alldata[:index_smallest_value]

    # get call option
    # out_of_money_call = alldata[index_smallest_value+1:]

    # get ATM option
    atm_option = alldata[index_smallest_value:index_smallest_value+1]

    return atm_option


def find_forward_index_p(df,present_time):
    '''
    return: F index value
            expiration date
    '''
    alldata = copy.deepcopy(df)

    # get Minutes left, expiration date and strike price
    _T, expiration_date, mins_left = find_how_many_mins_left(alldata, present_time)
    strike_p = df[0:1]['P_symbol'].item().replace('SPX','').replace('W','').replace(' ','').replace(' ','')[-8:]

    # calculate risk free interested until expiration
    risk_free_interest =float(ANNUL_RATE**(1/365))**float((expiration_date-datetime.today()).days) - 1

    # F = Strike Price + e^RT x (Call Price - Put Price)
    F = int(strike_p[:5]) + np.exp(risk_free_interest*_T) * (
        ((alldata['C_ask'].astype(float).item() + alldata['C_bid'].astype(float).item()) / 2 -
         (alldata['P_ask'].astype(float).item() + alldata['P_bid'].astype(float).item()) / 2)
    )

    return F


def get_ride_of_two_zero_bid(df,put_or_call):
    option_len = len(df)

    # if call from top to bottom, put from bottom to top
    if put_or_call == 'call':
        call_option = df
        for row_number in range(option_len-1):
            if df[row_number:row_number + 1].C_bid.item() == 0 and \
                            df[row_number + 1:row_number + 2].C_bid.item() == 0:
                call_option = df[:row_number]
                return call_option[call_option['C_bid'] != 0]

        return call_option[call_option['C_bid'] != 0]

    else:
        put_option = df
        for row_number in range(option_len-1):
            if df[-row_number - 1:][:1].P_bid.item() == 0 and \
                            df[-row_number - 2:][:1].P_bid.item() == 0:
                put_option = df[-row_number:]
                return put_option[put_option['P_bid'] != 0]
        return put_option[put_option['P_bid'] != 0]


def find_put_call_option(option_chain, f_1):
    option_chain = copy.deepcopy(option_chain)
    option_chain.loc[:, 'strike_price'] = option_chain['C_symbol'].str[-8:-3].astype(int)

    # find all put options for option_chain term and next term
    _out_of_money_put = option_chain[option_chain['strike_price'] < f_1][:-1]
    _out_of_money_put = get_ride_of_two_zero_bid(_out_of_money_put,'put')

    # find atm option
    _k0 = option_chain[option_chain['strike_price'] < f_1][-1:]

    # find out of money call
    _out_of_money_call = option_chain[option_chain['strike_price'] > f_1][:-1]
    _out_of_money_call = get_ride_of_two_zero_bid(_out_of_money_call, 'call')


    return (_out_of_money_put,_out_of_money_call,_k0)


def find_options_volatility(put,call,k0,f_index,present_time):
    '''
    return: Volatility Theta
            T fraction mins/mins of one year
            mins_left
    '''
    _T_1, expiration_date, mins_left = find_how_many_mins_left(put,present_time)
    _T_2 = find_how_many_mins_left(call,present_time)[0]
    _T = (_T_1+_T_2)/2

    # calculate risk free interested until expiration
    risk_free_interest = float(ANNUL_RATE ** (1 / 365)) ** float((expiration_date - datetime.today()).days) - 1

    # reorganize put call k0 options
    # for put options
    put_mid_quote = pd.DataFrame((put['P_bid'].astype(float)+put['P_ask'].astype(float))/2)
    put_mid_quote.columns=['mid_quote']
    put_all = pd.concat([
        put_mid_quote['mid_quote'],
        put['strike_price'],
        ],axis=1)
    put_all.loc[:,'type'] = 'put'

    # for call options
    call_mid_quote = pd.DataFrame((call['C_bid'].astype(float) + call['C_ask'].astype(float)) / 2)
    call_mid_quote.columns = ['mid_quote']
    call_all = pd.concat([
        call_mid_quote['mid_quote'],
        call['strike_price'],
    ], axis=1)
    call_all.loc[:, 'type'] = 'call'

    # for k0 : middle row df of Put/Call Average
    k0_mid_quote = pd.DataFrame(((k0['C_bid'].astype(float) + k0['C_ask'].astype(float)) / 2 +
                                  (k0['P_bid'].astype(float) + k0['P_ask'].astype(float)) / 2) /2 )
    k0_mid_quote.columns = ['mid_quote']
    k0_all = pd.concat([
        k0_mid_quote['mid_quote'],
        k0['strike_price'],
    ], axis=1)
    k0_all.loc[:, 'type'] = 'Put/Call Average'

    # concat put & k0 & call
    alldata = pd.concat([put_all,k0_all,call_all],axis=0)

    # reset index
    alldata.reset_index(inplace=True,drop=True)

    ##################################################
    # To check all the put call options that will count into calculation
    # Put/Call Average should have largest value
    #
    # print(alldata, _T, risk_free_interest)
    #
    ##################################################

    # value for summation
    sum_value = 0
    for index,row in alldata.iterrows():

        # first row use adjacent row to calculate delta k
        if index == 0:
            delta_k = alldata['strike_price'][1:2].item() - row['strike_price']
            sum_value += delta_k/row['strike_price'] ** 2 * np.exp(_T * risk_free_interest) * row['mid_quote']

        # last row use adjacent row to calculate delta k
        elif index == len(alldata)-1:
            delta_k = abs(alldata['strike_price'][-2:-1].item() - row['strike_price'])
            sum_value += delta_k / row['strike_price'] ** 2 * np.exp(_T * risk_free_interest) * row['mid_quote']

        else:
            # delta k is half the difference between the strike prices on either side of
            delta_k = abs(alldata['strike_price'][index - 1:index].item() -
                          alldata['strike_price'][index:index + 1].item())
            sum_value += delta_k / row['strike_price'] ** 2 * np.exp(_T * risk_free_interest) * row['mid_quote']

    return sum_value*2/_T - ((f_index/k0_all['strike_price'].item() - 1)**2)/_T , _T, mins_left


def find_month_option(futureDepth,calculating=False,cur_date = datetime.today().strftime("%Y-%m-%d %T")):
    # return option_expire_date and future expiration date

    cur_date = datetime.strptime(cur_date,"%Y-%m-%d %H:%M:%S")

    # futureDepth 1 ==> front month future
    cur_option = datetime(cur_date.year,cur_date.month,1)

    # finding this month future expiration date
    for i in range(14,22):
        if ((cur_option+timedelta(i)).weekday() == 2) and (14 < (cur_option+timedelta(i)).day <22):
            cur_option = cur_option+timedelta(i)
            break
    print(cur_option)
    # if this month future not expire front future is the that month,
    if cur_option <= cur_date:
        futureDepth += 1
        # check if future month is 12
        if cur_date.month + futureDepth-1 == 12:
            cur_option = datetime(cur_option.year, 12, 1)
        elif cur_date.month + futureDepth-1 != 12:
            cur_option = datetime(cur_option.year + int((cur_option.month + futureDepth - 1) / 12),
                                  int(cur_option.month + futureDepth - 1) % 12, 1)
        for i in range(14, 22):
            if ((cur_option + timedelta(i)).weekday() == 2) and (14 < (cur_option + timedelta(i)).day < 22):
                cur_option = cur_option + timedelta(i)
                break

    if cur_date.month + futureDepth == 12:
        date_ = datetime(cur_date.year,12, 1)
    if cur_date.month + futureDepth != 12:
        date_ = datetime(cur_date.year + int((cur_date.month  + futureDepth) / 12 ),
                         int(cur_date.month  + futureDepth)%12 ,1)
    # print('Future matureDate:',cur_option)
    for i in range(14,22):
        if (date_+timedelta(i)).weekday() == 4:
            front_date = date_ + timedelta(i)
            # check if it is the third friday
            if calculating == True:
                return front_date.strftime('%Y%m%d'),cur_option.strftime('%Y%m%d')
            else:
                return (front_date - timedelta(1)).strftime('%Y%m%d'),cur_option.strftime('%Y%m%d')


def main(expiration_t,nearest_timestamp):
    assert isinstance(expiration_t,list), 'input of exiration data must be list'
    alldata,und_price = get_spx_opt_data(expiration_t,nearest_timestamp)
    assert len(alldata) != 0, 'Data not avaliable'
    # if there is no data inside return empty pandas df
    if len(alldata) == 0: return pd.DataFrame({})
    # record time span for calculating the vix
    data_time_range = list(alldata['C_TS']) + list(alldata['P_TS'])
    time_dic = pd.DataFrame({
        'end': [max(data_time_range)],
        'start': [min(data_time_range)]
    })

    # Step 1:
    # calculate forward index price
    option_chain = alldata
    # get ATM option
    option_atm = find_out_atm_option(option_chain)

    # get forward_index price
    f_price = find_forward_index_p(option_atm,nearest_timestamp)
    forward_strick = pd.DataFrame({'Forward Price: ':[f_price]})

    # get out of money put call and k0
    # some times if there is no enough data, return empty DataFrame
    # _k0 first term below the forward price
    _out_of_money_put, _out_of_money_call, _k0 \
        = find_put_call_option(option_chain, f_price)
    if len(_out_of_money_call) == 0 or len(_out_of_money_put) == 0: return pd.DataFrame({})
    skew_dic = pd.DataFrame({ 'put/call_Ratio': [round(len(_out_of_money_put)/len(_out_of_money_call),3)]})


    # Step 2:
    # Calculate volatility for both near-term and next-term options
    # get near and next term T parameter for further calculation
    # _theta_square ===> Implied Vol, min_left_ratio==> minLeft/minOfYear, _mins_left==>mins int

    _theta_square, min_left_ratio, _mins_left = find_options_volatility(
        _out_of_money_put,
        _out_of_money_call,
        _k0,
        f_price,
        nearest_timestamp
    )

    # Step 3:
    # Calculate the option Volatility

    VIX = np.sqrt(_theta_square) * 100
    VIX = pd.DataFrame({'Vol_Index':[VIX]})
    return pd.concat([VIX,time_dic,forward_strick,skew_dic,
                      pd.DataFrame({'UndPrice':[und_price]}),
                      pd.DataFrame({'min_ratio': [min_left_ratio]}),
                      pd.DataFrame({'min_left': [_mins_left]}),
                      pd.DataFrame({'theta_square': [_theta_square]})],axis=1)


if __name__=='__main__':
    vix_1 = main(['170818'],'2017-07-20 13:10:00')
    print(vix_1)
