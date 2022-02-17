import numpy as np
import pandas as pd

def pf_limits(gas_conc,calc_type='Tcorr',output_type='combined'):
    '''
    The values below are gathered from the following document
    https://docs.google.com/document/d/1nNsXKDLFjpTtatEaTFqVL7Rxe7GRthU4CqpGqM7NBt8/edit#heading=h.gjdgxs
    
    Text excerpt is the following:
    The system passes validation if the CO2 value falls within the criteria listed below.
    MAPCO2 passes when the residual between the standard reference gas and MAPCO2 measurements is less than:
	    0 -  <2 (if higher then run again to see if there is residual from the 2500)
        200 <4 ppm
        300, 400, 500 less than 3 ppm
        800,  less than 3 ppm (this may be adjusted)
        2500 ppm less than 40 (typically less than 20)

    Pass-fail limits exist as tuples of (gas concentration, limit) pairs
    '''
    # 6/8/2021
    # These limits will apply to temperature corrected units.
    # We would like to have a bare minimum of 3 samples, ideally 5 or 6 samples.
    # everything between 300 to 800ppm will be 2ppm, 0 will be 2ppm, 
    # 50 to 300ppm will have a limit of 3ppm,
    # above 1000ppm 6ppm, 1500ppm 8ppm, 2000ppm 12ppm
    #
    # From MApCO2 SOP document as of 2021:
    # GAS_LIMITS=[(0, 2),(200, 4),
    #     (300, 3),(400, 3),
    #     (500, 3),(800, 3),
    #     (2500, 40)]
    
    # For temperature corrected data, GAS LIMITS are as follows
    if ( calc_type == 'Tcorr' and output_type == 'combined'):
        # Adjusted 400, 500 and 800 from 2ppm to 3ppm on 6/11/2021
        GAS_LIMITS=[(0, 2),(50,3),
        (300, 3),(400, 3),
        (500,3), (800, 3),
        (1000, 6), (1500, 8),
        (2000, 12), (2500, 20)]

        # Legacy from MApCO2
        # GAS_LIMITS=[(0, 2),(200, 4),
        #     (300, 3),(400, 3),
        #     (500, 3),(800, 3),
        #     (2500, 40)]
    elif ( calc_type != 'Tcorr' and output_type == 'combined'):
        # GAS_LIMITS=[(0, 2),(200, 4),
        # (300, 3),(400, 3),
        # (500, 3),(800,3),
        # (1000, 10),(1500,15),
        # (2000,20),(2500, 25)]

        # Hybridized limit created on 6/11/2021 for non-Temperature corrected stuff
        GAS_LIMITS=[(0, 2),(200, 4),
            (300, 3),(400, 3),
            (500, 3),(800,3),
            (1000, 10),(1500,25),
            (2000,35),(2500, 40)]

    elif ( calc_type == 'Tcorr' and output_type == 'mean'):
        #initially set, 6/28/2021
        # GAS_LIMITS=[(0, 2),(50,3),
        # (300, 3),(400, 3),
        # (500,3), (800, 3),
        # (1000, 6), (1500, 8),
        # (2000, 12), (2500, 20)]

        #amended, 2/7/2021
        GAS_LIMITS=[(0, 1),(2,1),
        (2.001, 4),(300, 4),
        (300.001,2), (775, 2),
        (775.001, 7), (1075, 8),
        (1075.001, 14), (2575, 14)]
    
    elif ( calc_type != 'Tcorr' and output_type == 'mean'):
        #initially set, 6/28/2021
        # GAS_LIMITS=[(0, 2),(200, 4),
        #     (300, 3),(400, 3),
        #     (500, 3),(800,3),
        #     (1000, 10),(1500,25),
        #     (2000,35),(2500, 40)]
        
        #amended, 2/7/2021
        GAS_LIMITS=[(0, 1),(2,1),
        (2.001, 4),(300, 4),
        (300.001,2), (775, 2),
        (775.001, 7), (1075, 8),
        (1075.001, 14), (2575, 14)]

    elif ( calc_type == 'Tcorr' and output_type == 'stdev'):
        #initially set, 6/28/2021
        # GAS_LIMITS=[(0, 1), (50,1),
        # (300, 1), (400, 1),
        # (500,1), (800, 1),
        # (1000, 1), (1500, 1),
        # (2000, 1), (2500, 1)]

        #amended, 2/7/2021
        GAS_LIMITS=[(0, 0.5),(2,0.5),
        (2.001, 0.5),(300, 0.5),
        (300.001,1), (775, 1),
        (775.001, 2), (1075, 2),
        (1075.001, 2), (2575, 2)]
    
    elif ( calc_type != 'Tcorr' and output_type == 'stdev'):
        #initially set, 6/28/2021
        # GAS_LIMITS=[(0, 1), (200, 1),
        #     (300, 1), (400, 1),
        #     (500, 1), (800, 1),
        #     (1000, 2), (1500, 2),
        #     (2000, 2), (2500, 2)]

        #amended, 2/7/2021
        GAS_LIMITS=[(0, 0.5),(2,0.5),
        (2.001, 0.5),(300, 0.5),
        (300.001,1), (775, 1),
        (775.001, 2), (1075, 2),
        (1075.001, 2), (2575, 2)]
    
    else:
        raise Exception(f'Unknown argument {output_type} given to pf_limits()')

    N = len(GAS_LIMITS)
    if ( gas_conc < GAS_LIMITS[0][0] or gas_conc > GAS_LIMITS[N-1][0]):
        raise Exception(f'''{gas_conc} ppm is outside limits of the GAS_LIMITS table in
        pass_fail_processing.py, which must be between {GAS_LIMITS[0][0]} and 
        {GAS_LIMITS[N-1][0]} ppm''')

    #Limits with the nearest gas concentration value will be linearly interpolated
    
    #find index, idx where the closest gas concentrations are found
    #they are expected to be greater than the lower_idx and less than
    #the value found in the upper_idx
    lower_idx=N-1
    while( lower_idx > 0 and gas_conc < GAS_LIMITS[lower_idx][0] ):
        lower_idx -= 1
    #print(f'lower_idx = {lower_idx}')
    upper_idx=lower_idx
    while ( upper_idx < N and gas_conc > GAS_LIMITS[upper_idx][0]):
        upper_idx += 1
    #print(f'upper_idx = {upper_idx}')
    
    if ( upper_idx != lower_idx ):
        #calculate slope, delta_y / delta_x, where x is concentration and y is the limit
        delta_x = GAS_LIMITS[upper_idx][0]-GAS_LIMITS[lower_idx][0]
        delta_y = GAS_LIMITS[upper_idx][1]-GAS_LIMITS[lower_idx][1]
        slope = delta_y / delta_x
        # simple linear interpolation of limits, y = slope*(x - x0) + y0
        pf_limit = slope*(gas_conc-GAS_LIMITS[lower_idx][0])+GAS_LIMITS[lower_idx][1]
    else:
        pf_limit = GAS_LIMITS[lower_idx][1]
    
    return pf_limit

def calculate_pf_df(df_with_stdev_mean,n_std_dev,calc_type='Tcorr',output_type='combined'):
    #print(f'calc_type = {calc_type}, output_type = {output_type}')
    if ( output_type == 'combined' ):
        pass_or_fail_column=[]
        for idx, row in df_with_stdev_mean.iterrows():
            if (abs(row["mean"])+n_std_dev*row["stdev"]) > pf_limits(row["gas_standard"],\
                calc_type, output_type):
                pass_or_fail_column.append("FAIL") 
            else:
                pass_or_fail_column.append("PASS")
            
        upper_limit_column = [pf_limits(row["gas_standard"],calc_type) for idx, row in df_with_stdev_mean.iterrows()]
        
        df_4_table_2 = df_with_stdev_mean.copy()
        df_4_table_2["pass_or_fail"] = pass_or_fail_column
        df_4_table_2["upper_limit"] = upper_limit_column
        df_4_table_2["margin"] = df_4_table_2["upper_limit"]-abs(df_4_table_2["mean"])\
            -n_std_dev*df_4_table_2["stdev"]
    
    elif ( output_type == 'separate' ):
        #### calculate pass/fail for the mean only ####
        mean_pass_or_fail_column=[]
        for idx, row in df_with_stdev_mean.iterrows():
            if (abs(row["mean"])) > pf_limits(row["gas_standard"],calc_type, 'mean'):
                mean_pass_or_fail_column.append("FAIL") 
            else:
                mean_pass_or_fail_column.append("PASS")
            
        mean_upper_limit_column = [pf_limits(row["gas_standard"],calc_type, 'mean')\
             for idx, row in df_with_stdev_mean.iterrows()]
        
        df_4_table_2 = df_with_stdev_mean.copy()
        df_4_table_2["mean_pass_or_fail"] = mean_pass_or_fail_column
        df_4_table_2["mean_upper_limit"] = mean_upper_limit_column

        #### calculate pass/fail for standard deviation only ####
        stdev_pass_or_fail_column=[]
        for idx, row in df_with_stdev_mean.iterrows():
            if (abs(row["stdev"])) > pf_limits(row["gas_standard"],calc_type, 'stdev'):
                stdev_pass_or_fail_column.append("FAIL") 
            else:
                stdev_pass_or_fail_column.append("PASS")
            
        stdev_upper_limit_column = [pf_limits(row["gas_standard"],calc_type, 'stdev')\
             for idx, row in df_with_stdev_mean.iterrows()]
        
        df_4_table_2["stdev_pass_or_fail"] = stdev_pass_or_fail_column
        df_4_table_2["stdev_upper_limit"] = stdev_upper_limit_column
        
    else:
        raise Exception(f'Unknown argument {output_type} given to calculate_pf_df()')

    return df_4_table_2

def pf_limits_v2(gas_conc,calc_type='Tcorr',output_type='combined'):
    '''
    The values below are gathered from the following document
    https://docs.google.com/document/d/1nNsXKDLFjpTtatEaTFqVL7Rxe7GRthU4CqpGqM7NBt8/edit#heading=h.gjdgxs
    
    Text excerpt is the following:
    The system passes validation if the CO2 value falls within the criteria listed below.
    MAPCO2 passes when the residual between the standard reference gas and MAPCO2 measurements is less than:
	    0 -  <2 (if higher then run again to see if there is residual from the 2500)
        200 <4 ppm
        300, 400, 500 less than 3 ppm
        800,  less than 3 ppm (this may be adjusted)
        2500 ppm less than 40 (typically less than 20)

    Pass-fail limits exist as tuples of (gas concentration, limit) pairs
    '''
    # 6/8/2021
    # These limits will apply to temperature corrected units.
    # We would like to have a bare minimum of 3 samples, ideally 5 or 6 samples.
    # everything between 300 to 800ppm will be 2ppm, 0 will be 2ppm, 
    # 50 to 300ppm will have a limit of 3ppm,
    # above 1000ppm 6ppm, 1500ppm 8ppm, 2000ppm 12ppm
    #
    # From MApCO2 SOP document as of 2021:
    # GAS_LIMITS=[(0, 2),(200, 4),
    #     (300, 3),(400, 3),
    #     (500, 3),(800, 3),
    #     (2500, 40)]
    

    if ( calc_type == 'Tcorr' and output_type == 'mean'):
        #initially set, 6/28/2021
        # GAS_LIMITS=[(0, 2),(50,3),
        # (300, 3),(400, 3),
        # (500,3), (800, 3),
        # (1000, 6), (1500, 8),
        # (2000, 12), (2500, 20)]

        #amended, 2/7/2021
        GAS_LIMITS=[(0, 1),(2,1),
        (2.001, 4),(300, 4),
        (300.001,2), (775, 2),
        (775.001, 7), (1075, 7),
        (1075.001, 14), (2575, 14)]
    
    elif ( calc_type != 'Tcorr' and output_type == 'mean'):
        #initially set, 6/28/2021
        # GAS_LIMITS=[(0, 2),(200, 4),
        #     (300, 3),(400, 3),
        #     (500, 3),(800,3),
        #     (1000, 10),(1500,25),
        #     (2000,35),(2500, 40)]
        
        #amended, 2/7/2021
        GAS_LIMITS=[(0, 1),(2,1),
        (2.001, 4),(300, 4),
        (300.001,2), (775, 2),
        (775.001, 7), (1075, 7),
        (1075.001, 14), (2575, 14)]

    elif ( calc_type == 'Tcorr' and output_type == 'stdev'):
        #initially set, 6/28/2021
        # GAS_LIMITS=[(0, 1), (50,1),
        # (300, 1), (400, 1),
        # (500,1), (800, 1),
        # (1000, 1), (1500, 1),
        # (2000, 1), (2500, 1)]

        #amended, 2/7/2021
        GAS_LIMITS=[(0, 0.5),(2,0.5),
        (2.001, 0.5),(300, 0.5),
        (300.001,1), (775, 1),
        (775.001, 2), (1075, 2),
        (1075.001, 2), (2575, 2)]
    
    elif ( calc_type != 'Tcorr' and output_type == 'stdev'):
        #initially set, 6/28/2021
        # GAS_LIMITS=[(0, 1), (200, 1),
        #     (300, 1), (400, 1),
        #     (500, 1), (800, 1),
        #     (1000, 2), (1500, 2),
        #     (2000, 2), (2500, 2)]

        #amended, 2/7/2021
        GAS_LIMITS=[(0, 0.5),(2,0.5),
        (2.001, 0.5),(300, 0.5),
        (300.001,1), (775, 1),
        (775.001, 2), (1075, 2),
        (1075.001, 2), (2575, 2)]

    elif ( calc_type == 'Tcorr' and output_type == 'max'):
        #initially set, 6/28/2021
        # GAS_LIMITS=[(0, 1), (50,1),
        # (300, 1), (400, 1),
        # (500,1), (800, 1),
        # (1000, 1), (1500, 1),
        # (2000, 1), (2500, 1)]

        #amended, 2/7/2021
        GAS_LIMITS=[(0, 2.0),(2,2.0),
        (2.001, 4.0),(300, 4.0),
        (300.001,4.0), (775, 4.0),
        (775.001, 7), (1075, 7),
        (1075.001, 15), (2575, 15)]
    
    elif ( calc_type != 'Tcorr' and output_type == 'max'):
        #initially set, 6/28/2021
        # GAS_LIMITS=[(0, 1), (200, 1),
        #     (300, 1), (400, 1),
        #     (500, 1), (800, 1),
        #     (1000, 2), (1500, 2),
        #     (2000, 2), (2500, 2)]

        #amended, 2/7/2021
        GAS_LIMITS=[(0, 2.0),(2,2.0),
        (2.001, 4.0),(300, 4.0),
        (300.001,4.0), (775, 4.0),
        (775.001, 7), (1075, 7),
        (1075.001, 15), (2575, 15)]
    
    else:
        raise Exception(f'Unknown argument {output_type} given to pf_limits()')

    N = len(GAS_LIMITS)
    if ( gas_conc < GAS_LIMITS[0][0] or gas_conc > GAS_LIMITS[N-1][0]):
        raise Exception(f'''{gas_conc} ppm is outside limits of the GAS_LIMITS table in
        pass_fail_processing.py, which must be between {GAS_LIMITS[0][0]} and 
        {GAS_LIMITS[N-1][0]} ppm''')

    #Limits with the nearest gas concentration value will be linearly interpolated
    
    #find index, idx where the closest gas concentrations are found
    #they are expected to be greater than the lower_idx and less than
    #the value found in the upper_idx
    lower_idx=N-1
    while( lower_idx > 0 and gas_conc < GAS_LIMITS[lower_idx][0] ):
        lower_idx -= 1
    #print(f'lower_idx = {lower_idx}')
    upper_idx=lower_idx
    while ( upper_idx < N and gas_conc > GAS_LIMITS[upper_idx][0]):
        upper_idx += 1
    #print(f'upper_idx = {upper_idx}')
    
    if ( upper_idx != lower_idx ):
        #calculate slope, delta_y / delta_x, where x is concentration and y is the limit
        delta_x = GAS_LIMITS[upper_idx][0]-GAS_LIMITS[lower_idx][0]
        delta_y = GAS_LIMITS[upper_idx][1]-GAS_LIMITS[lower_idx][1]
        slope = delta_y / delta_x
        # simple linear interpolation of limits, y = slope*(x - x0) + y0
        pf_limit = slope*(gas_conc-GAS_LIMITS[lower_idx][0])+GAS_LIMITS[lower_idx][1]
    else:
        pf_limit = GAS_LIMITS[lower_idx][1]
    
    return pf_limit

def calculate_pf_df_v2(df_with_stdev_mean_max,calc_type='Tcorr'):
    #### calculate pass/fail for the mean only ####

    mean_pass_or_fail_column=[]
    for idx, row in df_with_stdev_mean_max.iterrows():
        ref_gas_midpoint = (row["gas_standard_lower"]+row["gas_standard_upper"])/2.0
        if (abs(row["mean"])) > pf_limits_v2(ref_gas_midpoint,calc_type, 'mean'):
            mean_pass_or_fail_column.append("FAIL") 
        else:
            mean_pass_or_fail_column.append("PASS")
            
    mean_upper_limit_column = [pf_limits_v2((row["gas_standard_lower"]+\
        row["gas_standard_upper"])/2.0, calc_type, 'mean')\
        for idx, row in df_with_stdev_mean_max.iterrows()]
        
    df_4_table_2 = df_with_stdev_mean_max.copy()
    df_4_table_2["mean_pass_or_fail"] = mean_pass_or_fail_column
    df_4_table_2["mean_upper_limit"] = mean_upper_limit_column

    #### calculate pass/fail for standard deviation only ####
    stdev_pass_or_fail_column=[]
    for idx, row in df_with_stdev_mean_max.iterrows():
        ref_gas_midpoint = (row["gas_standard_lower"]+row["gas_standard_upper"])/2.0
        if (abs(row["stdev"])) > pf_limits_v2(ref_gas_midpoint,calc_type, 'stdev'):
            stdev_pass_or_fail_column.append("FAIL") 
        else:
            stdev_pass_or_fail_column.append("PASS")
            
    stdev_upper_limit_column = [pf_limits_v2((row["gas_standard_lower"]+\
        row["gas_standard_upper"])/2.0,calc_type, 'stdev')\
        for idx, row in df_with_stdev_mean_max.iterrows()]
        
    df_4_table_2["stdev_pass_or_fail"] = stdev_pass_or_fail_column
    df_4_table_2["stdev_upper_limit"] = stdev_upper_limit_column

    #### calculate pass/fail for max only ####
    max_pass_or_fail_column=[]
    for idx, row in df_with_stdev_mean_max.iterrows():
        ref_gas_midpoint = (row["gas_standard_lower"]+row["gas_standard_upper"])/2.0
        if (abs(row["max"])) > pf_limits_v2(ref_gas_midpoint,calc_type, 'max'):
            max_pass_or_fail_column.append("FAIL") 
        else:
            max_pass_or_fail_column.append("PASS")
            
    max_upper_limit_column = [pf_limits_v2((row["gas_standard_lower"]+\
        row["gas_standard_upper"])/2.0,calc_type, 'max')\
        for idx, row in df_with_stdev_mean_max.iterrows()]
        
    df_4_table_2["max_pass_or_fail"] = max_pass_or_fail_column
    df_4_table_2["max_upper_limit"] = max_upper_limit_column

    return df_4_table_2
        

if __name__ == "__main__":
    print(f'pf_limits(50) = {pf_limits(50)}')
    print(f'pf_limits(100) = {pf_limits(100)}')
    print(f'pf_limits(150) = {pf_limits(150)}')
    print(f'pf_limits(150) = {pf_limits(200)}')
    print(f'pf_limits(250) = {pf_limits(250)}')
    print(f'pf_limits(350) = {pf_limits(350)}')
    print(f'pf_limits(600) = {pf_limits(600)}')
    print(f'pf_limits(900) = {pf_limits(900)}')
    print(f'pf_limits(1200) = {pf_limits(1200)}')
    print(f'pf_limits(1800) = {pf_limits(1800)}')
    print(f'pf_limits(2400) = {pf_limits(2400)}')
    print(f'pf_limits(2500) = {pf_limits(2500)}')
    #print(f'pf_limits(0) = {pf_limits(0)}')
    #print(f'pf_limits(2600) = {pf_limits(2600)}')
    gases_to_test = [50,100,150,250,350,600,900,1200,1800,2400,2500]
    for gas_conc in gases_to_test:
        limit = pf_limits_v2(gas_conc,'Tcorr','mean')
        print(f'pf_limits_v2({gas_conc}) = {limit}')
    # print(f'pf_limits_v2(50) = {pf_limits_v2(50,'Tcorr','mean')}')
    # print(f'pf_limits_v2(100) = {pf_limits_v2(100,'Tcorr','mean')}')
    # print(f'pf_limits_v2(150) = {pf_limits_v2(150,'Tcorr','mean')}')
    # print(f'pf_limits_v2(150) = {pf_limits_v2(200,'Tcorr','mean')}')
    # print(f'pf_limits_v2(250) = {pf_limits_v2(250,'Tcorr','mean')}')
    # print(f'pf_limits_v2(350) = {pf_limits_v2(350,'Tcorr','mean')}')
    # print(f'pf_limits_v2(600) = {pf_limits_v2(600,'Tcorr','mean')}')
    # print(f'pf_limits_v2(900) = {pf_limits_v2(900,'Tcorr','mean')}')
    # print(f'pf_limits_v2(1200) = {pf_limits_v2(1200,'Tcorr','mean')}')
    # print(f'pf_limits_v2(1800) = {pf_limits_v2(1800,'Tcorr','mean')}')
    # print(f'pf_limits_v2(2400) = {pf_limits_v2(2400,'Tcorr','mean')}')
    # print(f'pf_limits_v2(2500) = {pf_limits_v2(2500,'Tcorr','mean')}')
    # print(f'pf_limits_v2(0) = {pf_limits_v2(0,'Tcorr','mean')}')
    # print(f'pf_limits_v2(2600) = {pf_limits_v2(2600,'Tcorr','mean')}')

