import pandas as pd
import numpy as np

def calculate_xco2_from_data_pt_by_pt(data, zerocoeff, S0_tcorr, S1_tcorr, scalar=False):
    
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
    
    if ( not scalar):
        Li_Raw_float = data.Li_Raw.astype(int)  # w - raw count
        Li_ref_float = data.Li_ref.astype(int)  # w0 - raw count reference
        Pres_float = data.Pres.astype(float)  # p1 - measured pressure
        Temp_float = data.Temp.astype(float)  # T - temperature
    else:
        Li_Raw_float = float(data.Li_Raw)
        Li_ref_float = float(data.Li_ref)
        Pres_float = float(data.Pres)
        Temp_float = float(data.Temp)

    w = Li_Raw_float
    w0 = Li_ref_float
    p1 = Pres_float
    T = Temp_float
    #print(f'w = {w}, w0 = {w0}, p1 = {p1}, T = {T}')
    #use averaged values
    # w_mean = w.mean()
    # w0_mean =w0.mean()
    # p1_mean = p1.mean()
    # T_mean = T.mean()

    #Pascal, new alphaC to reflect "APOFF" dataset
    #alphaC = (1 - ((w_mean / w0_mean) * zerocoeff))

    # No longer using averaged values
    alphaC = (1 - (w/w0)*zerocoeff)
    
    # Pascal - valid, these are intermediate variables used to calculate alphaCprime, below

    #Need to shift S0_tcorr index to match alphaC index for calculation
    #idx_delta = S0_tcorr.index[0]-alphaC.index[0]
    #S0_tcorr.index = [val-idx_delta for val in S0_tcorr.index]
    #print(f'double check: S0_tcorr = {S1_tcorr}, S0_tcorr = {S1_tcorr}')
    alphaC_1 = alphaC * S0_tcorr
    alphaC_2 = (alphaC ** 2) * S1_tcorr
    # print("alphaC_2\n",alphaC_2)

    # Pascal - valid, relates to eq. A-3 or eq. A-10 of LiCor 830/850 manual
    alphaCprime = alphaC_1 + alphaC_2
    #print(f"alphaCprime = {alphaCprime}")

    #df_bugs = pd.DataFrame([alphaC, BetaC, S0_tcorr, alphaCprime, alphaCprime-BetaC])
    #df_bugs = df_bugs.transpose()

    #p = p1_mean / p0 
    p = p1 / p0  # No longer using averaged values
    #pif = p > 1
    
    # if pif.any():
    #     p = p1_mean / p0
    # else:
    #     p = p0 / p1_mean

    # No longer using averaged values
    if ( not scalar ):
        mask_p_gt_1 = p < 1.0
        temp = pd.Series(dtype='float64')
        temp = p0 / p1.loc[mask_p_gt_1]
        p.update(temp)
        del temp
    else:
        if p <= 1:
            p = p0 / p1  #invert p


    # Pascal - valid, relates to eq. A-11 of LiCor 830/850 manual, note b1:=a, b2:=b, b3:=c and b4:=d
    #    ' compute some terms for the pressure correction function
    A = (1 / (b1 * (p - 1)))
    B = 1 / ((1 / (b2 + (b3 * p))) + b4)
    X = 1 + (1 / (A + (B * ((1 / (z - alphaC)) - (1 / z)))))  # change whether alphaC or alphaCprime here
    
    # Pascal - valid, w.r.t g, relates to eq. A-13 or eq. A-11 of LiCor 830/850 manual
    # g is the empirical correction function and is a function of absorptance and pressure

    # if pif.any():
    #     g = 1 / X
    # else:
    #     g = X

    # No longer using averaged values
    if (not scalar):
        g = 1/X
        temp = pd.Series(dtype='float64')
        temp = X.loc[mask_p_gt_1]
        g.update(temp)
        del temp
    else:
        g =  1/X

    # Pascal - valid, w.r.t. eq. A-10 of LiCor 830/850 manual
    #    'alphapc is the pressure corrected absorptance, alphaC'', and equal absorptance(absp) * correction (g)
    alphapc = alphaCprime * g

    #print(f'alphapc = {alphapc}')
    
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
    # xco2 = F * ((T_mean + 273.15))  # / (T0 + 273.15)) # added the bottom TO
    #print(f'T_mean = {T.mean()}')
    #print(f'xco2_mean = {xco2.mean()}')

    # No longer using averaged values
    xco2 = F * (T+273.15)

    return xco2

def calculate_xco2_from_data_pt_by_pt_older(data, zerocoeff, S0_tcorr, S1_tcorr):
    
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
    # w_mean = w.mean()
    # w0_mean =w0.mean()
    # p1_mean = p1.mean()
    # T_mean = T.mean()

    #Pascal, new alphaC to reflect "APOFF" dataset
    #alphaC = (1 - ((w_mean / w0_mean) * zerocoeff))

    # No longer using averaged values
    alphaC = (1 - (w/w0)*zerocoeff)
    
    # Pascal - valid, these are intermediate variables used to calculate alphaCprime, below

    #Need to shift S0_tcorr index to match alphaC index for calculation
    #idx_delta = S0_tcorr.index[0]-alphaC.index[0]
    #S0_tcorr.index = [val-idx_delta for val in S0_tcorr.index]
    #print(f'double check: S0_tcorr = {S1_tcorr}, S0_tcorr = {S1_tcorr}')
    alphaC_1 = alphaC * S0_tcorr
    alphaC_2 = (alphaC ** 2) * S1_tcorr
    # print("alphaC_2\n",alphaC_2)

    # Pascal - valid, relates to eq. A-3 or eq. A-10 of LiCor 830/850 manual
    alphaCprime = alphaC_1 + alphaC_2
    #print("alphaCprime\n",alphaCprime)

    #df_bugs = pd.DataFrame([alphaC, BetaC, S0_tcorr, alphaCprime, alphaCprime-BetaC])
    #df_bugs = df_bugs.transpose()

    #p = p1_mean / p0 
    p = p1 / p0  # No longer using averaged values
    #pif = p > 1
    
    # if pif.any():
    #     p = p1_mean / p0
    # else:
    #     p = p0 / p1_mean

    # No longer using averaged values
    mask_p_gt_1 = p < 1.0
    temp = pd.Series(dtype='float64')
    temp = p0 / p1.loc[mask_p_gt_1]
    p.update(temp)
    del temp


    # Pascal - valid, relates to eq. A-11 of LiCor 830/850 manual, note b1:=a, b2:=b, b3:=c and b4:=d
    #    ' compute some terms for the pressure correction function
    A = (1 / (b1 * (p - 1)))
    B = 1 / ((1 / (b2 + (b3 * p))) + b4)
    X = 1 + (1 / (A + (B * ((1 / (z - alphaC)) - (1 / z)))))  # change whether alphaC or alphaCprime here
    
    # Pascal - valid, w.r.t g, relates to eq. A-13 or eq. A-11 of LiCor 830/850 manual
    # g is the empirical correction function and is a function of absorptance and pressure

    # if pif.any():
    #     g = 1 / X
    # else:
    #     g = X

    # No longer using averaged values
    g = 1/X
    temp = pd.Series(dtype='float64')
    temp = X.loc[mask_p_gt_1]
    g.update(temp)
    del temp

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
    # xco2 = F * ((T_mean + 273.15))  # / (T0 + 273.15)) # added the bottom TO
    #print(f'T_mean = {T.mean()}')
    #print(f'xco2_mean = {xco2.mean()}')

    # No longer using averaged values
    xco2 = F * (T+273.15)

    return xco2

def dry_correction(xCO2_wet,RH_T,Pressure,RH_sample,RH_span):
    return xCO2_wet / ((Pressure-((RH_sample-RH_span)*0.61365*\
        np.exp((17.502*RH_T)/(240.97+RH_T)))/100.0)/Pressure)


if __name__ == "__main__":
    LiRawTxt = ['5240531','5235621','5218432','5219999','5220389','5224905', \
        '5225956' ,'5221836' ,'5215258']
    LiRefTxt = ['5460447','5457594','5462031','5460153','5458942','5459929', \
        '5460368','5459898','5460235']
    PresTxt = ['101.838','101.858','101.796','101.758','101.757','101.755', \
        '101.47','101.452','101.373']
    TempTxt = ['21.969','22.523','22.095','22.395','22.578','22.494','22.543',\
        '22.612','22.57']
    RH_Temp_Txt = ['21.153','21.519','21.253','21.346','21.424','21.206','21.392',\
        '21.434','21.386']
    RH_EPOFF_Txt = ['54.684','55.717','56.599','56.8','56.875','57.083','57.577',\
        '57.573','57.624']
    RH_SPOFF_Txt = ['50.802','54.725','55.558','56.074','56.365','56.524','57.326',\
        '57.294','57.236']
    zerocoeff_list = [0.9540895,0.9481111,0.94824,0.948162,0.9481555,0.9481498,\
        0.9481083,0.9481093,0.9481752]
    # S0_list = [0.971408146,0.911213653,0.912737495,0.912282464,0.912159691,\
    #     0.911663428,0.911970097,0.911985808,0.912421142]
    S0_list = [0.971408146136595,0.911213653045612,0.912737495137589,\
            0.912282463595316,0.912159690847173,0.911663427508474,\
            0.911970097044245,0.911985808387440,0.912421142306706]
    # S1_list = [0.057695557,0.054956835,0.05721575,0.055389935,0.054447305,\
    #     0.054527981,0.054549211,0.054294446,0.054396352]
    S1_list = [0.0576955566799836,0.0549568347275535,0.0572157495782400,\
        0.0553899349432866,0.0544473050619851,0.0545279805923667,\
        0.0545492109950988,0.0542944461623146,0.0543963520954283]


    data = pd.DataFrame({'Li_Raw':LiRawTxt,'Li_ref':LiRefTxt,\
        'Pres':PresTxt,'Temp':TempTxt,'RH_Temp':RH_Temp_Txt,\
        'RH_EPOFF':RH_EPOFF_Txt,'RH_SPOFF':RH_SPOFF_Txt})
    S0 = pd.Series(data=S0_list,name='S0')
    S1 = pd.Series(data=S1_list,name='S1')
    zerocoeff = pd.Series(data=zerocoeff_list,name='zerocoeff')
    xco2_wet = calculate_xco2_from_data_pt_by_pt(data,zerocoeff_list,S0,S1)
    print('xco2_wet\n',xco2_wet)
    xco2_dry = pd.Series([],name='xco2_dry',dtype='float64')
    for idx, row in data.iterrows():
        xco2_dry[idx]=dry_correction(xco2_wet[idx],float(row['RH_Temp']),\
            float(row['Pres']),float(row['RH_EPOFF']),float(row['RH_SPOFF']))
    print('xco2_dry\n',xco2_dry)