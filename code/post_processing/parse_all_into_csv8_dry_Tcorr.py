import pandas as pd
import re
import glob
import datetime as dt
import pprint
import json
import numpy as np
import sys
import os
from special_functions import dry_correction, calculate_xco2_from_data_pt_by_pt

def loadASVall_coeff(filename):
    coeff = []
    # apoff = []
    linenum = 0
    pattern_coeff = re.compile("COEFF")  
    with open(filename, 'rt') as myfile:
        for line in myfile:
            linenum += 1
            if pattern_coeff.search(line) != None:  # If a match is found
                coeff.append((linenum, line.rstrip('\n')))
    
    # No coeff found, insert NaN and Jan 1st in the year 1 A.D?
    if ( len(coeff) == 0 ):  
        coeff = [(0,'COEFF: 	CO2LastZero: 01 JAN 0001'),\
        (1,'COEFF: 	CO2kzero: NaN'),\
        (2,'COEFF: 	CO2LastSpan: 01 JAN 0001'),\
        (3,'COEFF: 	CO2LastSpan2: 01 JAN 0001'),\
        (4,'COEFF: 	CO2kspan: NaN'),\
        (5,'COEFF: 	CO2kspan2: NaN')]
    
    df = pd.DataFrame(coeff, columns=['Linenumber', 'Data'])
    df = df.Data.str.split(':', expand=True)
    df = df.drop(columns=[0]).rename(columns={1: "label", 2: "coeff"})

    mask1 = df['label'].str.contains("k")  
    df = df[mask1]  #take only lines with coefficients
    mask2 = df.index < 7  
    df = df[mask2]  #take first set of coefficients after span

    # Pascal, 8/19/2021, remove /t
    df['label'] = df['label'].str.strip()

    df = df.reset_index()

    return df

def loadASVall_coeff_with_dates(filename):
    coeff = []
    # apoff = []
    linenum = 0
    pattern_coeff = re.compile("COEFF")  
    with open(filename, 'rt') as myfile:
        for line in myfile:
            linenum += 1
            if pattern_coeff.search(line) != None:  # If a match is found
                coeff.append((linenum, line.rstrip('\n')))
    
    # No coeff found, insert NaN and Jan 1st in the year 1 A.D?
    if ( len(coeff) == 0 ):  
        coeff = [(0,'COEFF: 	CO2LastZero: 01 JAN 0001'),\
        (1,'COEFF: 	CO2kzero: NaN'),\
        (2,'COEFF: 	CO2LastSpan: 01 JAN 0001'),\
        (3,'COEFF: 	CO2LastSpan2: 01 JAN 0001'),\
        (4,'COEFF: 	CO2kspan: NaN'),\
        (5,'COEFF: 	CO2kspan2: NaN')]
    
    df = pd.DataFrame(coeff, columns=['Linenumber', 'Data'])
    df = df.Data.str.split(':', expand=True)
    df = df.drop(columns=[0]).rename(columns={1: "label", 2: "coeff"})

    mask1 = (df['label'].str.contains("CO2k")) | (df['label'].str.contains("CO2L")) 
    df = df[mask1]  #take only lines with coefficients
    mask2 = df.index < 7  
    df = df[mask2]  #take first set of coefficients after span

    # Pascal, 8/19/2021, remove /t
    df['label'] = df['label'].str.strip()

    df = df.reset_index()

    return df

def loadASVall_coeff_sync(filename):
    coeff = []
    # apoff = []
    linenum = 0
    pattern_coeff = re.compile("COEFF")  
    with open(filename, 'rt') as myfile:
        for line in myfile:
            linenum += 1
            if pattern_coeff.search(line) != None:  # If a match is found
                coeff.append((linenum, line.rstrip('\n')))
    
    # No coeff found, insert NaN and Jan 1st in the year 1 A.D?
    if ( len(coeff) == 0 ):  
        coeff = [(0,'COEFF: 	CO2LastZero: 01 JAN 0001'),\
        (1,'COEFF: 	CO2kzero: NaN'),\
        (2,'COEFF: 	CO2LastSpan: 01 JAN 0001'),\
        (3,'COEFF: 	CO2LastSpan2: 01 JAN 0001'),\
        (4,'COEFF: 	CO2kspan: NaN'),\
        (5,'COEFF: 	CO2kspan2: NaN')]
    
    df = pd.DataFrame(coeff, columns=['Linenumber', 'Data'])
    df = df.Data.str.split(':', expand=True)
    df = df.drop(columns=[0]).rename(columns={1: "label", 2: "coeff"})

    # df_str = df.copy()
    # f0 = (df['label'].str.contains('LastSpan')) | \
    #     (df['label'].str.contains('LastZero'))
    # df_str = df_str[f0]

    # df_str = df_str.reset_index()

    f1 = df['label'].str.contains("k")  
    df = df[f1]  #take only lines with coefficients
    f2 = df.index < 7  
    df = df[f2]  #take first set of coefficients after span

    # Pascal, 8/19/2021, remove /t
    df['label'] = df['label'].str.strip()

    df = df.reset_index()

    #### Move coefficient values into corresponding timestamps found in STATS ####
    #### Note that no special knowledge of when the coefficients were updated ####
    #### applies here, as the coefficients will go through all instrument states. #### 
    df_stats = loadASVall_stats(filename)
    #print(df_stats.columns.values)
    list_of_instrument_states = ['ZPON','ZPOFF','ZPPCAL','SPON','SPOFF',\
        'SPPCAL','EPON','EPOFF','APON','APOFF']
    list_of_ts = []
    for state_name in list_of_instrument_states:
        mask_state = df_stats['State'].str.contains(state_name)
        #ts_state = df_stats[mask_state].iloc[0,df_stats.columns.get_loc('Timestamp')]
        ts_state = df_stats.loc[mask_state,'Timestamp'].to_list()[0]
        list_of_ts.append(ts_state)

    df_coeff_sync = pd.DataFrame({'Timestamp':list_of_ts,\
        'mode':list_of_instrument_states})

    # add in coefficients to df_coeff_sync
    for idx, row in df.iterrows():
        duplicates=[float(row['coeff'])]*len(list_of_instrument_states)
        df_coeff_sync[row['label']]=duplicates

    # add in coefficients to df_coeff_sync
    # for idx, row in df_str.iterrows():
    #     duplicates=[row['coeff']]*len(list_of_instrument_states)
    #     df_coeff_sync[row['label'].strip()]=duplicates

    return df_coeff_sync

def loadASVall_stats(filename):
    stats = []
    pattern_stats = re.compile("STATS")  
    with open(filename, 'rt') as myfile:
        linenum = 0
        lines = myfile.readlines()
        first_header_entered=False
        for idx, line in enumerate(lines):  # start from reverse
            if pattern_stats.search(line) != None:  # If a match is found
                line=line.rstrip('\n')  ### add in another strip or replace here, found whitespace
                right_of_STATS=re.split(r'STATS:',line)[1]
                letter_score = sum([c.isalpha() for c in right_of_STATS]) \
                    /len(right_of_STATS)
                header_detected = letter_score > 0.5
                if ( (not header_detected) and \
                    (first_header_entered) ):
                    stats.append((idx,right_of_STATS))
                elif ( (not first_header_entered) and \
                    header_detected and \
                    re.search(r'(\w+,)+',right_of_STATS) ): #'State' in right_of_STATS ):
                    first_part_of_header = right_of_STATS.replace(' ','')
                    # This is most likely unnecessary, initially thought that
                    # header will extend onto two lines, but this is just notepad wrapping
                    # letter_score_2nd_line = sum([c.isalpha() for c in lines[idx+1]]) \
                    #     /len(lines[idx+1])
                    # if ( letter_score_2nd_line > 0.5 and \
                    #     re.search(r'(\w+,)+',line[idx+1]) ):
                    #     second_part_of_header = lines[idx+1].replace(' ','').rstrip('\n')
                    # else:
                    #     second_part_of_header = ''
                    # stats_header = first_part_of_header + second_part_of_header
                    stats_header = first_part_of_header
                    stats.append((idx,stats_header))
                    first_header_entered=True

    # No dry data found, insert NaN and Jan 1st in the year 1 A.D?
    if ( len(stats) == 0 ):
       stats = [(0,'State,SN,Timestamp,Li_Temp_ave(C),Li_Temp_sd,Li_Pres_ave(kPa),' + \
        'Li_Pres_sd,CO2_ave(PPM),CO2_SD,O2_ave(%),O2_S,RH_ave(%),RH_sd,RH_T_ave(C),Rh_T_sd,' + \
        'Li_RawSample_ave,Li_RawSample_sd,Li_RawDetector_ave,Li_RawReference_sd'),\
            (1,'XXXX,XXXXXXXXX, 0001-01-01T00:00:00Z,NaN,NaN,NaN,NaN,NaN,' + \
                'NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN')]*10


    df = pd.DataFrame(stats, columns=['Linenumber', 'Data'])
    df = df.Data.str.split(',', expand=True)
    #df = df.drop(columns=[0])
    col_names = df.iloc[0,:].to_list()  # extract column names from first row
    #print(col_names)
    #rename dataframe column names to first row
    rename_dict = {}
    for idx, name in enumerate(col_names):
        rename_dict[idx] = name
    df = df.rename(columns=rename_dict)  # rename columns
    # delete alternating rows starting with 1st row with column names,
    # only retain the even 2nd, 4th, 6th, etc. rows with the actual numbers
    # even = list(range(0,20,2))  # 0 index is 1st row, so actually drop even indexed rows
    # df = df.drop(labels=even,axis=0)  
    
    df = df.reset_index()
    df = df.drop(columns=['index'])  # silly pandas artifact, a new column named index appears

    # delete 1st row with column names, only retain the 2nd row with actual numbers
    df = df.drop(labels=0,axis=0)  

    #### Add in the number of samples per State like 'APON','APOFF',etc. ####
    data_df = loadASVall_data(filename)
    slice = data_df[['State','CO2(ppm)']]
    counts_per_state = slice.groupby('State').count()#.agg(['mean','std','count'])
    df_num_samples = pd.DataFrame({'State':counts_per_state.index,\
        'Num_samples':counts_per_state['CO2(ppm)'].to_list()})
    df = df.merge(df_num_samples, left_on='State',right_on='State',\
            how='left',suffixes=('','_data'))
    # pd.set_option('max_columns',None)
    # print('#### check each mode statistics ####')
    # print(check)
    # pd.reset_option('max_columns')

    #### Add in dry correction ####
    # if ( dry ):
    #     dry_correction(xCO2_wet,RH_T,Pressure,RH_sample,RH_span)
    # else:
    #     pass

    # change data types from string to float or int
    #print(f'df stats column names = {df.columns.values}')
    dtype_dict = {'Li_Temp_ave(C)':'float64','Li_Temp_sd':'float64',\
        'Li_Pres_ave(kPa)':'float64','Li_Pres_sd':'float64',\
        'CO2_ave(PPM)':'float64','CO2_SD':'float64',\
        'O2_ave(%)':'float64','O2_S':'float64','RH_ave(%)':'float64',\
        'RH_sd':'float64','RH_T_ave(C)':'float64','Rh_T_sd':'float64',\
        'Li_RawSample_ave':'int64','Li_RawSample_sd':'int64',\
        'Li_RawDetector_ave':'int64','Li_RawReference_sd':'int64'}
    df = df.astype(dtype_dict)

    return df

def loadASVall_dry(filename):
    dry = []
    pattern_dry = re.compile("DRY")  
    with open(filename, 'rt') as myfile:
        lines = myfile.readlines()
        numlines = len(lines)
        linenum = numlines
        for idx in range(numlines-1,-1,-1):  # start from reverse
            line = lines[idx]
            linenum -= 1
            if pattern_dry.search(line) != None:  # If a match is found
                right_of_DRY = re.split(r'DRY:',line)[1]
                dry.append((linenum, right_of_DRY.replace(' ','').rstrip('\n')))
            if len(dry) >= 2:
                break  # all done, only expecting 2 lines here
    dry.reverse()

    # No dry data found, insert NaN and Jan 1st in the year 1 A.D?
    if ( len(dry) == 0 ):
       dry = [(0,'TS, SW_xCO2(dry), Atm_xCO2(dry)'),\
            (1,' 0001-01-01T00:00:00Z,NaN,NaN')]
    
    #print(dry)
    df = pd.DataFrame(dry, columns=['Linenumber', 'Data'])
    df = df.Data.str.split(',', expand=True)
    #df = df.drop(columns=[0])
    col_names = df.iloc[0,:].to_list()  # extract column names from first row
    #print(f"dry df col names = {col_names}")
    #rename dataframe column names to first row
    rename_dict = {}
    for idx, name in enumerate(col_names):
        rename_dict[idx] = name
    df = df.rename(columns=rename_dict)  # rename columns
    # delete 1st row with column names, only retain the 2nd row with actual numbers
    df = df.drop(labels=0,axis=0)  
    
    df = df.reset_index()
    df = df.drop(columns=['index'])  # silly pandas artifact, a new column named index appears

    #### move dry xCO2 values into corresponding timestamps found in STATS ####
    df_stats = loadASVall_stats(filename)
    #print(df_stats.columns.values)
    mask_apoff = df_stats['State'].str.contains('APOFF')
    #ts_apoff = df_stats['Timestamp'].loc[mask_apoff]
    ts_apoff = df_stats[mask_apoff].iloc[0,df_stats.columns.get_loc('Timestamp')]
    #print(f'ts_apoff = {ts_apoff}')
    mask_epoff = df_stats['State'].str.contains('EPOFF')
    #ts_epoff = df_stats['Timestamp'].loc[mask_epoff]
    ts_epoff = df_stats[mask_epoff].iloc[0,df_stats.columns.get_loc('Timestamp')]
    #print(f'ts_epoff = {ts_epoff}')
    #print(df)

    # pd.set_option('max_columns',None)
    # print('##### Df Stats #####')
    # print(df_stats)
    # pd.reset_option('max_columns')

    df_dry_sync = pd.DataFrame({'TS':[ts_epoff,ts_apoff],\
        'mode':['EPOFF','APOFF'],\
        'xCO2(dry)':[df.loc[0,'SW_xCO2(dry)'],df.loc[0,'Atm_xCO2(dry)']]})

    #print(df_dry_sync)
    df_dry_sync['xCO2(dry)'] = df_dry_sync['xCO2(dry)'].astype(float)

    return df_dry_sync, df

def loadASVall_flags(filename):
    sub_flags = []
    pattern_flags = re.compile("FLAGS")  
    with open(filename, 'rt') as myfile:
        lines = myfile.readlines()
        flags_found = False
        for line in reversed(lines):
            if pattern_flags.search(line) != None:  # If a match is found
                flags_found = True
                each4=re.findall(r'(\d{4})',line.rstrip('\n'))
                # all4 = '0x' + ''.join(each4)
                sub_flags=re.split(r' ',line.rstrip('\n'))
                break
    
    list_of_flag_names = ['ASVCO2_GENERAL_ERROR_FLAGS', 'ASVCO2_ZERO_ERROR_FLAGS',
    'ASVCO2_SPAN_ERROR_FLAGS', 'ASVCO2_SECONDARYSPAN_ERROR_FLAGS',
    'ASVCO2_EQUILIBRATEANDAIR_ERROR_FLAGS', 'ASVCO2_RTC_ERROR_FLAGS',
    'ASVCO2_FLOWCONTROLLER_FLAGS', 'ASVCO2_LICOR_FLAGS']

    df = pd.DataFrame(columns=list_of_flag_names)

    
    if ( flags_found and len(each4) == 8 ):  
        # No FLAGS: entry found, use 0x10000 (decimal 65536) > 0xffff (decimal 65535)
        for idx in range(0,len(list_of_flag_names)):
            df[list_of_flag_names[idx]]=[int(each4[idx],16)]
    # No FLAGS: text found in the file, default to 0x10000, which is greater than 0xffff
    else:
        # No FLAGS: entry found, use 0x10000 (decimal 65536) > 0xffff (decimal 65535)  
        for idx in range(0,len(list_of_flag_names)):
            df[list_of_flag_names[idx]]=[16**4]

    df = df.reset_index()  # should be unnecessary, but use anyway

    return df

def add_ts_to_flags(df_flags,df_stats):
    # copy and drop index from df_flags
    df_flags_local = df_flags.copy()
    df_flags_local = df_flags_local.drop(columns=['index'])

    # use local copy of df_stats and drop everything except timestamps
    df_stats_local = df_stats.copy()
    cols = df_stats_local.columns.to_list()
    everything_except_timestamp_and_state = [col for col in cols \
        if 'Timestamp' not in col and 'State' not in col]
    df_stats_local = df_stats_local.drop(columns=everything_except_timestamp_and_state)
    
    # create new df_ts_flags with timestamps
    df_flags_cols = df_flags_local.columns.to_list()
    new_cols = ['Timestamp'] + df_flags_cols
    df_ts_flags = pd.DataFrame(columns=new_cols)
    df_ts_flags['Timestamp']=df_stats_local['Timestamp']
    for col in df_flags_cols:
        df_ts_flags[col] = df_flags_local[col].loc[0]*len(df_stats_local)
    
    return df_ts_flags

##### No longer filters by modename, timestamp "TS" unchanged now #####
def loadASVall_data(filename):
    data = []
    linenum = 0
    pattern_data = re.compile("DATA")
    with open(filename, 'rt') as myfile:
        first_header_entered=False
        for line in myfile:
            linenum += 1
            if pattern_data.search(line) != None:  # If a match is found
                line=line.rstrip('\n')  ### add in another strip or replace here, found whitespace
                right_of_DATA=re.split(r'DATA:',line)[1]
                letter_score = sum([c.isalpha() for c in right_of_DATA]) \
                    /len(right_of_DATA)
                header_detected = letter_score > 0.5
                # if ( not first_header_detected and header_detected ):
                #     first_header_detected = True
                if ( (not header_detected) or \
                    (not first_header_entered) ):
                    data.append((linenum,right_of_DATA))
                    first_header_entered=True

                #data.append((linenum, right_of_DATA))
    df = pd.DataFrame(data, columns=['Linenumber', 'Data'])

    #df = df.Data.str.split(':|,', expand=True)
    df = df.Data.str.split(',', expand=True)


    df = df.rename(columns={0: "State", 1: "TS", 2: "SN", 3: "CO2(ppm)",\
        4: "Li_Temp(C)", 5: "Li_Pres(kPa)", 6: "Li_RawSample", \
        7: "Li_RawReference", 8: "RH(%)",9: "RH_T(C)", 10: "O2(%)"})
    df = df.drop(index=[0])  # drop redundant first row

    #df = df.drop(columns=['None'])  # drop no-name "DATA" column

    # df = df.drop(columns=[0]).rename(
    #     columns={1: "Mode", 2: "Date", 3: "Minute", 4: "Seconds", 5: "SN", 6: "CO2", 7: "Temp", 8: "Pres", 9: "Li_Raw",
    #              10: "Li_ref", 11: "RHperc", 12: "RH_T", 13: "O2perc"})

    # mask = df['Mode'].str.contains(modename)  
    # df = df[mask]

    return df

def parse_all_file_into_df(filename):
    #filename = './data/1006/20210430/ALL/20210429_183017.txt'
    linenum = 0
    with open(filename, 'rt') as myfile:
        sys_rep={}
        for line in myfile:
            linenum += 1
            if '=' in line:  # equals sign found and system report likely
                line = line.rstrip('\n')
                line = line.strip()
                lhs_and_rhs = re.split(r'=',line)
                sys_rep[lhs_and_rhs[0]]=lhs_and_rhs[1]
            if 'LOG:' in line:
                break
    # print('This is the system report...')
    # print(sys_rep)
    
    maybe_missing = {'secondaryspan_calibrated_temperature': np.NaN,
    'secondaryspan_calibrated_spanconcentration': np.NaN,
    'last_secondaryspan_temperaturedependantslope': '0001-01-01T00:00:00Z',
    'secondaryspan_temperaturedependantslope':np.NaN,
    'secondaryspan_temperaturedependantslopefit':np.NaN,
    'secondaryspan_calibrated_rh':np.NaN,
    'ASVCO2_secondaryspan2_concentration': np.NaN,
    'last_ASVCO2_validation': '0001-01-01T00:00:00Z',
    'pressure_bias': np.NaN,
    'last_pressure_bias_measured' : '0001-01-01T00:00:00Z',
    'ASVCO2_ATRH_serial': 'XXXXXXXXX',
    'ASVCO2_O2_serial': 'XXXX',
    'ASVCO2_manufacturer': 'XXXX',
    'secondaryspan_calibrated_spanserialnumber':'XXXXXXXX',
    'ASVCO2_secondaryspan_serialnumber':'XXXXXXXX',
    'ASVCO2_span_serialnumber':'XXXXXXXX',
    'last_secondaryspan_calibration':'0000-01-01T00:00:00Z'}

    for k,v in maybe_missing.items():
        if (k not in sys_rep):
            sys_rep[k]=v

    coeff_df = loadASVall_coeff(filename)
    data_df = loadASVall_data(filename)

    pd.set_option('max_columns',None)
    # print(coeff_df.describe(include='all'))
    # print(coeff_df.head())
    # print(data_df.describe(include='all'))
    # print(data_df.head())
    

    # add in extra columns to data_df from system report, sys_rep
    big_df = data_df.copy()
    num_rows=len(big_df)
    for k,v in sys_rep.items():
        duplicates=[v]*num_rows
        big_df[k]=duplicates
    for index, row in coeff_df.iterrows():
        #print(row['coeff'],row['label'])
        #print(f'row of coeff = {row[/'coeff']}, row of label = {row['label']}')
        duplicates=[row['coeff']]*num_rows
        big_df[row['label']]=duplicates

    #Pascal, 8/13/2021, choose which gas list to use based upon time string from filename,
    #will need to update this to a more fully featured lookup later
    time_str=re.search(r'\d{8}_\d{6}\.txt',filename)[0]  #grab 8 digits, underscore and 6 digits
    year_month_day_str = re.split(r'_',time_str)[0]
    num_yr_mo_dd = float(year_month_day_str)
    if ( (20210801 - num_yr_mo_dd) > 0 ):  # if it preceded Aug 1 2021, then used older gaslists
        if ((20210427 - num_yr_mo_dd) > 0):
            gaslist=[0, 104.25, 349.79, 552.9, 732.64, 999.51, 1487.06, 1994.25] #552.9 before 4/27
        else:
            gaslist=[0, 104.25, 349.79, 506.16, 732.64, 999.51, 1487.06, 1994.25]
    else:  # use newer gaslist if after Aug 1 2021
        gaslist=[0, 104.25, 349.79, 494.72, 732.64, 999.51, 1487.06, 1961.39] #update in early Aug 2021
    
    #add column for standard gas
    mask_EPOFF = data_df['State'].str.contains('EPOFF')
    df_epoff = data_df[mask_EPOFF]
    #print(f'len(df_epoff) = {len(df_epoff)}')
    mins=[]
    for index, row in df_epoff.iterrows():
        for gas in gaslist:
            #print(row['CO2(ppm)'])
            minimum=abs(float(row['CO2(ppm)'])-gas)
            #print(f'minimum = {minimum}')
            if minimum<50:
                #df_epoff['gas_standard'][i]=gas
                mins.append(gas)
    
    closest_gas_standards = pd.Series(data=mins,dtype='float64')
    most_likely_gas_standard = closest_gas_standards.median()
    # print(closest_gas_standards.values)
    big_df['gas_standard']=[most_likely_gas_standard]*num_rows

    # print('big_df is like...')
    # print(big_df.describe(include='all'))
    # print(big_df.head())
    # print('END big_df')
    pd.reset_option('max_columns')

    return big_df

def all_df_make_temp_and_dry_correction(data_df,coeff_df,sys_rep):
    # State,SN,Timestamp,Li_Temp_ave(C),Li_Temp_sd,Li_Pres_ave(kPa),' + \
    #'Li_Pres_sd,CO2_ave(PPM),CO2_SD,O2_ave(%),O2_S,RH_ave(%),RH_sd,RH_T_ave(C),Rh_T_sd,' + \
    #'Li_RawSample_ave,Li_RawSample_sd,Li_RawDetector_ave,Li_RawReference_sd
    # print('hello, inside val_df_make_temp_and_dry_correction()...')
    # pd.set_option('max_columns',None)
    # print('big_stats_df first five rows...')
    # print(data_df.head())
    # print('big_stats_df described...')
    # print(data_df.describe(include='all'))
    # pd.reset_option('max_columns')
    temp_data = pd.DataFrame()
    filt_ref = (data_df['State'].str.contains("APOFF")) | \
        (data_df['State'].str.contains("EPOFF"))
    temp_data = data_df[filt_ref].copy()
    temp_data['CO2_dry_Tcorr'] = [np.NaN]*len(temp_data)
    temp_data['CO2_dry'] = [np.NaN]*len(temp_data)
    # zerocoeff = super_big_val_df[mask_ref].loc[:,'CO2kzero']
    # S0 = super_big_val_df[mask_ref].loc[:,'CO2kspan']
    # S1 = super_big_val_df[mask_ref].loc[:,'CO2kspan2']
    # pd.set_option('max_columns',None)
    # print('temp data first five rows...')
    # print(temp_data.head())
    # print('temp data described...')
    # print(temp_data.describe(include='all'))
    # pd.reset_option('max_columns')
    #CO2kzero_col_num = temp_data.columns.get_loc('CO2kzero')
    #print(f'CO2kzero_col_num = {CO2kzero_col_num}')
    # pd.set_option('max_columns',None)
    # print('coeff_df is...')
    # print(coeff_df)
    # pd.reset_option('max_columns')
    
    SPOFF_filt = data_df['State'].str.contains("SPOFF")
    RH_span_ave = data_df[SPOFF_filt].loc[:,'RH(%)'].astype(float).mean()
    span1_avgT = data_df[SPOFF_filt].loc[:,'Li_Temp(C)'].astype(float).mean()
    w_mean = data_df[SPOFF_filt].loc[:,'Li_RawSample'].astype(float).mean()
    w0_mean = data_df[SPOFF_filt].loc[:,'Li_RawReference'].astype(float).mean()
    p1_mean = data_df[SPOFF_filt].loc[:,'Li_Pres(kPa)'].astype(float).mean()  # not used currently
    T_mean = data_df[SPOFF_filt].loc[:,'Li_Temp(C)'].astype(float).mean()  # not used currently

    S_0 = coeff_df['coeff'].loc[coeff_df['label']=='CO2kspan'].astype(float).iloc[0]
    S_1 = coeff_df['coeff'].loc[coeff_df['label']=='CO2kspan2'].astype(float).iloc[0]
    zerocoeff = coeff_df['coeff'].loc[coeff_df['label']=='CO2kzero'].astype(float).iloc[0]

    span2_in = float(sys_rep['secondaryspan_calibrated_temperature'])
    slope_in = float(sys_rep['secondaryspan_temperaturedependantslope'])

    alphaC = (1 - ((w_mean / w0_mean) * zerocoeff))
    BetaC = alphaC * (S_0 + S_1 * alphaC)
    #span2_in = row['Temp']
    #difference in temp from span2 at 20C and span1 temp
    span2_cal2_temp_diff = span1_avgT - span2_in  #old comment: was this number supposed to be negative?
    S1_tcorr = (S_1 + slope_in * span2_cal2_temp_diff)#.astype(float)

    # Algebraic manipulation from LiCor Appendix A, eq. A-28
    # note that overbar symbol on alphaC symbol in the LiCor 830/850 manual indicates a 5 second average value
    S0_tcorr = (BetaC / alphaC) - (S1_tcorr * alphaC)

    #print(f'zeroc = {zerocoeff}, S0_tcorr = {S0_tcorr}, S1_tcorr = {S1_tcorr}, S_0 = {S_0}, S_1 = {S_1}')

    #rename for compatibility with calculate_xco2_from_data_pt_by_pt()
    rename_dict = {'State':'Mode','CO2(ppm)':'CO2','Li_Temp(C)':'Temp',\
        'Li_Pres(kPa)':'Pres','Li_RawSample':'Li_Raw','Li_RawReference':'Li_ref',\
         'RH(%)':'RHperc','RH_T(C)':'RH_T','O2(%)': 'O2perc'}
    temp_data = temp_data.rename(columns=rename_dict)

    temp_data = temp_data.reset_index()
    temp_data = temp_data.drop(columns=['index'])  # correction for silly artifact of reset_index() 

    # print('#### temp_data before for loop ####')
    # pd.set_option('max_columns',None)
    # print(temp_data)
    # pd.reset_option('max_columns')
    # print(temp_data.index.values)

    for idx, row in temp_data.iterrows():
        #print('loop ' + str(idx))
        #print(row.dtypes)
        #print(row)
        xCO2_tcorr = calculate_xco2_from_data_pt_by_pt(row,\
            zerocoeff, S0_tcorr, S1_tcorr, scalar=True)
        #print(f'xCO2_tcorr = {xCO2_tcorr}')
        temp_data.loc[idx,'CO2_dry_Tcorr'] = dry_correction(xCO2_tcorr,\
            float(row['RH_T']),float(row['Pres']),float(row['RHperc']),RH_span_ave)

        temp_data.loc[idx,'CO2_dry'] = dry_correction(float(row['CO2']),\
            float(row['RH_T']),float(row['Pres']),float(row['RHperc']),RH_span_ave)
        
    #### Merge in the num samples data from the stats dataframe ####
    data_df = data_df.merge(temp_data[\
        ['TS','CO2_dry_Tcorr','CO2_dry']],left_on='TS',\
        right_on='TS',how='left',suffixes=('','_dtc'))

    del temp_data

    # print('#### After merge inside val_df_make_temp_and_dry correction #####')
    # print(f'data_df.columns.values = {data_df.columns.values}')

    return data_df

def all_df_make_dry_residual_columns(big_df,most_probable_span_gas):
    big_df['residual'] = [np.NaN]*len(big_df)
    big_df['residual_dry_Tcorr'] = [np.NaN]*len(big_df)  # new
    big_df['residual_dry'] = [np.NaN]*len(big_df)  # new
    #super_big_val_df['residual_dry'] = [np.NaN]*len(super_big_val_df)  # new
    
    # idx_of_most_probable_span_gas = abs(big_df['gas_standard']-500).sort_values().index[0]
    # most_probable_span_gas = big_df['gas_standard'].iloc[idx_of_most_probable_span_gas]
    # print(f'most_probable_span_gas = {most_probable_span_gas}')
    temp = pd.DataFrame()
    filt_zero = (big_df['State'].str.contains("ZPOFF")) \
        | (big_df['State'].str.contains("ZPON")) \
        | (big_df['State'].str.contains("ZPPCAL")) 
    temp['residual'] = big_df[filt_zero].loc[:,'CO2(ppm)'].astype(float)

    # identity of probability theory, see Sheldon Ross, p. 143
    # temp['residual']=big_df[filt_zero].loc[:,'CO2(ppm)']   
    big_df.update(temp)

    # print('temp is like',temp.head())
    # print('super_big_val_df is like',super_big_val_df['residual'].head())
    del temp

    temp = pd.DataFrame()
    filt_span = (big_df['State'].str.contains("SPOFF")) \
        | (big_df['State'].str.contains("SPON")) \
        | (big_df['State'].str.contains("SPPCAL"))
    temp['residual'] = big_df[filt_span].loc[:,'CO2(ppm)'].astype(float) - most_probable_span_gas
    
    # identity of probability theory, see Sheldon Ross, p. 143
    # temp['residual']=big_df[filt_span].loc[:,'CO2']   
    big_df.update(temp)
    
    temp = pd.DataFrame()
    filt_ref = (big_df['State'].str.contains("EPON")) \
        | (big_df['State'].str.contains("APON")) \
        | (big_df['State'].str.contains("EPOFF")) \
        | (big_df['State'].str.contains("APOFF"))
    temp['residual'] = big_df[filt_ref].loc[:,'CO2(ppm)'].astype(float) -\
        big_df[filt_ref].loc[:,'gas_standard']

    # identity of probability theory, see Sheldon Ross, p. 143
    #temp['residual']=big_df[filt_ref].loc[:,'CO2']
    big_df.update(temp)
    # print('temp is like',temp.head())
    # print('super_big_val_df is like',super_big_val_df['residual'].head())
    del temp

    temp = pd.DataFrame()
    filt_ref = (big_df['State'].str.contains("APOFF")) \
        | (big_df['State'].str.contains("EPOFF"))
    temp['residual_dry'] = big_df[filt_ref].loc[:,'CO2_dry'] -\
        big_df[filt_ref].loc[:,'gas_standard']
    # approximation dry CO2 standard deviation for now, 
    # would need to calculate from 2Hz data to actually calculate temperature
    # corrected standard deviation.
    #temp['residual_dry_sd'] = super_big_val_df[filt_ref].loc[:,'CO2_sd']
    big_df.update(temp)
    # print('temp is like',temp.head())
    # print('super_big_val_df is like',super_big_val_df['residual'].head())
    del temp

    # New
    temp = pd.DataFrame()
    filt_ref = (big_df['State'].str.contains("APOFF")) \
        | (big_df['State'].str.contains("EPOFF"))
    temp['residual_dry_Tcorr'] = big_df[filt_ref].loc[:,'CO2_dry_Tcorr'] -\
        big_df[filt_ref].loc[:,'gas_standard']
    # approximation temperature corrected standard deviation for now, 
    # would need to calculate from 2Hz data to actually calculate temperature
    # corrected standard deviation.
    # temp['residual_Tcorr'] = big_df[filt_ref].loc[:,'CO2']  
    
    big_df.update(temp)

    # CO2_dry_Tcorr_stuff = big_df[filt_ref].loc[:,'CO2_dry_Tcorr']
    # print('CO2_dry_Tcorr is like...',CO2_dry_Tcorr_stuff.describe())
    # print('calculated temp and dry corrected residuals',temp['residual_dry_Tcorr'].describe())
    # print('super_big_val_df is like',super_big_val_df['residual_ave'].head())
    del temp

    #super_big_val_df['residual_sd']=super_big_val_df['CO2_sd']  # identity of probability theory, see Sheldon Ross, p. 143 

    return big_df

def parse_all_file_df_w_summary(filename):
    #filename = './data/1006/20210430/ALL/20210429_183017.txt'
    linenum = 0
    with open(filename, 'rt') as myfile:
        sys_rep={}
        for line in myfile:
            linenum += 1
            if '=' in line:  # equals sign found and system report likely
                line = line.rstrip('\n')
                line = line.strip()
                lhs_and_rhs = re.split(r'=',line)
                sys_rep[lhs_and_rhs[0].strip()]=lhs_and_rhs[1]
            if 'LOG:' in line:
                break
    #print(sys_rep)
    
    maybe_missing = {'secondaryspan_calibrated_temperature': np.NaN,
    'secondaryspan_calibrated_spanconcentration': np.NaN,
    'last_secondaryspan_temperaturedependantslope': '0001-01-01T00:00:00Z',
    'secondaryspan_temperaturedependantslope':np.NaN,
    'secondaryspan_temperaturedependantslopefit':np.NaN,
    'secondaryspan_calibrated_rh':np.NaN,
    'ASVCO2_secondaryspan2_concentration': np.NaN,
    'last_ASVCO2_validation': '0001-01-01T00:00:00Z',
    'pressure_bias': np.NaN,
    'last_pressure_bias_measured' : '0001-01-01T00:00:00Z',
    'ASVCO2_ATRH_serial': 'XXXXXXXXX',
    'ASVCO2_O2_serial': 'XXXX',
    'ASVCO2_manufacturer': 'XXXX',
    'secondaryspan_calibrated_spanserialnumber':'XXXXXXXX',
    'ASVCO2_secondaryspan_serialnumber':'XXXXXXXX',
    'ASVCO2_span_serialnumber':'XXXXXXXX',
    'last_secondaryspan_calibration':'0000-01-01T00:00:00Z'}

    for k,v in maybe_missing.items():
        if (k not in sys_rep):
            sys_rep[k]=v

    coeff_df = loadASVall_coeff(filename)
    flags_df = loadASVall_flags(filename)
    data_df = loadASVall_data(filename)
    dry_df = loadASVall_dry(filename)  # new stuff

    data_df = all_df_make_temp_and_dry_correction(data_df,coeff_df,sys_rep)

    # pd.set_option('max_columns',None)
    # print(coeff_df.describe(include='all'))
    # print(coeff_df.head())
    # print(data_df.describe(include='all'))
    # print(data_df.head())
    

    # add in extra columns to data_df from system report, sys_rep
    big_df = data_df.copy()
    num_rows=len(big_df)
    for k,v in sys_rep.items():
        #duplicates=[v]*num_rows
        #big_df[k]=duplicates
        big_df[k]=""
    for index, row in coeff_df.iterrows():
        #print(row['coeff'],row['label'])
        #print(f'row of coeff = {row[/'coeff']}, row of label = {row['label']}')
        #duplicates=[row['coeff']]*num_rows
        big_df[row['label']]=""

    #Pascal, 8/13/2021, choose which gas list to use based upon time string from filename,
    #will need to update this to a more fully featured lookup later
    time_str=re.search(r'\d{8}_\d{6}\.txt',filename)[0]  #grab 8 digits, underscore and 6 digits
    year_month_day_str = re.split(r'_',time_str)[0]
    num_yr_mo_dd = float(year_month_day_str)
    if ( (20210801 - num_yr_mo_dd) > 0 ):  # if it preceded Aug 1 2021, then used older gaslists
        if ((20210420 - num_yr_mo_dd) > 0):
            gaslist=[0, 104.25, 349.79, 552.9, 732.64, 999.51, 1487.06, 1994.25] #552.9 before 4/27
        else:
            gaslist=[0, 104.25, 349.79, 506.16, 732.64, 999.51, 1487.06, 1994.25]
    else:  # use newer gaslist if after Aug 1 2021
        gaslist=[0, 104.25, 349.79, 494.72, 732.64, 999.51, 1487.06, 1961.39] #update in early Aug 2021
    
    #add column for standard gas
    mask_EPOFF = data_df['State'].str.contains('EPOFF')
    df_epoff = data_df[mask_EPOFF]
    #print(f'len(df_epoff) = {len(df_epoff)}')
    mins=[]
    for index, row in df_epoff.iterrows():
        for gas in gaslist:
            #print(row['CO2(ppm)'])
            minimum=abs(float(row['CO2(ppm)'])-gas)
            #print(f'minimum = {minimum}')
            if minimum<50:
                #df_epoff['gas_standard'][i]=gas
                mins.append(gas)
    
    closest_gas_standards = pd.Series(data=mins,dtype='float64')
    most_likely_gas_standard = closest_gas_standards.median()
    # print(closest_gas_standards.values)
    big_df['gas_standard']=[most_likely_gas_standard]*num_rows

    #### Check for number of samples per state ####
    # slice = big_df[['TS','State','CO2(ppm)']]
    # check = slice.groupby('State').count()#.agg(['mean','std','count'])
    # pd.set_option('max_columns',None)
    # print('#### check each mode statistics ####')
    # print(check)
    # pd.reset_option('max_columns')

    ### New stuff, figure out most probable span gas ###
    min=max(gaslist)
    for gas in gaslist:
        diff=abs(gas-500)
        if diff < min:
            most_probable_span_gas = gas
            min = diff

    #### New stuff, create residual columns ####
    big_df = all_df_make_dry_residual_columns(big_df,most_probable_span_gas)

    #construct final row, which is summary data into big_df
    final_row = pd.DataFrame()
    for col_name in data_df.columns.values:
        if ( col_name == 'State'):
            final_row[col_name]=['Summary']
        else:
            final_row[col_name]=""
    for k,v in sys_rep.items():
        final_row[k]=v
    for index, row in coeff_df.iterrows():
        final_row[row['label']]=row['coeff']
    for col_name in flags_df.columns.values:  # NEW, 9/7/2021
        if (col_name != 'index'):
            final_row[col_name]=flags_df[col_name]  # NEW, 9/7/2021

    #special manipulations to move between raw data and sample data    
    final_ts_str = big_df['TS'].iloc[-1]
    final_ts_str = final_ts_str.strip()
    last_whole_sec_idx = re.search(r'\.\d',final_ts_str).span()[0]
    floored_final_ts_str = final_ts_str[:last_whole_sec_idx] + 'Z'
    final_ts_plus_1sec = dt.datetime.strptime(floored_final_ts_str, '%Y-%m-%dT%H:%M:%SZ') + \
        dt.timedelta(0,1)
    final_row['TS']=final_ts_plus_1sec.strftime(' %Y-%m-%dT%H:%M:%S') + '.0Z'
    final_row['SN']=big_df['SN'].iloc[-1]
    final_row['gas_standard']=big_df['gas_standard'].iloc[-1]

    big_df['last_ASVCO2_validation'] = [final_row['last_ASVCO2_validation'].iloc[-1]]*num_rows

    #### special additional items for final row (summary data) ####
    final_row['CO2DETECTOR_vendor_name']=['LI-COR Biosciences']
    final_row['CO2DETECTOR_model_name']=['LI-830']

    #print(f'before adding last row, len(big_df) = {len(big_df)}')
    #print(f'len(final_row) = {len(final_row)}')
    big_df = pd.concat([big_df,final_row], axis=0, ignore_index=True)
    #print(f'after adding last row, len(big_df) = {len(big_df)}')

    # print('big_df is like...')
    # print(big_df.describe(include='all'))
    # print(big_df.head())
    # print('END big_df')

    big_df = big_df.drop(columns=['serial','time','gps'])

    #### Reorder columns ####
    list_of_column_names = big_df.columns.to_list()
    idx_res_chunk_start = list_of_column_names.index('gas_standard')
    idx_res_chunk_end = list_of_column_names.index('residual_dry')
    idx_last_val_date = list_of_column_names.index('last_ASVCO2_validation')
    #idx_last_physical_datum = list_of_column_names('CO2_dry')
    reordered_col_names = list_of_column_names[0:3] + \
        list_of_column_names[idx_res_chunk_start:idx_res_chunk_end+1] + \
        [list_of_column_names[idx_last_val_date]] + \
        list_of_column_names[3:idx_last_val_date] + \
        list_of_column_names[idx_last_val_date+1:idx_res_chunk_start] + \
        list_of_column_names[idx_res_chunk_end+1:len(list_of_column_names)]
    big_df = big_df[reordered_col_names]
    for name in list_of_column_names:
        if (name not in reordered_col_names):
            raise Exception(f'ERROR: {name} did make it into reordered columns')


    ERDDAP_rename_dict = {'State':'INSTRUMENT_STATE','TS':'time','SN':'SN_ASVCO2',\
    'CO2(ppm)':'CO2_ASVCO2','Li_Temp(C)':'CO2DETECTOR_TEMP_ASVCO2',\
    'Li_Pres(kPa)':'CO2DETECTOR_PRESS_UNCOMP_ASVCO2',\
    'Li_RawSample':'CO2DETECTOR_RAWSAMPLE_ASVCO2',\
    'Li_RawReference':'CO2DETECTOR_RAWREFERENCE_ASVCO2',\
    'RH(%)':'RH_ASVCO2','RH_T(C)':'RH_TEMP_ASVCO2','O2(%)':'O2_ASVCO2',\
    'ver':'ASVCO2_firmware','sample':'sampling_frequency',\
    'LI_ver':'CO2DETECTOR_firmware','LI_ser':'CO2DETECTOR_serialnumber',\
    'ASVCO2_secondaryspan2_concentration':'ASVCO2_secondaryspan_concentration',\
    'ASVCO2_ATRH_serial':'ASVCO2_ATRH_serialnumber',\
    'ASVCO2_O2_serial':'ASVCO2_O2_serialnumber',\
    'ASVCO2_manufacturer':'ASVCO2_vendor_name',\
    'CO2kzero':'CO2DETECTOR_ZERO_COEFFICIENT_ASVCO2',\
    'CO2kspan':'CO2DETECTOR_SPAN_COEFFICIENT_ASVCO2',\
    'CO2kspan2':'CO2DETECTOR_SECONDARY_COEFFICIENT_ASVCO2',\
    'gas_standard':'CO2_REF_LAB',\
    'CO2_dry':'CO2_DRY_ASVCO2','CO2_dry_Tcorr':'CO2_DRY_TCORR_ASVCO2',\
    'residual':'CO2_RESIDUAL_ASVCO2','residual_dry':'CO2_DRY_RESIDUAL_ASVCO2',\
    'residual_dry_Tcorr':'CO2_DRY_TCORR_RESIDUAL_ASVCO2'}
    
    big_df = big_df.rename(columns=ERDDAP_rename_dict)

    #Last and final thing, add in Notes column
    #big_df['Notes'] = ['x'*257]*len(big_df)
    big_df['Notes'] = ['']*len(big_df)

    pd.reset_option('max_columns')

    return big_df

def parse_all_file_df_w_summary_v2(filename):
    #filename = './data/1006/20210430/ALL/20210429_183017.txt'
    linenum = 0
    with open(filename, 'rt') as myfile:
        sys_rep={}
        for line in myfile:
            linenum += 1
            if '=' in line:  # equals sign found and system report likely
                line = line.rstrip('\n')
                line = line.strip()
                lhs_and_rhs = re.split(r'=',line)
                sys_rep[lhs_and_rhs[0].strip()]=lhs_and_rhs[1]
            if 'LOG:' in line:
                break
    #print(sys_rep)
    
    if ( 'serial' in sys_rep ):
        ASVCO2_sn = sys_rep['serial'].strip()
    else:
        raise Exception('No serial number entered in system report from {filename}, cannot continue.')
    
    sys_rep = all_update_missing_v1_8(sys_rep,ASVCO2_sn)  #new for v2

    #coeff_df = loadASVall_coeff(filename)
    coeff_df = loadASVall_coeff_with_dates(filename)  #new for v2
    flags_df = loadASVall_flags(filename)
    data_df = loadASVall_data(filename)
    dry_df = loadASVall_dry(filename)  # new stuff

    data_df = all_df_make_temp_and_dry_correction(data_df,coeff_df,sys_rep)

    # pd.set_option('max_columns',None)
    # print(coeff_df.describe(include='all'))
    # print(coeff_df.head())
    # print(data_df.describe(include='all'))
    # print(data_df.head())
    

    # add in extra columns to data_df from system report, sys_rep
    big_df = data_df.copy()
    num_rows=len(big_df)
    for k,v in sys_rep.items():
        #duplicates=[v]*num_rows
        #big_df[k]=duplicates
        big_df[k]=""
    for index, row in coeff_df.iterrows():
        #print(row['coeff'],row['label'])
        #print(f'row of coeff = {row[/'coeff']}, row of label = {row['label']}')
        #duplicates=[row['coeff']]*num_rows
        big_df[row['label']]=""

    #Pascal, 8/13/2021, choose which gas list to use based upon time string from filename,
    #will need to update this to a more fully featured lookup later
    time_str=re.search(r'\d{8}_\d{6}\.txt',filename)[0]  #grab 8 digits, underscore and 6 digits
    year_month_day_str = re.split(r'_',time_str)[0]
    num_yr_mo_dd = float(year_month_day_str)
    if ( (20210801 - num_yr_mo_dd) > 0 ):  # if it preceded Aug 1 2021, then used older gaslists
        if ((20210420 - num_yr_mo_dd) > 0):
            gaslist=[0, 104.25, 349.79, 552.9, 732.64, 999.51, 1487.06, 1994.25] #552.9 before 4/27
        else:
            gaslist=[0, 104.25, 349.79, 506.16, 732.64, 999.51, 1487.06, 1994.25]
    else:  # use newer gaslist if after Aug 1 2021
        gaslist=[0, 104.25, 349.79, 494.72, 732.64, 999.51, 1487.06, 1961.39] #update in early Aug 2021
    
    #add column for standard gas
    mask_EPOFF = data_df['State'].str.contains('EPOFF')
    df_epoff = data_df[mask_EPOFF]
    #print(f'len(df_epoff) = {len(df_epoff)}')
    mins=[]
    for index, row in df_epoff.iterrows():
        for gas in gaslist:
            #print(row['CO2(ppm)'])
            minimum=abs(float(row['CO2(ppm)'])-gas)
            #print(f'minimum = {minimum}')
            if minimum<50:
                #df_epoff['gas_standard'][i]=gas
                mins.append(gas)
    
    closest_gas_standards = pd.Series(data=mins,dtype='float64')
    most_likely_gas_standard = closest_gas_standards.median()
    # print(closest_gas_standards.values)
    big_df['gas_standard']=[most_likely_gas_standard]*num_rows

    #### Check for number of samples per state ####
    # slice = big_df[['TS','State','CO2(ppm)']]
    # check = slice.groupby('State').count()#.agg(['mean','std','count'])
    # pd.set_option('max_columns',None)
    # print('#### check each mode statistics ####')
    # print(check)
    # pd.reset_option('max_columns')

    ### New stuff, figure out most probable span gas ###
    min=max(gaslist)
    for gas in gaslist:
        diff=abs(gas-500)
        if diff < min:
            most_probable_span_gas = gas
            min = diff

    #### New stuff, create residual columns ####
    big_df = all_df_make_dry_residual_columns(big_df,most_probable_span_gas)

    #construct final row, which is summary data into big_df
    final_row = pd.DataFrame()
    for col_name in data_df.columns.values:
        if ( col_name == 'State'):
            final_row[col_name]=['Summary']
        else:
            final_row[col_name]=""
    for k,v in sys_rep.items():
        final_row[k]=v
    for index, row in coeff_df.iterrows():
        final_row[row['label']]=row['coeff']
    for col_name in flags_df.columns.values:  # NEW, 9/7/2021
        if (col_name != 'index'):
            final_row[col_name]=flags_df[col_name]  # NEW, 9/7/2021

    #special manipulations to move between raw data and sample data    
    final_ts_str = big_df['TS'].iloc[-1]
    final_ts_str = final_ts_str.strip()
    last_whole_sec_idx = re.search(r'\.\d',final_ts_str).span()[0]
    floored_final_ts_str = final_ts_str[:last_whole_sec_idx] + 'Z'
    final_ts_plus_1sec = dt.datetime.strptime(floored_final_ts_str, '%Y-%m-%dT%H:%M:%SZ') + \
        dt.timedelta(0,1)
    final_row['TS']=final_ts_plus_1sec.strftime(' %Y-%m-%dT%H:%M:%S') + '.0Z'
    final_row['SN']=big_df['SN'].iloc[-1]
    final_row['gas_standard']=big_df['gas_standard'].iloc[-1]

    big_df['last_ASVCO2_validation'] = [final_row['last_ASVCO2_validation'].iloc[-1]]*num_rows

    #### special additional items for final row (summary data) ####
    final_row['CO2DETECTOR_vendor_name']=['LI-COR Biosciences']
    final_row['CO2DETECTOR_model_name']=['LI-830']

    #print(f'before adding last row, len(big_df) = {len(big_df)}')
    #print(f'len(final_row) = {len(final_row)}')
    big_df = pd.concat([big_df,final_row], axis=0, ignore_index=True)
    #print(f'after adding last row, len(big_df) = {len(big_df)}')

    # print('big_df is like...')
    # print(big_df.describe(include='all'))
    # print(big_df.head())
    # print('END big_df')

    big_df = big_df.drop(columns=['serial','time','gps'])

    #### Reorder columns ####
    list_of_column_names = big_df.columns.to_list()
    idx_res_chunk_start = list_of_column_names.index('gas_standard')
    idx_res_chunk_end = list_of_column_names.index('residual_dry')
    idx_last_val_date = list_of_column_names.index('last_ASVCO2_validation')
    #idx_last_physical_datum = list_of_column_names('CO2_dry')
    reordered_col_names = list_of_column_names[0:3] + \
        list_of_column_names[idx_res_chunk_start:idx_res_chunk_end+1] + \
        [list_of_column_names[idx_last_val_date]] + \
        list_of_column_names[3:idx_last_val_date] + \
        list_of_column_names[idx_last_val_date+1:idx_res_chunk_start] + \
        list_of_column_names[idx_res_chunk_end+1:len(list_of_column_names)]
    big_df = big_df[reordered_col_names]
    for name in list_of_column_names:
        if (name not in reordered_col_names):
            raise Exception(f'ERROR: {name} did make it into reordered columns')


    ERDDAP_rename_dict = {'State':'INSTRUMENT_STATE','TS':'time','SN':'SN_ASVCO2',\
    'CO2(ppm)':'CO2_ASVCO2','Li_Temp(C)':'CO2DETECTOR_TEMP_ASVCO2',\
    'Li_Pres(kPa)':'CO2DETECTOR_PRESS_UNCOMP_ASVCO2',\
    'Li_RawSample':'CO2DETECTOR_RAWSAMPLE_ASVCO2',\
    'Li_RawReference':'CO2DETECTOR_RAWREFERENCE_ASVCO2',\
    'RH(%)':'RH_ASVCO2','RH_T(C)':'RH_TEMP_ASVCO2','O2(%)':'O2_ASVCO2',\
    'ver':'ASVCO2_firmware','sample':'sampling_frequency',\
    'LI_ver':'CO2DETECTOR_firmware','LI_ser':'CO2DETECTOR_serialnumber',\
    'ASVCO2_secondaryspan2_concentration':'ASVCO2_secondaryspan_concentration',\
    'ASVCO2_ATRH_serial':'ASVCO2_ATRH_serialnumber',\
    'ASVCO2_O2_serial':'ASVCO2_O2_serialnumber',\
    'ASVCO2_manufacturer':'ASVCO2_vendor_name',\
    'CO2kzero':'CO2DETECTOR_ZERO_COEFFICIENT_ASVCO2',\
    'CO2kspan':'CO2DETECTOR_SPAN_COEFFICIENT_ASVCO2',\
    'CO2kspan2':'CO2DETECTOR_SECONDARY_COEFFICIENT_ASVCO2',\
    'gas_standard':'CO2_REF_LAB',\
    'CO2_dry':'CO2_DRY_ASVCO2','CO2_dry_Tcorr':'CO2_DRY_TCORR_ASVCO2',\
    'residual':'CO2_RESIDUAL_ASVCO2','residual_dry':'CO2_DRY_RESIDUAL_ASVCO2',\
    'residual_dry_Tcorr':'CO2_DRY_TCORR_RESIDUAL_ASVCO2'}
    
    big_df = big_df.rename(columns=ERDDAP_rename_dict)

    #Last and final thing, add in Notes column
    #big_df['Notes'] = ['x'*257]*len(big_df)
    big_df['Notes'] = ['']*len(big_df)

    pd.reset_option('max_columns')

    return big_df

def load_Val_File_into_dicts(val_filename):
    val_file = open(val_filename,'rt')
    big_str = val_file.read()
    stuff = re.split(r'ASVCO2v2\n',big_str)
    #print("...stuff[0]... ",stuff[0])
    d_by_time = {}
    other_stuff = {}
    for idx in range(1,len(stuff)):
        if ( re.search(r'time=(.*)',stuff[idx]) and \
            re.search(r'Validation with reference gas:(.*)',stuff[idx]) ):
            time_str = re.search(r'time=(.*)',stuff[idx]).groups()[0]#.strip()
            ref_gas = float(re.search(r'Validation with reference gas:(.*)',stuff[idx]).groups()[0])
            split_by_newline = re.split(r'\n',stuff[idx])
            first_header_entered=False
            nested_dict = {}
            other_parts = {}
            crazy = r'[+-]?\d+\.?\d*[eE][+-]?\d+|[-]?\d+\.\d+|[-]?\d+'  # number, scientific notation
            time_re = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z'
            for idx, line in enumerate(split_by_newline):
                line = line.replace(" ","")
                if len(line) > 0:
                    letter_score = sum([c.isalpha() for c in line]) \
                            /len(line)
                else:
                    letter_score = 0
                if ( re.match(r'(\w+,)+',line) \
                    and letter_score > 0.5 and first_header_entered == False):
                    header = re.split(r',',line)
                    header.append('gas_standard')
                    for field_name in header:
                        nested_dict[field_name]=[]
                    first_header_entered = True
                elif ( first_header_entered == True \
                    and re.match(r'(\w+,)+',line) ):
                    entries_of_data = re.split(r',',line)
                    entries_of_data.append(str(ref_gas))  # cast back to string
                    for idx,field_name in enumerate(header):
                        if ( re.search(crazy,entries_of_data[idx]) and \
                            len(re.search(crazy,entries_of_data[idx])[0]) == \
                            len(entries_of_data[idx]) ):  # most likely a number
                            entries_of_data[idx]=float(entries_of_data[idx])
                        if (field_name == 'datetime'):
                            some_datetime_object = pd.to_datetime(float(entries_of_data[idx]),unit='D')
                            ### round up to the nearest second ###
                            if some_datetime_object.microsecond > 500_000:
                                some_datetime_object += dt.timedelta(seconds=1)
                            some_datetime_object = some_datetime_object.replace(microsecond=0)
                            #entries_of_data[idx]=some_datetime_object.strftime(" %Y-%m-%dT%H:%M:%S.%f")[:-5]+'Z'
                            entries_of_data[idx]=some_datetime_object.strftime(" %Y-%m-%dT%H:%M:%S")+'Z'
                        nested_dict[field_name].append(entries_of_data[idx])
                elif ( "=" in line ):
                    parts = line.split( "=" )
                    #print(line)
                    # if ( re.search(crazy,parts[1].strip()) 
                    if ( re.search(crazy,parts[1].strip()) and \
                        len(re.search(crazy,parts[1].strip())[0]) == \
                            len(parts[1].strip()) ):  # most likely a number
                        other_parts[parts[0].strip()] = float(parts[1].strip())
                    #special case for time = YYYY-MM-DDThh:mm:ssZ
                    elif ( re.search(time_re,parts[1].strip()) and \
                        'time' in line ):
                        other_parts['time_of_report_command'] = parts[1].strip()
                    else:
                        other_parts[parts[0].strip()] = parts[1].strip()
                elif ( ":" in line and \
                    re.search(time_re,line) is None and \
                        "Mode" not in line and \
                        "CO2" in line and \
                        "Validationwithreferencegas" not in line):
                    parts = line.split(":")
                    if ( re.search(crazy,parts[1].strip()) and \
                        len(re.search(crazy,parts[1].strip())[0]) == \
                            len(parts[1].strip()) ):  # most likely a number
                        other_parts[parts[0].strip()] = float(parts[1].strip())
                    else:
                        other_parts[parts[0].strip()] = parts[1].strip()
        
        other_stuff[time_str]=other_parts
        #d_by_time[time_str]={ref_gas:nested_dict}
        d_by_time[time_str]=nested_dict

    return d_by_time, other_stuff

def load_Val_File_into_dicts_v3(val_filename, timestamp_mode='ISO-8601 string'):
    # optional timestamp_mode = 'Unix epoch, days'

    val_file = open(val_filename,'rt')
    big_str = val_file.read()
    stuff = re.split(r'ASVCO2v2\n',big_str)
    #print("...stuff[0]... ",stuff[0])
    d_by_time = {}
    other_stuff = {}
    mode_and_gas_stuff = {}
    flush_stuff = {}
    for idx in range(1,len(stuff)):
        time_str = re.search(r'time=(.*)',stuff[idx]).groups()[0]#.strip()
        ref_gas = float(re.search(r'Validation with reference gas:(.*)',stuff[idx]).groups()[0])
        split_by_newline = re.split(r'\n',stuff[idx])
        first_header_entered=False
        nested_dict = {}
        other_parts = {}
        mode_and_gas_parts = {}
        flush_mean_and_std_parts = {}
        crazy = r'[+-]?\d+\.?\d*[eE][+-]?\d+|[-]?\d+\.\d+|[-]?\d+'  # number, scientific notation
        crazier=r'([+-]?\d+\.?\d*[eE][+-]?\d+)|([-]?\d+\.\d+)|([-]?\d+)'  # number, scientific notation with groups
        time_re = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z'
        for idx, line in enumerate(split_by_newline):
            line = line.replace(" ","")
            if len(line) > 0:
                letter_score = sum([c.isalpha() for c in line]) \
                        /len(line)
            else:
                letter_score = 0
            if ( re.match(r'(\w+,)+',line) \
                and letter_score > 0.5 and first_header_entered == False):
                header = re.split(r',',line)
                header.append('gas_standard')
                for field_name in header:
                    nested_dict[field_name]=[]
                first_header_entered = True
            elif ( first_header_entered == True \
                and re.match(r'(\w+,)+',line) ):
                entries_of_data = re.split(r',',line)
                entries_of_data.append(str(ref_gas))  # cast back to string
                for idx,field_name in enumerate(header):
                    if ( re.search(crazy,entries_of_data[idx]) and \
                         len(re.search(crazy,entries_of_data[idx])[0]) == \
                         len(entries_of_data[idx]) ):  # most likely a number
                        entries_of_data[idx]=float(entries_of_data[idx])
                    if (field_name == 'datetime' and \
                        timestamp_mode == 'Unix epoch, days'):
                        some_datetime_object = pd.to_datetime(float(entries_of_data[idx]),unit='D')
                        ### round up to the nearest second ###
                        if some_datetime_object.microsecond > 500_000:
                            some_datetime_object += dt.timedelta(seconds=1)
                        some_datetime_object = some_datetime_object.replace(microsecond=0)
                        #entries_of_data[idx]=some_datetime_object.strftime(" %Y-%m-%dT%H:%M:%S.%f")[:-5]+'Z'
                        entries_of_data[idx]=some_datetime_object.strftime(" %Y-%m-%dT%H:%M:%S")+'Z'
                    elif (field_name == 'datetime' and \
                        timestamp_mode == 'ISO-8601 string'):
                        if ( re.search(time_re,parts[1].strip()) ):
                            entries_of_data[idx] = " " + entries_of_data[idx]  # prepend leading space???
                        else:
                            raise Exception (f"""Unrecognized timestamp format for {entries_of_data[idx]} 
                            found in {val_filename}""")
                    elif (field_name == 'datetime' and \
                        not ( timestamp_mode == 'ISO-8601 string' or \
                            timestamp_mode == 'Unix epoch, days')):
                        raise Exception (f"""Unrecognized timestamp format of {timestamp_mode} as
                        second argument of this subroutine""")
                    nested_dict[field_name].append(entries_of_data[idx])
            elif ( "=" in line ):
                parts = line.split( "=" )
                #print(line)
                # if ( re.search(crazy,parts[1].strip()) 
                if ( re.search(crazy,parts[1].strip()) and \
                    len(re.search(crazy,parts[1].strip())[0]) == \
                         len(parts[1].strip()) ):  # most likely a number
                    other_parts[parts[0].strip()] = float(parts[1].strip())
                #special case for time = YYYY-MM-DDThh:mm:ssZ
                elif ( re.search(time_re,parts[1].strip()) and \
                    'time' in line ):
                    other_parts['time_of_report_command'] = parts[1].strip()
                else:
                    other_parts[parts[0].strip()] = parts[1].strip()
            elif ( ":" in line and \
                re.search(time_re,line) is None and \
                    "Mode" not in line and \
                    ("CO2k" in line or "CO2L" in line) and \
                    "Validationwithreferencegas" not in line):
                parts = line.split(":")
                if ( re.search(crazy,parts[1].strip()) and \
                    len(re.search(crazy,parts[1].strip())[0]) == \
                         len(parts[1].strip()) ):  # most likely a number
                    other_parts[parts[0].strip()] = float(parts[1].strip())
                else:
                    other_parts[parts[0].strip()] = parts[1].strip()
            elif ( ":" in line and \
                re.search(time_re,line) is None and \
                    "Mode" in line and \
                    "CO2k" not in line and \
                    "CO2L" not in line and \
                    "Validationwithreferencegas" not in line and \
                    "OFF" in line):
                mode_and_gas_comma_parts = line.split(",")
                for this_txt in mode_and_gas_comma_parts:
                    left_and_right_of_colon = this_txt.split(":")
                    if ( len(left_and_right_of_colon) == 2 ):
                        left_of_colon = left_and_right_of_colon[0]
                        right_of_colon = left_and_right_of_colon[1]
                        if ( "Mode" in left_of_colon ):
                            if ( not(right_of_colon in mode_and_gas_parts) ):
                                mode_and_gas_parts[right_of_colon] = {}
                            this_mode = right_of_colon
                        else:
                            if ( re.search(crazy,right_of_colon.strip()) and \
                                len(re.search(crazy,right_of_colon.strip())[0]) == \
                                    len(right_of_colon.strip()) ):  # most likely a number
                                mode_and_gas_parts[this_mode][left_of_colon] = \
                                    float(right_of_colon.strip())
                            elif ( not(left_of_colon in mode_and_gas_parts[this_mode]) and \
                                re.search(crazier,right_of_colon.strip()) ):
                                #find the number within the groups() of regex
                                for item in re.search(crazier,right_of_colon.strip()).groups():
                                    if ( item ):
                                        num_as_str = item
                                        break
                                mode_and_gas_parts[this_mode][left_of_colon] = \
                                    float(num_as_str)
                            else:
                                mode_and_gas_parts[this_mode][left_of_colon] = \
                                    right_of_colon
            elif ( ":" in line and \
                re.search(time_re,line) is None and \
                    "Mode" not in line and \
                    "CO2k" not in line and \
                    "CO2L" not in line and \
                    "Mean" in line and \
                    "STD" in line and \
                    "Validationwithreferencegas" not in line and \
                    "OFF" not in line):
                flush_mean_and_std_comma_parts = line.split(",")
                for this_txt in flush_mean_and_std_comma_parts:
                    left_and_right_of_colon = this_txt.split(":")
                    if ( len(left_and_right_of_colon) == 2 ):
                        left_of_colon = left_and_right_of_colon[0]
                        right_of_colon = left_and_right_of_colon[1]
                        if ( "Mean" in left_of_colon ):
                            if ( not(left_of_colon in flush_mean_and_std_parts) and \
                                re.search(crazier,right_of_colon) ):  # most likely a number in right_of_colon
                                #find the number within the groups() of regex
                                for item in re.search(crazier,right_of_colon.strip()).groups():
                                    if ( item ):
                                        this_mean_as_str = item
                                        break
                                flush_mean_and_std_parts[left_of_colon] = float(this_mean_as_str)
                            else:
                                flush_mean_and_std_parts[left_of_colon] = right_of_colon
                        elif ( "STD" in left_of_colon ):
                            if ( not(left_of_colon in flush_mean_and_std_parts) and \
                                re.search(crazier,right_of_colon) ):  # most likely a number in right_of_colon
                                #find the number within the groups() of regex
                                for item in re.search(crazier,right_of_colon.strip()).groups():
                                    if ( item ):
                                        this_std_as_str = item
                                        break
                                flush_mean_and_std_parts[left_of_colon] = float(this_std_as_str)
                            else:
                                flush_mean_and_std_parts[left_of_colon] = right_of_colon
            elif ( re.search(r'Flushing validaiton gas for (\d+\.\d+|\d+) seconds',line) ):
                flush_time_str = re.search(r'Flushing validaiton gas for (\d+\.\d+)|(\d+) seconds',line).groups()[0]
                flush_mean_and_std_parts["flush_time"] = float(flush_time_str)

        flush_stuff[time_str] = flush_mean_and_std_parts
        mode_and_gas_stuff[time_str] = mode_and_gas_parts
        other_stuff[time_str]=other_parts
        #d_by_time[time_str]={ref_gas:nested_dict}
        d_by_time[time_str]=nested_dict

    return d_by_time, other_stuff, mode_and_gas_stuff, flush_stuff

def val_df_make_residual_column(super_big_val_df):
    super_big_val_df['residual_ave'] = [np.NaN]*len(super_big_val_df)
    
    idx_of_most_probable_span_gas = abs(super_big_val_df['gas_standard']-500).sort_values().index[0]
    most_probable_span_gas = super_big_val_df['gas_standard'].iloc[idx_of_most_probable_span_gas]

    temp = pd.DataFrame()
    filt_zero = (super_big_val_df['mode'] == "ZPOFF") | (super_big_val_df['mode'] == "ZPON") \
        | (super_big_val_df['mode'] == "ZPPCAL") 
    temp['residual_ave'] = super_big_val_df[filt_zero].loc[:,'CO2_ave']

    # identity of probability theory, see Sheldon Ross, p. 143
    temp['residual_sd']=super_big_val_df[filt_zero].loc[:,'CO2_sd']   
    super_big_val_df.update(temp)

    # print('temp is like',temp.head())
    # print('super_big_val_df is like',super_big_val_df['residual_ave'].head())
    del temp

    temp = pd.DataFrame()
    filt_span = (super_big_val_df['mode'] == "SPOFF") | (super_big_val_df['mode'] == "SPON") \
        | (super_big_val_df['mode'] == "SPPCAL")
    temp['residual_ave'] = super_big_val_df[filt_span].loc[:,'CO2_ave'] - most_probable_span_gas
    
    # identity of probability theory, see Sheldon Ross, p. 143
    temp['residual_sd']=super_big_val_df[filt_span].loc[:,'CO2_sd']   
    super_big_val_df.update(temp)

    # print('temp is like',temp.head())
    # print('super_big_val_df is like',super_big_val_df['residual_ave'].head())
    del temp
    
    temp = pd.DataFrame()
    mask_ref = (super_big_val_df['mode'] == "APOFF") | (super_big_val_df['mode'] == "APON") \
        | (super_big_val_df['mode'] == "EPOFF") | (super_big_val_df['mode'] == "EPON")
    temp['residual_ave'] = super_big_val_df[mask_ref].loc[:,'CO2_ave'] -\
        super_big_val_df[mask_ref].loc[:,'gas_standard']
    super_big_val_df.update(temp)
    # print('temp is like',temp.head())
    # print('super_big_val_df is like',super_big_val_df['residual_ave'].head())
    del temp

    super_big_val_df['residual_sd']=super_big_val_df['CO2_sd']  # identity of probability theory, see Sheldon Ross, p. 143 

    return super_big_val_df

def val_df_make_dry_residual_columns(super_big_val_df):
    super_big_val_df['residual_ave'] = [np.NaN]*len(super_big_val_df)
    super_big_val_df['residual_sd'] = [np.NaN]*len(super_big_val_df)
    super_big_val_df['residual_Tcorr_ave'] = [np.NaN]*len(super_big_val_df)  # new
    super_big_val_df['residual_Tcorr_sd'] = [np.NaN]*len(super_big_val_df)  # new
    super_big_val_df['residual_dry_ave'] = [np.NaN]*len(super_big_val_df)  # new
    #super_big_val_df['residual_dry_sd'] = [np.NaN]*len(super_big_val_df)  # new
    
    idx_of_most_probable_span_gas = abs(super_big_val_df['gas_standard']-500).sort_values().index[0]
    most_probable_span_gas = super_big_val_df['gas_standard'].iloc[idx_of_most_probable_span_gas]

    temp = pd.DataFrame()
    filt_zero = (super_big_val_df['mode'] == "ZPOFF") | (super_big_val_df['mode'] == "ZPON") \
        | (super_big_val_df['mode'] == "ZPPCAL") 
    temp['residual_ave'] = super_big_val_df[filt_zero].loc[:,'CO2_ave']

    # identity of probability theory, see Sheldon Ross, p. 143
    temp['residual_sd']=super_big_val_df[filt_zero].loc[:,'CO2_sd']   
    super_big_val_df.update(temp)

    # print('temp is like',temp.head())
    # print('super_big_val_df is like',super_big_val_df['residual_ave'].head())
    del temp

    temp = pd.DataFrame()
    filt_span = (super_big_val_df['mode'] == "SPOFF") | (super_big_val_df['mode'] == "SPON") \
        | (super_big_val_df['mode'] == "SPPCAL")
    temp['residual_ave'] = super_big_val_df[filt_span].loc[:,'CO2_ave'] - most_probable_span_gas
    
    # identity of probability theory, see Sheldon Ross, p. 143
    temp['residual_sd']=super_big_val_df[filt_span].loc[:,'CO2_sd']   
    super_big_val_df.update(temp)
    
    temp = pd.DataFrame()
    filt_ref = (super_big_val_df['mode'] == "EPON") | (super_big_val_df['mode'] == "APON")
    temp['residual_ave'] = super_big_val_df[filt_ref].loc[:,'CO2_ave'] -\
        super_big_val_df[filt_ref].loc[:,'gas_standard']

    # identity of probability theory, see Sheldon Ross, p. 143
    temp['residual_sd']=super_big_val_df[filt_ref].loc[:,'CO2_sd']
    super_big_val_df.update(temp)
    # print('temp is like',temp.head())
    # print('super_big_val_df is like',super_big_val_df['residual_ave'].head())
    del temp

    temp = pd.DataFrame()
    filt_ref = (super_big_val_df['mode'] == "APOFF") | (super_big_val_df['mode'] == "EPOFF")
    temp['residual_dry_ave'] = super_big_val_df[filt_ref].loc[:,'CO2_dry_ave'] -\
        super_big_val_df[filt_ref].loc[:,'gas_standard']
    # approximation dry CO2 standard deviation for now, 
    # would need to calculate from 2Hz data to actually calculate temperature
    # corrected standard deviation.
    #temp['residual_dry_sd'] = super_big_val_df[filt_ref].loc[:,'CO2_sd']
    super_big_val_df.update(temp)
    # print('temp is like',temp.head())
    # print('super_big_val_df is like',super_big_val_df['residual_ave'].head())
    del temp

    # New
    temp = pd.DataFrame()
    filt_ref = (super_big_val_df['mode'] == "APOFF") | (super_big_val_df['mode'] == "EPOFF")
    temp['residual_Tcorr_ave'] = super_big_val_df[filt_ref].loc[:,'CO2_dry_Tcorr_ave'] -\
        super_big_val_df[filt_ref].loc[:,'gas_standard']
    # approximation temperature corrected standard deviation for now, 
    # would need to calculate from 2Hz data to actually calculate temperature
    # corrected standard deviation.
    temp['residual_Tcorr_sd'] = super_big_val_df[filt_ref].loc[:,'CO2_sd']  
    
    super_big_val_df.update(temp)

    CO2_dry_Tcorr_stuff = super_big_val_df[filt_ref].loc[:,'CO2_dry_Tcorr_ave']
    # print('CO2_dry_Tcorr_ave is like...',CO2_dry_Tcorr_stuff.describe())
    # print('calculated temp and dry corrected residuals',temp['residual_Tcorr_ave'].describe())
    # print('super_big_val_df is like',super_big_val_df['residual_ave'].head())
    del temp

    #super_big_val_df['residual_sd']=super_big_val_df['CO2_sd']  # identity of probability theory, see Sheldon Ross, p. 143 

    return super_big_val_df

def val_df_make_temp_and_dry_correction_v2(super_big_val_df,big_stats_df):
    # State,SN,Timestamp,Li_Temp_ave(C),Li_Temp_sd,Li_Pres_ave(kPa),' + \
    #'Li_Pres_sd,CO2_ave(PPM),CO2_SD,O2_ave(%),O2_S,RH_ave(%),RH_sd,RH_T_ave(C),Rh_T_sd,' + \
    #'Li_RawSample_ave,Li_RawSample_sd,Li_RawDetector_ave,Li_RawReference_sd
    # print('hello, inside val_df_make_temp_and_dry_correction()...')
    # pd.set_option('max_columns',None)
    # print('big_stats_df first five rows...')
    # print(big_stats_df.head())
    # print('big_stats_df described...')
    # print(big_stats_df.describe(include='all'))
    # pd.reset_option('max_columns')
    temp_data = pd.DataFrame()
    filt_ref = (big_stats_df['State'].str.contains("APOFF")) | \
        (big_stats_df['State'].str.contains("EPOFF")) | \
        (big_stats_df['State'].str.contains("SPOFF"))
    rename_stats2data = {'Li_RawSample_ave':'Li_Raw','Li_RawDetector_ave':'Li_ref',\
        'Li_Pres_ave(kPa)':'Pres','Li_Temp_ave(C)':'Temp','RH_T_ave(C)':'RH_T(C)',\
        'RH_ave(%)':'RH(%)'}  #just use RH instead of RH(%) if using itertuples
    temp_data = big_stats_df[filt_ref].copy()
    temp_data = temp_data.rename(columns=rename_stats2data)
    temp_data['CO2_dry_Tcorr_ave'] = [np.NaN]*len(temp_data)
    # zerocoeff = super_big_val_df[mask_ref].loc[:,'CO2kzero']
    # S0 = super_big_val_df[mask_ref].loc[:,'CO2kspan']
    # S1 = super_big_val_df[mask_ref].loc[:,'CO2kspan2']
    # pd.set_option('max_columns',None)
    # print('temp data first five rows...')
    # print(temp_data.head())
    # print('temp data described...')
    # print(temp_data.describe(include='all'))
    # pd.reset_option('max_columns')
    CO2kzero_col_num = super_big_val_df.columns.get_loc('CO2kzero')
    print(f'CO2kzero_col_num = {CO2kzero_col_num}')

    S_0_idx = super_big_val_df.columns.get_loc('CO2kspan')
    S_1_idx = super_big_val_df.columns.get_loc('CO2kspan2')
    z_0_idx = super_big_val_df.columns.get_loc('CO2kzero')
    # Does not work for unknown reason,
    for idx, row in temp_data.iterrows():
        #print('loop ' + str(idx))
        if ( 'SPOFF' in row['State'] ):
            ts_val_filt = super_big_val_df['datetime'] == row['Timestamp']
            # pd.set_option('max_columns',None)
            # print('first five rows of filtered by ts super big val df')
            # print(super_big_val_df[ts_val_filt].head())
            # pd.reset_option('max_columns')

            #print('spoff')
            RH_span_prev = row['RH(%)']
            S_0 = super_big_val_df[ts_val_filt].iloc[0,S_0_idx] 
            S_1 = super_big_val_df[ts_val_filt].iloc[0,S_1_idx]
            zerocoeff = super_big_val_df[ts_val_filt].iloc[0,z_0_idx]
            w_mean = row['Li_Raw']; w0_mean = row['Li_ref']
            alphaC = (1 - ((w_mean / w0_mean) * zerocoeff))
            BetaC = alphaC * (S_0 + S_1 * alphaC)
            span2_in = super_big_val_df[ts_val_filt].iloc[0,\
                super_big_val_df.columns.\
                get_loc('secondaryspan_calibrated_temperature')]
            span1_avgT = row['Temp']
            slope_in = super_big_val_df[ts_val_filt].iloc[0,\
                super_big_val_df.columns.\
                get_loc('secondaryspan_temperaturedependantslope')]
            #difference in temp from span2 at 20C and span1 temp
            span2_cal2_temp_diff = span1_avgT - span2_in
            #span2_cal2_temp_diff = span2_in - span1_avgT
            S1_tcorr = (S_1 + slope_in * span2_cal2_temp_diff)#.astype(float)
            # Algebraic manipulation from LiCor Appendix A, eq. A-28
            # note that overbar symbol on alphaC symbol in the LiCor 830/850 manual indicates a 5 second average value
            S0_tcorr = (BetaC / alphaC) - (S1_tcorr * alphaC)
        else:
            #print('not spoff')
            # use timestamp to get span coefficients
            xCO2_tcorr = calculate_xco2_from_data_pt_by_pt(row,\
                zerocoeff, S0_tcorr, S1_tcorr,scalar=True)
            # the_numba = dry_correction(xCO2_tcorr,\
            #     row['RH_T(C)'],row['Pres'],row['RH(%)'],RH_span_prev)
            # print(f'the_numba = {the_numba}')
            temp_data.loc[idx,'CO2_dry_Tcorr_ave'] = dry_correction(xCO2_tcorr,\
                row['RH_T(C)'],row['Pres'],row['RH(%)'],RH_span_prev) 
        
    #### Merge in the num samples data from the stats dataframe ####
    super_big_val_df = super_big_val_df.merge(temp_data[\
        ['Timestamp','CO2_dry_Tcorr_ave']],left_on='datetime',\
        right_on='Timestamp',how='left',suffixes=('','_dtc'))

    del temp_data

    print('#### After merge inside val_df_make_temp_and_dry correction #####')
    print(f'super_big_val_df.columns.values = {super_big_val_df.columns.values}')

    return super_big_val_df

def val_df_make_temp_and_dry_correction(super_big_val_df,big_stats_df):
    # State,SN,Timestamp,Li_Temp_ave(C),Li_Temp_sd,Li_Pres_ave(kPa),' + \
    #'Li_Pres_sd,CO2_ave(PPM),CO2_SD,O2_ave(%),O2_S,RH_ave(%),RH_sd,RH_T_ave(C),Rh_T_sd,' + \
    #'Li_RawSample_ave,Li_RawSample_sd,Li_RawDetector_ave,Li_RawReference_sd
    # print('hello, inside val_df_make_temp_and_dry_correction()...')
    # pd.set_option('max_columns',None)
    # print('big_stats_df first five rows...')
    # print(big_stats_df.head())
    # print('big_stats_df described...')
    # print(big_stats_df.describe(include='all'))
    # pd.reset_option('max_columns')
    temp_data = pd.DataFrame()
    filt_ref = (big_stats_df['State'].str.contains("APOFF")) | \
        (big_stats_df['State'].str.contains("EPOFF")) | \
        (big_stats_df['State'].str.contains("SPOFF"))
    rename_stats2data = {'Li_RawSample_ave':'Li_Raw','Li_RawDetector_ave':'Li_ref',\
        'Li_Pres_ave(kPa)':'Pres','Li_Temp_ave(C)':'Temp','RH_T_ave(C)':'RH_T(C)',\
        'RH_ave(%)':'RH(%)'}  #just use RH instead of RH(%) if using itertuples
    temp_data = big_stats_df[filt_ref].copy()
    temp_data = temp_data.rename(columns=rename_stats2data)
    temp_data['CO2_dry_Tcorr_ave'] = [np.NaN]*len(temp_data)
    # zerocoeff = super_big_val_df[mask_ref].loc[:,'CO2kzero']
    # S0 = super_big_val_df[mask_ref].loc[:,'CO2kspan']
    # S1 = super_big_val_df[mask_ref].loc[:,'CO2kspan2']
    # pd.set_option('max_columns',None)
    # print('temp data first five rows...')
    # print(temp_data.head())
    # print('temp data described...')
    # print(temp_data.describe(include='all'))
    # pd.reset_option('max_columns')
    CO2kzero_col_num = super_big_val_df.columns.get_loc('CO2kzero')
    print(f'CO2kzero_col_num = {CO2kzero_col_num}')

    S_0_idx = super_big_val_df.columns.get_loc('CO2kspan')
    S_1_idx = super_big_val_df.columns.get_loc('CO2kspan2')
    z_0_idx = super_big_val_df.columns.get_loc('CO2kzero')
    # Does not work for unknown reason,
    for idx, row in temp_data.iterrows():
        #print('loop ' + str(idx))
        if ( 'SPOFF' in row['State'] ):
            #print('spoff')
            RH_span_prev = row['RH(%)']
        else:
            #print('not spoff')
            # use timestamp to get span coefficients
            ts_val_filt = super_big_val_df['datetime'] == row['Timestamp']
            # pd.set_option('max_columns',None)
            # print('first five rows of filtered by ts super big val df')
            # print(super_big_val_df[ts_val_filt].head())
            # pd.reset_option('max_columns')
            S_0 = super_big_val_df[ts_val_filt].iloc[0,S_0_idx] 
            S_1 = super_big_val_df[ts_val_filt].iloc[0,S_1_idx]
            zerocoeff = super_big_val_df[ts_val_filt].iloc[0,z_0_idx]
            w_mean = row['Li_Raw']; w0_mean = row['Li_ref']
            alphaC = (1 - ((w_mean / w0_mean) * zerocoeff))
            BetaC = alphaC * (S_0 + S_1 * alphaC)
            span2_in = super_big_val_df[ts_val_filt].iloc[0,\
                super_big_val_df.columns.\
                get_loc('secondaryspan_calibrated_temperature')]
            span1_avgT = row['Temp']
            slope_in = super_big_val_df[ts_val_filt].iloc[0,\
                super_big_val_df.columns.\
                get_loc('secondaryspan_temperaturedependantslope')]
            #difference in temp from span2 at 20C and span1 temp
            span2_cal2_temp_diff = span1_avgT - span2_in

            S1_tcorr = (S_1 + slope_in * span2_cal2_temp_diff)#.astype(float)

            # Algebraic manipulation from LiCor Appendix A, eq. A-28
            # note that overbar symbol on alphaC symbol in the LiCor 830/850 manual indicates a 5 second average value
            S0_tcorr = (BetaC / alphaC) - (S1_tcorr * alphaC)

            xCO2_tcorr = calculate_xco2_from_data_pt_by_pt(row,\
                zerocoeff, S0_tcorr, S1_tcorr,scalar=True)
            # the_numba = dry_correction(xCO2_tcorr,\
            #     row['RH_T(C)'],row['Pres'],row['RH(%)'],RH_span_prev)
            # print(f'the_numba = {the_numba}')
            temp_data.loc[idx,'CO2_dry_Tcorr_ave'] = dry_correction(xCO2_tcorr,\
                row['RH_T(C)'],row['Pres'],row['RH(%)'],RH_span_prev) 
        
    #### Merge in the num samples data from the stats dataframe ####
    super_big_val_df = super_big_val_df.merge(temp_data[\
        ['Timestamp','CO2_dry_Tcorr_ave']],left_on='datetime',\
        right_on='Timestamp',how='left',suffixes=('','_dtc'))

    del temp_data

    print('#### After merge inside val_df_make_temp_and_dry correction #####')
    print(f'super_big_val_df.columns.values = {super_big_val_df.columns.values}')

    return super_big_val_df

def val_df_reorder_columns(super_big_val_df):
    # col_o = super_big_val_df.columns.tolist()
    # #print('The column names are:\n',col_o)
    # #print(f'col[18] = {col_o[18]}')
    # #print(f'col[48] = {col_o[48]}')
    # cols_1 = col_o[2:16]  # physical quantities like, temperature, pressure, etc.
    # #print(f'cols_1 = {cols_1}')
    # cols_2 = col_o[18:42] + col_o[43:48] 
    # #print(f'cols_2 = {cols_2}')
    # cols_3 = col_o[48:54]
    # #print(f'cols_3 = {cols_3}')
    # reordered_cols = col_o[0:2] + col_o[54:56] + col_o[16:18] + [col_o[42]] + \
    #     cols_1 + col_o[-2:] + cols_3 + cols_2
    # #print(f'cols = {cols}')
    
    fw_string = super_big_val_df.loc[0,'ver']
    print(f'fw_string = {fw_string}')
    if ( re.match(r'.*v1\.8.*',fw_string) ):
        span2_conc_name = 'ASVCO2_secondaryspan2_concentration'
    else:
        span2_conc_name = 'ASVCO2_secondaryspan_concentration'

    col_o = super_big_val_df.columns.tolist()
    reordered_cols = ['mode', 'datetime', 'residual_ave', 'residual_sd',
        'residual_dry_ave','residual_Tcorr_ave','residual_Tcorr_sd',
        'gas_standard','gas_standard_tag','serial', 'last_ASVCO2_validation',
        'Li_Temp_ave', 'Li_Temp_sd','Li_Pres_ave', 'Li_Pres_sd', 'CO2_ave',
        'CO2_sd', 'O2_ave','O2_sd', 'RH_ave', 'RH_sd', 'RH_T_ave', 'RH_T_sd',
        'Flow_ave', 'Flow_sd', 'CO2_dry_ave', 'CO2_dry_Tcorr_ave',
        'Num_samples','CO2_dry_residual_ave_of_ave','CO2_dry_residual_sd_of_ave',
        'CO2_dry_Tcorr_residual_ave_of_ave','CO2_dry_Tcorr_residual_sd_of_ave',
        'CO2_dry_residual_max_of_ave','CO2_dry_Tcorr_residual_max_of_ave',
        'CO2LastZero', 'CO2kzero', 'CO2LastSpan', 'CO2LastSpan2', 'CO2kspan',
        'CO2kspan2', 'ver', 'startup', 'gps', 'time_of_report_command', 'span',
        'spandiff', 'equil', 'warmup', 'pumpon', 'pumpoff', 'sampleco2',
        'vent', 'heater', 'sample', 'LI_ser', 'LI_ver', 'runtime',
        'secondaryspan_calibrated_temperature',
        'secondaryspan_calibrated_spanconcentration',
        'last_secondaryspan_temperaturedependantslope',
        'secondaryspan_temperaturedependantslope',
        'secondaryspan_temperaturedependantslopefit',
        'secondaryspan_calibrated_rh',
        span2_conc_name, 'pressure_bias',
        'last_pressure_bias_measured', 'ASVCO2_ATRH_serial',
        'ASVCO2_O2_serial', 'ASVCO2_manufacturer',
        'secondaryspan_calibrated_spanserialnumber',  #new for firmware v1.9
        'ASVCO2_secondaryspan_serialnumber',  #new for firmware v1.9
        'ASVCO2_span_serialnumber',  #new for firmware v1.9
        'last_secondaryspan_calibration']  #new for firmware v1.9
    list_of_flag_names = ['ASVCO2_GENERAL_ERROR_FLAGS', 'ASVCO2_ZERO_ERROR_FLAGS',
    'ASVCO2_SPAN_ERROR_FLAGS', 'ASVCO2_SECONDARYSPAN_ERROR_FLAGS',
    'ASVCO2_EQUILIBRATEANDAIR_ERROR_FLAGS', 'ASVCO2_RTC_ERROR_FLAGS',
    'ASVCO2_FLOWCONTROLLER_FLAGS', 'ASVCO2_LICOR_FLAGS']
    reordered_cols += list_of_flag_names
    super_big_val_df = super_big_val_df[reordered_cols]
    if ( len(col_o) == len(reordered_cols) ):
        print('length sanity check passed')
    else:
        print('length sanity check failed')
    for name in col_o:
        if ( name not in reordered_cols):
            print(f'{name} not found in cols')
    
    return super_big_val_df

def val_df_rename_columns(super_big_val_df):
    #### Rename the stuff ####
    ERDDAP_val_rename_dict = {'mode':'INSTRUMENT_STATE','datetime':'time','serial':'SN_ASVCO2',\
    'Li_Temp_ave':'CO2DETECTOR_TEMP_MEAN_ASVCO2',\
    'Li_Temp_sd':'CO2DETECTOR_TEMP_STDDEV_ASVCO2',\
    'Li_Pres_ave':'CO2DETECTOR_PRESS_UNCOMP_MEAN_ASVCO2',\
    'Li_Pres_sd':'CO2DETECTOR_PRESS_UNCOMP_STDDEV_ASVCO2',\
    'time_of_report_command':'REPORT_COMMAND_TIME_ASVCO2',\
    'CO2_ave':'CO2_MEAN_ASVCO2','CO2_sd':'CO2_STDDEV_ASVCO2',\
    'O2_ave':'O2_MEAN_ASVCO2','O2_sd':'O2_STDDEV_ASVCO2',\
    'RH_ave':'RH_MEAN_ASVCO2','RH_sd':'RH_STDDEV_ASVCO2',\
    'RH_T_ave':'RH_TEMP_MEAN_ASVCO2','RH_T_sd':'RH_TEMP_STDDEV_ASVCO2',\
    'Flow_ave':'FLOW_MEAN_ASVCO2','Flow_sd':'FLOW_STDDEV_ASVCO2',\
    'residual_ave':'CO2_RESIDUAL_MEAN_ASVCO2',\
    'residual_sd':'CO2_RESIDUAL_STDDEV_ASVCO2',\
    'residual_dry_ave':'CO2_DRY_RESIDUAL_MEAN_ASVCO2',\
    'residual_Tcorr_ave':'CO2_DRY_TCORR_RESIDUAL_MEAN_ASVCO2',\
    'residual_Tcorr_sd':'CO2_DRY_TCORR_RESIDUAL_STDDEV_ASVCO2',\
    'gas_standard':'CO2_REF_LAB',\
    'gas_standard_tag':'CO2_DRY_RESIDUAL_REF_LAB_TAG',\
    'Num_samples':'NUM_SAMPLES',\
    'ver':'ASVCO2_firmware','sample':'sampling_frequency',\
    'LI_ver':'CO2DETECTOR_firmware','LI_ser':'CO2DETECTOR_serialnumber',\
    'ASVCO2_secondaryspan2_concentration':'ASVCO2_secondaryspan_concentration',\
    'ASVCO2_ATRH_serial':'ASVCO2_ATRH_serialnumber',\
    'ASVCO2_O2_serial':'ASVCO2_O2_serialnumber',\
    'ASVCO2_manufacturer':'ASVCO2_vendor_name',\
    'CO2kzero':'CO2DETECTOR_ZERO_COEFFICIENT_ASVCO2',\
    'CO2kspan':'CO2DETECTOR_SPAN_COEFFICIENT_ASVCO2',\
    'CO2kspan2':'CO2DETECTOR_SECONDARY_COEFFICIENT_ASVCO2',\
    'CO2_dry_ave':'CO2_DRY_MEAN_ASVCO2',\
    'CO2_dry_Tcorr_ave':'CO2_DRY_TCORR_MEAN_ASVCO2',\
    'CO2_dry_residual_ave_of_ave':'CO2_DRY_RESIDUAL_REF_LAB_MEAN_ASVCO2',\
    'CO2_dry_residual_sd_of_ave':'CO2_DRY_RESIDUAL_REF_LAB_STDDEV_ASVCO2',\
    'CO2_dry_Tcorr_residual_ave_of_ave':'CO2_DRY_TCORR_RESIDUAL_REF_LAB_MEAN_ASVCO2',\
    'CO2_dry_Tcorr_residual_sd_of_ave':'CO2_DRY_TCORR_RESIDUAL_REF_LAB_STDDEV_ASVCO2',\
    'CO2_dry_residual_max_of_ave':'CO2_DRY_RESIDUAL_REF_LAB_MAX_ASVCO2',\
    'CO2_dry_Tcorr_residual_max_of_ave':'CO2_DRY_TCORR_RESIDUAL_REF_LAB_MAX_ASVCO2',\
    'out_of_range':'OUT_OF_RANGE','out_of_range_reason':'OUT_OF_RANGE_REASON'}
    
    super_big_val_df = super_big_val_df.rename(columns=ERDDAP_val_rename_dict)

    return super_big_val_df

def val_df_add_gas_standard_tag_column(super_big_val_df):
    
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    json_file = open(PROJECT_ROOT + '/code/post_processing/config/gas_standard_tag_ranges.json','r',encoding='utf-8')
    ppm_range2tag_name = json.load(json_file)
    json_file.close()

    #super_big_val_df['gas_standard_tag']=['']*len(super_big_val_df)

    # For some reason, the above code does not write changes to the 'gas_standard_tag'
    # column, so this code was re-written so that it will now work.
    gas_standard_tag_list = []
    for idx, row in super_big_val_df.iterrows():
        in_range = False
        for d in ppm_range2tag_name:
            if ( row['gas_standard'] >= d['min'] and \
                row['gas_standard'] <= d['max'] ):
                gas_standard_tag_list.append(d['tag']) 
                in_range = True
                break
        if not in_range:
            gas_standard_tag_list.append('unknown')

    # first_entry=super_big_val_df['gas_standard_tag'].iloc[0]
    # print(f'first_entry = {first_entry}')

    super_big_val_df['gas_standard_tag'] = gas_standard_tag_list

    return super_big_val_df

def add_final_summary_rows(super_big_val_df):
    #if only the last row is copied, pandas will return series,
    #so, copy the last two rows and manipulate values
    last_two_rows = super_big_val_df.iloc[-2:,:].copy().reset_index()

    final_ts_str = super_big_val_df['datetime'].iloc[-1]
    print(f'finat_ts_str = {final_ts_str}')
    final_ts_str = final_ts_str.strip()
    #last_whole_sec_idx = re.search(r'\dZ',final_ts_str).span()[0]  # whole seconds here
    #floored_final_ts_str = final_ts_str[:last_whole_sec_idx] + 'Z'
    floored_final_ts_str = final_ts_str  # unusual for this case
    final_ts_plus_1sec = dt.datetime.strptime(floored_final_ts_str, '%Y-%m-%dT%H:%M:%SZ') + \
        dt.timedelta(0,1)
    final_ts_plus_2sec = dt.datetime.strptime(floored_final_ts_str, '%Y-%m-%dT%H:%M:%SZ') + \
        dt.timedelta(0,2)

    # ftp1s and ftps2s are final time plus 1 sec. and 2 sec., respectively.
    ftp1s=final_ts_plus_1sec.strftime(' %Y-%m-%dT%H:%M:%S') + 'Z'
    ftp2s=final_ts_plus_2sec.strftime(' %Y-%m-%dT%H:%M:%S') + 'Z'

    mask_EPOFF_0_thru_750 = (super_big_val_df['mode'] == 'EPOFF') & \
        (super_big_val_df['gas_standard'] >= 0.0) & \
        (super_big_val_df['gas_standard'] <= 750.0)

    mask_APOFF_0_thru_750 = (super_big_val_df['mode'] == 'APOFF') & \
        (super_big_val_df['gas_standard'] >= 0.0) & \
        (super_big_val_df['gas_standard'] <= 750.0)

    list_of_cols_for_stats = ['residual_dry_ave','residual_sd',\
        'residual_Tcorr_ave','residual_Tcorr_sd',\
        'Li_Temp_ave','Li_Temp_sd','Li_Pres_ave','Li_Pres_sd',\
        'O2_ave','O2_sd','RH_ave','RH_sd','RH_T_ave', 'RH_T_sd',
        'Flow_ave', 'Flow_sd']
    df_EPOFF_0_thru_750 = super_big_val_df[list_of_cols_for_stats].\
        loc[mask_EPOFF_0_thru_750].copy()

    df_APOFF_0_thru_750 = super_big_val_df[list_of_cols_for_stats].\
        loc[mask_APOFF_0_thru_750].copy()

    #EPOFF_desc = df_EPOFF_0_thru_750.describe()
    #APOFF_desc = df_APOFF_0_thru_750.describe()
    # pd.set_option('max_columns',None)
    # print('df_EPOFF_0_thry_750 is like...')
    # print(df_EPOFF_0_thru_750.head())
    # print('df_APOFF_0_thry_750 is like...')
    # print(df_APOFF_0_thru_750.head())
    # pd.reset_option('max_columns')
    EPOFF_mean = df_EPOFF_0_thru_750.mean()
    APOFF_mean = df_APOFF_0_thru_750.mean()
    EPOFF_std = df_EPOFF_0_thru_750.std(ddof=0)
    APOFF_std = df_APOFF_0_thru_750.std(ddof=0)
    EPOFF_max = df_EPOFF_0_thru_750.max()
    APOFF_max = df_APOFF_0_thru_750.max()

    change={'mode':['EPOFF Summary','APOFF Summary'],\
        'datetime':[ftp1s,ftp2s], 'residual_ave':[np.NaN,np.NaN],\
        'residual_sd':[np.NaN,np.NaN],\
        'gas_standard':[np.NaN,np.NaN],\
        'gas_standard_tag':['0 thru 750 ppm Range']*2,
        'Li_Temp_ave':[EPOFF_mean.loc['Li_Temp_ave'],\
            APOFF_mean.loc['Li_Temp_ave']],\
        'Li_Temp_sd':[EPOFF_std.loc['Li_Temp_ave'],\
            APOFF_std.loc['Li_Temp_ave']],\
        'Li_Pres_ave':[EPOFF_mean.loc['Li_Pres_ave'],\
            APOFF_mean.loc['Li_Pres_ave']],\
        'Li_Pres_sd':[EPOFF_std.loc['Li_Pres_ave'],\
            APOFF_std.loc['Li_Pres_ave']],\
        'CO2_ave':[np.NaN,np.NaN], 'CO2_sd':[np.NaN,np.NaN],\
        'O2_ave':[EPOFF_mean.loc['O2_ave'],\
            APOFF_mean.loc['O2_ave']],\
        'O2_sd':[EPOFF_std.loc['O2_ave'],\
            APOFF_std.loc['O2_ave']],\
        'RH_ave':[EPOFF_mean.loc['RH_ave'],\
            APOFF_mean.loc['RH_ave']],\
        'RH_sd':[EPOFF_std.loc['RH_ave'],\
            APOFF_std.loc['O2_ave']],\
        'RH_T_ave':[EPOFF_mean.loc['RH_T_ave'],\
            APOFF_mean.loc['RH_T_ave']],\
        'RH_T_sd':[EPOFF_std.loc['RH_T_ave'],\
            APOFF_std.loc['RH_T_ave']],\
        'Flow_ave':[EPOFF_mean.loc['Flow_ave'],\
            APOFF_mean.loc['Flow_ave']],
        'Flow_sd':[EPOFF_std.loc['Flow_ave'],\
            APOFF_std.loc['Flow_ave']],\
        'CO2_dry_ave':[np.NaN,np.NaN],\
        'CO2_dry_Tcorr_ave':[np.NaN,np.NaN],\
        'CO2_dry_residual_ave_of_ave':[EPOFF_mean.loc['residual_dry_ave'],\
            APOFF_mean.loc['residual_dry_ave']],\
        'CO2_dry_residual_sd_of_ave':[EPOFF_std.loc['residual_dry_ave'],\
            APOFF_std.loc['residual_dry_ave']],\
        'CO2_dry_Tcorr_residual_ave_of_ave':[EPOFF_mean.loc['residual_Tcorr_ave'],\
            APOFF_mean.loc['residual_Tcorr_ave']],\
        'CO2_dry_Tcorr_residual_sd_of_ave':[EPOFF_std.loc['residual_Tcorr_ave'],\
            APOFF_std.loc['residual_Tcorr_ave']],
        'CO2_dry_residual_max_of_ave':[EPOFF_max.loc['residual_dry_ave'],\
            APOFF_max.loc['residual_dry_ave']],
        'CO2_dry_Tcorr_residual_max_of_ave':[EPOFF_max.loc['residual_Tcorr_ave'],\
            APOFF_max.loc['residual_Tcorr_ave']],
        'Num_samples':[len(df_EPOFF_0_thru_750),len(df_APOFF_0_thru_750)]}

    last_two_rows.update(pd.DataFrame(change))

    list_of_flag_names = ['ASVCO2_GENERAL_ERROR_FLAGS', 'ASVCO2_ZERO_ERROR_FLAGS',
    'ASVCO2_SPAN_ERROR_FLAGS', 'ASVCO2_SECONDARYSPAN_ERROR_FLAGS',
    'ASVCO2_EQUILIBRATEANDAIR_ERROR_FLAGS', 'ASVCO2_RTC_ERROR_FLAGS',
    'ASVCO2_FLOWCONTROLLER_FLAGS', 'ASVCO2_LICOR_FLAGS']
    
    # Unfortunatley, df.update(another_df) arbitrarily avoids NaN values. So force NaN.
    list_of_NaN_cols = ['residual_ave','residual_sd','residual_dry_ave',
        'residual_Tcorr_ave','residual_Tcorr_sd','gas_standard','CO2_ave',\
        'CO2_sd','CO2_dry_ave','CO2_dry_Tcorr_ave']
    list_of_NaN_cols += list_of_flag_names

    for col in list_of_NaN_cols:
        last_two_rows[col]=[np.NaN,np.NaN]

    super_big_val_df = super_big_val_df.append(last_two_rows,ignore_index=True)

    return super_big_val_df

def add_final_summary_rows_v2(super_big_val_df):

    # read in json file from config folder to get the gas standard tag ranges for the summary
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    json_file = open(PROJECT_ROOT + '/code/post_processing/config/summary_gas_standard_tag_ranges.json','r',encoding='utf-8')
    summary_gas_standard_tag_ranges = json.load(json_file)
    json_file.close()
    num_ranges = len(summary_gas_standard_tag_ranges)

    #if only the last row is copied, pandas will return series,
    #so, copy the last two rows and manipulate values
    #last_two_rows = super_big_val_df.iloc[-2:,:].copy().reset_index()
    last_twelve_or_more_rows = super_big_val_df.iloc[-2*num_ranges:,:].copy().reset_index()

    final_ts_str = super_big_val_df['datetime'].iloc[-1]
    print(f'finat_ts_str = {final_ts_str}')
    final_ts_str = final_ts_str.strip()
    #last_whole_sec_idx = re.search(r'\dZ',final_ts_str).span()[0]  # whole seconds here
    #floored_final_ts_str = final_ts_str[:last_whole_sec_idx] + 'Z'
    floored_final_ts_str = final_ts_str  # unusual for this case

    list_of_cols_for_stats = ['residual_dry_ave','residual_sd',\
        'residual_Tcorr_ave','residual_Tcorr_sd',\
        'Li_Temp_ave','Li_Temp_sd','Li_Pres_ave','Li_Pres_sd',\
        'O2_ave','O2_sd','RH_ave','RH_sd','RH_T_ave', 'RH_T_sd',
        'Flow_ave', 'Flow_sd']

    list_of_extra_ts=[]
    list_of_changes=[]
    for idx in range(0,num_ranges):
        final_ts_plus_x_sec = dt.datetime.strptime(floored_final_ts_str, '%Y-%m-%dT%H:%M:%SZ') + \
            dt.timedelta(0,2*idx+1)
        final_ts_plus_x_plus_1_sec = dt.datetime.strptime(floored_final_ts_str, '%Y-%m-%dT%H:%M:%SZ') + \
            dt.timedelta(0,2*idx+2)
        ftp_idx_s = final_ts_plus_x_sec.strftime(' %Y-%m-%dT%H:%M:%S') + 'Z'
        ftp_idx_plus_1_s = final_ts_plus_x_plus_1_sec.strftime(' %Y-%m-%dT%H:%M:%S') + 'Z'

        list_of_extra_ts.append(ftp_idx_s)
        list_of_extra_ts.append(ftp_idx_plus_1_s)

        upper_limit = summary_gas_standard_tag_ranges[idx]['upper']
        lower_limit = summary_gas_standard_tag_ranges[idx]['lower']

        mask_EPOFF_lower_thru_upper = (super_big_val_df['mode'] == 'EPOFF') & \
            (super_big_val_df['gas_standard'] >= lower_limit) & \
            (super_big_val_df['gas_standard'] < upper_limit)

        mask_APOFF_lower_thru_upper = (super_big_val_df['mode'] == 'APOFF') & \
            (super_big_val_df['gas_standard'] >= lower_limit) & \
            (super_big_val_df['gas_standard'] < upper_limit)
        # not big_dry_df.empty and not big_stats_df.empty
        if ( not super_big_val_df.loc[mask_EPOFF_lower_thru_upper].empty and \
            not super_big_val_df.loc[mask_APOFF_lower_thru_upper].empty ):

            df_EPOFF_lower_thru_upper = super_big_val_df[list_of_cols_for_stats].\
                loc[mask_EPOFF_lower_thru_upper].copy()

            df_APOFF_lower_thru_upper = super_big_val_df[list_of_cols_for_stats].\
                loc[mask_APOFF_lower_thru_upper].copy()
        else:
            raise Exception(f"""No gas standards within range of {upper_limit} and {lower_limit}
                ppm found in .\config\summary_gas_standard_tag_ranges.json""")

        EPOFF_mean = df_EPOFF_lower_thru_upper.mean()
        APOFF_mean = df_APOFF_lower_thru_upper.mean()
        EPOFF_std = df_EPOFF_lower_thru_upper.std(ddof=0)
        APOFF_std = df_APOFF_lower_thru_upper.std(ddof=0)
        EPOFF_max = df_EPOFF_lower_thru_upper.max()
        APOFF_max = df_APOFF_lower_thru_upper.max()
    
        change_entry={'mode':['EPOFF Summary','APOFF Summary'],\
        'datetime':[ftp_idx_s,ftp_idx_plus_1_s], 'residual_ave':[np.NaN,np.NaN],\
        'residual_sd':[np.NaN,np.NaN],\
        'gas_standard':[np.NaN,np.NaN],\
        'gas_standard_tag':[summary_gas_standard_tag_ranges[idx]['tag']]*2,
        'Li_Temp_ave':[EPOFF_mean.loc['Li_Temp_ave'],\
            APOFF_mean.loc['Li_Temp_ave']],\
        'Li_Temp_sd':[EPOFF_std.loc['Li_Temp_ave'],\
            APOFF_std.loc['Li_Temp_ave']],\
        'Li_Pres_ave':[EPOFF_mean.loc['Li_Pres_ave'],\
            APOFF_mean.loc['Li_Pres_ave']],\
        'Li_Pres_sd':[EPOFF_std.loc['Li_Pres_ave'],\
            APOFF_std.loc['Li_Pres_ave']],\
        'CO2_ave':[np.NaN,np.NaN], 'CO2_sd':[np.NaN,np.NaN],\
        'O2_ave':[EPOFF_mean.loc['O2_ave'],\
            APOFF_mean.loc['O2_ave']],\
        'O2_sd':[EPOFF_std.loc['O2_ave'],\
            APOFF_std.loc['O2_ave']],\
        'RH_ave':[EPOFF_mean.loc['RH_ave'],\
            APOFF_mean.loc['RH_ave']],\
        'RH_sd':[EPOFF_std.loc['RH_ave'],\
            APOFF_std.loc['O2_ave']],\
        'RH_T_ave':[EPOFF_mean.loc['RH_T_ave'],\
            APOFF_mean.loc['RH_T_ave']],\
        'RH_T_sd':[EPOFF_std.loc['RH_T_ave'],\
            APOFF_std.loc['RH_T_ave']],\
        'Flow_ave':[EPOFF_mean.loc['Flow_ave'],\
            APOFF_mean.loc['Flow_ave']],
        'Flow_sd':[EPOFF_std.loc['Flow_ave'],\
            APOFF_std.loc['Flow_ave']],\
        'CO2_dry_ave':[np.NaN,np.NaN],\
        'CO2_dry_Tcorr_ave':[np.NaN,np.NaN],\
        'CO2_dry_residual_ave_of_ave':[EPOFF_mean.loc['residual_dry_ave'],\
            APOFF_mean.loc['residual_dry_ave']],\
        'CO2_dry_residual_sd_of_ave':[EPOFF_std.loc['residual_dry_ave'],\
            APOFF_std.loc['residual_dry_ave']],\
        'CO2_dry_Tcorr_residual_ave_of_ave':[EPOFF_mean.loc['residual_Tcorr_ave'],\
            APOFF_mean.loc['residual_Tcorr_ave']],\
        'CO2_dry_Tcorr_residual_sd_of_ave':[EPOFF_std.loc['residual_Tcorr_ave'],\
            APOFF_std.loc['residual_Tcorr_ave']],
        'CO2_dry_residual_max_of_ave':[EPOFF_max.loc['residual_dry_ave'],\
            APOFF_max.loc['residual_dry_ave']],
        'CO2_dry_Tcorr_residual_max_of_ave':[EPOFF_max.loc['residual_Tcorr_ave'],\
            APOFF_max.loc['residual_Tcorr_ave']],
        'Num_samples':[len(df_EPOFF_lower_thru_upper),len(df_APOFF_lower_thru_upper)]}

        list_of_changes.append(change_entry)

    # transform list_of_changes from a list of dictionary into a single large dictionary for
    # integration into pandas
    these_keys = list(list_of_changes[0].keys())
    print(these_keys)
    change = {}
    for k in these_keys:
        change[k] = []
    for item in list_of_changes:
        for k in these_keys:
            change[k] += item[k]
            #change[k] = change[k] + item[k]

    #last_two_rows.update(pd.DataFrame(change))
    #last_twelve_or_more_rows.update(pd.DataFrame(change),errors='raise')

    # For unknown reasons, the last_twelve_or_more_rows.update() was failing.
    # Instead, force a manual replacement below.
    temp_df = pd.DataFrame(change)
    print(f'index for temp_df is {temp_df.index.values}')
    print(f'index for last_twelve_or_more_rows is {last_twelve_or_more_rows.index.values}')
    for col in last_twelve_or_more_rows.columns:
        if col in temp_df.columns:
            #last_twelve_or_more_rows[col].fillna(temp_df[col], inplace=True)
            last_twelve_or_more_rows[col] = temp_df[col].copy()

    del temp_df

    list_of_flag_names = ['ASVCO2_GENERAL_ERROR_FLAGS', 'ASVCO2_ZERO_ERROR_FLAGS',
    'ASVCO2_SPAN_ERROR_FLAGS', 'ASVCO2_SECONDARYSPAN_ERROR_FLAGS',
    'ASVCO2_EQUILIBRATEANDAIR_ERROR_FLAGS', 'ASVCO2_RTC_ERROR_FLAGS',
    'ASVCO2_FLOWCONTROLLER_FLAGS', 'ASVCO2_LICOR_FLAGS']
    
    # Unfortunatley, df.update(another_df) arbitrarily avoids NaN values. So force NaN.
    list_of_NaN_cols = ['residual_ave','residual_sd','residual_dry_ave',
        'residual_Tcorr_ave','residual_Tcorr_sd','gas_standard','CO2_ave',\
        'CO2_sd','CO2_dry_ave','CO2_dry_Tcorr_ave']
    list_of_NaN_cols += list_of_flag_names

    for col in list_of_NaN_cols:
        last_twelve_or_more_rows[col] = [np.NaN]*(2*num_ranges)

    print("!### This is the change !###")
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(change)
    print("!### This is last_twelve_or_more_rows after update() !###")
    print(last_twelve_or_more_rows[['datetime'] + list_of_cols_for_stats])

    #super_big_val_df = super_big_val_df.append(last_two_rows,ignore_index=True)
    super_big_val_df = super_big_val_df.append(last_twelve_or_more_rows,ignore_index=True)

    return super_big_val_df

def val_fix_nan_in_dict(bigDictionary):
    # It is expected that bigDictionary is a nested dictionary
    # with two keys referencing a list. Some of the entries of
    # the list might be strings of "nan" which need to be replaced
    # with the float version of "nan".
    for k1, d in bigDictionary.items():
        for k2, list1 in d.items():
            for idx, item in enumerate(list1):
                if ( item == "nan"):
                    bigDictionary[k1][k2][idx] = float(item)
    return bigDictionary

def val_fix_span_coeff_in_dict(bigDictionary):
    #k0 = list(bigDictionary.keys())[0]
    for k, val in bigDictionary.items():
        if ( 'CO2kzero' not in bigDictionary[k]):
            bigDictionary[k]['CO2kzero'] = [np.NaN]*10
        if ( 'CO2kspan' not in bigDictionary[k]):
            bigDictionary[k]['CO2kspan'] = [np.NaN]*10
        if ( 'CO2kspan2' not in bigDictionary[k]):
            bigDictionary[k]['CO2kspan2'] = [np.NaN]*10
    return bigDictionary

def pressure_range_checks(on_state_name,off_state_name,Pdiff_limit,super_big_val_df):
    f_on = super_big_val_df['mode'] == on_state_name
    f_off = super_big_val_df['mode'] == off_state_name
    P_on = super_big_val_df.loc[f_on,'Li_Pres_ave'].to_list()
    P_off =super_big_val_df.loc[f_off,'Li_Pres_ave'].to_list()
    P_diff = []
    new_reasons = []
    #print(f'len(P_apon) = {len(P_apon)}')
    #print(f'len(P_apoff) = {len(P_apoff)}')
    min_len = min(len(P_on),len(P_off))
    for idx in range(0,min_len):
        P_diff.append(P_on[idx]-P_off[idx])
        if ( P_diff[idx] < Pdiff_limit ):
            new_reasons.append(f"""The pressure difference between {on_state_name} 
            and {off_state_name} is not greater than {Pdiff_limit}kPa. """)
        else:
            new_reasons.append('')
    return new_reasons, f_off

def val_df_add_range_check(super_big_val_df):
    # create two new columns, out_of_range and out_of_range_reason
    N_rows = len(super_big_val_df)

    # 1 - something was out of range, 0 - within range
    super_big_val_df['out_of_range']=[0]*N_rows
    super_big_val_df['out_of_range_reason']=['']*N_rows
    #last_two_rows = super_big_val_df.iloc[-2:,:]
    
    # Range check for APOFF and APON here
    new_reasons, f_apoff = pressure_range_checks("APON","APOFF",2.5,super_big_val_df)
    
    reasons = super_big_val_df.loc[f_apoff,'out_of_range_reason'].to_list()
    out_of_range_codes = super_big_val_df.loc[f_apoff,'out_of_range'].to_list()
    for idx, item in enumerate(reasons):
        reasons[idx] += new_reasons[idx]
        if len(new_reasons[idx]) != 0:
            out_of_range_codes[idx] = 1  # 1 - something was out of range, 0 - within range

    super_big_val_df.loc[f_apoff,'out_of_range_reason'] = reasons
    super_big_val_df.loc[f_apoff,'out_of_range'] = out_of_range_codes

    # Range check for EPOFF and EPON
    new_reasons, f_epoff = pressure_range_checks("EPON","EPOFF",2.5,super_big_val_df)

    reasons = super_big_val_df.loc[f_epoff,'out_of_range_reason'].to_list()
    out_of_range_codes = super_big_val_df.loc[f_epoff,'out_of_range'].to_list()
    for idx, item in enumerate(reasons):
        reasons[idx] += new_reasons[idx]
        if len(new_reasons[idx]) != 0:
            out_of_range_codes[idx] = 1  # 1 - something was out of range, 0 - within range

    super_big_val_df.loc[f_epoff,'out_of_range_reason'] = reasons
    super_big_val_df.loc[f_epoff,'out_of_range'] = out_of_range_codes

    # Range check for SPOFF and SPON
    new_reasons, f_spoff = pressure_range_checks("SPON","SPOFF",2.0,super_big_val_df)

    reasons = super_big_val_df.loc[f_spoff,'out_of_range_reason'].to_list()
    out_of_range_codes = super_big_val_df.loc[f_spoff,'out_of_range'].to_list()
    for idx, item in enumerate(reasons):
        reasons[idx] += new_reasons[idx]
        if len(new_reasons[idx]) != 0:
            out_of_range_codes[idx] = 1  # 1 - something was out of range, 0 - within range

    super_big_val_df.loc[f_spoff,'out_of_range_reason'] = reasons
    super_big_val_df.loc[f_spoff,'out_of_range'] = out_of_range_codes

    # Range check for ZPOFF and ZPON
    new_reasons, f_zpoff = pressure_range_checks("ZPON","ZPOFF",0.0,super_big_val_df)

    reasons = super_big_val_df.loc[f_zpoff,'out_of_range_reason'].to_list()
    out_of_range_codes = super_big_val_df.loc[f_zpoff,'out_of_range'].to_list()
    for idx, item in enumerate(reasons):
        reasons[idx] += new_reasons[idx]
        if len(new_reasons[idx]) != 0:
            out_of_range_codes[idx] = 1  # 1 - something was out of range, 0 - within range

    super_big_val_df.loc[f_zpoff,'out_of_range_reason'] = reasons
    super_big_val_df.loc[f_zpoff,'out_of_range'] = out_of_range_codes

    # Do relative humidity check on standard deviation, use 1% relative humidity tolerance
    new_reasons = []
    RH_sd_list = super_big_val_df.loc[:,'RH_sd'].to_list()
    len_RH_sd = len(RH_sd_list)
    for idx in range(0,len_RH_sd):
        if ( RH_sd_list[idx] > 1.0 ):
            new_reasons.append(f"The standard deviation of relative humidity exceeded 1.0%. ")
        else:
            new_reasons.append('')
    # rh_mean_mean = super_big_val_df['RH_ave'].mean()
    # ones = pd.Series([1]*len(super_big_val_df['RH_ave']))
    # RH_mean_delta_from_RH_mean_mean = (super_big_val_df['RH_ave']-ones*rh_mean_mean).to_list()
    # for rh_delta, idx  in enumerate(RH_mean_delta_from_RH_mean_mean):
    #     if ( rh_delta > 3.0 or rh_delta < -3.0 ):
    #         new_reasons.append(f"""The difference between the average relative humidity during this state and the average 
    #         of all average relative humidities during this period exceeded 3.0%.""")
    #     else:
    #         new_reasons.append('')

    reasons = super_big_val_df.loc[:,'out_of_range_reason'].to_list()
    out_of_range_codes = super_big_val_df.loc[:,'out_of_range'].to_list()
    for idx, item in enumerate(reasons):
        reasons[idx] += new_reasons[idx]
        if len(new_reasons[idx]) != 0:
            out_of_range_codes[idx] = 1  # 1 - something was out of range, 0 - within range

    super_big_val_df.loc[:,'out_of_range_reason'] = reasons
    super_big_val_df.loc[:,'out_of_range'] = out_of_range_codes

    # take output from range check here
    # super_big_val_df.loc[N_rows-2:N_rows-1,'out_of_range'] = [False]*2
    # super_big_val_df.loc[N_rows-2:N_rows-1,'out_of_range_reason'] = ['']*2
    
    return super_big_val_df

def val_update_missing_v1_8(config_stuff,sn):

    list_of_applicable_sn = [
        "3CADC7573",
        "3CADC7565",
        "3CA8A2538",
        "3CA8A2535",
        "3CA8A2533",
        "3CADC7571",
        "3CB942928",
        "3CB94292E",
        "3CB94292C",
        "3CD6D1DD5"]

    if ( sn in list_of_applicable_sn ):
        # read in json file from config folder and look up parameters by serial number
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_file = open(PROJECT_ROOT + '/code/post_processing/config/missing_from_Saildrone_v1_8.json','r',encoding='utf-8')
        missing_from_Saildrone_v1_8 = json.load(json_file)
        json_file.close()

        # maybe_missing = {'secondaryspan_calibrated_temperature': span2_temp,  # unique
        # 'secondaryspan_calibrated_spanconcentration': 502.76,
        # 'last_secondaryspan_temperaturedependantslope': '2021-02-22T00:00:00Z',  
        # 'secondaryspan_temperaturedependantslope':float(span2_20deg_cal2_temp_licor.co2kspan2.values),  # unique
        # 'secondaryspan_temperaturedependantslopefit':float(oventesta_licor_cal2_span2.R2.values),  # unique
        # 'secondaryspan_calibrated_rh': 1.27283262,
        # 'ASVCO2_secondaryspan2_concentration': 1994.25,
        # 'last_ASVCO2_validation': this_last_ASVCO2_validation,  # unique
        # 'pressure_bias': np.NaN,
        # 'last_pressure_bias_measured' : '', # format of '0001-01-01T00:00:00Z',
        # 'ASVCO2_ATRH_serial': '', # format of 'XXXXXXXXX',
        # 'ASVCO2_O2_serial':'EK59499036', # unique
        # 'ASVCO2_manufacturer': 'PMEL',
        # 'secondaryspan_calibrated_spanserialnumber':'JA02448',
        # 'ASVCO2_secondaryspan_serialnumber':'CB11490',
        # 'ASVCO2_span_serialnumber':'CC738196',
        # 'last_secondaryspan_calibration':'2021-02-22T00:00:00Z'}

        maybe_missing = missing_from_Saildrone_v1_8[sn]
        for k, v in config_stuff.items():
            for kk, vv in maybe_missing.items():
                if (kk not in config_stuff[k]):
                    config_stuff[k][kk] = vv
        
    else:
        raise Exception (f'the serial number {sn} is not in the list of applicable serial numbers')

    return config_stuff

def all_update_missing_v1_8(sys_rep,sn):

    list_of_applicable_sn = [
        "3CADC7573",
        "3CADC7565",
        "3CA8A2538",
        "3CA8A2535",
        "3CA8A2533",
        "3CADC7571",
        "3CB942928",
        "3CB94292E",
        "3CB94292C",
        "3CD6D1DD5"]

    if ( sn in list_of_applicable_sn ):
        # read in json file from config folder and look up parameters by serial number
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_file = open(PROJECT_ROOT + '/code/post_processing/config/missing_from_Saildrone_v1_8.json','r',encoding='utf-8')
        missing_from_Saildrone_v1_8 = json.load(json_file)
        json_file.close()

        # maybe_missing = {'secondaryspan_calibrated_temperature': span2_temp,  # unique
        # 'secondaryspan_calibrated_spanconcentration': 502.76,
        # 'last_secondaryspan_temperaturedependantslope': '2021-02-22T00:00:00Z',  
        # 'secondaryspan_temperaturedependantslope':float(span2_20deg_cal2_temp_licor.co2kspan2.values),  # unique
        # 'secondaryspan_temperaturedependantslopefit':float(oventesta_licor_cal2_span2.R2.values),  # unique
        # 'secondaryspan_calibrated_rh': 1.27283262,
        # 'ASVCO2_secondaryspan2_concentration': 1994.25,
        # 'last_ASVCO2_validation': this_last_ASVCO2_validation,  # unique
        # 'pressure_bias': np.NaN,
        # 'last_pressure_bias_measured' : '', # format of '0001-01-01T00:00:00Z',
        # 'ASVCO2_ATRH_serial': '', # format of 'XXXXXXXXX',
        # 'ASVCO2_O2_serial':'EK59499036', # unique
        # 'ASVCO2_manufacturer': 'PMEL',
        # 'secondaryspan_calibrated_spanserialnumber':'JA02448',
        # 'ASVCO2_secondaryspan_serialnumber':'CB11490',
        # 'ASVCO2_span_serialnumber':'CC738196',
        # 'last_secondaryspan_calibration':'2021-02-22T00:00:00Z'}

        maybe_missing = missing_from_Saildrone_v1_8[sn]
        for kk, vv in maybe_missing.items():
                if (kk not in sys_rep):
                    sys_rep[kk] = vv
        
    else:
        raise Exception (f'the serial number {sn} is not in the list of applicable serial numbers')

    return sys_rep

def load_Val_file(val_filename,big_dry_df=pd.DataFrame(),\
    big_stats_df=pd.DataFrame(),big_flags_df=pd.DataFrame(),\
    big_coeff_sync_df=pd.DataFrame()):

    #### load_Val_File_into_dicts() is useful for validation datasets in 2021 ####
    # bigDictionary, config_stuff = load_Val_File_into_dicts(val_filename)
    #### or
    # bigDictionary, config_stuff, mode_and_gas_stuff, flush_stuff = \
    #     load_Val_File_into_dicts_v3(validation_text_filename,timestamp_mode='Unix epoch, days')

    #### load_Val_File_into_dicts_v3() is useful for validation datasets 2022 and later ####
    bigDictionary, config_stuff, mode_and_gas_stuff, flush_stuff = \
        load_Val_File_into_dicts_v3(val_filename)

    # pp = pprint.PrettyPrinter(indent=4)
    # pp.pprint(other_stuff)
    # pp.pprint(bigDictionary)

    # unique to Saildrone serial numbers where things like secondaryspan_calibrated_spanserialnumber
    # were not output by the microcontroller.
    this_sn = config_stuff[list(config_stuff.keys())[0]]['serial']
    config_stuff = val_update_missing_v1_8(config_stuff,this_sn)

    #### New stuff to fix "nan" issues found in data from 3CADC7565 ####
    bigDictionary = val_fix_nan_in_dict(bigDictionary)
    bDkeys = list(bigDictionary.keys())
    typeflow_ave = type(bigDictionary[bDkeys[0]]['Flow_ave'][0])
    flow_ave_example = bigDictionary[bDkeys[0]]['Flow_ave'][0]
    print(f'type of flow_ave bigDictionary = {typeflow_ave}')
    print(f'first entry of Flow_ave = {flow_ave_example}')

    # put config_stuff into bigDictionary
    for k, v in config_stuff.items():
        for kk, vv in v.items():
            bigDictionary[k][kk] = [vv]*10  # 10 total valve states, duplicate the values

    #deal with issues on missing entries of span coefficient, mostly at the first entry
    bigDictionary = val_fix_span_coeff_in_dict(bigDictionary)

    out = open("parsed_data_pascal_style.json", "w")
    json.dump(bigDictionary, out, indent=4, ensure_ascii=False, allow_nan=True) 
    out.close()

    list_of_val_df=[]
    for k, v in bigDictionary.items():
        list_of_val_df.append(pd.DataFrame(v))
    super_big_val_df = pd.concat(list_of_val_df,axis=0,ignore_index=True)
    #super_big_val_df = super_big_val_df.rename(columns={'datetime':'time'})
    print('### After pd.concat, first timestamp is = ',super_big_val_df.loc[0,'datetime'])
    
    if ( big_dry_df.empty or big_stats_df.empty or big_flags_df.empty or\
        big_coeff_sync_df.empty):
        super_big_val_df['CO2_dry_ave']=[np.NaN]*len(super_big_val_df)
        super_big_val_df['CO2_dry_Tcorr_ave']=[np.NaN]*len(super_big_val_df)
        super_big_val_df['CO2_dry_residual_ave_of_ave']=[np.NaN]*len(super_big_val_df)
        super_big_val_df['CO2_dry_residual_sd_of_ave']=[np.NaN]*len(super_big_val_df)
        super_big_val_df['CO2_dry_Tcorr_residual_ave_of_ave']=[np.NaN]*len(super_big_val_df)
        super_big_val_df['CO2_dry_Tcorr_residual_sd_of_ave']=[np.NaN]*len(super_big_val_df)
        super_big_val_df['CO2_dry_residual_max_of_ave']=[np.NaN]*len(super_big_val_df)
        super_big_val_df['CO2_dry_Tcorr_residual_max_of_ave']=[np.NaN]*len(super_big_val_df)
        super_big_val_df['residual_Tcorr_ave'] = [np.NaN]*len(super_big_val_df)
        super_big_val_df['residual_Tcorr_sd'] = [np.NaN]*len(super_big_val_df)
    elif ( not big_dry_df.empty and not big_stats_df.empty \
        and not big_flags_df.empty and not big_coeff_sync_df.empty):

        #### Merge in the dry CO2 data by timestamp from the dry dataframe #### 
        super_big_val_df = super_big_val_df.merge(big_dry_df, left_on='datetime',\
            right_on='TS',how='left',suffixes=('','_from_dry'))
        dry_rename = {'xCO2(dry)':'CO2_dry_ave'}
        super_big_val_df = super_big_val_df.rename(columns=dry_rename)

        #### Merge in the num samples data from the stats dataframe ####
        super_big_val_df = super_big_val_df.merge(big_stats_df[['Timestamp','Num_samples']],\
            left_on='datetime',right_on='Timestamp',how='left',suffixes=('',''))
        
        #super_big_val_df = super_big_val_df.drop(columns=[])

        #### Merge in the flags data from the big_flags_df dataframe ####
        super_big_val_df = super_big_val_df.merge(big_flags_df,\
            left_on='datetime',right_on='Timestamp',how='left',suffixes=('','_flg'))

        #### Overwrite the coefficient data 'CO2kzero', 'CO2kspan' and 'CO2kspan2' ####
        super_big_val_df = super_big_val_df.merge(big_coeff_sync_df,\
            left_on='datetime',right_on='Timestamp',how='left',suffixes=('','_sync'))
        super_big_val_df = super_big_val_df.drop(columns=['CO2kzero','CO2kspan',\
            'CO2kspan2','Timestamp_sync','mode_sync'])
        super_big_val_df = super_big_val_df.rename(columns={'CO2kzero_sync':'CO2kzero',
            'CO2kspan_sync':'CO2kspan', 'CO2kspan2_sync':'CO2kspan2'})
        # print('###! After merging big_coeff_df, first timestamp is = ',super_big_val_df.loc[0,'datetime'])

        print('#### After merge inside load_Val_file() ####')
        print(f'super_big_val_df.columns.values = {super_big_val_df.columns.values}')
    else: 
        raise Exception('STATS data provided but not DRY data or vice versa')

    # synced = super_big_val_df['CO2_dry_ave'] >= -1.0 #np.NaN  # why doesn't xCO2(dry) have _from_dry suffix?
    # pd.set_option('max_columns',None)
    # print('#### Check number of samples insertion ####')
    # print(super_big_val_df.head())
    # print('#### Check dry CO2 insertion ####')
    # print(super_big_val_df.loc[synced].head())
    # pd.reset_option('max_columns')
    # print('(((((((Check length of timestamps)))))))')
    # l1=len(super_big_val_df['datetime'].loc[0]);l2=len(big_dry_df['TS'].loc[0])
    # print(f'len(super_big_val timestamp)={l1}, len(dry_df timestamp)={l2}')

    super_big_val_df = val_df_add_gas_standard_tag_column(super_big_val_df)
    
    # print('Column Names before reordering are')
    # pp.print()

    # Used to just subtract by the reference gas, but not anymore
    #super_big_val_df['residual_ave']=super_big_val_df['CO2_ave']-super_big_val_df['gas_standard']
    #super_big_val_df = val_df_make_residual_column(super_big_val_df)\

    # super_big_val_df = val_df_make_temp_and_dry_correction(super_big_val_df,\
    #     big_stats_df)
    
    #update to v2, 11/1/2021
    super_big_val_df = val_df_make_temp_and_dry_correction_v2(super_big_val_df,\
        big_stats_df)

    print('#### After val_df_make_temp_and_dry_correction() inside load_Val_file() ####')
    print(f'super_big_val_df.columns.values = {super_big_val_df.columns.values}')

    #drop the new column, updated in val_update_xco2_10XX()
    #super_big_val_df = super_big_val_df.drop(columns=['CO2kspan2_new'])

    # Used to do residuals on wet xCO2 columns, but not anymore
    super_big_val_df = val_df_make_dry_residual_columns(super_big_val_df) 

    print('#### After val_df_make_dry_residual_columns() inside load_Val_file() ####')
    print(f'super_big_val_df.columns.values = {super_big_val_df.columns.values}')
    residual_Tcorr_min = super_big_val_df['residual_Tcorr_ave'].min()
    print(f'residual_Tcorr_min = {residual_Tcorr_min}')

    # Add in placeholder for summary columns for final summary
    # These will be populated in add_final_summary_rows()
    super_big_val_df['CO2_dry_residual_ave_of_ave']=[np.NaN]*len(super_big_val_df)
    super_big_val_df['CO2_dry_residual_sd_of_ave']=[np.NaN]*len(super_big_val_df) 
    super_big_val_df['CO2_dry_Tcorr_residual_ave_of_ave']=[np.NaN]*len(super_big_val_df)
    super_big_val_df['CO2_dry_Tcorr_residual_sd_of_ave']=[np.NaN]*len(super_big_val_df)
    super_big_val_df['CO2_dry_residual_max_of_ave']=[np.NaN]*len(super_big_val_df)  # added 1/24/2021
    super_big_val_df['CO2_dry_Tcorr_residual_max_of_ave']=[np.NaN]*len(super_big_val_df)  # added 1/24/2021

    # drop leftover columns created during merging
    super_big_val_df = super_big_val_df.drop(columns=['TS',\
        'mode_from_dry','Timestamp','Timestamp_dtc','Timestamp_flg'])

    super_big_val_df = val_df_reorder_columns(super_big_val_df)
    # print('Column Names after reordering are...')
    # pp.pprint(super_big_val_df.columns.values)

    #print(f'Before...len(super_big_val_df) = {len(super_big_val_df)}')
    #super_big_val_df = add_final_summary_rows(super_big_val_df)
    super_big_val_df = add_final_summary_rows_v2(super_big_val_df)
    #print(f'After...len(super_big_val_df) = {len(super_big_val_df)}')

    super_big_val_df = super_big_val_df.drop(columns=['time_of_report_command',\
        'gps','startup'])

    # add in range check
    super_big_val_df = val_df_add_range_check(super_big_val_df)

    #rename columns
    super_big_val_df = val_df_rename_columns(super_big_val_df)

    #super_big_val_df['Notes']=['x'*257]*len(super_big_val_df)
    super_big_val_df['Notes']=['']*len(super_big_val_df)

    # Chop off first 10 rows since they correspond to the first run, which does
    # not include CO2kzero, CO2kspan or CO2kspan2 values. So, Temperature
    # correction cannot be performed.
    # super_big_val_df = super_big_val_df.iloc[10:len(super_big_val_df),:]

    # Unknown as to why pandas re-inserts 'index', so just remove it
    super_big_val_df = super_big_val_df.drop(columns=['index'])

    # Final edit per Noah's request on 10-21-2021 to drop the residual standard deviation
    # for the dry and temperature corrected values since they were just estimated from the
    # standard deviation of the wet values as output by the MSP 430 microcontroller.
    super_big_val_df = super_big_val_df.drop(columns=['CO2_DRY_TCORR_RESIDUAL_STDDEV_ASVCO2'])

    #### END New stuff for flow ####    
    out = open("parsed_data_w_other_stuff_pascal_style.json", "w")
    json.dump(bigDictionary, out, indent=4, ensure_ascii=False, allow_nan=True) 
    out.close()

    #### BEGIN to put flow values into super_duper_df, which is derived from super_big_df ####
    # super_duper_df = super_big_df.append(super_big_val_df[['time','Flow_ave','Flow_sd']],sort=False)
    # super_duper_df = super_duper_df.sort_values(by=['time'])
    #### END to put flow values into super_duper_df, which is derived from super_big_df ####

    #### Create new dataframe for averaged data, etc. ####
    #super_big_val_df = super_big_val_df

    #super_duper_df = super_duper_df.reset_index()  # This does not work after sorting values

    # Index will persist if .reset_index is used above
    #super_duper_df.to_csv('.\\experimental_w_summary_3CADC7571.csv', index=False)  

    #pd.set_option('max_columns',None)
    #print(super_big_val_df.describe(include='all'))
    #print(super_duper_df.head())
    #print(super_big_val_df.describe(include='all'))
    #print(super_duper_df.head())
    #pd.reset_option('max_columns')

    return super_big_val_df
    #### END New stuff for flow ####

def get_glob_pattern(validation_text_filename):
    m = re.search(r'.*(\d{8})-(\d{6}).txt',validation_text_filename)
    if ( m ):
        recent_date_for_glob = m.groups()[0]
        year_for_glob = recent_date_for_glob[0:4]  # something like 2021
        month_for_glob = recent_date_for_glob[4:6]
        day_for_glob = recent_date_for_glob[6:8]

        #look one week-ish ahead for glob pattern, even at end of month and year...
        lower_day_for_glob_int = int(day_for_glob)
        upper_day_for_glob_int = lower_day_for_glob_int+7
        upper_month_for_glob_int = int(month_for_glob)
        lower_month_for_glob_int = upper_year_for_glob_int
        upper_year_for_glob_int = int(year_for_glob)
        lower_year_for_glob_int = upper_year_for_glob_int
        if ( upper_day_for_glob_int > 30 ):
            upper_day_for_glob_int = 30 - upper_day_for_glob_int
            upper_month_for_glob_int +=1 
            if ( upper_month_for_glob_int > 12):
                upper_month_for_glob_int = 1  #reset to january
                upper_year_for_glob_int += 1
        YYYY_start = str(lower_year_for_glob_int); YYYY_end = str(upper_year_for_glob_int)
        MM_start = str('{:02d}'.format(lower_month_for_glob_int))  # keep leading zero, 2 digits
        MM_end = str('{:02d}'.format(upper_month_for_glob_int))  # keep leading zero, 2 digits
        DD_start = str('{:02d}'.format(lower_day_for_glob_int))  # keep leading zero, 2 digits
        DD_end = str('{:02d}'.format(upper_day_for_glob_int))  # keep leading zero, 2 digits
        glob_date_pattern = ''
        for idx in range(0,4):
            if ( YYYY_start[idx] <= YYYY_end[idx] ):
                glob_date_pattern += '[' + YYYY_start[idx] + '-' + YYYY_end[idx] + ']'
            else:
                glob_date_pattern += '[' + YYYY_end[idx] + '-' + YYYY_start[idx] + ']'
        for idx in range(0,2):
            if ( MM_start[idx] <= MM_end[idx] ):
                glob_date_pattern += '[' + MM_start[idx] + '-' + MM_end[idx] + ']'
            else:
                glob_date_pattern += '[' + MM_end[idx] + '-' + MM_start[idx] + ']'
        for idx in range(0,2):
            if ( DD_start[idx] <= DD_end[idx] ):
                glob_date_pattern += '[' + MM_start[idx] + '-' + MM_end[idx] + ']'
            else:
                glob_date_pattern += '[' + MM_end[idx] + '-' + MM_start[idx] + ']'
    else:
        raise Exception("""Irregular filename pattern for {validation_text_filename}, 
        it needs to have 8 digit date with a dash followed by a 6 digit hour, minute and second""")


    glob_pattern =  glob_date_pattern + '*.txt'

    return glob_pattern

def extract_summary_and_raw_to_csv(sn,path_to_data,validation_text_filename):
    #%%
    if sys.platform.startswith('win'):
        dir_sep = '\\'
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        dir_sep = '/'
    reports_path = str(os.path.normpath( path_to_data + '%sreports' % (dir_sep)))
    if not os.path.exists(reports_path):
        os.mkdir(reports_path)
    csv_path = str(os.path.normpath(reports_path + '%scsv' % (dir_sep)))
    if not os.path.exists(csv_path):
        os.mkdir(csv_path)
    path_to_ALL = path_to_data + dir_sep + 'ALL'

    #path_to_ALL= path_to_data + 'ALL'
    #filenames=glob.glob(path_to_ALL + '/20*.txt')  #glob files produced sometime in the year 20XX?
    
    #### Need to filter through ALL folder for files that were created recently ####
    glob_pattern = get_glob_pattern(validation_text_filename)

    #filenames = glob.glob(path_to_ALL + dir_sep + '20' + '*.txt' )
    filenames = glob.glob(path_to_ALL + dir_sep + glob_pattern )
    filenames.sort()

    # get date range from the filenames
    start_filename_without_path=re.findall(r'\d+_\d+\.txt',filenames[0])[0]
    end_filename_without_path=re.findall(r'\d+_\d+\.txt',filenames[-1])[0]
    date_range=(start_filename_without_path,end_filename_without_path)
    
    list_of_df = []
    list_of_dry_df = []
    list_of_dry_df_sync = []
    list_of_stats_df = []
    list_of_flags_df = []
    list_of_coeff_sync_df =[]
    for idx, filename in enumerate(filenames):
        print(filename)
        # bypass files without coefficients
        COEFF_found_in_file=False
        with open(filename) as f:
            if 'COEFF' in f.read():
                COEFF_found_in_file =True
        f.close()
        del f
        if ( COEFF_found_in_file ):
            df_file = parse_all_file_df_w_summary_v2(filename)
            df_dry_sync, df_dry = loadASVall_dry(filename)
            df_stats = loadASVall_stats(filename)
            df_flags = loadASVall_flags(filename)
            df_ts_flags = add_ts_to_flags(df_flags,df_stats)
            df_coeff_sync = loadASVall_coeff_sync(filename)
            list_of_df.append(df_file)
            list_of_dry_df.append(df_dry)
            list_of_stats_df.append(df_stats)
            list_of_flags_df.append(df_ts_flags)
            #print(f'percent done = {100*idx/len(filenames)}%')
            list_of_dry_df_sync.append(df_dry_sync)
            list_of_coeff_sync_df.append(df_coeff_sync)

    super_big_df = pd.concat(list_of_df,axis=0,ignore_index=True)
    super_big_dry_df = pd.concat(list_of_dry_df,axis=0,ignore_index=True)
    super_big_dry_df_sync = pd.concat(list_of_dry_df_sync,axis=0,ignore_index=True)
    super_big_stats_df = pd.concat(list_of_stats_df,axis=0,ignore_index=True)
    super_big_flags_df = pd.concat(list_of_flags_df,axis=0,ignore_index=True)
    super_big_coeff_sync_df = pd.concat(list_of_coeff_sync_df,axis=0,ignore_index=True)
    raw_csv_filename = csv_path + dir_sep + 'raw_' + sn + '_' + date_range[0][0:8] + '.csv'
    super_big_df.to_csv(raw_csv_filename, index=False)

    stats_csv_filename = csv_path + dir_sep + 'stats_' + sn + '_' + date_range[0][0:8] + '.csv'
    super_big_stats_df.to_csv(stats_csv_filename, index=False)

    super_big_val_df = load_Val_file(validation_text_filename,super_big_dry_df_sync,\
        super_big_stats_df,super_big_flags_df,super_big_coeff_sync_df)
    summary_csv_filename = csv_path + dir_sep + 'summary_' + sn + '_' + date_range[0][0:8] + '.csv'
    super_big_val_df.to_csv(summary_csv_filename,index=False)

    return super_big_val_df, super_big_df


if __name__ == '__main__':

    #### Good stuff ####
    path_to_data='./data/3CB94292E/'
    path_to_ALL= path_to_data + 'ALL'
    filenames=glob.glob(path_to_ALL + '/2021*.txt')
    filenames.sort()
    list_of_df = []
    list_of_dry_df = []
    list_of_dry_df_sync = []
    list_of_stats_df = []
    list_of_flags_df = []
    list_of_coeff_sync_df =[]
    for idx, filename in enumerate(filenames):
        print(filename)
        # bypass files without coefficients
        COEFF_found_in_file=False
        with open(filename) as f:
            if 'COEFF' in f.read():
                COEFF_found_in_file =True
        f.close()
        del f
        if ( COEFF_found_in_file ):
            df_file = parse_all_file_df_w_summary_v2(filename)
            df_dry_sync, df_dry = loadASVall_dry(filename)
            df_stats = loadASVall_stats(filename)
            df_flags = loadASVall_flags(filename)
            df_ts_flags = add_ts_to_flags(df_flags,df_stats)
            df_coeff_sync = loadASVall_coeff_sync(filename)
            list_of_df.append(df_file)
            list_of_dry_df.append(df_dry)
            list_of_stats_df.append(df_stats)
            list_of_flags_df.append(df_ts_flags)
            #print(f'percent done = {100*idx/len(filenames)}%')
            list_of_dry_df_sync.append(df_dry_sync)
            list_of_coeff_sync_df.append(df_coeff_sync)

    super_big_df = pd.concat(list_of_df,axis=0,ignore_index=True)
    super_big_dry_df = pd.concat(list_of_dry_df,axis=0,ignore_index=True)
    super_big_dry_df_sync = pd.concat(list_of_dry_df_sync,axis=0,ignore_index=True)
    super_big_stats_df = pd.concat(list_of_stats_df,axis=0,ignore_index=True)
    super_big_flags_df = pd.concat(list_of_flags_df,axis=0,ignore_index=True)
    super_big_coeff_sync_df = pd.concat(list_of_coeff_sync_df,axis=0,ignore_index=True)
    super_big_df.to_csv(path_to_data + 'raw_w_summary_3CB94292E.csv', index=False)
    #### END Good stuff ####

    # pd.set_option('max_columns',None)
    # super_big_dry_df_sync.head()
    # pd.reset_option('max_columns')

    # pd.set_option('max_columns',None)
    # print('super_big_stats_df first five rows...')
    # print(super_big_stats_df.head())
    # print('super_big_stats_df described...')
    # print(super_big_stats_df.describe(include='all'))
    # pd.reset_option('max_columns')

    super_big_stats_df.to_csv(path_to_data + 'stats_3CB94292E.csv', index=False)

    #validation_filename = './data/3CADC7571/3CADC7571_Validation_20210817-222532.txt'
    #validation_filename = './data/3CADC7565/3CADC7565_Validation_20210820-230908.txt'
    #validation_filename = './data/3CA8A2538/3CA8A2538_Validation_20210813-221913.txt'
    #validation_filename = './data/3CA8A2535/3CA8A2535_Validation_20210811-183246.txt'
    #validation_filename = './data/3CA8A2533/3CA8A2533_Validation_20210812-192805.txt'
    #validation_filename = './data/3CB94292C/3CB94292C_Validation_20211012-210208.txt'
    validation_filename = './data/3CB94292E/3CB94292E_Validation_20210921-223759.txt'
    #validation_filename = './data/3CB942928/3CB942928_Validation_20210915-001423.txt'
    #validation_filename = './data/3CD6D1DD5/3CD6D1DD5_Validation_20211005-225409.txt'
    super_big_val_df = load_Val_file(validation_filename,super_big_dry_df_sync,\
        super_big_stats_df,super_big_flags_df,super_big_coeff_sync_df)
    super_big_val_df.to_csv(path_to_data + 'Report_Summary_parsed_from_every_txt_file_3CB94292E.csv',index=False)

    # print('big df timestamp=',super_big_df['time'].iloc[0])
    # print('val df timestamp=',super_big_val_df['time'].iloc[0])
    # print('len(big timestamp)=',len(super_big_df['time'].iloc[0]))
    # print('len(val timestamp)=',len(super_big_val_df['time'].iloc[0]))
    # for idx, row in super_big_val_df.iterrows():
    #     target_timestamp = row['time']
    #     matching = super_big_df['time'] == target_timestamp
    #     print(super_big_df['time'].loc[matching])
    # matching = super_big_df['time'] == super_big_val_df['time']
    # print(matching)

    # df1 = pd.DataFrame(data={'bears':[100,98,96,94],'pigs':""})
    # df2 = pd.DataFrame(data={'bears':"",'pigs':[64]})
    # df1 = df1.rename(columns={'bears':'chickens','pigs':'rabbits'})
    # df2 = df2.rename(columns={'bears':'chickens','pigs':'rabbits'})
    # df_missing = pd.concat([df1,df2],axis=0,ignore_index=True)
    # print(df_missing)