# ===============================================================================
# LIBRARIES
# ===============================================================================
from dbCon import mysql_con
import pandas as pd
import numpy as np
import copy
from datetime import datetime,timedelta
from GetOptDataFromMysql import get_spx_opt_data
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


def get_most_updated_data(term_date_list,nearest_timestamp=datetime.today().strftime("%Y-%m-%d %T")):
    '''
    near_term: e.g '170623'
    next_term: '170623'
    '''
    if nearest_timestamp[-8:] >= '16:00:00':
        nearest_timestamp = nearest_timestamp[:10]+' 16:00:00'
    print('The timestamp you looking @: ',nearest_timestamp)
    conn = mysql_con()
    all_dates = term_date_list
    bid_ask = pd.DataFrame({})
    # get table name like `SPX1601`
    db_table_name = 'SPX' + nearest_timestamp[2:7].replace('-','')

    for term_date in all_dates:
        # calculate one date options
        print('getting ',term_date,' option ')
        all_contract_name = [name for (name,) in conn.query("show tables like '%" + term_date + "%bidask'")]
        if len(all_contract_name) == 0: raise 'THIS OPTION IS NOT EXIST IN DATABASE CHECK DATABASE'
        print('fetching :',term_date,' data from DataBase')
        # sort
        all_contract_name.sort()
        # print(all_contract_name)
        # sql query to find e.g  170519C01600000_bidask
        for name in all_contract_name:
            dic = {}
            if 'C' in name:
                # get call contract name if exist, if drop or not
                dic['C_symbol'] = name

                # check if both call and put exist
                if name.replace('C','P') in all_contract_name:
                    dic['P_symbol'] = name.replace('C','P')

                    # print('getting ',name)


                    # organize data into df
                    # C_bid,C_ask,C_bidtime,C_asktime,C_symbol,P_bid,P_ask,P_bidtime,P_asktime,P_symbol
                    call_bid = conn.get_data_by_pandas(
                        'select * from `' + name + '` where B_A_C="bid" order by ABS('
                                                   'STR_TO_DATE(Record_TS,"%Y-%m-%d %T") - STR_TO_DATE("'+nearest_timestamp
                                                    + '","%Y-%m-%d %T")' +
                                                   ')' +
                                                   ' ASC limit 1'
                    )
                    call_ask = conn.get_data_by_pandas(
                        'select * from `' + name + '` where B_A_C="ask" order by ABS('
                                                   'STR_TO_DATE(Record_TS,"%Y-%m-%d %T") - STR_TO_DATE("'+nearest_timestamp
                                                    + '","%Y-%m-%d %T")' +
                                                   ')' +
                                                   ' ASC limit 1'
                    )

                    put_bid = conn.get_data_by_pandas(
                        'select * from `' + name.replace('C',
                                                         'P') + '` where B_A_C="bid" order by ABS('
                                                   'STR_TO_DATE(Record_TS,"%Y-%m-%d %T") - STR_TO_DATE("'+nearest_timestamp
                                                    + '","%Y-%m-%d %T")' +
                                                   ')' +
                                                   ' ASC limit 1'
                    )
                    put_ask = conn.get_data_by_pandas(
                        'select * from `' + name.replace('C',
                                                         'P') + '` where B_A_C="ask" order by ABS('
                                                   'STR_TO_DATE(Record_TS,"%Y-%m-%d %T") - STR_TO_DATE("'+nearest_timestamp
                                                    + '","%Y-%m-%d %T")' +
                                                   ')' +
                                                   ' ASC limit 1'
                    )

                    # if no data in database, continue
                    if len(call_bid) == 0 or len(put_bid) == 0: continue

                    call_dic = {'C_bid': [call_bid['P'].item()],
                                'C_symbol': [call_bid['Symbol'].item()],
                                'C_ask': [call_ask['P'].item()],
                                'C_bidtime': [call_bid['Record_TS'].item()],
                                'C_asktime': [call_ask['Record_TS'].item()]}

                    put_dic = {'P_bid': [put_bid['P'].item()],
                               'P_symbol': [put_bid['Symbol'].item()],
                               'P_ask': [put_ask['P'].item()],
                               'P_bidtime': [put_bid['Record_TS'].item()],
                               'P_asktime': [put_ask['Record_TS'].item()]}

                    # combine two dic together
                    call_dic.update(put_dic)
                    # print(call_dic)
                    bid_ask = pd.concat([bid_ask, pd.DataFrame(call_dic)], axis=0)

                # if one the contract (put or call) not exist, then move to next call option
                else:
                    continue

    # if there is no data in the bid_ask
    if len(bid_ask) == 0:return bid_ask

    # change bid price into 0 (-1 in database), all in str format
    bid_ask['P_bid'] = bid_ask['P_bid'].astype(float)
    bid_ask.loc[bid_ask['P_bid'] == -1, 'P_bid'] = 0

    bid_ask['P_ask'] = bid_ask['P_ask'].astype(float)
    bid_ask.loc[bid_ask['P_ask'] == -1, 'P_ask'] = 0

    bid_ask['C_bid'] = bid_ask['C_bid'].astype(float)
    bid_ask.loc[bid_ask['C_bid'] == -1, 'C_bid'] = 0

    bid_ask['C_ask'] = bid_ask['C_ask'].astype(float)
    bid_ask.loc[bid_ask['C_ask'] == -1, 'C_ask'] = 0

    return bid_ask


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


def read_from_csv():

    bid_ask = pd.read_csv('ssss.csv')

    return bid_ask


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
    index_smallest_value = abs(alldata['bid_ask_diff']).sort_values(0).index[0]

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


def find_put_call_option(near_term,f_1,next_term,f_2):
    near = copy.deepcopy(near_term)
    next = copy.deepcopy(next_term)
    near.loc[:, 'strike_price'] = near['C_symbol'].str[-8:-3].astype(int)
    next.loc[:, 'strike_price'] = next['C_symbol'].str[-8:-3].astype(int)

    # find all put options for near term and next term
    near_term_out_of_money_put = near[near['strike_price'] < f_1][:-1]
    near_term_out_of_money_put = get_ride_of_two_zero_bid(near_term_out_of_money_put,'put')

    next_term_out_of_money_put = next[next['strike_price'] < f_2][:-1]
    next_term_out_of_money_put = get_ride_of_two_zero_bid(next_term_out_of_money_put, 'put')

    # find atm option
    near_term_k0 = near[near['strike_price'] < f_1][-1:]
    next_term_k0 = next[next['strike_price'] < f_2][-1:]

    # find out of money call
    near_term_out_of_money_call = near[near['strike_price'] > f_1][:-1]
    near_term_out_of_money_call = get_ride_of_two_zero_bid(near_term_out_of_money_call, 'call')

    next_term_out_of_money_call = next[next['strike_price'] > f_2][:-1]
    next_term_out_of_money_call = get_ride_of_two_zero_bid(next_term_out_of_money_call, 'call')

    return (near_term_out_of_money_put,near_term_out_of_money_call,near_term_k0,
            next_term_out_of_money_put,next_term_out_of_money_call,next_term_k0
            )


def find_options_volatility(put,call,k0,f_index,present_time):
    '''
    return: Volatility Theta
            T fraction
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

    # for k0
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


def weighted_vix(near_term_theta,near_term_mins_left,T_1,next_term_theta,next_term_mins_left,T_2):
    '''
     N_t1 : number of minutes to settlement of the near-term options
     N_t2 : number of minutes to settlement of the next-term options
     N_30 : number of minutes in a 30 days ==> int : 43200
     N_365 : number of minutes in a 365 days ==> int : 525600
    '''

    N_t1 = near_term_mins_left
    N_t2 = next_term_mins_left
    N_30 = 43200
    N_365 = 525600

    VIX_square = (( T_1 * near_term_theta * ((N_t2 - N_30) / (N_t2 - N_t1)) +
          T_2 * next_term_theta * ((N_30 - N_t1) / (N_t2 - N_t1)) ) * (N_365/N_30))

    VIX = np.sqrt(VIX_square)*100

    near_term_weight = (N_t2 - N_30) / (N_t2 - N_t1)
    next_term_weight = (N_30 - N_t1) / (N_t2 - N_t1)
    return VIX,near_term_weight,next_term_weight


def vix_spot_main(neartermdate,nexttermdate,nearest_timestamp):
    # alldata = get_most_updated_data([neartermdate,nexttermdate],nearest_timestamp)
    alldata,und_price = get_spx_opt_data([neartermdate,nexttermdate], nearest_timestamp)
    if len(alldata)==0:
        print('No Data in ', nearest_timestamp)
        return pd.DataFrame({})
    # alldata = read_from_csv()
    data_time_range = list(alldata['C_TS']) + list(alldata['P_TS'])
    time_dic = pd.DataFrame({
        'end':[max(data_time_range)],
        'start':[min(data_time_range)]
    })

    # Step 1:
    # calculate forward index price
    near_term = alldata[alldata['C_symbol'].str.contains(neartermdate)]
    next_term = alldata[alldata['C_symbol'].str.contains(nexttermdate)]

    # get ATM option
    near_term_atm = find_out_atm_option(near_term)
    next_term_atm = find_out_atm_option(next_term)


    # get forward_index price
    f_1 = find_forward_index_p(near_term_atm,nearest_timestamp)
    f_2 = find_forward_index_p(next_term_atm,nearest_timestamp)
    # print(f_1,f_2)

    # get near term and next term's put call and k0
    near_term_out_of_money_put, near_term_out_of_money_call, near_term_k0, \
    next_term_out_of_money_put, next_term_out_of_money_call, next_term_k0 \
        = find_put_call_option(near_term,f_1,next_term,f_2)
    if len(near_term_out_of_money_call) == 0 or len(near_term_out_of_money_put) == 0\
            or len(next_term_out_of_money_call) == 0 or len(next_term_out_of_money_put) == 0: return pd.DataFrame({})
    skew_dic = pd.DataFrame({
    'nearTerm_skew' :[round(len(near_term_out_of_money_put)/len(near_term_out_of_money_call),3)],
    'nextTerm_skew' : [round(len(next_term_out_of_money_put)/len(next_term_out_of_money_call),3)],
    })
    # Step 2:
    # Calculate volatility for both near-term and next-term options
    # get near and next term T parameter for further calculation
    near_term_theta_square,T_1,near_term_mins_left = find_options_volatility(

        near_term_out_of_money_put,
        near_term_out_of_money_call,
        near_term_k0,
        f_1,
        nearest_timestamp
    )

    next_term_theta_square,T_2,next_term_mins_left = find_options_volatility(

        next_term_out_of_money_put,
        next_term_out_of_money_call,
        next_term_k0,
        f_2,
        nearest_timestamp
    )

    # Step 3:
    # Calculate the 30-day weighted average of near and next term theta, that square root of the value

    VIX,near_term_weight,next_term_weight = weighted_vix(near_term_theta_square, near_term_mins_left, T_1,
                       next_term_theta_square, next_term_mins_left, T_2
                       )
    weight_dic = pd.DataFrame({
        '_near_weight':[round(near_term_weight,3)],
        '_next_weight':[round(next_term_weight,3)]
    })
    return pd.concat([pd.DataFrame({'Price':[VIX]}),time_dic,weight_dic,skew_dic,pd.DataFrame({'UndPrice':[und_price]})],axis=1)


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


def main_single_day(expiration_t,nearest_timestamp):
    # alldata = get_most_updated_data([expiration_t],nearest_timestamp)
    alldata,und_price = get_spx_opt_data([expiration_t],nearest_timestamp)
    # if there is no data inside return empty pandas df
    if len(alldata) == 0: return pd.DataFrame({})
    alldata.to_csv('rrr.csv')
    # record time span for calculating the vix
    data_time_range = list(alldata['C_TS']) + list(alldata['P_TS'])
    time_dic = pd.DataFrame({
        'end': [max(data_time_range)],
        'start': [min(data_time_range)]
    })

    # Step 1:
    # calculate forward index price
    next_term = alldata[alldata['C_symbol'].str.contains(expiration_t)]
    # get ATM option
    next_term_atm = find_out_atm_option(next_term)

    # get forward_index price
    f_2 = find_forward_index_p(next_term_atm,nearest_timestamp)
    forward_strick = pd.DataFrame({'Forward Price: ':[f_2]})
    # get near term and next term's put call and k0
    # some times if there is no enough data, return empty DataFrame
    near_term_out_of_money_put, near_term_out_of_money_call, near_term_k0, \
    next_term_out_of_money_put, next_term_out_of_money_call, next_term_k0 \
        = find_put_call_option(next_term, f_2, next_term, f_2)
    if len(near_term_out_of_money_call) == 0 or len(near_term_out_of_money_put) == 0: return pd.DataFrame({})
    skew_dic = pd.DataFrame({ 'skewness': [round(len(near_term_out_of_money_put)/len(near_term_out_of_money_call),3)]})


    # Step 2:
    # Calculate volatility for both near-term and next-term options
    # get near and next term T parameter for further calculation

    next_term_theta_square, T_2, next_term_mins_left = find_options_volatility(

        next_term_out_of_money_put,
        next_term_out_of_money_call,
        next_term_k0,
        f_2,
        nearest_timestamp
    )

    # Step 3:
    # Calculate the 30-day VIX

    VIX = np.sqrt(next_term_theta_square) * 100
    VIX = pd.DataFrame({'Price':[VIX]})
    return pd.concat([VIX,time_dic,forward_strick,skew_dic,pd.DataFrame({'UndPrice':[und_price]})],axis=1)


def VIX_index(nearest_timestamp=datetime.today().strftime("%Y-%m-%d %T")):
    date_front, date_back = find_which_two_options(30,calculating=True,cur_date=nearest_timestamp)

    if date_back == None:
        date_front = date_front.strftime("%Y%m%d")[2:]
        # print('The option you looking:',date_front)
        return main_single_day(date_front,nearest_timestamp=nearest_timestamp)
    else:
        date_front = date_front.strftime("%Y%m%d")[2:]
        date_back = date_back.strftime("%Y%m%d")[2:]
        return vix_spot_main(date_front, date_back,nearest_timestamp=nearest_timestamp)


def VIX_future(which_term,nearest_timestamp=datetime.today().strftime("%Y-%m-%d %T")):
    date_,mature_date = find_month_option(which_term,True,cur_date=nearest_timestamp)
    date_ = date_[2:]
    # print('The option you looking:',date_)
    return pd.concat([main_single_day(date_,nearest_timestamp=nearest_timestamp),pd.DataFrame({'Future_expiration':[mature_date[2:]],
                                                                                               'OptionExpiration':[date_]})],axis=1)


if __name__=='__main__':
    # print(VIX_index('2016-01-22 13:10:00'))
    # spot = VIX_index('2017-06-05 12:00:00')
    # print(spot)
    # print(find_which_two_options(30))


    # spot = VIX_index('2016-01-05 12:00:00')
    # print(spot)
    # print(find_month_option(1,True,'2017-11-05 21:00:00'))
    vix_1 = VIX_future(3,'2017-07-20 13:00:00')
    # vix_2 = VIX_future(2, '2016-01-05 13:00:00')
    # vix_3 = VIX_future(3, '2016-01-05 13:00:00')
    print(vix_1)


    # zz = pd.concat([spot,vix_1], axis=0)
    # print(spot,vix_1)
    # vix_2 = VIX_future(2)
    # vix_3 = VIX_future(3)
    # zz = pd.concat([vix_1,vix_2,vix_3],axis=0)
    # print(zz)
    # print(find_which_two_options())