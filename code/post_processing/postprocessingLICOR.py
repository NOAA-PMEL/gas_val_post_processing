#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 29 11:47:52 2021

@author: chu

Edited on Mon Mar 15 15:07:35 2021

@author: chu and nespeca

Further edits on 6/23/2021 and later

@author: nespeca
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm   #plot one color for each run
import glob
import re
import pickle
import os
import sys
import pprint
import json
from scipy.stats import t
from special_functions import dry_correction
import datetime as dt


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
    df = pd.DataFrame(coeff, columns=['Linenumber', 'Data'])
    df = df.Data.str.split(':', expand=True)
    df = df.drop(columns=[0]).rename(columns={1: "label", 2: "coeff"})

    mask1 = df['label'].str.contains("k")  
    df = df[mask1]  #take only lines with coefficients
    mask2 = df.index < 7  
    df = df[mask2]  #take first set of coefficients after span

    df = df.reset_index()

    return df

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

##### Modified by Pascal to take in modename as an argument #####
def loadASVall_data_with_mode(filename,modename):
    data = []
    linenum = 0
    pattern_data = re.compile("DATA")
    with open(filename, 'rt') as myfile:
        for line in myfile:
            linenum += 1
            if pattern_data.search(line) != None:  # If a match is found
                data.append((linenum, line.rstrip('\n')))
    df = pd.DataFrame(data, columns=['Linenumber', 'Data'])

    df = df.Data.str.split(':|,', expand=True)

    df = df.drop(columns=[0]).rename(
        columns={1: "Mode", 2: "Date", 3: "Minute", 4: "Seconds", 5: "SN", 6: "CO2", 7: "Temp", 8: "Pres", 9: "Li_Raw",
                 10: "Li_ref", 11: "RHperc", 12: "RH_T", 13: "O2perc"})

    mask = df['Mode'].str.contains(modename)  
    df = df[mask]
    return df

def loadASVall_stats(filename):
    data_dict = {}
    linenum = 0
    first_header_entered = False
    pattern_stats = re.compile("STATS")
    with open(filename, 'rt') as myfile:
        for line in myfile:
            linenum += 1
            if pattern_stats.search(line) != None:  # If a match is found
                #check if it's a header or not
                line=line.rstrip('\n')
                right_of_STATS=re.split(r'STATS:',line)[1]
                letter_score = sum([c.isalpha() for c in right_of_STATS]) \
                    /len(right_of_STATS)
                header_detected = letter_score > 0.5
                #csv_txt = re.split(r':|,',line)[1:]  # split by ',' or ':' ignore the first item, STATS
                csv_txt = re.split(r',',line)
                str_list = [s.strip() for s in csv_txt]  # remove leading and trailing whitespace
                str_list = [s.replace(" ","") for s in str_list] # remove all whitespace
                str_list[0]=str_list[0].replace("STATS:","")
                if ( (not header_detected) and \
                    first_header_entered ):
                    #data.append(pd.DataFrame(columns=header,data=str_list))
                    for idx, k in enumerate(data_dict.keys()):
                        data_dict[k].append(str_list[idx])
                elif ( header_detected and \
                    not first_header_entered ):
                    header=str_list
                    #populate empty list with keys, k, the items from the header
                    for k in header:
                        data_dict[k] = []
                    first_header_entered=True
                elif ( header_detected and \
                    first_header_entered):
                    pass  # do nothing 
                else:
                    weird_txt = f'File:{filename}\nUnexpected text happened on line number = {linenum}\n{line}'
                    raise Exception(weird_txt)

        if ( data_dict ):
            #convert from string to float, if applicable
            crazy = r'[+-]?\\d+\\.?\\d*[eE][+-]?\\d+|[-]?\\d+\\.\\d+|[-]?\\d+'
            ts_re = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.?\d*Z'
            for k, v in data_dict.items():
                temp = []
                for item in v:
                    if ( re.match(crazy,item) and \
                        re.match(ts_re,item) is None):
                        temp.append(float(item))
                    else:
                        temp.append(item)
            #construct dataframe
            df = pd.DataFrame(data_dict)
        else:
            df = pd.DataFrame()
    

    #df = df.Data.str.split(':|,', expand=True)

    # df = df.drop(columns=[0]).rename(
    #     columns={1: "Mode", 2: "Date", 3: "Minute", 4: "Seconds", 5: "SN", 6: "CO2", 7: "Temp", 8: "Pres", 9: "Li_Raw",
    #              10: "Li_ref", 11: "RHperc", 12: "RH_T", 13: "O2perc"})

    #mask = df['Mode'].str.contains(modename)  
    #df = df[mask]
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

##### Special addition to avoid manual maintenance of gaslist #####
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

def extra_range_checks(filename):
    df_flags = loadASVall_flags(filename)
    df_stats = loadASVall_stats(filename)
    data_all_modes = []
    all_modes = ['ZPON','ZPOFF','ZPPCAL','SPON','SPOFF','SPPCAL',\
        'EPON','EPOFF','APON','APOFF']
    for m in all_modes:
        data_all_modes.append(loadASVall_data_with_mode(filename,m))
    df_all_modes = pd.concat(data_all_modes,ignore_index=True)

    #initialize fault string
    fault_str = ''

    #check if pressure checks for pump on vs pump off
    df_all_modes['Pres'] = df_all_modes['Pres'].astype(float)
    # mask_zpon = df_all_modes['Mode'] == 'ZPON'
    # mask_zpoff = df_all_modes['Mode'] == 'ZPOFF'
    # mask_spon = df_all_modes['Mode'] == 'SPON'
    # mask_spoff = df_all_modes['Mode'] == 'SPOFF'
    # mask_apon = df_all_modes['Mode'] == 'APON'
    # mask_apoff = df_all_modes['Mode'] == 'APOFF'
    # mask_epon = df_all_modes['Mode'] == 'EPON'
    # mask_epoff = df_all_modes['Mode'] == 'EPOFF'
    mask_zpon = df_all_modes['Mode'].str.contains('ZPON')
    mask_zpoff = df_all_modes['Mode'].str.contains('ZPOFF')
    mask_spon = df_all_modes['Mode'].str.contains('SPON')
    mask_spoff = df_all_modes['Mode'].str.contains('SPOFF')
    mask_apon = df_all_modes['Mode'].str.contains('APON')
    mask_apoff = df_all_modes['Mode'].str.contains('APOFF')
    mask_epon = df_all_modes['Mode'].str.contains('EPON')
    mask_epoff = df_all_modes['Mode'].str.contains('EPOFF')
    #mean_zpon = df_all_modes['Pres'].loc[mask_zpon].mean()
    #print(f'mean_zpon = {mean_zpon} kPa')
    # pd.set_option('max_columns',None)
    # print(df_all_modes.head())
    # pd.reset_option('max_columns')
    diff_P_zp = df_all_modes['Pres'].loc[mask_zpon].mean() - \
        df_all_modes['Pres'].loc[mask_zpoff].mean()
    diff_P_sp = df_all_modes['Pres'].loc[mask_spon].mean() - \
        df_all_modes['Pres'].loc[mask_spoff].mean()
    diff_P_ap = df_all_modes['Pres'].loc[mask_apon].mean() - \
        df_all_modes['Pres'].loc[mask_apoff].mean()
    diff_P_ep = df_all_modes['Pres'].loc[mask_epon].mean() - \
        df_all_modes['Pres'].loc[mask_epoff].mean()
    # print(f'diff_P_zp = {diff_P_zp}')
    # print(f'diff_P_sp = {diff_P_sp}')
    # print(f'diff_P_ap = {diff_P_ap}')
    # print(f'diff_P_ep = {diff_P_ep}')
    if ( abs(diff_P_zp) <= 0.0):
        fault_str+="The mean pressure for ZPON was not greater "\
            "than the mean pressure for ZPOFF by 0.0kPa.<br/>"
    if ( abs(diff_P_sp) <= 2.0):
        fault_str+="The mean pressure for SPON was not greater "\
            "than the mean pressure for SPOFF by 2.0kPa.<br/>"
    if ( abs(diff_P_ap) <= 2.5):
        fault_str+="The mean pressure for APON was not greater "\
            "than the mean pressure for APOFF by 2.5kPa.<br/>"
    if ( abs(diff_P_ep) <= 2.5):
        fault_str+="The mean pressure for EPON was not greater "\
            "than the mean pressure for EPOFF by 2.5kPa.<br/>"

    #check if RH is within 3% of mean
    df_all_modes['RHperc'] = df_all_modes['RHperc'].astype(float)
    rh_mean = df_all_modes['RHperc'].mean()
    #print(f'rh_mean = {rh_mean}')
    ones=pd.Series([1]*len(df_all_modes['RHperc']))
    mask_rh = ((df_all_modes['RHperc'] - rh_mean*ones) > 3.0) | \
        ((df_all_modes['RHperc'] - rh_mean*ones) < -3.0)
    if ( len(df_all_modes[mask_rh]) != 0 ):
        fault_str += "A relative humidity measurement was greater "\
            "than 3% away from the mean.<br/>"

    #check for flags not equal to 0 or 65536
    mask_f = (df_flags[df_flags.columns.values[0]] != 0) & \
        (df_flags[df_flags.columns.values[0]] != 16**4)
    for col in df_flags.columns.values:
        mask_f = mask_f | ((df_flags[col] != 0) & (df_flags[col] != 16**4))
    if ( len(df_flags[mask_f]) != 0 ):
        fault_str += 'A non-zero flag indicating a fault was found.<br/>'

    #check if xCO2 standard deviations less than 2ppm
    df_stats['CO2_SD'] = df_stats['CO2_SD'].astype(float)
    # pd.set_option('max_columns',None)
    # print(df_stats)
    # pd.reset_option('max_columns')
    mask_co2_sd = df_stats['CO2_SD'] >= 2.0
    if ( len(df_stats[mask_co2_sd]) != 0 ):
        fault_str += 'A CO2 standard deviation was found greater than or equal to 2ppm.<br/>'
    
    #Pascal, 8/13/2021, choose which gas list to use based upon time string from filename,
    #will need to update this to a more fully featured lookup later
    time_str=re.search(r'\d{8}_\d{6}\.txt',filename)[0]  #grab 8 digits, underscore and 6 digits
    year_month_day_str = re.split(r'_',time_str)[0]
    num_yr_mo_dd = float(year_month_day_str)
    # if ( (20210801 - num_yr_mo_dd) > 0 ):  # if it preceded Aug 1 2021, then used older gaslist
    #     gaslist=[0, 104.25, 349.79, 506.16, 732.64, 999.51, 1487.06, 1994.25] #552.9 before 4/27
    # else:  # use newer gaslist if after Aug 1 2021
    #     gaslist=[0, 104.25, 349.79, 494.72, 732.64, 999.51, 1487.06, 1961.39] #update in early Aug 2021
    if ( (20210801 - num_yr_mo_dd) > 0 ):  # if it preceded Aug 1 2021, then used older gaslists
        if ((20210427 - num_yr_mo_dd) > 0):
            span_gas = 552.9 #552.9 before 4/27
        else:
            span_gas = 506.16
    else:  # use newer gaslist if after Aug 1 2021
        span_gas = 494.72 #update in early Aug 2021
    

    #### New stuff to avoid doing gaslist ####
    # bigDictionary, config_stuff, mode_and_gas_stuff, flush_stuff = \
    #     load_Val_File_into_dicts_v3(validation_text_filename)

    bigDictionary, config_stuff, mode_and_gas_stuff, flush_stuff = \
        load_Val_File_into_dicts_v3(validation_text_filename,timestamp_mode='Unix epoch, days')

    #### New stuff to fix "nan" issues found in data from 3CADC7565 ####
    bigDictionary = val_fix_nan_in_dict(bigDictionary)
    bDkeys = list(bigDictionary.keys())
    typeflow_ave = type(bigDictionary[bDkeys[0]]['Flow_ave'][0])
    flow_ave_example = bigDictionary[bDkeys[0]]['Flow_ave'][0]
    print(f'type of flow_ave bigDictionary = {typeflow_ave}')
    print(f'first entry of Flow_ave = {flow_ave_example}')
    pp = pprint.PrettyPrinter(indent=4)
    #pp.pprint(bigDictionary)
    out = open("bigD_parsed_from_val_file.json", "w")
    json.dump(bigDictionary, out, indent=4, ensure_ascii=False, allow_nan=True) 
    out.close()

    pp.pprint(mode_and_gas_stuff)
    out = open("mode_and_gas_parsed_from_val_file.json", "w")
    json.dump(mode_and_gas_stuff, out, indent=4, ensure_ascii=False, allow_nan=True) 
    out.close()

    cskeys = list(config_stuff.keys())
    something = type(config_stuff[cskeys[0]]['LI_ser'])
    something_else = config_stuff[cskeys[0]]['LI_ser']
    print(f'type of LI_ser = {something}')
    print(f'LI_ser = {something_else}')
    pp.pprint(config_stuff)
    out = open("other_stuff_from_val_file.json", "w")
    json.dump(config_stuff, out, indent=4, ensure_ascii=False, allow_nan=True) 
    out.close()

    mgkeys = list(mode_and_gas_stuff.keys())
    pp.pprint(mode_and_gas_stuff[mgkeys[0]])
    out = open("mode_and_gas_stuff_from_val_file.json", "w")
    json.dump(mode_and_gas_stuff, out, indent=4, ensure_ascii=False, allow_nan=True) 
    out.close()

    #add column for standard gas
    df_all_modes['CO2'] = df_all_modes['CO2'].astype(float)
    mask_sppcal = df_all_modes['Mode'].str.contains('SPPCAL')
    mask_zppcal = df_all_modes['Mode'].str.contains('ZPPCAL')
    co2_sppcal_list = df_all_modes[mask_sppcal].\
        iloc[:,df_all_modes.columns.get_loc('CO2')].to_list()
    co2_zppcal_list = df_all_modes[mask_zppcal].\
        iloc[:,df_all_modes.columns.get_loc('CO2')].to_list()
    #check CO2 within 2ppm during zppcal
    co2_zppcal_check = [True if abs(x) > 2.0 else False for x in co2_zppcal_list]
    #check CO2 within 2ppm during sppcal
    co2_sppcal_check = [True if abs(x-span_gas) > 2.0 else False for x in co2_sppcal_list]
    if ( True in co2_zppcal_check ):
        fault_str += "A CO2 measurement exceeded 2ppm away " \
            "from the zero gas during ZPPCAL.<br/>"
    if ( True in co2_sppcal_check ):
        fault_str += "A CO2 measurement exceeded 2ppm away" \
            "from the span gas during SPPCAL.<br/>"

    #check if xCO2 standard deviations less than 2ppm
    mask_co2_sd = df_stats['CO2_SD'] >= 2.0
    if ( len(df_stats[mask_co2_sd]) != 0 ):
        fault_str += 'The standard deviation of CO2 concentration was above 2ppm.<br/>'

    if (len(fault_str) == 0):
        fault_str = 'No problems were found in ' + filename + '<br/>'
    else:
        fault_str = 'The following problems were found in ' + filename + '<br/>' \
            + fault_str + '<br/>'

    return fault_str

def calculate_xco2_from_data(data, zerocoeff, S0_tcorr, S1_tcorr):
    
    # CO2 calibration function constants (from Israel's email)
    a1 = 0.3989974
    a2 = 18.249359
    a3 = 0.097101984
    a4 = 1.8458913
    n = ((a2 * a3) + (a1 * a4))
    o = (a2 + a4)
    q = (a2 - a4)
    q_1 = (q ** 2)
    r = ((a2 * a3) + (a1 * a4))
    r_1 = (r ** 2)
    D = 2 * (a2 - a4) * ((a1 * a4) - (a2 * a3))

    # constants to compute X
    b1 = 1.10158  # 'a
    b2 = -0.00612178  # 'b
    b3 = -0.266278  # 'c
    b4 = 3.69895  # 'd
    z = a1 + a3

    p0 = 99  # po is std pressure, po = 99.0 kPa

    Li_Raw_float = data.Li_Raw.astype(int)  # w - raw count
    Li_ref_float = data.Li_ref.astype(int)  # w0 - raw count reference
    Pres_float = data.Pres.astype(float)  # p1 - measured pressure
    Temp_float = data.Temp.astype(float)  # T - temperature

    w = Li_Raw_float
    w0 = Li_ref_float
    p1 = Pres_float
    T = Temp_float
    
    #use averaged values
    w_mean = w.mean()
    w0_mean =w0.mean()
    p1_mean = p1.mean()
    T_mean = T.mean()

    #Pascal, new alphaC to reflect "APOFF" dataset
    alphaC = (1 - ((w_mean / w0_mean) * zerocoeff))
    
    # Pascal - valid, these are intermediate variables used to calculate alphaCprime, below

    #Need to shift S0_tcorr index to match alphaC index for calculation
    #idx_delta = S0_tcorr.index[0]-alphaC.index[0]
    #S0_tcorr.index = [val-idx_delta for val in S0_tcorr.index]
    print(f'double check: S0_tcorr = {S1_tcorr}, S0_tcorr = {S1_tcorr}')
    alphaC_1 = alphaC * S0_tcorr
    alphaC_2 = (alphaC ** 2) * S1_tcorr
    # print("alphaC_2\n",alphaC_2)

    # Pascal - valid, relates to eq. A-3 or eq. A-10 of LiCor 830/850 manual
    alphaCprime = alphaC_1 + alphaC_2
    print("alphaCprime\n",alphaCprime)

    #df_bugs = pd.DataFrame([alphaC, BetaC, S0_tcorr, alphaCprime, alphaCprime-BetaC])
    #df_bugs = df_bugs.transpose()

    p = p1_mean / p0
    pif = p > 1

    if pif.any():
        p = p1_mean / p0
    else:
        p = p0 / p1_mean

    # Pascal - valid, relates to eq. A-11 of LiCor 830/850 manual, note b1:=a, b2:=b, b3:=c and b4:=d
    #    ' compute some terms for the pressure correction function
    A = (1 / (b1 * (p - 1)))
    B = 1 / ((1 / (b2 + (b3 * p))) + b4)
    X = 1 + (1 / (A + (B * ((1 / (z - alphaC)) - (1 / z)))))  # change whether alphaC or alphaCprime here
    
    # Pascal - valid, w.r.t g, relates to eq. A-13 or eq. A-11 of LiCor 830/850 manual
    # g is the empirical correction function and is a function of absorptance and pressure

    if pif.any():
        g = 1 / X
    else:
        g = X

    # Pascal - valid, w.r.t. eq. A-10 of LiCor 830/850 manual
    #    'alphapc is the pressure corrected absorptance, alphaC'', and equal absorptance(absp) * correction (g)
    alphapc = alphaCprime * g

    #print(f'span2_temp = {span2_in}')
    
    #    'F is the calibration polynomial

    # Pascal - invalid without stated assumption of psi(W) per eq. A-18, A-14 and A-16 in LiCor 830/850 manual
    # if it is presumed that psi(W) is 1, then this should be valid, but that needs some kind of statement
    numr = (n - o * alphapc) - np.sqrt(q_1 * (alphapc ** 2) + D * alphapc + r_1)
    denom = 2 * (alphapc - a1 - a3)

    # Pascal - invalid per eq. A-16 of LiCor 830/850 manual, where x should be alphapc/psi(W)
    # if psi(W) is 1, then it is valid, but the psi(W) being assumed as 1 should be stated
    F = numr / denom
    #print(f'F_mean = {F.mean()}')
    
    # Pascal - invalid without stated assumption of psi(W) per eq. A-18, A-14 and A-16 in LiCor 830/850 manual
    # if it is presumed that psi(W) is 1, then this should be valid, but that needs some kind of statement
    xco2 = F * ((T_mean + 273.15))  # / (T0 + 273.15)) # added the bottom TO
    #print(f'T_mean = {T.mean()}')
    #print(f'xco2_mean = {xco2.mean()}')
    return xco2
# %%
def postprocesslicorspan2_w_mode(filename_coeff, filename_data, span2_in, S1_lab_in, slope_in,\
    mode_for_recalc):

    coeff = loadASVall_coeff(filename_coeff)  #
    # print(coeff)
    data_spoff = loadASVall_data_with_mode(filename_data,"SPOFF")  # Modified by Pascal to change dataset from APOFF to SPOFF
    # print(data)

    #span1 = loadASVall_data_with_mode(filename_data,"SPOFF")  # Modified by Pascal, but span1 should be the same
    #span1_avgT = span1.Temp.astype(float).mean()
    #print(f'span1_avgT = {span1_avgT}')
    span1_avgT = data_spoff.Temp.astype(float).mean()  # duplicate span1 dataframe unnecessary, 10/25/2021

    zerocoeff = float(coeff.coeff[0])  # zerocoeff - zero coefficient
    # print(zerocoeff)
    S0 = float(coeff.coeff[1])  # S0 - span offset, middle span
    # print(f'double check: S0 = {S0}')
    S1 = float(coeff.coeff[2])  # S1 - high span
    # print(S1)

    Li_Raw_float = data_spoff.Li_Raw.astype(int)  # w - raw count
    Li_ref_float = data_spoff.Li_ref.astype(int)  # w0 - raw count reference
    Pres_float = data_spoff.Pres.astype(float)  # p1 - measured pressure
    Temp_float = data_spoff.Temp.astype(float)  # T - temperature

    w = Li_Raw_float
    w0 = Li_ref_float
    p1 = Pres_float
    T = Temp_float
    
    #use averaged values
    w_mean = w.mean()
    w0_mean = w0.mean()
    p1_mean = p1.mean()
    T_mean = T.mean()
    
    ######################## BEGIN - Constants which do not vary upon loaded dataset ######################
    # CO2 calibration function constants (from Israel's email)
    a1 = 0.3989974
    a2 = 18.249359
    a3 = 0.097101984
    a4 = 1.8458913
    n = ((a2 * a3) + (a1 * a4))
    o = (a2 + a4)
    q = (a2 - a4)
    q_1 = (q ** 2)
    r = ((a2 * a3) + (a1 * a4))
    r_1 = (r ** 2)
    D = 2 * (a2 - a4) * ((a1 * a4) - (a2 * a3))

    # constants to compute X
    b1 = 1.10158  # 'a
    b2 = -0.00612178  # 'b
    b3 = -0.266278  # 'c
    b4 = 3.69895  # 'd
    z = a1 + a3

    T0 = 50
    p0 = 99  # po is std pressure, po = 99.0 kPa
    # p1 is the measured pressure
    # P is the ratio of the std pressure and measured press whichever is > 1
    ######################## END - Constants which do not vary upon loaded dataset #######################

    #    'innerTerm is alphaC

    # Pascal - valid, relates to LiCor 830/850 manual Appendix A, eq. A-4 or eq. A-10, with X_wc = 0
    alphaC = (1 - ((w_mean / w0_mean) * zerocoeff))
    #print(f'w_mean = {w_mean}')
    #print(f'w0_mean = {w0_mean}')

    #print(f'zerocoeff = {zerocoeff}')
    #print(f'alphaC_mean = {alphaC}')
    # Pascal - valid, relates to algebraic manipulation of LiCor 830/850 manual Appendix A, eq. A-28
    # note that overbar symbol on alphaC symbol in the LiCor manual indicates that it is a 5 second average value
    BetaC = alphaC * (S0 + S1 * alphaC) #use S1 not S1_lab**************
    #print(f'BetaC_mean = {BetaC.mean()}')
    # print(f'S0 = {S0}')
    # print(f'S1_lab = {S1_lab}')

    #difference in temp from span2 at 20C and span1 temp
    span2_cal2_temp_diff = span1_avgT - span2_in ############IS THIS SUPPOSED TO BE NEGATIVE?
    #print(f'span2_cal2_temp_diff = {span2_cal2_temp_diff}')  

    S1_tcorr = (S1_lab_in + slope_in * span2_cal2_temp_diff)#.astype(float)

    # print(f'comparison: span2_cal2_temp_diff = {span2_cal2_temp_diff}')
    #print(f"S1_tcorr = {S1_tcorr}")
    # Pascal - valid, comes from LiCor Appendix A, eq. A-28
    # note that overbar symbol on alphaC symbol in the LiCor 830/850 manual indicates a 5 second average value
    S0_tcorr = (BetaC / alphaC) - (S1_tcorr * alphaC)

    # print(BetaC/alphaC)
    # print(S1_tcorr * alphaC)
    #print(f'type(S0_tcorr) = {type(S0_tcorr)}')
    #print(f"S0_tcorr_mean = {S0_tcorr.mean()}")

    # alphaCprime = ((alphaC * S0) + ((alphaC ** 2) * S1)) .astype(float)   #without coefficient temp correction

    ################ Temperature adjustment done, use "APOFF" dataset to calculate the rest #####################
    #data = loadASVall_data_with_mode(filename_data, "APOFF")
    data = loadASVall_data_with_mode(filename_data, mode_for_recalc)

    # Use temperature adjusted S0 and S1, S0_tcorr and S1_tcorr, to get xco2 using data
    xco2 = calculate_xco2_from_data(data, zerocoeff, S0_tcorr, S1_tcorr)

    # Do dry recalculation here
    RH_T = data['RH_T'].astype(float).mean()
    Pressure = data['Pres'].astype(float).mean()
    RH_sample = data['RHperc'].astype(float).mean()
    RH_span = data_spoff['RHperc'].astype(float).mean()
    xco2_dry = dry_correction(xco2,RH_T,Pressure,RH_sample,RH_span)

    # Get DRY ppm values from ALL file
    df_dry_sync, df_dry = loadASVall_dry(filename_data)

    #avg_830 = pd.Series(data.CO2.astype(float).mean())  # old, used wet data previously, 10/25/2021
    #avg_830_recalc = pd.Series(xco2.mean())  # old, used temperature corrected values, 10/25/2021
    avg_830_recalc = pd.Series(xco2_dry.mean())  # new, use dry and temperature corrected values, 10/25/2021
    if ( mode_for_recalc == "APOFF" ):
        avg_830 = pd.Series(df_dry['Atm_xCO2(dry)'].astype(float).mean())  # mean of one number is just the number
    elif ( mode_for_recalc == "EPOFF" ): 
        avg_830 = pd.Series(df_dry['SW_xCO2(dry)'].astype(float).mean())  # mean of one number is just the number
    else:
        avg_830 = pd.Series(np.NaN)
        raise Exception('currently, only dry values exist for APOFF and EPOFF')

    df_res = pd.concat([avg_830, avg_830_recalc], axis=1)
      
    df_res['gas_standard']=np.nan

    #Pascal, 8/13/2021, choose which gas list to use based upon time string from filename,
    #will need to update this to a more fully featured lookup later
    time_str=re.search(r'\d{8}_\d{6}\.txt',filename_data)[0]  #grab 8 digits, underscore and 6 digits
    year_month_day_str = re.split(r'_',time_str)[0]
    num_yr_mo_dd = float(year_month_day_str)
    # if ( (20210801 - num_yr_mo_dd) > 0 ):  # if it preceded Aug 1 2021, then used older gaslist
    #     gaslist=[0, 104.25, 349.79, 506.16, 732.64, 999.51, 1487.06, 1994.25] #552.9 before 4/27
    # else:  # use newer gaslist if after Aug 1 2021
    #     gaslist=[0, 104.25, 349.79, 494.72, 732.64, 999.51, 1487.06, 1961.39] #update in early Aug 2021
    if ( (20210801 - num_yr_mo_dd) > 0 ):  # if it preceded Aug 1 2021, then used older gaslists
        if ((20210427 - num_yr_mo_dd) > 0):
            gaslist=[0, 104.25, 349.79, 552.9, 732.64, 999.51, 1487.06, 1994.25] #552.9 before 4/27
        else:
            gaslist=[0, 104.25, 349.79, 506.16, 732.64, 999.51, 1487.06, 1994.25]
    else:  # use newer gaslist if after Aug 1 2021
        gaslist=[0, 104.25, 349.79, 494.72, 732.64, 999.51, 1487.06, 1961.39] #update in early Aug 2021
    
    #add column for standard gas
    for i in range(len(df_res)):
        for gas in gaslist:
            minimum=abs(df_res.iloc[:,1][i]-gas)
            #print(minimum)
            if minimum<50:
                df_res['gas_standard'][i]=gas
            
    
    
    #df_res[ = data.CO2.astype(float) - xco2
    
    df_res['std_830_res'] = df_res.iloc[:,0]-df_res.gas_standard
    df_res['std_830recalc_res'] = df_res.iloc[:,1]-df_res.gas_standard

    # print(avg_830.mean())
    # print(avg_830_recalc.mean())
    # print(df_res['std_830recalc_res'].mean())

    return df_res #, df_bugs

# # %%

# results = postprocesslicorspan2('./ASV1002_March2021_ALL_Files/20210312_160017.txt', \
#                                 './ASV1002_March2021_ALL_Files/20210312_160017.txt', span2_temp, S1_lab, slope_licor)

# sn = systems[0].CO2.serial_number  # assume systems[0] contains serial number
# path_to_ALL = systems[0].CO2.path + 'ALL'  # should be folder with 'ALL' data
# validation_text_filename = systems[0].report.filename  # contains data returned from "report\r\n"
# temperature_slope_files=['slope_cal_1_csv_all_6_10.csv','slope_cal_2_csv_all_6_10.csv']

def get_summary_stats_df_by_group(df_830_830eq_EPOFF,df_830_830eq_APOFF):
    ## working here now
    gas_standard_groups = [(0,750),(0,2),(2,300),(300,775),(775,1075),(1075,2575)]
    list_of_df_APOFF = []
    list_of_df_EPOFF = []
    d_for_df_APOFF_t_corr_summary_stats = {"gas_standard_lower":[],"gas_standard_upper":[],\
        "mean":[],"stdev":[],"max":[]}
    d_for_df_EPOFF_t_corr_summary_stats = {"gas_standard_lower":[],"gas_standard_upper":[],\
        "mean":[],"stdev":[],"max":[]}
    d_for_df_APOFF_not_t_corr_summary_stats = {"gas_standard_lower":[],"gas_standard_upper":[],\
        "mean":[],"stdev":[],"max":[]}
    d_for_df_EPOFF_not_t_corr_summary_stats = {"gas_standard_lower":[],"gas_standard_upper":[],\
        "mean":[],"stdev":[],"max":[]}
    for idx, this_group in enumerate(gas_standard_groups):
        
        #assemble upper and lower limits from each group
        lower_ppm_limit = this_group[0]; upper_ppm_limit = this_group[1]
        d_for_df_EPOFF_not_t_corr_summary_stats["gas_standard_lower"].append(lower_ppm_limit)
        d_for_df_APOFF_not_t_corr_summary_stats["gas_standard_lower"].append(lower_ppm_limit)
        d_for_df_EPOFF_t_corr_summary_stats["gas_standard_lower"].append(lower_ppm_limit)
        d_for_df_APOFF_t_corr_summary_stats["gas_standard_lower"].append(lower_ppm_limit)
        d_for_df_EPOFF_not_t_corr_summary_stats["gas_standard_upper"].append(upper_ppm_limit)
        d_for_df_APOFF_not_t_corr_summary_stats["gas_standard_upper"].append(upper_ppm_limit)
        d_for_df_EPOFF_t_corr_summary_stats["gas_standard_upper"].append(upper_ppm_limit)
        d_for_df_APOFF_t_corr_summary_stats["gas_standard_upper"].append(upper_ppm_limit)

        #perform statistics within limits of this_group
        f_EPOFF_group = (df_830_830eq_EPOFF['gas_standard'] >= lower_ppm_limit) & \
            (df_830_830eq_EPOFF['gas_standard'] < upper_ppm_limit)
        f_APOFF_group = (df_830_830eq_APOFF['gas_standard'] >= lower_ppm_limit) & \
            (df_830_830eq_APOFF['gas_standard'] < upper_ppm_limit)
        EPOFF_this_group_mean_t_corr = df_830_830eq_EPOFF.loc[f_EPOFF_group,'std_830recalc_res'].mean()
        APOFF_this_group_mean_t_corr = df_830_830eq_APOFF.loc[f_APOFF_group,'std_830recalc_res'].mean()
        EPOFF_this_group_mean_not_t_corr = df_830_830eq_EPOFF.loc[f_EPOFF_group,'std_830_res'].mean()
        APOFF_this_group_mean_not_t_corr = df_830_830eq_APOFF.loc[f_APOFF_group,'std_830_res'].mean()
        EPOFF_this_group_stdev_t_corr = df_830_830eq_EPOFF.loc[f_EPOFF_group,'std_830recalc_res'].std(ddof=0)
        APOFF_this_group_stdev_t_corr = df_830_830eq_APOFF.loc[f_APOFF_group,'std_830recalc_res'].std(ddof=0)
        EPOFF_this_group_stdev_not_t_corr = df_830_830eq_EPOFF.loc[f_EPOFF_group,'std_830_res'].std(ddof=0)
        APOFF_this_group_stdev_not_t_corr = df_830_830eq_APOFF.loc[f_APOFF_group,'std_830_res'].std(ddof=0)
        EPOFF_this_group_max_t_corr = max(abs(df_830_830eq_EPOFF.loc[f_EPOFF_group,'std_830recalc_res']))
        APOFF_this_group_max_t_corr = max(abs(df_830_830eq_APOFF.loc[f_APOFF_group,'std_830recalc_res']))
        EPOFF_this_group_max_not_t_corr = max(abs(df_830_830eq_EPOFF.loc[f_EPOFF_group,'std_830_res']))
        APOFF_this_group_max_not_t_corr = max(abs(df_830_830eq_APOFF.loc[f_APOFF_group,'std_830_res']))

        d_for_df_EPOFF_t_corr_summary_stats["mean"].append(EPOFF_this_group_mean_t_corr)
        d_for_df_APOFF_t_corr_summary_stats["mean"].append(APOFF_this_group_mean_t_corr)
        d_for_df_EPOFF_not_t_corr_summary_stats["mean"].append(EPOFF_this_group_mean_not_t_corr)
        d_for_df_APOFF_not_t_corr_summary_stats["mean"].append(APOFF_this_group_mean_not_t_corr)
        d_for_df_EPOFF_t_corr_summary_stats["stdev"].append(EPOFF_this_group_stdev_t_corr)
        d_for_df_APOFF_t_corr_summary_stats["stdev"].append(APOFF_this_group_stdev_t_corr)
        d_for_df_EPOFF_not_t_corr_summary_stats["stdev"].append(EPOFF_this_group_stdev_not_t_corr)
        d_for_df_APOFF_not_t_corr_summary_stats["stdev"].append(APOFF_this_group_stdev_not_t_corr) 
        d_for_df_EPOFF_t_corr_summary_stats["max"].append(EPOFF_this_group_max_t_corr)
        d_for_df_APOFF_t_corr_summary_stats["max"].append(APOFF_this_group_max_t_corr)
        d_for_df_EPOFF_not_t_corr_summary_stats["max"].append(EPOFF_this_group_max_not_t_corr)
        d_for_df_APOFF_not_t_corr_summary_stats["max"].append(APOFF_this_group_max_not_t_corr)

        list_of_df_APOFF.append(df_830_830eq_APOFF.loc[f_APOFF_group,:])
        list_of_df_EPOFF.append(df_830_830eq_EPOFF.loc[f_EPOFF_group,:])

    df_EPOFF_t_corr_summary_stats = pd.DataFrame(d_for_df_EPOFF_t_corr_summary_stats)
    df_APOFF_t_corr_summary_stats = pd.DataFrame(d_for_df_APOFF_t_corr_summary_stats)
    df_EPOFF_not_t_corr_summary_stats = pd.DataFrame(d_for_df_EPOFF_not_t_corr_summary_stats)
    df_APOFF_not_t_corr_summary_stats = pd.DataFrame(d_for_df_APOFF_not_t_corr_summary_stats)

    return df_EPOFF_t_corr_summary_stats, df_APOFF_t_corr_summary_stats, \
        df_EPOFF_not_t_corr_summary_stats, df_APOFF_not_t_corr_summary_stats

def plot_and_produce_report(sn,path_to_data,validation_text_filename):
    #%%
    if sys.platform.startswith('win'):
        dir_sep = '\\'
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        dir_sep = '/'
    reports_path = str(os.path.normpath( path_to_data + '%sreports' % (dir_sep)))
    if not os.path.exists(reports_path):
        os.mkdir(reports_path)
    figs_path = str(os.path.normpath(reports_path + '%sfigs' % (dir_sep)))
    if not os.path.exists(figs_path):
        os.mkdir(figs_path)
    csv_path = str(os.path.normpath(reports_path + '%scsv' % (dir_sep)))
    if not os.path.exists(csv_path):
        os.mkdir(csv_path)
    path_to_ALL = path_to_data + dir_sep + 'ALL'
    
    # load slopes from oven test a
    # with open('slope_cal_1.pickle','rb') as f:
    #     slope_cal_1 = pickle.load(f)
    # with open('slope_cal_2.pickle', 'rb') as f:
    #     slope_cal_2 = pickle.load(f)

    # with open('avgslope_cal_1.pickle','rb') as f:
    #     avgslope_cal_1 = pickle.load(f)
    # with open('avgslope_cal_2.pickle','rb') as f:
    #     avgslope_cal_2 = pickle.load(f)

    # pd.set_option('max_columns',None)
    # print('Data from slope_cal_1 is like...')
    # print(slope_cal_1.describe(include='all'))
    # print('Headers from slope_cal_1...')
    # print(slope_cal_1.head())
    # print('Data from slope_cal_2 is like...')
    # print(slope_cal_2.describe(include='all'))
    # print('Headers from slope_cal_2...')
    # print(slope_cal_2.head())
    # pd.reset_option('max_columns')  # Pascal, added to check on pickle files
    # slope_cal_1.to_csv(path_or_buf='.\\slope_cal_1_csv.csv')
    # slope_cal_2.to_csv(path_or_buf='.\\slope_cal_2_csv.csv')

    # slope_cal_1_all = pd.read_csv('./post_processing/config/slope_cal_1_csv_all_6_10.csv',index_col=0)
    # slope_cal_2_all = pd.read_csv('./post_processing/config/slope_cal_2_csv_all_6_10.csv',index_col=0)
    # slope_cal_1_all = pd.read_csv('./post_processing/config/slope_cal_1_csv_7_6.csv',index_col=0)
    # slope_cal_2_all = pd.read_csv('./post_processing/config/slope_cal_2_csv_7_6.csv',index_col=0)
    # slope_cal_1_all = pd.read_csv('./post_processing/config/slope_cal_1_csv_all_8_12.csv',index_col=0)
    # slope_cal_2_all = pd.read_csv('./post_processing/config/slope_cal_2_csv_all_8_12.csv',index_col=0)
    slope_cal_1_all = pd.read_csv('./post_processing/config/slope_cal_1_csv_all_8_25.csv',index_col=0)
    slope_cal_2_all = pd.read_csv('./post_processing/config/slope_cal_2_csv_all_8_25.csv',index_col=0)


    # pd.set_option('max_columns',None)
    # print('Data from slope_cal_1_all is like...')
    # print(slope_cal_1_all.describe(include='all'))
    # print('Headers from slope_cal_1_all...')
    # print(slope_cal_1_all.head())
    # print('Data from slope_cal_2_all is like...')
    # print(slope_cal_2_all.describe(include='all'))
    # print('Headers from slope_cal_2_all...')
    # print(slope_cal_2_all.head())
    # pd.reset_option('max_columns')  # Pascal, added to check on pickle files

    #replace old pickle data with the latest from csv
    #del slope_cal_1, slope_cal_2
    slope_cal_1 = slope_cal_1_all; slope_cal_2 = slope_cal_2_all

    # SN for 1004 is 5272, licor SN for 1005 is 5030

    #choose licor to get span 2 slope*********************
    #licorsernum = 'cga-5270'
    ASVCO2sn2LICORsn = {'1004':'cga-5272', '1005': 'cga-5030','1006':'cga-5270',\
    '1008':'cga-5176','1009':'cga-5178','3CA8A2533':'cga-5375','3CA8A2535':'cga-5353',\
    '3CA8A2538':'cga-5379','3CADC7571':'cga-5354','3CADC7573':'cga-5177',\
    '3CADC7565':'cga-5377','3CB942928':'cga-5378', '3CB94292E':'cga-5380',\
    '3CD6D1DD5':'cga-5376','3CD94292C':'cga-5352','1011':'cga-5180','ASVTEST12':'cga-5081'}
    licorsernum = ASVCO2sn2LICORsn[sn]

    #choose 1st or 2nd cal for slope
    # calnum = slope_cal_1  # older choice, dates back to code from Sophie on May 17th, 2021
    calnum = slope_cal_2

    mask_ota = (calnum['Serialnum'] == licorsernum) & \
            (calnum.index == 'co2kspan2')  

    oventesta_licor_cal2_span2 = calnum[mask_ota]  
    print("oventesta_licor_cal2_span2 = ",oventesta_licor_cal2_span2)
    # load span2 coefficient from 20 deg 2nd cal
    # with open('span2_20deg_cal2_temp.pickle', 'rb') as f:  
    #     span2_20deg_cal2_temp = pickle.load(f)

    # Instead of using pickle file, use csv file with LI-COR serial numbers 5081, 5177 and 5269
    # span2_20deg_cal2_temp = pd.read_csv('./post_processing/config/span2_20deg_cal2_temp_csv_all_6_10.csv')
    #
    # Changed on 8/5/2021 per Noah's direction, use averaged co2kspan2, etc. see email from Sophie on 7/28/2021
    # span2_20deg_cal2_temp = pd.read_csv('./post_processing/config/tempavg_20deg_span2_cal1.csv') 

    # Changed on 8/12/2021 for temporary data post processing on 3CA8A2535
    # span2_20deg_cal2_temp = pd.read_csv('./post_processing/config/twenty_degree_avg_no_T_Ramp_down_07_06.csv')

    # Changed on 8/13/2021 for larger dataset and long term processing
    # span2_20deg_cal2_temp = pd.read_csv('./post_processing/config/span2_20deg_cal2_temp_avg_csv_all_8_12.csv')
    # span2_20deg_cal2_temp = pd.read_csv('./post_processing/config/span2_20deg_cal2_temp_avg_csv_all_8_16.csv')

    span2_20deg_cal2_temp = pd.read_csv('./post_processing/config/span2_20deg_cal2_temp_avg_csv_all_8_25.csv') 

    print(f'licorsernum = {licorsernum}')
    mask_sp2 = span2_20deg_cal2_temp.serialnum == licorsernum  
    span2_20deg_cal2_temp_licor = span2_20deg_cal2_temp[mask_sp2]
    print(f'co2kspan2 = {span2_20deg_cal2_temp_licor.co2kspan2}')
    # set span2 (S1_lab) coefficient to 20 deg span 2 cal 2
    # Correct Sc1(lab) for the temperature change from the temperature at which Sc1(lab) was calibrated (linear eq based on oven testA results) to get Sc1(Tcorr).
    S1_lab = float(span2_20deg_cal2_temp_licor.co2kspan2)#-0.00591593#0.005772628#float(span2_20deg_cal2_temp_licor.co2kspan2)

    # set actual span2 temperature with setpoint 20 deg
    span2_temp = float(span2_20deg_cal2_temp_licor.celltemp.values)#27.0689#22.13#float(span2_20deg_cal2_temp_licor.celltemp.values)

    # set slope of licor from oven test a results
    print(f'slope = {oventesta_licor_cal2_span2.slope.values}')
    slope_licor = float(oventesta_licor_cal2_span2.slope.values)#0#-0.00260834#float(oventesta_licor_cal2_span2.slope.values)

    # double check values
    print(f'double check: S1_lab = {S1_lab}, span2_temp = {span2_temp}, slope_licor = {slope_licor}')

    #%%
    #load data here *******************************************
    #filenames=glob.glob('./ASV1002_March2021_ALL_Files/2021*.txt')
    #filenames=glob.glob('./1006/20210429/2021*.txt')#***************
    #filenames=glob.glob('./data/1006/20210430/ALL/2021*.txt')#***************
    filenames=glob.glob(path_to_ALL + '/2021*.txt')
    filenames.sort()
    #print(filenames)

    # get date range from the filenames
    start_filename_without_path=re.findall(r'\d+_\d+\.txt',filenames[0])[0]
    end_filename_without_path=re.findall(r'\d+_\d+\.txt',filenames[-1])[0]
    date_range=(start_filename_without_path,end_filename_without_path)

    data_APOFF=[]
    data_EPOFF=[]
    df = pd.DataFrame()

    for i in range(len(filenames)):
        if i > 0:
            filename_data = filenames[i]
            filename_coeff = filenames[i] #when data and coeff wasn't lined up, used filenames[i-1]
            
            #print(filenames[i])
            
            # Pascal, bypass files without coefficients
            COEFF_found_in_file=False
            with open(filename_coeff) as f:
                if 'COEFF' in f.read():
                    COEFF_found_in_file =True
            f.close()
            del f

            # Pascal, only process the file if COEFF was found in the file
            if COEFF_found_in_file:
                res_from_each_file_APOFF = postprocesslicorspan2_w_mode(filename_coeff, filename_data, \
                    span2_temp, S1_lab, slope_licor, "APOFF")
                res_from_each_file_EPOFF = postprocesslicorspan2_w_mode(filename_coeff, filename_data, \
                    span2_temp, S1_lab, slope_licor, "EPOFF")
                #print (i, res_from_each_file)
                data_APOFF.append(res_from_each_file_APOFF)
                data_EPOFF.append(res_from_each_file_EPOFF)


    #Pascal, needed to rewrite for different file types in different folders
    # ALL_filenames=glob.glob('./data/1006/20210430/ALL/2021*.txt')#***************
    # ALL_filenames.sort()
    # #print(filenames)
    # COEFF_filenames=glob.glob('./data/1006/20210430/COEFF/2021*.txt')#***************
    # COEFF_filenames.sort()
    # for i in range(len(ALL_filenames)):
    #     if i > 0:
    #         filename_data = ALL_filenames[i]
    #         filename_coeff = COEFF_filenames[i] #when data and coeff wasn't lined up, used filenames[i-1]
    #         res_from_each_file = postprocesslicorspan2(filename_coeff, filename_data, span2_temp, S1_lab, slope_licor)
    #         #print (i, res_from_each_file)
    #         data.append(res_from_each_file)


    residuals_830_830eq_APOFF = df.append(data_APOFF,ignore_index=True)
    residuals_830_830eq_APOFF = residuals_830_830eq_APOFF.rename(columns={0: 'CO2', 1: 'CO2_recalc', 2: 'Res (meas-recalc)'}) 
    #residuals_830_830eq=pd.concat(res_from_each_file, ignore_index=True, sort=False)

    residuals_830_830eq_EPOFF = df.append(data_EPOFF,ignore_index=True)
    residuals_830_830eq_EPOFF = residuals_830_830eq_EPOFF.rename(columns={0: 'CO2', 1: 'CO2_recalc', 2: 'Res (meas-recalc)'})

    #line up average residuals with filenames
    filenames_ser=pd.Series([elem[0:] for elem in filenames] )

    df_830_830eq_APOFF = pd.concat([filenames_ser,residuals_830_830eq_APOFF], axis=1)
    df_830_830eq_EPOFF = pd.concat([filenames_ser,residuals_830_830eq_EPOFF], axis=1)

    ############################## Plotting for APOFF ##############################
    fig1 = plt.figure(1)
    #ax11 = plt.gca()
    l1=plt.scatter(df_830_830eq_APOFF.gas_standard, df_830_830eq_APOFF.std_830_res)
    l2=plt.scatter(df_830_830eq_APOFF.gas_standard, df_830_830eq_APOFF.std_830recalc_res)
    
    # ax11.scatter(df_830_830eq_APOFF.gas_standard, df_830_830eq_APOFF.std_830_res,\
    #     label='Measured CO2 - standard CO2, ppm')
    # ax11.scatter(df_830_830eq_APOFF.gas_standard, df_830_830eq_APOFF.std_830recalc_res,\
    #     label='Recalculated CO2 - standard CO2, ppm')
    
    plt.legend([l1,l2],['Measured CO2 - standard CO2, ppm','Recalculated CO2 - standard CO2, ppm'])  # Pascal, changed legend
    # plt.grid(b=True,which='major',axis='both')  # Pascal, added grid
    # plt.ylabel('Avg CO2 residual, measured CO2 - CO2 gas standard (ppm)')  # Pascal, changed ylabel 
    # plt.xlabel('CO2 gas standard') 
    # plt.title('APOFF ' + sn + ' ' + date_range[0][0:8])

    #fig1.legend(loc='upper left')  # Pascal, changed legend
    plt.grid(b=True,which='major',axis='both')  # Pascal, added grid
    plt.ylabel('Avg CO2 residual, measured CO2 - CO2 gas standard (ppm)')  # Pascal, changed ylabel 
    plt.xlabel('CO2 gas standard') 
    plt.title('APOFF ' + sn + ' ' + date_range[0][0:8])

    #save plot as...
    saveplotname_recalc_vs_no_recalc_APOFF = figs_path + dir_sep + \
        'APOFF_' + sn + '_' + date_range[0][0:8] + '_T_recalc_vs_No_T_recalc.png'

    #plt.savefig(saveplotname_recalc_vs_no_recalc_APOFF)  # Pascal, changed to png file
    fig1.savefig(saveplotname_recalc_vs_no_recalc_APOFF)  # Pascal, changed to png file

    ############################## Plotting for EPOFF ##############################
    fig2 = plt.figure(2)
    #ax21 = plt.gca()
    
    l3=plt.scatter(df_830_830eq_EPOFF.gas_standard, df_830_830eq_EPOFF.std_830_res)
    l4=plt.scatter(df_830_830eq_EPOFF.gas_standard, df_830_830eq_EPOFF.std_830recalc_res)

    #plt.legend([l1,l2],['Meas - std','Recalc-std'])
    plt.legend([l3,l4],['Measured CO2 - standard CO2, ppm','Recalculated CO2 - standard CO2, ppm'])  # Pascal, changed legend
    plt.grid(b=True,which='major',axis='both')  # Pascal, added grid
    #plt.ylabel('Avg CO2 res (830-std)') 
    plt.ylabel('Avg CO2 residual, measured CO2 - CO2 gas standard (ppm)')  # Pascal, changed ylabel 
    plt.xlabel('CO2 gas standard') 
    #plt.savefig('830_830eq_res_all.jpg')
    plt.title('EPOFF ' + sn + ' ' + date_range[0][0:8])

    #save plot as...
    saveplotname_recalc_vs_no_recalc_EPOFF = figs_path + dir_sep + \
        'EPOFF_' + sn + '_' + date_range[0][0:8] + '_T_recalc_vs_No_T_recalc.png'
    #plt.savefig(saveplotname_recalc_vs_no_recalc_EPOFF)  # Pascal, changed to png file
    fig2.savefig(saveplotname_recalc_vs_no_recalc_EPOFF)  # Pascal, changed to png file

    ###################### Dataframes for APOFF ################################
    df_830_830eq_avg_APOFF = df_830_830eq_APOFF.groupby('gas_standard').std_830recalc_res.agg(['mean','std'])
    df_830_830eq_avg_APOFF = df_830_830eq_avg_APOFF.reset_index()
    df_830_830eq_avg_APOFF = df_830_830eq_avg_APOFF.rename(columns={'std':'stdev'})

    ###################### Dataframes for EPOFF ################################
    df_830_830eq_avg_EPOFF = df_830_830eq_EPOFF.groupby('gas_standard').std_830recalc_res.agg(['mean','std'])
    df_830_830eq_avg_EPOFF = df_830_830eq_avg_EPOFF.reset_index()
    df_830_830eq_avg_EPOFF = df_830_830eq_avg_EPOFF.rename(columns={'std':'stdev'})

    # To Do - put df_830_830eq_avg into table for reportlab
    # print('Data from df_830_830eq_avg is like...')
    # print(df_830_830eq_avg_EPOFF.describe())
    # print(df_830_830eq_avg_EPOFF.head())
    pd.set_option('max_columns',None)
    print('Data from df_830_830eq_APOFF is like...')
    # print(df_830_830eq_APOFF.describe())
    # print(df_830_830eq_APOFF.head())

    print('Data from df_830_830eq_EPOFF is like...')
    # print(df_830_830eq_EPOFF.describe())
    # print(df_830_830eq_EPOFF.head())
    pd.reset_option('max_columns')

    ##################### Save Dataframes as csv in the csv folder ##################
    savecsvname_APOFF = csv_path + dir_sep \
        + "APOFF_" + sn + '_' + date_range[0][0:8] + '.csv'
    savecsvname_EPOFF = csv_path + dir_sep \
        + "EPOFF_" + sn + '_' + date_range[0][0:8] + '.csv'
    df_830_830eq_APOFF.to_csv(savecsvname_APOFF,index=False)
    df_830_830eq_EPOFF.to_csv(savecsvname_EPOFF,index=False)

    ##################### More plots for APOFF ######################################

    lengthofrun = len(df_830_830eq_APOFF)
    numberofruns = round(lengthofrun/8)

    #number of runs
    n = numberofruns

    #save plot name as *******************
    #change this, changed by Pascal, 6/22/2021
    saveplotname_APOFF_T_recalc = figs_path + dir_sep \
        + "APOFF_" + sn + '_' + date_range[0][0:8] + '_T_recalc.png' 
    fig_title_APOFF_T_recalc =  "APOFF_" + sn + '_' + date_range[0][0:8] + '_T_recalc'

    #create colorbar
    colors = cm.cool(np.linspace(0,1,n))

    #make plot with one color for each run
    fig3, (ax31,ax32) = plt.subplots(1,2)

    for run in range(0,n):
        #print(run)

        startind=run*8
        endind=startind+8

        p=ax31.scatter(df_830_830eq_APOFF.gas_standard.iloc[startind:endind],df_830_830eq_APOFF.std_830recalc_res.iloc[startind:endind], color=colors[run])
        ax32.scatter(df_830_830eq_APOFF.gas_standard.iloc[startind:endind],df_830_830eq_APOFF.std_830recalc_res.iloc[startind:endind], color=colors[run])
        maxy=max(df_830_830eq_APOFF.std_830recalc_res)+3

        labels = list(range(1,n+1))


    ax31.set_title(fig_title_APOFF_T_recalc) 
    ax31.set_xlabel('Standard Gas Concentration (ppm)')
    #ax31.set_ylabel('Residual (ppm)')
    ax31.set_ylabel('Residual, measured CO2 - CO2 gas standard (ppm)')  # Pascal, changed ylabel
    ax31.set_xlim([-100,2700])
    ax31.set_ylim([-maxy,maxy])
    ax31.axhline(y=0,color='k', linestyle='--')

    #plt.grid(b=True,which='major',axis='both')  # Pascal, added grid

    #ax32.legend([1,2,3,4,5], loc='lower left')
    ax32.legend(labels, bbox_to_anchor=(1.9, 1), loc="upper right",framealpha=0, title='# of run', fontsize="small")

    ax32.set_title('Zoomed <1000 ppm')
    ax32.set_xlabel('Std Gas Conc (ppm)')
    #ax32.set_ylabel('Residual (ppm)')
    ax32.set_ylabel('Residual, measured CO2 - CO2 gas standard (ppm)')  # Pascal, changed ylabel
    ax32.set_xlim([-100,1100])
    ax32.set_ylim([-5,5])
    ax32.axhline(y=0,color='k', linestyle='--')

    ax31.grid(b=True,which='major',axis='both')  # Pascal, added grid
    ax32.grid(b=True,which='major',axis='both')  # Pascal, added grid

    fig3.set_size_inches(10,6) # Pascal, added to expand size

    ##################### More plots for EPOFF ######################################

    lengthofrun = len(df_830_830eq_EPOFF)
    numberofruns = round(lengthofrun/8)

    #number of runs
    n = numberofruns

    #save plot name as *******************
    #change this, changed by Pascal, 6/22/2021
    saveplotname_EPOFF_T_recalc = figs_path + dir_sep \
        + "EPOFF_" + sn + '_' + date_range[0][0:8] + '_T_recalc.png' 
    fig_title_EPOFF_T_recalc =  "EPOFF_" + sn + '_' + date_range[0][0:8] + '_T_recalc'

    #create colorbar
    colors = cm.cool(np.linspace(0,1,n))

    #make plot with one color for each run
    fig4, (ax41,ax42) = plt.subplots(1,2)

    for run in range(0,n):
        #print(run)

        startind=run*8
        endind=startind+8

        p=ax41.scatter(df_830_830eq_EPOFF.gas_standard.iloc[startind:endind],df_830_830eq_EPOFF.std_830recalc_res.iloc[startind:endind], color=colors[run])
        ax42.scatter(df_830_830eq_EPOFF.gas_standard.iloc[startind:endind],df_830_830eq_EPOFF.std_830recalc_res.iloc[startind:endind], color=colors[run])
        maxy=max(df_830_830eq_EPOFF.std_830recalc_res)+3

        labels = list(range(1,n+1))


    ax41.set_title(fig_title_EPOFF_T_recalc) 
    ax41.set_xlabel('Standard Gas Concentration (ppm)')
    ax41.set_ylabel('Residual, measured CO2 - CO2 gas standard (ppm)')  # Pascal, changed ylabel
    ax41.set_xlim([-100,2700])
    ax41.set_ylim([-maxy,maxy])
    ax41.axhline(y=0,color='k', linestyle='--')

    #plt.grid(b=True,which='major',axis='both')  # Pascal, added grid

    #ax2.legend([1,2,3,4,5], loc='lower left')
    ax42.legend(labels, bbox_to_anchor=(1.9, 1), loc="upper right",framealpha=0, title='# of run', fontsize="small")

    ax42.set_title('Zoomed <1000 ppm')
    ax42.set_xlabel('Std Gas Conc (ppm)')
    #ax2.set_ylabel('Residual (ppm)')
    ax42.set_ylabel('Residual, measured CO2 - CO2 gas standard (ppm)')  # Pascal, changed ylabel
    ax42.set_xlim([-100,1100])
    ax42.set_ylim([-5,5])
    ax42.axhline(y=0,color='k', linestyle='--')

    ax41.grid(b=True,which='major',axis='both')  # Pascal, added grid
    ax42.grid(b=True,which='major',axis='both')  # Pascal, added grid

    fig4.set_size_inches(10,6) # Pascal, added to expand size


    plt.tight_layout()
    #plt.show()

    fig3.savefig(saveplotname_APOFF_T_recalc, dpi=300) #change this filename
    fig4.savefig(saveplotname_EPOFF_T_recalc, dpi=300) #change this filename

    #################### Create a pdf report ##########################
    from create_a_pdf import generate_validation_report, generate_bigger_validation_report
    from create_a_pdf import generate_bigger_validation_report_reordered


    #sn='1006'
    figure_filenames_and_sizes=((saveplotname_APOFF_T_recalc,6,18/5.0),\
        (saveplotname_recalc_vs_no_recalc_APOFF,6,4),\
        (saveplotname_EPOFF_T_recalc,6,18/5.0),\
        (saveplotname_recalc_vs_no_recalc_EPOFF,6,4))

    ###################### Dataframes for APOFF ######################   
    # temperature corrected mean and standard deviation by gas standard
    df_4_table_tcorr_APOFF=df_830_830eq_avg_APOFF  

    # uncorrected mean and standard deviation by gas standard
    df_4_table_not_tcorr_APOFF = df_830_830eq_APOFF.groupby('gas_standard').std_830_res.agg(['mean','std'])  
    df_4_table_not_tcorr_APOFF = df_4_table_not_tcorr_APOFF.reset_index()
    df_4_table_not_tcorr_APOFF = df_4_table_not_tcorr_APOFF.rename(columns={'std':'stdev'})

    ###################### Dataframes for EPOFF ######################
    # temperature corrected mean and standard deviation by gas standard
    df_4_table_tcorr_EPOFF=df_830_830eq_avg_EPOFF  

    # uncorrected mean and standard deviation by gas standard
    df_4_table_not_tcorr_EPOFF = df_830_830eq_EPOFF.groupby('gas_standard').std_830_res.agg(['mean','std'])  
    df_4_table_not_tcorr_EPOFF = df_4_table_not_tcorr_EPOFF.reset_index()
    df_4_table_not_tcorr_EPOFF = df_4_table_not_tcorr_EPOFF.rename(columns={'std':'stdev'})
    
    #### Collect Tuple of dataframes ####
    tuple_of_df_4_tables=(df_4_table_tcorr_APOFF,df_4_table_not_tcorr_APOFF,\
        df_4_table_tcorr_EPOFF,df_4_table_not_tcorr_EPOFF)

    # generate_validation_report(reports_path,sn,date_range,figure_filenames_and_sizes,\
    #     df_4_table_tcorr_APOFF,df_4_table_not_tcorr_APOFF,validation_text_filename)

    generate_bigger_validation_report(reports_path,sn,date_range,figure_filenames_and_sizes,\
        tuple_of_df_4_tables,validation_text_filename)

def plot_and_produce_report_w_extra_checks(sn,path_to_data,validation_text_filename):
    #%%
    if sys.platform.startswith('win'):
        dir_sep = '\\'
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        dir_sep = '/'
    reports_path = str(os.path.normpath( path_to_data + '%sreports' % (dir_sep)))
    if not os.path.exists(reports_path):
        os.mkdir(reports_path)
    figs_path = str(os.path.normpath(reports_path + '%sfigs' % (dir_sep)))
    if not os.path.exists(figs_path):
        os.mkdir(figs_path)
    csv_path = str(os.path.normpath(reports_path + '%scsv' % (dir_sep)))
    if not os.path.exists(csv_path):
        os.mkdir(csv_path)
    path_to_ALL = path_to_data + dir_sep + 'ALL'
    

    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    slope_cal_1_all = pd.read_csv(PROJECT_ROOT + '/code/post_processing/config/slope_cal_1_csv_all_8_25.csv',index_col=0)
    slope_cal_2_all = pd.read_csv(PROJECT_ROOT + '/code/post_processing/config/slope_cal_2_csv_all_8_25.csv',index_col=0)


    slope_cal_1 = slope_cal_1_all; slope_cal_2 = slope_cal_2_all

    # SN for 1004 is 5272, licor SN for 1005 is 5030

    #choose licor to get span 2 slope*********************
    #licorsernum = 'cga-5270'
    ASVCO2sn2LICORsn = {'1004':'cga-5272', '1005': 'cga-5030','1006':'cga-5270',\
    '1008':'cga-5176','1009':'cga-5178','3CA8A2533':'cga-5375','3CA8A2535':'cga-5353',\
    '3CA8A2538':'cga-5379','3CADC7571':'cga-5354','3CADC7573':'cga-5177',\
    '3CADC7565':'cga-5377','3CB942928':'cga-5378','XYXYXYXY':'cga-5378','3CB94292E':'cga-5380',\
    '3CD6D1DD5':'cga-5376','3CD94292C':'cga-5352'}
    licorsernum = ASVCO2sn2LICORsn[sn]

    #choose 1st or 2nd cal for slope
    # calnum = slope_cal_1  # older choice, dates back to code from Sophie on May 17th, 2021
    calnum = slope_cal_2

    mask_ota = (calnum['Serialnum'] == licorsernum) & \
            (calnum.index == 'co2kspan2')  

    oventesta_licor_cal2_span2 = calnum[mask_ota]  
    print("oventesta_licor_cal2_span2 = ",oventesta_licor_cal2_span2)
    
    # load span2 coefficient from 20 deg 2nd cal    
    span2_20deg_cal2_temp = pd.read_csv(PROJECT_ROOT + '/code/post_processing/config/span2_20deg_cal2_temp_avg_csv_all_8_25.csv')  

    print(f'licorsernum = {licorsernum}')
    mask_sp2 = span2_20deg_cal2_temp.serialnum == licorsernum  
    span2_20deg_cal2_temp_licor = span2_20deg_cal2_temp[mask_sp2]
    print(f'co2kspan2 = {span2_20deg_cal2_temp_licor.co2kspan2}')
    
    # set span2 (S1_lab) coefficient to 20 deg span 2 cal 2
    # Correct Sc1(lab) for the temperature change from the temperature at which Sc1(lab) was calibrated (linear eq based on oven testA results) to get Sc1(Tcorr).
    S1_lab = float(span2_20deg_cal2_temp_licor.co2kspan2)#-0.00591593#0.005772628#float(span2_20deg_cal2_temp_licor.co2kspan2)

    # set actual span2 temperature with setpoint 20 deg
    span2_temp = float(span2_20deg_cal2_temp_licor.celltemp.values)#27.0689#22.13#float(span2_20deg_cal2_temp_licor.celltemp.values)

    # set slope of licor from oven test a results
    print(f'slope = {oventesta_licor_cal2_span2.slope.values}')
    slope_licor = float(oventesta_licor_cal2_span2.slope.values)#0#-0.00260834#float(oventesta_licor_cal2_span2.slope.values)

    # double check values
    print(f'double check: S1_lab = {S1_lab}, span2_temp = {span2_temp}, slope_licor = {slope_licor}')

    #%%
    #load data here *******************************************
    #filenames=glob.glob(path_to_ALL + '/2021*.txt')
    filenames=glob.glob(path_to_ALL + '/20*.txt')
    filenames.sort()
    #print(filenames)

    # get date range from the filenames
    start_filename_without_path=re.findall(r'\d+_\d+\.txt',filenames[0])[0]
    end_filename_without_path=re.findall(r'\d+_\d+\.txt',filenames[-1])[0]
    date_range=(start_filename_without_path,end_filename_without_path)

    data_APOFF=[]
    data_EPOFF=[]
    df = pd.DataFrame()

    fault_text = ''  # new feature added 9/21/2021
    for i in range(len(filenames)):
        if i > 0:
            filename_data = filenames[i]
            filename_coeff = filenames[i] #when data and coeff wasn't lined up, used filenames[i-1]
            
            # Pascal, bypass files without coefficients
            COEFF_found_in_file=False
            with open(filename_coeff) as f:
                if 'COEFF' in f.read():
                    COEFF_found_in_file =True
            f.close()
            del f

            # Pascal, only process the file if COEFF was found in the file
            if COEFF_found_in_file:
                res_from_each_file_APOFF = postprocesslicorspan2_w_mode(filename_coeff, filename_data, \
                    span2_temp, S1_lab, slope_licor, "APOFF")
                res_from_each_file_EPOFF = postprocesslicorspan2_w_mode(filename_coeff, filename_data, \
                    span2_temp, S1_lab, slope_licor, "EPOFF")
                #print (i, res_from_each_file)
                #print(f'filename = {filenames[i]}')
                fault_text += extra_range_checks(filenames[i])  # new feature added 9/21/2021
                #print(f'fault_text = {fault_text}')
                data_APOFF.append(res_from_each_file_APOFF)
                data_EPOFF.append(res_from_each_file_EPOFF)
                
    print(fault_text)

    #Pascal, needed to rewrite for different file types in different folders
    # ALL_filenames=glob.glob('./data/1006/20210430/ALL/2021*.txt')#***************
    # ALL_filenames.sort()
    # #print(filenames)
    # COEFF_filenames=glob.glob('./data/1006/20210430/COEFF/2021*.txt')#***************
    # COEFF_filenames.sort()
    # for i in range(len(ALL_filenames)):
    #     if i > 0:
    #         filename_data = ALL_filenames[i]
    #         filename_coeff = COEFF_filenames[i] #when data and coeff wasn't lined up, used filenames[i-1]
    #         res_from_each_file = postprocesslicorspan2(filename_coeff, filename_data, span2_temp, S1_lab, slope_licor)
    #         #print (i, res_from_each_file)
    #         data.append(res_from_each_file)


    residuals_830_830eq_APOFF = df.append(data_APOFF,ignore_index=True)
    residuals_830_830eq_APOFF = residuals_830_830eq_APOFF.rename(columns={0: 'CO2', 1: 'CO2_recalc', 2: 'Res (meas-recalc)'}) 
    #residuals_830_830eq=pd.concat(res_from_each_file, ignore_index=True, sort=False)

    residuals_830_830eq_EPOFF = df.append(data_EPOFF,ignore_index=True)
    residuals_830_830eq_EPOFF = residuals_830_830eq_EPOFF.rename(columns={0: 'CO2', 1: 'CO2_recalc', 2: 'Res (meas-recalc)'})

    #line up average residuals with filenames
    filenames_ser=pd.Series([elem[0:] for elem in filenames] )

    df_830_830eq_APOFF = pd.concat([filenames_ser,residuals_830_830eq_APOFF], axis=1)
    df_830_830eq_EPOFF = pd.concat([filenames_ser,residuals_830_830eq_EPOFF], axis=1)

    ##### New feature to add +/- values from t-distribution #####
    alpha = 0.05  # significance level = 5% 
    # df = 5  # degrees of freedom
    mask_low_ppm = (df_830_830eq_APOFF['gas_standard'] >= 0.0) & \
        (df_830_830eq_APOFF['gas_standard'] <= 800.0)
    dof_APOFF = len(df_830_830eq_APOFF.loc[mask_low_ppm])-1  # degrees of freedom                                     
    v = t.ppf(1 - alpha/2, dof_APOFF) 
    print(f'v: {v}, dof: {dof_APOFF}')
    res_mean_APOFF = df_830_830eq_APOFF['std_830_res'].loc[mask_low_ppm].mean()
    res_standard_error_APOFF = df_830_830eq_APOFF['std_830_res'].loc[mask_low_ppm].sem(ddof=1)
    plus_or_minus = v*res_standard_error_APOFF
    print(f'Mean APOFF residual between 0 and 750ppm: {res_mean_APOFF} +/- {plus_or_minus}ppm, 95% confidence')
    APOFF_std = df_830_830eq_APOFF['std_830_res'].loc[mask_low_ppm].std(ddof=1)
    print(f'Standard deviation of APOFF between 0 and 800ppm: {APOFF_std}ppm')

    mask_low_ppm = (df_830_830eq_EPOFF['gas_standard'] >= 0.0) & \
        (df_830_830eq_EPOFF['gas_standard'] <= 800.0)
    dof_EPOFF = len(df_830_830eq_EPOFF.loc[mask_low_ppm])-1  # degrees of freedom                                     
    v = t.ppf(1 - alpha/2, dof_EPOFF)
    print(f'v: {v}, dof: {dof_EPOFF}')
    res_mean_EPOFF = df_830_830eq_EPOFF['std_830_res'].loc[mask_low_ppm].mean()
    res_standard_error_EPOFF = df_830_830eq_EPOFF['std_830_res'].loc[mask_low_ppm].sem(ddof=1)
    plus_or_minus = v*res_standard_error_EPOFF
    print(f'Mean EPOFF residual between 0 and 750ppm: {res_mean_EPOFF} +/- {plus_or_minus}ppm, 95% confidence')
    EPOFF_std = df_830_830eq_EPOFF['std_830_res'].loc[mask_low_ppm].std(ddof=1)
    print(f'standard deviation of EPOFF between 0 and 800ppm: {EPOFF_std}ppm')

    df_APOFF_group = df_830_830eq_APOFF.groupby('gas_standard')
    df_APOFF_group_stats = df_APOFF_group['std_830_res'].agg(['mean','std','count','sem'])

    mean_plus_or_minus_list = []
    for idx, row in df_APOFF_group_stats.iterrows():
        #val = row['count']
        #print(f'type(row[\'count\']) = {type(val)}')
        dof_row = row['count']-1
        v = t.ppf(1-alpha/2,dof_row)
        print(f'v: {v}, dof: {dof_row}')
        mean_plus_or_minus_list.append(v*row['sem'])
    df_APOFF_group_stats['mean_plus_or_minus'] = mean_plus_or_minus_list
    pd.set_option('max_columns',None)
    print('df_APOFF_group_stats is like...')
    print(df_APOFF_group_stats)
    pd.reset_option('max_columns')
    
    df_EPOFF_group = df_830_830eq_EPOFF.groupby('gas_standard')
    df_EPOFF_group_stats = df_EPOFF_group['std_830_res'].agg(['mean','std','count','sem'])

    mean_plus_or_minus_list = []
    for idx, row in df_EPOFF_group_stats.iterrows():
        #val = row['count']
        #print(f'type(row[\'count\']) = {type(val)}')
        dof_row = row['count']-1
        v = t.ppf(1-alpha/2,dof_row)
        print(f'v: {v}, dof: {dof_row}')
        mean_plus_or_minus_list.append(v*row['sem'])
    df_EPOFF_group_stats['mean_plus_or_minus'] = mean_plus_or_minus_list
    pd.set_option('max_columns',None)
    print('df_EPOFF_group_stats is like...')
    print(df_EPOFF_group_stats)
    pd.reset_option('max_columns')

    ############################## Plotting for APOFF ##############################
    fig1 = plt.figure(1)
    #ax11 = plt.gca()
    l1=plt.scatter(df_830_830eq_APOFF.gas_standard, df_830_830eq_APOFF.std_830_res)
    l2=plt.scatter(df_830_830eq_APOFF.gas_standard, df_830_830eq_APOFF.std_830recalc_res)
    
    # ax11.scatter(df_830_830eq_APOFF.gas_standard, df_830_830eq_APOFF.std_830_res,\
    #     label='Measured CO2 - standard CO2, ppm')
    # ax11.scatter(df_830_830eq_APOFF.gas_standard, df_830_830eq_APOFF.std_830recalc_res,\
    #     label='Recalculated CO2 - standard CO2, ppm')
    
    plt.legend([l1,l2],['Measured CO2 - standard CO2, ppm','Recalculated CO2 - standard CO2, ppm'])  # Pascal, changed legend
    # plt.grid(b=True,which='major',axis='both')  # Pascal, added grid
    # plt.ylabel('Avg CO2 residual, measured CO2 - CO2 gas standard (ppm)')  # Pascal, changed ylabel 
    # plt.xlabel('CO2 gas standard') 
    # plt.title('APOFF ' + sn + ' ' + date_range[0][0:8])

    #fig1.legend(loc='upper left')  # Pascal, changed legend
    plt.grid(b=True,which='major',axis='both')  # Pascal, added grid
    plt.ylabel('Avg CO2 residual, measured CO2 - CO2 gas standard (ppm)')  # Pascal, changed ylabel 
    plt.xlabel('CO2 gas standard') 
    plt.title('APOFF ' + sn + ' ' + date_range[0][0:8])

    #save plot as...
    saveplotname_recalc_vs_no_recalc_APOFF = figs_path + dir_sep + \
        'APOFF_' + sn + '_' + date_range[0][0:8] + '_T_recalc_vs_No_T_recalc.png'

    #plt.savefig(saveplotname_recalc_vs_no_recalc_APOFF)  # Pascal, changed to png file
    fig1.savefig(saveplotname_recalc_vs_no_recalc_APOFF)  # Pascal, changed to png file

    ############################## Plotting for EPOFF ##############################
    fig2 = plt.figure(2)
    #ax21 = plt.gca()
    
    l3=plt.scatter(df_830_830eq_EPOFF.gas_standard, df_830_830eq_EPOFF.std_830_res)
    l4=plt.scatter(df_830_830eq_EPOFF.gas_standard, df_830_830eq_EPOFF.std_830recalc_res)

    #plt.legend([l1,l2],['Meas - std','Recalc-std'])
    plt.legend([l3,l4],['Measured CO2 - standard CO2, ppm','Recalculated CO2 - standard CO2, ppm'])  # Pascal, changed legend
    plt.grid(b=True,which='major',axis='both')  # Pascal, added grid
    #plt.ylabel('Avg CO2 res (830-std)') 
    plt.ylabel('Avg CO2 residual, measured CO2 - CO2 gas standard (ppm)')  # Pascal, changed ylabel 
    plt.xlabel('CO2 gas standard') 
    #plt.savefig('830_830eq_res_all.jpg')
    plt.title('EPOFF ' + sn + ' ' + date_range[0][0:8])

    #save plot as...
    saveplotname_recalc_vs_no_recalc_EPOFF = figs_path + dir_sep + \
        'EPOFF_' + sn + '_' + date_range[0][0:8] + '_T_recalc_vs_No_T_recalc.png'
    #plt.savefig(saveplotname_recalc_vs_no_recalc_EPOFF)  # Pascal, changed to png file
    fig2.savefig(saveplotname_recalc_vs_no_recalc_EPOFF)  # Pascal, changed to png file

    ###################### Dataframes for APOFF ################################
    df_830_830eq_avg_APOFF = df_830_830eq_APOFF.groupby('gas_standard').std_830recalc_res.agg(['mean','std'])
    df_830_830eq_avg_APOFF = df_830_830eq_avg_APOFF.reset_index()
    df_830_830eq_avg_APOFF = df_830_830eq_avg_APOFF.rename(columns={'std':'stdev'})

    ###################### Dataframes for EPOFF ################################
    df_830_830eq_avg_EPOFF = df_830_830eq_EPOFF.groupby('gas_standard').std_830recalc_res.agg(['mean','std'])
    df_830_830eq_avg_EPOFF = df_830_830eq_avg_EPOFF.reset_index()
    df_830_830eq_avg_EPOFF = df_830_830eq_avg_EPOFF.rename(columns={'std':'stdev'})

    # To Do - put df_830_830eq_avg into table for reportlab
    # print('Data from df_830_830eq_avg is like...')
    # print(df_830_830eq_avg_EPOFF.describe())
    # print(df_830_830eq_avg_EPOFF.head())
    pd.set_option('max_columns',None)
    print('Data from df_830_830eq_APOFF is like...')
    print(df_830_830eq_APOFF.describe())
    print(df_830_830eq_APOFF.head())

    print('Data from df_830_830eq_EPOFF is like...')
    print(df_830_830eq_EPOFF.describe())
    print(df_830_830eq_EPOFF.head())
    pd.reset_option('max_columns')

    ##################### Save Dataframes as csv in the csv folder ##################
    savecsvname_APOFF = csv_path + dir_sep \
        + "APOFF_" + sn + '_' + date_range[0][0:8] + '.csv'
    savecsvname_EPOFF = csv_path + dir_sep \
        + "EPOFF_" + sn + '_' + date_range[0][0:8] + '.csv'
    df_830_830eq_APOFF.to_csv(savecsvname_APOFF,index=False)
    df_830_830eq_EPOFF.to_csv(savecsvname_EPOFF,index=False)

    ##################### More plots for APOFF ######################################

    lengthofrun = len(df_830_830eq_APOFF)
    numberofruns = round(lengthofrun/8)

    #number of runs
    n = numberofruns

    #save plot name as *******************
    #change this, changed by Pascal, 6/22/2021
    saveplotname_APOFF_T_recalc = figs_path + dir_sep \
        + "APOFF_" + sn + '_' + date_range[0][0:8] + '_T_recalc.png' 
    fig_title_APOFF_T_recalc =  "APOFF_" + sn + '_' + date_range[0][0:8] + '_T_recalc'

    #create colorbar
    colors = cm.cool(np.linspace(0,1,n))

    #make plot with one color for each run
    fig3, (ax31,ax32) = plt.subplots(1,2)

    for run in range(0,n):
        #print(run)

        startind=run*8
        endind=startind+8

        p=ax31.scatter(df_830_830eq_APOFF.gas_standard.iloc[startind:endind],df_830_830eq_APOFF.std_830recalc_res.iloc[startind:endind], color=colors[run])
        ax32.scatter(df_830_830eq_APOFF.gas_standard.iloc[startind:endind],df_830_830eq_APOFF.std_830recalc_res.iloc[startind:endind], color=colors[run])
        maxy=max(df_830_830eq_APOFF.std_830recalc_res)+3

        labels = list(range(1,n+1))


    ax31.set_title(fig_title_APOFF_T_recalc) 
    ax31.set_xlabel('Standard Gas Concentration (ppm)')
    #ax31.set_ylabel('Residual (ppm)')
    ax31.set_ylabel('Residual, measured CO2 - CO2 gas standard (ppm)')  # Pascal, changed ylabel
    ax31.set_xlim([-100,2700])
    ax31.set_ylim([-maxy,maxy])
    ax31.axhline(y=0,color='k', linestyle='--')

    #plt.grid(b=True,which='major',axis='both')  # Pascal, added grid

    #ax32.legend([1,2,3,4,5], loc='lower left')
    ax32.legend(labels, bbox_to_anchor=(1.9, 1), loc="upper right",framealpha=0, title='# of run', fontsize="small")

    ax32.set_title('Zoomed <1000 ppm')
    ax32.set_xlabel('Std Gas Conc (ppm)')
    #ax32.set_ylabel('Residual (ppm)')
    ax32.set_ylabel('Residual, measured CO2 - CO2 gas standard (ppm)')  # Pascal, changed ylabel
    ax32.set_xlim([-100,1100])
    ax32.set_ylim([-5,5])
    ax32.axhline(y=0,color='k', linestyle='--')

    ax31.grid(b=True,which='major',axis='both')  # Pascal, added grid
    ax32.grid(b=True,which='major',axis='both')  # Pascal, added grid

    fig3.set_size_inches(10,6) # Pascal, added to expand size

    ##################### More plots for EPOFF ######################################

    lengthofrun = len(df_830_830eq_EPOFF)
    numberofruns = round(lengthofrun/8)

    #number of runs
    n = numberofruns

    #save plot name as *******************
    #change this, changed by Pascal, 6/22/2021
    saveplotname_EPOFF_T_recalc = figs_path + dir_sep \
        + "EPOFF_" + sn + '_' + date_range[0][0:8] + '_T_recalc.png' 
    fig_title_EPOFF_T_recalc =  "EPOFF_" + sn + '_' + date_range[0][0:8] + '_T_recalc'

    #create colorbar
    colors = cm.cool(np.linspace(0,1,n))

    #make plot with one color for each run
    fig4, (ax41,ax42) = plt.subplots(1,2)

    for run in range(0,n):
        #print(run)

        startind=run*8
        endind=startind+8

        p=ax41.scatter(df_830_830eq_EPOFF.gas_standard.iloc[startind:endind],df_830_830eq_EPOFF.std_830recalc_res.iloc[startind:endind], color=colors[run])
        ax42.scatter(df_830_830eq_EPOFF.gas_standard.iloc[startind:endind],df_830_830eq_EPOFF.std_830recalc_res.iloc[startind:endind], color=colors[run])
        maxy=max(df_830_830eq_EPOFF.std_830recalc_res)+3

        labels = list(range(1,n+1))


    ax41.set_title(fig_title_EPOFF_T_recalc) 
    ax41.set_xlabel('Standard Gas Concentration (ppm)')
    ax41.set_ylabel('Residual, measured CO2 - CO2 gas standard (ppm)')  # Pascal, changed ylabel
    ax41.set_xlim([-100,2700])
    ax41.set_ylim([-maxy,maxy])
    ax41.axhline(y=0,color='k', linestyle='--')

    #plt.grid(b=True,which='major',axis='both')  # Pascal, added grid

    #ax2.legend([1,2,3,4,5], loc='lower left')
    ax42.legend(labels, bbox_to_anchor=(1.9, 1), loc="upper right",framealpha=0, title='# of run', fontsize="small")

    ax42.set_title('Zoomed <1000 ppm')
    ax42.set_xlabel('Std Gas Conc (ppm)')
    #ax2.set_ylabel('Residual (ppm)')
    ax42.set_ylabel('Residual, measured CO2 - CO2 gas standard (ppm)')  # Pascal, changed ylabel
    ax42.set_xlim([-100,1100])
    ax42.set_ylim([-5,5])
    ax42.axhline(y=0,color='k', linestyle='--')

    ax41.grid(b=True,which='major',axis='both')  # Pascal, added grid
    ax42.grid(b=True,which='major',axis='both')  # Pascal, added grid

    fig4.set_size_inches(10,6) # Pascal, added to expand size


    plt.tight_layout()
    #plt.show()

    fig3.savefig(saveplotname_APOFF_T_recalc, dpi=300) #change this filename
    fig4.savefig(saveplotname_EPOFF_T_recalc, dpi=300) #change this filename

    #################### Create a pdf report ##########################
    from create_a_pdf_dry import generate_validation_report, generate_bigger_validation_report
    from create_a_pdf_dry import generate_bigger_validation_report_reordered
    from create_a_pdf_dry import generate_bigger_validation_report_reordered_Feb_2022


    #sn='1006'
    figure_filenames_and_sizes=((saveplotname_APOFF_T_recalc,6,18/5.0),\
        (saveplotname_recalc_vs_no_recalc_APOFF,6,4),\
        (saveplotname_EPOFF_T_recalc,6,18/5.0),\
        (saveplotname_recalc_vs_no_recalc_EPOFF,6,4))

    ###################### Dataframes for APOFF ######################   
    # temperature corrected mean and standard deviation by gas standard
    df_4_table_tcorr_APOFF=df_830_830eq_avg_APOFF  

    # uncorrected mean and standard deviation by gas standard
    df_4_table_not_tcorr_APOFF = df_830_830eq_APOFF.groupby('gas_standard').std_830_res.agg(['mean','std'])  
    df_4_table_not_tcorr_APOFF = df_4_table_not_tcorr_APOFF.reset_index()
    df_4_table_not_tcorr_APOFF = df_4_table_not_tcorr_APOFF.rename(columns={'std':'stdev'})

    ###################### Dataframes for EPOFF ######################
    # temperature corrected mean and standard deviation by gas standard
    df_4_table_tcorr_EPOFF=df_830_830eq_avg_EPOFF  

    # uncorrected mean and standard deviation by gas standard
    df_4_table_not_tcorr_EPOFF = df_830_830eq_EPOFF.groupby('gas_standard').std_830_res.agg(['mean','std'])  
    df_4_table_not_tcorr_EPOFF = df_4_table_not_tcorr_EPOFF.reset_index()
    df_4_table_not_tcorr_EPOFF = df_4_table_not_tcorr_EPOFF.rename(columns={'std':'stdev'})
    
        
    ##### New feature to add +/- values from t-distribution #####
    alpha = 0.05  # significance level = 5% 
    # df = 5  # degrees of freedom
    mask_low_ppm = (df_830_830eq_APOFF['gas_standard'] >= 0.0) & \
        (df_830_830eq_APOFF['gas_standard'] <= 800.0)
    dof_APOFF = len(df_830_830eq_APOFF.loc[mask_low_ppm])-1  # degrees of freedom                                     
    v = t.ppf(1 - alpha/2, dof_APOFF) 
    print(f'v: {v}, dof: {dof_APOFF}')
    res_mean_APOFF = df_830_830eq_APOFF['std_830_res'].loc[mask_low_ppm].mean()
    res_standard_error_APOFF = df_830_830eq_APOFF['std_830_res'].loc[mask_low_ppm].sem(ddof=1)
    plus_or_minus_APOFF = v*res_standard_error_APOFF
    print(f"""Mean APOFF residual between 0 and 750ppm: {res_mean_APOFF} 
    +/- {plus_or_minus_APOFF}ppm, 95% confidence""")
    APOFF_std = df_830_830eq_APOFF['std_830_res'].loc[mask_low_ppm].std(ddof=1)
    print(f'Standard deviation of APOFF between 0 and 800ppm: {APOFF_std}ppm')

    mask_low_ppm = (df_830_830eq_EPOFF['gas_standard'] >= 0.0) & \
        (df_830_830eq_EPOFF['gas_standard'] <= 750.0)
    dof_EPOFF = len(df_830_830eq_EPOFF.loc[mask_low_ppm])-1  # degrees of freedom                                     
    v = t.ppf(1 - alpha/2, dof_EPOFF)
    print(f'v: {v}, dof: {dof_EPOFF}')
    res_mean_EPOFF = df_830_830eq_EPOFF['std_830_res'].loc[mask_low_ppm].mean()
    res_standard_error_EPOFF = df_830_830eq_EPOFF['std_830_res'].loc[mask_low_ppm].sem(ddof=1)
    plus_or_minus_EPOFF = v*res_standard_error_EPOFF
    print(f"""Mean EPOFF residual between 0 and 750ppm: {res_mean_EPOFF} 
    +/- {plus_or_minus_EPOFF}ppm, 95% confidence""")
    EPOFF_std = df_830_830eq_EPOFF['std_830_res'].loc[mask_low_ppm].std(ddof=1)
    print(f'standard deviation of EPOFF between 0 and 800ppm: {EPOFF_std}ppm')

    df_0_thru_750_range_EPOFF = pd.DataFrame({'res_mean':[res_mean_EPOFF],\
        'conf_95':[plus_or_minus_EPOFF]})
    df_0_thru_750_range_APOFF = pd.DataFrame({'res_mean':[res_mean_APOFF],\
        'conf_95':[plus_or_minus_APOFF]})

    df_EPOFF_t_corr_summary_stats, df_APOFF_t_corr_summary_stats, \
    df_EPOFF_not_t_corr_summary_stats, df_APOFF_not_t_corr_summary_stats = \
    get_summary_stats_df_by_group(df_830_830eq_EPOFF,df_830_830eq_APOFF)

    #### Collect Tuple of dataframes ####
    legacy_report_format = False
    if ( legacy_report_format ):
        tuple_of_df_4_tables=(df_4_table_tcorr_APOFF,df_4_table_not_tcorr_APOFF,\
            df_4_table_tcorr_EPOFF,df_4_table_not_tcorr_EPOFF)
        generate_bigger_validation_report_reordered(reports_path,sn,date_range,figure_filenames_and_sizes,\
        tuple_of_df_4_tables,validation_text_filename,fault_text)
    else:
        tuple_of_df_4_tables=(df_APOFF_t_corr_summary_stats,df_APOFF_not_t_corr_summary_stats,\
            df_EPOFF_t_corr_summary_stats,df_EPOFF_not_t_corr_summary_stats,df_0_thru_750_range_APOFF,\
            df_0_thru_750_range_EPOFF)
        generate_bigger_validation_report_reordered_Feb_2022(reports_path,sn,date_range,figure_filenames_and_sizes,\
        tuple_of_df_4_tables,validation_text_filename,fault_text)

    # generate_validation_report(reports_path,sn,date_range,figure_filenames_and_sizes,\
    #     df_4_table_tcorr_APOFF,df_4_table_not_tcorr_APOFF,validation_text_filename)

    # generate_bigger_validation_report(reports_path,sn,date_range,figure_filenames_and_sizes,\
    #     tuple_of_df_4_tables,validation_text_filename)
    
    # new feature added 9/21/2021
    # generate_bigger_validation_report(reports_path,sn,date_range,figure_filenames_and_sizes,\
    #     tuple_of_df_4_tables,validation_text_filename,fault_text)



if __name__ == "__main__":
    #### 1006 ####
    # sn='1006'
    # path_to_ALL='./data/1006/20210430/ALL' # unnecessary at the moment
    # path_to_data = './data/1006/20210430/'
    # validation_text_filename = '.\\data\\1006\\20210430\\1006_Validation_20210430-003429.txt'
    
    #### 1008 ####
    # sn='1008'
    # path_to_ALL='./data/1008/20210429/ALL' # unnecessary at the moment
    # path_to_data = './data/1008/20210429/'
    # validation_text_filename = '.\\data\\1008\\20210429\\1008_Validation_20210429-164729.txt'

    #### 1009 ####
    # sn='1009'
    # path_to_data = './data/1009/20210428/'
    # validation_text_filename = '.\\data\\1009\\20210428\\1009_Validation_20210427-171323.txt'

    #### 1005 ####
    # sn='1005'
    # path_to_data = './data/1005/20210514/'
    # validation_text_filename = '.\\data\\1005\\20210514\\1005_Validation_20210514-004141.txt'

    #### 1004 ####
    # sn='1004'
    # path_to_data = './data/1004/20210512/'
    # validation_text_filename = '.\\data\\1004\\20210512\\1004_Validation_20210512-210237.txt'

    #### 3CA8A2535 ####
    # sn='3CA8A2535'
    # path_to_data = './data/3CA8A2535/'
    # validation_text_filename = '.\\data\\3CA8A2535\\3CA8A2535_Validation_20210811-183246.txt'

    #### 3CA8A2533 ####
    # sn='3CA8A2533'
    # path_to_data = './data/3CA8A2533/'
    # validation_text_filename = '.\\data\\3CA8A2533\\3CA8A2533_Validation_20210812-192805.txt'
    # sn='3CA8A2533'
    # path_to_data = './data/3CA8A2533/20210914/'
    # validation_text_filename = '.\\data\\3CA8A2533\\20210914\\2533_Validation_20210910-200321.txt'

    #### 3CA8A2538 ####
    # sn='3CA8A2538'
    # path_to_data = './data/3CA8A2538/'
    # validation_text_filename = '.\\data\\3CA8A2538\\3CA8A2538_Validation_20210813-221913.txt'

    #### 3CADC7573 ####
    # sn='3CADC7573'
    # path_to_data = './data/3CADC7573/'
    # validation_text_filename = '.\\data\\3CADC7573\\3CADC7573_Validation_20210818-225409.txt'

    #### 3CB942928 #####
    # sn='3CB942928'
    # path_to_data='./data/3CB942928/'
    # validation_text_filename='.\\data\\3CB942928\\3CB942928_Validation_20210915-001423.txt'

    #### 3CB94292E ####
    # sn = '3CB94292E'
    # path_to_data = './data/3CB94292E/'
    # validation_text_filename = '.\\data\\3CB94292E\\3CB94292E_Validation_20210921-223759.txt'

    #### XYXYXYXY #####
    sn='XYXYXYXY'
    path_to_data='./data/XYXYXYXY/'
    validation_text_filename='.\\data\\XYXYXYXY\\XYXYXYXY_Validation_20210915-001423.txt'
    
    # plot_and_produce_report(sn,path_to_data,validation_text_filename)

    #### 3CD6D1DD5 ####
    # sn = '3CD6D1DD5'
    # path_to_data = './data/3CD6D1DD5/'
    # validation_text_filename = '.\\data\\3CD6D1DD5\\3CD6D1DD5_Validation_20211005-225409.txt'

    #### 3CADC7571 ####
    # sn = '3CADC7571'
    # path_to_data = './data/3CADC7571/'
    # validation_text_filename = '.\\data\\3CADC7571\\3CADC7571_Validation_20210817-222532.txt'

    #### 3CADC7565 ####
    # sn = '3CADC7565'
    # path_to_data = './data/3CADC7565/'
    # validation_text_filename = '.\\data\\3CADC7565\\3CADC7565_Validation_20210820-230908.txt'

    #### 3CD94292C ####
    # sn = '3CD94292C'
    # path_to_data = './data/3CD94292C/'
    # validation_text_filename = '.\\data\\3CD94292C\\3CD94292C_Validation_20211012-210208.txt'

    #### ASV1011 ####
    #sn = 'ASV1011'
    #path_to_data = './data/ASV1011/validation/'
    #validation_text_filename = '.\\data\\ASV1011\\Validation\\ASV1011_VAL_20220208-212207.txt'
    #validation_text_filename = '.\\data\\ASV1011\\Validation\\ASV1011_VAL_20220203-001104.txt'

    # New feature in 9/21/2021
    plot_and_produce_report_w_extra_checks(sn,path_to_data,validation_text_filename)

    #print(extra_range_checks('./data/XYXYXYXY/ALL/20210914_180017.txt'))