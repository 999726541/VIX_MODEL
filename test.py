from GetOptDataFromMysql import *

dd = get_vix_daliy_all()
dd['CD'] = dd['CD'].astype(int)
month_1 = []
month_2 = []
month_3 = []
month_4 = []
record_ts = []
VIX = []
for iidex, content in dd.groupby(['vix_date']):
    content = content.sort_values('CD')
    if iidex < '2010-01-01': continue
    try:
        month_1.append(content[0:1]['front_f_price'].item())
    except:
        month_1.append(-1)
    try:
        month_2.append(content[1:2]['front_f_price'].item())
    except:
        month_2.append(-1)
    try:
        month_3.append(content[2:3]['front_f_price'].item())
    except:
        month_3.append(-1)
    try:
        month_4.append(content[3:4]['front_f_price'].item())
    except:
        month_4.append(-1)
    record_ts.append(iidex)
    VIX.append(content[0:1]['vix_open'].item())
    zzz = pd.DataFrame({'1_month':month_1,'2_month':month_2,'3_month':month_3,'4_month':month_4,'record_ts':record_ts,'VIX':VIX})
    zzz.to_csv('VIX_termStructure.csv')