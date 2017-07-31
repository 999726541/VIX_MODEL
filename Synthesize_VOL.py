#!/bin/usr/env python3
# -*- coding:utf-8 -*-
# ===============================================================================
# LIBRARIES
# ===============================================================================
from GetOptDataFromMysql import get_existing_month_contract
import pandas as pd
import numpy as np
from VOL_MODEL_MAIN import main as vol_caculator
from datetime import datetime,timedelta
ANNUL_RATE = 1.006
# ===============================================================================
# Class Reader
# ===============================================================================
'''

The purpose is using two point linear spline interpolation approach to find corresponding x-days implied volatility
e.g VIX is 30-days IV

'''


def Opts_For_VIX(days=30, calculating = False, cur_date = datetime.today().strftime("%Y-%m-%d %T")):
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


def monthOptsForVol(daysExpecting = 93, calculating = False,cur_date = datetime.today().strftime("%Y-%m-%d %T")):
    '''
    Return of one or two month options corresponding to daysExpction
    return : '160916', '161021'
    '''
    # get all existing option existing in database
    monthly_option_list = get_existing_month_contract(cur_date)
    cur_date = datetime.strptime(cur_date, "%Y-%m-%d %H:%M:%S")
    target_dates = cur_date + timedelta(daysExpecting)

    # find if the option of this month expired
    # only four continues month option exist
    # quarterly option appears after four continues opt and last one is about one year [3,6,9,12]
    # yearly option appears within the two years
    # e.g 2017-07-30 option list [17-8,17-9,17-10,17-11] + [17-9, 17-12, 18-1, 18-3, 18-6] + [17-12, 18-6, 18-12, 19-6, 19-12]
    # Together [17-8,17-9,17-10,17-11,    17-12, 18-1, 18-3,      18-6, 18-12, 19-6, 19-12]

    target_dates = target_dates.strftime('%Y%m%d')[2:]
    if target_dates not in monthly_option_list:
        monthly_option_list.append(target_dates)
        monthly_option_list.sort()
        assert monthly_option_list.index(target_dates)!=0, ValueError('Date is to short, please enter value larger than 30 days')
        assert monthly_option_list.index(target_dates) != len(monthly_option_list)-1, ValueError(
            'Date is to short, please enter value shorter days')
        _front_option = monthly_option_list[monthly_option_list.index(target_dates) - 1]
        _back_option = monthly_option_list[monthly_option_list.index(target_dates) + 1]
        if calculating == False:
            # for recording data purpose
            return (datetime.strptime('20' + _front_option, "%Y%m%d") - timedelta(1)).strftime("%Y%m%d")[2:],\
                   (datetime.strptime('20' + _back_option, "%Y%m%d") - timedelta(1)).strftime("%Y%m%d")[2:]

        # for calculating vix purpose
        return _front_option,_back_option
    else:
        return target_dates,None


def weighted_vix(near_term_theta,near_term_mins_left,T_1,next_term_theta,next_term_mins_left,T_2,days):
    '''
     N_t1 : number of minutes to settlement of the near-term options
     N_t2 : number of minutes to settlement of the next-term options
     N_X : number of minutes in a X days ==> int : x*1440
     N_365 : number of minutes in a 365 days ==> int : 525600
    '''

    N_t1 = near_term_mins_left
    N_t2 = next_term_mins_left
    N_X = days*1440
    N_365 = 525600

    VIX_square = (( T_1 * near_term_theta * ((N_t2 - N_X) / (N_t2 - N_t1)) +
          T_2 * next_term_theta * ((N_X - N_t1) / (N_t2 - N_t1)) ) * (N_365/N_X))

    VIX = np.sqrt(VIX_square)*100

    near_term_weight = (N_t2 - N_X) / (N_t2 - N_t1)
    next_term_weight = (N_X - N_t1) / (N_t2 - N_t1)

    return VIX,near_term_weight,next_term_weight


def VIX_index(nearest_timestamp=datetime.today().strftime("%Y-%m-%d %T")):
    date_front, date_back = Opts_For_VIX(30, calculating=True, cur_date=nearest_timestamp)

    if date_back == None:
        date_front = date_front.strftime("%Y%m%d")[2:]
        _front = vol_caculator([date_front], nearest_timestamp=nearest_timestamp)
        return {'vol_blend': _front['Vol_Index'].item(),
                'front_p/c_Ratio': _front['put/call_Ratio'].item(),
                'front_exipration': _front['expirationDate'].item(),
                'front_vol': _front['Vol_Index'].item(),
                'front_forward_Price': _front['ForwardPrice'].item(),
                'back_p/c_Ratio': 0,
                'back_exipration': 0,
                'back_vol': 0,
                'back_forward_Price': 0,
                'UndPrice': _front['UndPrice'].item(),
                'Record_TS': nearest_timestamp,
                'Quato_TS': _front['quot_TS'].item()
                }
    else:
        date_front = date_front.strftime("%Y%m%d")[2:]
        date_back = date_back.strftime("%Y%m%d")[2:]
        _front = vol_caculator([date_front], nearest_timestamp=nearest_timestamp)
        _back = vol_caculator([date_back], nearest_timestamp=nearest_timestamp)

        a = datetime.strptime((_front['quot_TS'].item()), '%Y-%m-%d %H:%M:%S')
        b = datetime.strptime((_back['quot_TS'].item()), '%Y-%m-%d %H:%M:%S')
        quot_time = (a + (b - a) / 2).strftime('%Y-%m-%d %H:%M:%S')

        vol, front_weight, back_weight = weighted_vix(_front['theta_square'].item(), _front['min_left'].item(),
                                                      _front['min_ratio'].item(),
                                                      _back['theta_square'].item(), _back['min_left'].item(),
                                                      _back['min_ratio'].item(), 30)
        print('FrontWeight:BackWeight ', front_weight, ':', back_weight)
        return {'vol_blend': vol,
                'front_p/c_Ratio': _front['put/call_Ratio'].item(),
                'front_exipration': _front['expirationDate'].item(),
                'front_vol': _front['Vol_Index'].item(),
                'front_forward_Price': _front['ForwardPrice'].item(),
                'back_p/c_Ratio': _back['put/call_Ratio'].item(),
                'back_exipration': _back['expirationDate'].item(),
                'back_vol': _back['Vol_Index'].item(),
                'back_forward_Price': _back['ForwardPrice'].item(),
                'UndPrice': _front['UndPrice'].item(),
                'Record_TS': nearest_timestamp,
                'Quato_TS': quot_time
                }


def linearSpineLine_X_days_vol(days,nearest_timestamp=datetime.today().strftime("%Y-%m-%d %T")):
    # find which one or two monthly option you need
    date_front, date_back = monthOptsForVol(days, calculating=True, cur_date=nearest_timestamp)

    if date_back == None:
        # print('The option you looking:',date_front)
        _front = vol_caculator([date_front], nearest_timestamp=nearest_timestamp)
        return {'vol_blend': _front['Vol_Index'].item(),
                'front_p/c_Ratio': _front['put/call_Ratio'].item(),
                'front_exipration': _front['expirationDate'].item(),
                'front_vol': _front['Vol_Index'].item(),
                'front_forward_Price': _front['ForwardPrice'].item(),
                'back_p/c_Ratio': 0,
                'back_exipration': 0,
                'back_vol': 0,
                'back_forward_Price': 0,
                'UndPrice': _front['UndPrice'].item(),
                'Record_TS': nearest_timestamp,
                'Quato_TS': _front['quot_TS'].item()
                }


    else:
        _front = vol_caculator([date_front], nearest_timestamp=nearest_timestamp)
        _back = vol_caculator([date_back], nearest_timestamp=nearest_timestamp)
        # print(_front,_back)

        # get quato time
        a = datetime.strptime((_front['quot_TS'].item()), '%Y-%m-%d %H:%M:%S')
        b = datetime.strptime((_back['quot_TS'].item()), '%Y-%m-%d %H:%M:%S')
        quot_time = (a + (b - a) / 2).strftime('%Y-%m-%d %H:%M:%S')

        vol,front_weight,back_weight =  weighted_vix(_front['theta_square'].item(), _front['min_left'].item(), _front['min_ratio'].item(),
                            _back['theta_square'].item(), _back['min_left'].item(), _back['min_ratio'].item(), days)
        print('FrontWeight:BackWeight ',front_weight,':',back_weight)

        return {'vol_blend':vol,
                'front_p/c_Ratio':_front['put/call_Ratio'].item(),
                'front_exipration':_front['expirationDate'].item(),
                'front_vol':_front['Vol_Index'].item(),
                'front_forward_Price': _front['ForwardPrice'].item(),
                'back_p/c_Ratio': _back['put/call_Ratio'].item(),
                'back_exipration': _back['expirationDate'].item(),
                'back_vol': _back['Vol_Index'].item(),
                'back_forward_Price': _back['ForwardPrice'].item(),
                'UndPrice':_front['UndPrice'].item(),
                'Record_TS':nearest_timestamp,
                'Quato_TS':quot_time
                }


if __name__=='__main__':
    print(VIX_index('2016-07-17 09:40:00'))
    # print(linearSpineLine_X_days_vol(279,'2016-09-20 16:15:00'))
