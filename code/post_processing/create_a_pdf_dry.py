from matplotlib.pyplot import title
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.rl_config import defaultPageSize
import pandas as pd
from pass_fail_processing import calculate_pf_df, calculate_pf_df_v2
import re
import os

def generate_validation_report(output_folder,sn,date_range,figure_filenames_and_sizes,\
    df_mean_stdev_tcorr,df_mean_stdev_not_tcorr,validation_text_filename):
    document = []
    
    ##### 1st page #####
    document.append(Image('./post_processing/config/ASVCO2_logo.png',3.87*inch,1.06*inch))
    #document.append(Spacer(6*inch,0.25*inch))
    document.append(Paragraph('Gas Validation for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))
    
    ##### format start date and end date #####
    start_year = date_range[0][0:4]; end_year = date_range[0][0:4]
    start_month = date_range[0][4:6]; end_month = date_range[0][4:6]
    start_day = date_range[0][6:8]; end_day = date_range[0][6:8]
    start_str = start_month + "/" + start_day + "/" + start_year
    end_str = end_month + "/" + end_day + "/" + end_year

    first_page_text_above_first_figure='''
    The data shown in this report was collected between ''' + start_str + " and " + end_str + '''
    using ASVCO2 Gen2 with S/N ''' + sn + '''.
    The residuals shown in the figure below represent the measured carbon dioxide (CO2)
    gas concentration from the ASVCO2 test article in parts per million (ppm) subtracted from the
    standard gas concentration of CO2 in ppm. The colors represent the number of runs, or
    successive samples of measurement.'''
    document.append(Paragraph(first_page_text_above_first_figure))
    #document.append(Image('APOFF 1006 20210429.png',6*inch,18/5.0*inch))
    document.append(Image(figure_filenames_and_sizes[0][0],\
        figure_filenames_and_sizes[0][1]*inch,figure_filenames_and_sizes[0][2]*inch))
    first_page_text_below_first_figure='''
    As shown above, it is expected that there will be two regions of accuracy. One region,
    where the standard gases are below 1000ppm, have a tendency to show greater accuracy 
    (i.e. lower residuals) in the lower range as two of the three standard gases used for 
    calibrating the ASVCO2 test article (0ppm and 500ppm, approximately) occur in that range. 
    The other region, where the standard gases are above 1000ppm, have a tendency to show less 
    accuracy and the magnitude of the residual increases with increasing concentration in 
    the sense that a percent error may be observed. 
    '''
    document.append(Paragraph(first_page_text_below_first_figure))
    document.append(PageBreak())

    ##### 2nd page #####
    more_text='''Mathematical coefficients which determine the calculation of CO2 gas 
    concentration have been observed to be a function of temperature. It is
    expected that the residuals will be lower once these temperature corrections/adjustments
    are made. For further details, see <font color=blue><link>
    https://github.com/NOAA-PMEL/EDD-ASVCO2_Automation/tree/develop</link></font>'''

    document.append(Paragraph(more_text))
    #document.append(Image('830_830eq_res_all.png',6*inch,18/5.0*inch))
    document.append(Image(figure_filenames_and_sizes[1][0],\
        figure_filenames_and_sizes[1][1]*inch,figure_filenames_and_sizes[1][2]*inch))
    
    document.append(Paragraph('Statistical summaries of the residual, grouped by gas standard:'))
    
    # convert dataframe to 2-D array, data1
    df_4_comparison = df_mean_stdev_tcorr.copy()
    df_4_comparison = df_4_comparison.rename(columns={'stdev':'res_stdev_recalc','mean':'res_mean_recalc'})
    df_4_comparison["res_mean_not_recalc"] = df_mean_stdev_not_tcorr["mean"]
    df_4_comparison["res_stdev_not_recalc"] = df_mean_stdev_not_tcorr["stdev"]
    num_rows=len(df_4_comparison)
    num_cols=len(df_4_comparison.columns)
    data1=[]
    header = [s.replace("_"," ") for s in df_4_comparison.columns.values]
    data1.append(header)
    #print(df_4_comparison.columns)
    for idx, row in df_4_comparison.iterrows():
        row_as_list = [row["gas_standard"],
                f'{row["res_mean_recalc"]:.4f}',
                f'{row["res_stdev_recalc"]:.4f}',
                f'{row["res_mean_not_recalc"]:.4f}',
                f'{row["res_stdev_not_recalc"]:.4f}']
        data1.append(row_as_list)

    t1=Table(data1)
    t1.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]))
    document.append(t1)

    document.append(PageBreak())

    ##### 3rd page #####
    document.append(Paragraph('Pass/Fail Determination for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))

    n_std_dev=1  # number of standard deviations from the mean to set pass fail criteria

    third_page_text_above_third_page_table='''
    The ASVCO2 unit is credited with a passing result if the sum of the standard deviation,
    multiplied by a factor of ''' + f'{n_std_dev:.1f}' + ''', and the absolute value of the 
    mean is less than or equal to the upper limit in ppm. Otherwise, it is determined that 
    the ASVCO2 unit has failed the test. This is shown in the table below.
    '''
    document.append(Paragraph(third_page_text_above_third_page_table))
    document.append(Spacer(6*inch,0.1*inch))
    
    document.append(Paragraph('Recalculated (recalc) Pass/Fail results:'))
    document.append(Spacer(6*inch,0.1*inch))

    # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    df_mean_stdev_tcorr_2 = calculate_pf_df(df_mean_stdev_tcorr,n_std_dev)

    # convert dataframe to 2-D array, data2, with pass/fail criteria
    num_rows=len(df_mean_stdev_tcorr_2)
    num_cols=len(df_mean_stdev_tcorr_2.columns)
    data2=[]
    header = [s.replace("_"," ") for s in df_mean_stdev_tcorr_2.columns.values]
    data2.append(header)
    #print(df_mean_stdev_tcorr_2.columns)
    for idx, row in df_mean_stdev_tcorr_2.iterrows():
        row_as_list = [row["gas_standard"],
                        f'{row["mean"]:.4f}',
                        f'{row["stdev"]:.4f}',
                        row["pass_or_fail"],
                        f'{row["upper_limit"]:.4f}',
                        f'{row["margin"]:.4f}']
        data2.append(row_as_list)
    
    t2=Table(data2)
    # t2.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
    #     ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
    #     ('TEXTCOLOR',(3,1),(3,num_rows), colors.green),\
    #     ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
    #     ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]))
    t2_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
    
    any_single_failure_flag=False
    for idx, row in df_mean_stdev_tcorr_2.iterrows():
        if row["pass_or_fail"] == "PASS":
            t2_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                 colors.green))
        else:
            t2_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                 colors.red))
            any_single_failure_flag=True

    t2.setStyle(t2_table_style)
    document.append(t2)

    document.append(Spacer(6*inch,0.1*inch))
    document.append(Paragraph('Pass/Fail results without recalculation (recalc):'))
    document.append(Spacer(6*inch,0.1*inch))

    # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    df_mean_stdev_not_tcorr_2 = calculate_pf_df(df_mean_stdev_not_tcorr,n_std_dev,'not_Tcorr')

    # convert dataframe to 2-D array, data2, with pass/fail criteria
    num_rows=len(df_mean_stdev_not_tcorr_2)
    num_cols=len(df_mean_stdev_not_tcorr_2.columns)
    data3=[]
    header = [s.replace("_"," ") for s in df_mean_stdev_not_tcorr_2.columns.values]
    data3.append(header)
    #print(df_mean_stdev_not_tcorr_2.columns)
    for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
        row_as_list = [row["gas_standard"],
                        f'{row["mean"]:.4f}',
                        f'{row["stdev"]:.4f}',
                        row["pass_or_fail"],
                        f'{row["upper_limit"]:.4f}',
                        f'{row["margin"]:.4f}']
        data3.append(row_as_list)
    
    t3=Table(data3)

    t3_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
    
    for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
        if row["pass_or_fail"] == "PASS":
            t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                 colors.green))
        else:
            t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                 colors.red))

    t3.setStyle(t3_table_style)
    document.append(t3)
    document.append(PageBreak())

    # document.append(Paragraph('Here\'s another table below:'))
    # mydata=[['stuff',0.0],['more stuff',-2.6],\
    #     ['even more stuff',-10.9],['yet again more stuff',9999999.099999]]
    # t2=Table(mydata)
    # t2.setStyle(TableStyle([('ALIGN',(0,0),(2,3),'LEFT'), ('TEXTCOLOR',(0,0),(2,3), colors.black),\
    #     ('INNERGRID', (0,0), (2,3), 0.25, colors.black),('BOX', (0,0), (2,3), 0.25, colors.black)]))
    # document.append(t2)

    ##### 4th page #####
    document.append(Paragraph('Configuration Description for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))

    file_ptr=open(validation_text_filename, 'r')
    lines = file_ptr.readlines()
    fourth_page_text = ''

    start_line = 0
    line_is_empty=len(lines[start_line].strip()) == 0
    while line_is_empty:
        start_line += 1
        line_is_empty = len(lines[start_line].strip()) == 0
        
    end_line = start_line
    line_is_not_empty=len(lines[end_line].strip()) != 0
    while line_is_not_empty:
        end_line += 1
        line_is_not_empty = len(lines[end_line].strip()) != 0          

    for idx in range(start_line,end_line):
        fourth_page_text += lines[idx] + "<br/>"

    document.append(Paragraph(fourth_page_text))

    
    #output_filename='demo_1006.pdf'
    if ( any_single_failure_flag ):
        last_piece_of_filename = "FAIL"
    else:
        last_piece_of_filename = "PASS"
    output_filename = output_folder + '/' + "Gas_Validation_" + sn + "_" + \
        date_range[0][0:8] + "_" + last_piece_of_filename + ".pdf"
    
    SimpleDocTemplate(output_filename,pagesize=letter,\
        rightMargin=1*inch, leftMargin=1*inch,\
            topMargin=1*inch, bottomMargin=1*inch).build(document)

def myLaterPages(canvas, doc):
    canvas.saveState()
    canvas.setFont('Times-Roman',9)
    pageinfo = "ASVCO2 Gas Val. - v0.0.6"
    canvas.drawString(inch, 0.75 * inch, "Page %d, %s" % (doc.page, pageinfo))
    canvas.restoreState()


def myFirstPage(canvas, doc):
    canvas.saveState()
    Title = "ASVCO2 Gas Validation Automatic Report - v0.0.6"
    pageinfo = "ASVCO2 Gas Val. - v0.0.6"
    PAGE_HEIGHT=defaultPageSize[1]; PAGE_WIDTH=defaultPageSize[0]
    canvas.setFont('Times-Roman',9)
    canvas.drawCentredString(PAGE_WIDTH/3.3333333, PAGE_HEIGHT-78, Title)
    canvas.setFont('Times-Roman',9)
    canvas.drawString(inch, 0.75 * inch, "Page %d, %s" % (doc.page, pageinfo))
    canvas.restoreState()

def generate_bigger_validation_report(output_folder,sn,date_range,figure_filenames_and_sizes,\
    tuple_of_df_4_tables,validation_text_filename,final_text=''):
    document = []
    
    ##### 1st page #####
    document.append(Image('./post_processing/config/ASVCO2_logo.png',3.87*inch,1.06*inch))
    #document.append(Spacer(6*inch,0.25*inch))
    document.append(Paragraph('Gas Validation for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))
    document.append(Paragraph('--APOFF Summary--',ParagraphStyle(name='Header12pt',fontSize=12)))
    document.append(Spacer(6*inch,0.1*inch))
    
    ##### format start date and end date #####
    start_year = date_range[0][0:4]; end_year = date_range[0][0:4]
    start_month = date_range[0][4:6]; end_month = date_range[0][4:6]
    start_day = date_range[0][6:8]; end_day = date_range[0][6:8]
    start_str = start_month + "/" + start_day + "/" + start_year
    end_str = end_month + "/" + end_day + "/" + end_year

    first_page_text_above_first_figure='''
    The data shown in this report was collected between ''' + start_str + " and " + end_str + '''
    using ASVCO2 Gen2 with S/N ''' + sn + '''.
    The residuals shown in the figure below represent the measured carbon dioxide (CO2)
    gas concentration from the ASVCO2 test article in parts per million (ppm) subtracted from the
    standard gas concentration of CO2 in ppm. The colors represent the number of runs, or
    successive samples of measurement.'''
    document.append(Paragraph(first_page_text_above_first_figure))
    #document.append(Image('APOFF 1006 20210429.png',6*inch,18/5.0*inch))
    document.append(Image(figure_filenames_and_sizes[0][0],\
        figure_filenames_and_sizes[0][1]*inch,figure_filenames_and_sizes[0][2]*inch))
    first_page_text_below_first_figure='''
    As shown above, it is expected that there will be two regions of accuracy. One region,
    where the standard gases are below 1000ppm, have a tendency to show greater accuracy 
    (i.e. lower residuals) in the lower range as two of the three standard gases used for 
    calibrating the ASVCO2 test article (0ppm and 500ppm, approximately) occur in that range. 
    The other region, where the standard gases are above 1000ppm, have a tendency to show less 
    accuracy and the magnitude of the residual increases with increasing concentration in 
    the sense that a percent error may be observed. 
    '''
    document.append(Paragraph(first_page_text_below_first_figure))
    document.append(PageBreak())

    ##### 2nd page #####
    more_text='''Mathematical coefficients which determine the calculation of CO2 gas 
    concentration have been observed to be a function of temperature. It is
    expected that the residuals will be lower once these temperature corrections/adjustments
    are made. For further details, see <font color=blue><link>
    https://github.com/NOAA-PMEL/EDD-ASVCO2_Automation/tree/develop</link></font>'''

    document.append(Paragraph(more_text))
    #document.append(Image('830_830eq_res_all.png',6*inch,18/5.0*inch))
    document.append(Image(figure_filenames_and_sizes[1][0],\
        figure_filenames_and_sizes[1][1]*inch,figure_filenames_and_sizes[1][2]*inch))
    
    document.append(Paragraph('APOFF Statistical summaries of the residual, grouped by gas standard:'))
    document.append(Spacer(6*inch,0.1*inch))
    
    # convert dataframe to 2-D array, data1
    #df_4_comparison = df_mean_stdev_tcorr.copy()
    df_4_comparison = tuple_of_df_4_tables[0].copy() 
    df_4_comparison = df_4_comparison.rename(columns={'stdev':'dry_res_stdev_recalc','mean':'dry_res_mean_recalc'})
    # df_4_comparison["res_mean_not_recalc"] = df_mean_stdev_not_tcorr["mean"]
    # df_4_comparison["res_stdev_not_recalc"] = df_mean_stdev_not_tcorr["stdev"]
    df_4_comparison["dry_res_mean_not_recalc"] = tuple_of_df_4_tables[1]["mean"]  # Bug fix, 6/25/2021 due to Noah's comment
    df_4_comparison["dry_res_stdev_not_recalc"] = tuple_of_df_4_tables[1]["stdev"]  # Bug fix, 6/25/2021 due to Noah's comment
    num_rows=len(df_4_comparison)
    num_cols=len(df_4_comparison.columns)
    data_summary_APOFF=[]
    header = [s.replace("_"," ") for s in df_4_comparison.columns.values]
    data_summary_APOFF.append(header)
    #print(df_4_comparison.columns)
    for idx, row in df_4_comparison.iterrows():
        row_as_list = [row["gas_standard"],
                f'{row["dry_res_mean_recalc"]:.4f}',
                f'{row["dry_res_stdev_recalc"]:.4f}',
                f'{row["dry_res_mean_not_recalc"]:.4f}',
                f'{row["dry_res_stdev_not_recalc"]:.4f}']
        data_summary_APOFF.append(row_as_list)

    t1=Table(data_summary_APOFF)
    t1.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]))
    document.append(t1)

    document.append(PageBreak())

    ##### 3rd page #####
    document.append(Spacer(6*inch,0.1*inch))
    document.append(Paragraph('--EPOFF Summary--',ParagraphStyle(name='Header12pt',fontSize=12)))
    document.append(Spacer(6*inch,0.1*inch))
    
    ##### format start date and end date #####
    start_year = date_range[0][0:4]; end_year = date_range[0][0:4]
    start_month = date_range[0][4:6]; end_month = date_range[0][4:6]
    start_day = date_range[0][6:8]; end_day = date_range[0][6:8]
    start_str = start_month + "/" + start_day + "/" + start_year
    end_str = end_month + "/" + end_day + "/" + end_year

    third_page_text_above_third_figure='''
    The data shown in this report was collected between ''' + start_str + " and " + end_str + '''
    using ASVCO2 Gen2 with S/N ''' + sn + '''.
    The residuals shown in the figure below represent the measured carbon dioxide (CO2)
    gas concentration from the ASVCO2 test article in parts per million (ppm) subtracted from the
    standard gas concentration of CO2 in ppm. The colors represent the number of runs, or
    successive samples of measurement.'''
    document.append(Paragraph(third_page_text_above_third_figure))
    #document.append(Image('APOFF 1006 20210429.png',6*inch,18/5.0*inch))
    document.append(Image(figure_filenames_and_sizes[2][0],\
        figure_filenames_and_sizes[2][1]*inch,figure_filenames_and_sizes[2][2]*inch))
    third_page_text_below_third_figure='''
    As shown above, it is expected that there will be two regions of accuracy. One region,
    where the standard gases are below 1000ppm, have a tendency to show greater accuracy 
    (i.e. lower residuals) in the lower range as two of the three standard gases used for 
    calibrating the ASVCO2 test article (0ppm and 500ppm, approximately) occur in that range. 
    The other region, where the standard gases are above 1000ppm, have a tendency to show less 
    accuracy and the magnitude of the residual increases with increasing concentration in 
    the sense that a percent error may be observed. 
    '''
    document.append(Paragraph(third_page_text_below_third_figure))
    document.append(PageBreak())

    ##### 4th page #####
    more_text='''Mathematical coefficients which determine the calculation of CO2 gas 
    concentration have been observed to be a function of temperature. It is
    expected that the residuals will be lower once these temperature corrections/adjustments
    are made. For further details, see <font color=blue><link>
    https://github.com/NOAA-PMEL/EDD-ASVCO2_Automation/tree/develop</link></font>'''

    document.append(Paragraph(more_text))
    #document.append(Image('830_830eq_res_all.png',6*inch,18/5.0*inch))
    document.append(Image(figure_filenames_and_sizes[3][0],\
        figure_filenames_and_sizes[3][1]*inch,figure_filenames_and_sizes[3][2]*inch))
    
    document.append(Paragraph('EPOFF Statistical summaries of the residual, grouped by gas standard:'))
    document.append(Spacer(6*inch,0.1*inch))
    
    # convert dataframe to 2-D array, data1
    #df_4_comparison = df_mean_stdev_tcorr.copy()
    df_4_comparison = tuple_of_df_4_tables[2].copy()  # Bug fix, 6/25/2021 due to Noah's comment
    df_4_comparison = df_4_comparison.rename(columns={'stdev':'dry_res_stdev_recalc','mean':'dry_res_mean_recalc'})
    # df_4_comparison["res_mean_not_recalc"] = df_mean_stdev_not_tcorr["mean"]
    # df_4_comparison["res_stdev_not_recalc"] = df_mean_stdev_not_tcorr["stdev"]
    df_4_comparison["dry_res_mean_not_recalc"] = tuple_of_df_4_tables[3]["mean"]  # Bug fix, 6/25/2021 due to Noah's comment
    df_4_comparison["dry_res_stdev_not_recalc"] = tuple_of_df_4_tables[3]["stdev"] # Bug fix, 6/25/2021 due to Noah's comment
    num_rows=len(df_4_comparison)
    num_cols=len(df_4_comparison.columns)
    data_summary_EPOFF=[]
    header = [s.replace("_"," ") for s in df_4_comparison.columns.values]
    data_summary_EPOFF.append(header)
    #print(df_4_comparison.columns)
    for idx, row in df_4_comparison.iterrows():
        row_as_list = [row["gas_standard"],
                f'{row["dry_res_mean_recalc"]:.4f}',
                f'{row["dry_res_stdev_recalc"]:.4f}',
                f'{row["dry_res_mean_not_recalc"]:.4f}',
                f'{row["dry_res_stdev_not_recalc"]:.4f}']
        data_summary_EPOFF.append(row_as_list)

    t2=Table(data_summary_EPOFF)
    t2.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]))
    document.append(t2)

    document.append(PageBreak())

    ##### 5th page #####
    document.append(Paragraph('APOFF Pass/Fail Determination for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))

    #comparison_type = 'combined'  # pass/fail will be by abs(mean) + n_std_dev * std_dev
    comparison_type = 'separate'  # pass/fail will be by separate limits of mean and std_dev

    n_std_dev=1  # for combined only number of standard deviations from the mean to set pass fail criteria
    
    if ( comparison_type == 'combined'):
        fifth_page_text_above_fifth_page_table='''
        The ASVCO2 unit is credited with a passing result if the sum of the standard deviation,
        multiplied by a factor of ''' + f'{n_std_dev:.1f}' + ''', and the absolute value of the 
        mean is less than or equal to the upper limit in ppm. Otherwise, it is determined that 
        the ASVCO2 unit has failed the test. This is shown in the table below.
        '''
    elif ( comparison_type == 'separate'):
        fifth_page_text_above_fifth_page_table='''
        The ASVCO2 unit is credited with a passing result if the mean and the standard deviation
        of the residual are within their separate limits in ppm. Otherwise, it is determined that 
        the ASVCO2 unit has failed the test. This is shown in the table below.
        '''
    else:
        fifth_page_text_above_fifth_page_table = '''An undefined pass/fail criterion has been chosen
        and these pass/fail results might be invalid.'''

    document.append(Paragraph(fifth_page_text_above_fifth_page_table))
    document.append(Spacer(6*inch,0.1*inch))
    
    document.append(Paragraph('APOFF Recalculated (recalc) Pass/Fail results:'))
    document.append(Spacer(6*inch,0.1*inch))

    # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    #df_mean_stdev_tcorr_2 = calculate_pf_df(df_mean_stdev_tcorr,n_std_dev)
    #df_mean_stdev_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[0],n_std_dev)
    df_mean_stdev_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[0],n_std_dev,\
        'Tcorr',comparison_type)
    
    # convert dataframe to 2-D array, data2, with pass/fail criteria
    num_rows=len(df_mean_stdev_tcorr_2)
    num_cols=len(df_mean_stdev_tcorr_2.columns)
    data_pf_APOFF_recalc=[]
    if ( comparison_type == 'combined' ):
        header = [s.replace("_"," ") for s in df_mean_stdev_tcorr_2.columns.values]
    elif ( comparison_type == 'separate' ):
        header=['gas_standard','dry_mean','mean_upper_limit','mean_pass_or_fail',\
            'dry_stdev','stdev_upper_limit','stdev_pass_or_fail']
        header = [s.replace("_"," ") for s in header]
        header[2] = Paragraph('mean<br/>upper limit')
        header[3] = Paragraph('mean<br/>pass or fail')
        header[5] = Paragraph('stdev<br/>upper limit')
        header[6] = Paragraph('stdev<br/>pass or fail')
    data_pf_APOFF_recalc.append(header)
    #print(df_mean_stdev_tcorr_2.columns)
    #print(df_mean_stdev_tcorr_2.columns.values)
    for idx, row in df_mean_stdev_tcorr_2.iterrows():
        if (comparison_type == 'combined'):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["stdev"]:.4f}',
                            row["pass_or_fail"],
                            f'{row["upper_limit"]:.4f}',
                            f'{row["margin"]:.4f}']
        elif ( comparison_type == 'separate' ):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["mean_upper_limit"]:.4f}',
                            row["mean_pass_or_fail"],
                            f'{row["stdev"]:.4f}',
                            f'{row["stdev_upper_limit"]:.4f}',
                            row["stdev_pass_or_fail"]]
        else:
            raise Exception(f'''undefined parameter {comparison_type} 
            in generate_bigger_validation_report()''')
        data_pf_APOFF_recalc.append(row_as_list)
    
    t3=Table(data_pf_APOFF_recalc)
    # t2.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
    #     ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
    #     ('TEXTCOLOR',(3,1),(3,num_rows), colors.green),\
    #     ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
    #     ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]))
    t3_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
    
    any_single_failure_flag=False
    if comparison_type == 'combined':
        for idx, row in df_mean_stdev_tcorr_2.iterrows():
            if row["pass_or_fail"] == "PASS":
                t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
    elif comparison_type == 'separate':
        for idx, row in df_mean_stdev_tcorr_2.iterrows():
            if row["mean_pass_or_fail"] == "PASS":
                t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
        for idx, row in df_mean_stdev_tcorr_2.iterrows():
            if row["stdev_pass_or_fail"] == "PASS":
                t3_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.green))
            else:
                t3_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.red))
                any_single_failure_flag=True

    t3.setStyle(t3_table_style)
    document.append(t3)

    document.append(Spacer(6*inch,0.1*inch))
    document.append(Paragraph('APOFF Pass/Fail results without recalculation (recalc):'))
    document.append(Spacer(6*inch,0.1*inch))

    # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    #df_mean_stdev_not_tcorr_2 = calculate_pf_df(df_mean_stdev_not_tcorr,n_std_dev,'not_Tcorr')
    #df_mean_stdev_not_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[1],n_std_dev,'not_Tcorr')
    df_mean_stdev_not_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[1],n_std_dev,\
        'not_Tcorr',comparison_type)

    # convert dataframe to 2-D array, data2, with pass/fail criteria
    num_rows=len(df_mean_stdev_not_tcorr_2)
    num_cols=len(df_mean_stdev_not_tcorr_2.columns)
    data_pf_APOFF_no_recalc=[]
    if ( comparison_type == 'combined' ):
        header = [s.replace("_"," ") for s in df_mean_stdev_tcorr_2.columns.values]
    elif ( comparison_type == 'separate' ):
        header=['gas_standard','dry_mean','mean_upper_limit','mean_pass_or_fail',\
            'dry_stdev','stdev_upper_limit','stdev_pass_or_fail']
        header = [s.replace("_"," ") for s in header]
        header[2] = Paragraph('mean<br/>upper limit')
        header[3] = Paragraph('mean<br/>pass or fail')
        header[5] = Paragraph('stdev<br/>upper limit')
        header[6] = Paragraph('stdev<br/>pass or fail')
    data_pf_APOFF_no_recalc.append(header)
    #print(df_mean_stdev_not_tcorr_2.columns)
    for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
        if (comparison_type == 'combined'):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["stdev"]:.4f}',
                            row["pass_or_fail"],
                            f'{row["upper_limit"]:.4f}',
                            f'{row["margin"]:.4f}']
        elif ( comparison_type == 'separate' ):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["mean_upper_limit"]:.4f}',
                            row["mean_pass_or_fail"],
                            f'{row["stdev"]:.4f}',
                            f'{row["stdev_upper_limit"]:.4f}',
                            row["stdev_pass_or_fail"]]
        else:
            raise Exception(f'''undefined parameter {comparison_type} 
            in generate_bigger_validation_report()''')
        data_pf_APOFF_no_recalc.append(row_as_list)
    
    t4=Table(data_pf_APOFF_no_recalc)

    t4_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
   
    # change from df_mean_stdev_tcorr_2 to df_mean_stdev_not_tcorr_2, 7/15/2021, Pascal and Sophie
    if comparison_type == 'combined':
        for idx, row in df_mean_stdev_not_tcorr_2.iterrows(): 
            if row["pass_or_fail"] == "PASS":
                t4_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t4_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
    elif comparison_type == 'separate':
        for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
            if row["mean_pass_or_fail"] == "PASS":
                t4_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t4_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
        for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
            if row["stdev_pass_or_fail"] == "PASS":
                t4_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.green))
            else:
                t4_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.red))
                any_single_failure_flag=True

    t4.setStyle(t4_table_style)
    document.append(t4)
    document.append(PageBreak())

    # document.append(Paragraph('Here\'s another table below:'))
    # mydata=[['stuff',0.0],['more stuff',-2.6],\
    #     ['even more stuff',-10.9],['yet again more stuff',9999999.099999]]
    # t2=Table(mydata)
    # t2.setStyle(TableStyle([('ALIGN',(0,0),(2,3),'LEFT'), ('TEXTCOLOR',(0,0),(2,3), colors.black),\
    #     ('INNERGRID', (0,0), (2,3), 0.25, colors.black),('BOX', (0,0), (2,3), 0.25, colors.black)]))
    # document.append(t2)


    ##### 6th page #####
    document.append(Paragraph('EPOFF Pass/Fail Determination for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))

    if ( comparison_type == 'combined'):
        sixth_page_text_above_sixth_page_table='''
        The ASVCO2 unit is credited with a passing result if the sum of the standard deviation,
        multiplied by a factor of ''' + f'{n_std_dev:.1f}' + ''', and the absolute value of the 
        mean is less than or equal to the upper limit in ppm. Otherwise, it is determined that 
        the ASVCO2 unit has failed the test. This is shown in the table below.
        '''
    elif ( comparison_type == 'separate'):
        sixth_page_text_above_sixth_page_table='''
        The ASVCO2 unit is credited with a passing result if the mean and the standard deviation
        of the residual are within their separate limits in ppm. Otherwise, it is determined that 
        the ASVCO2 unit has failed the test. This is shown in the table below.
        '''
    else:
        sixth_page_text_above_sixth_page_table = '''An undefined pass/fail criterion has been chosen
        and these pass/fail results might be invalid.'''
    document.append(Paragraph(sixth_page_text_above_sixth_page_table))
    document.append(Spacer(6*inch,0.1*inch))
    
    document.append(Paragraph('EPOFF Recalculated (recalc) Pass/Fail results:'))
    document.append(Spacer(6*inch,0.1*inch))

    # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    # df_mean_stdev_tcorr_2 = calculate_pf_df(df_mean_stdev_tcorr,n_std_dev)
    #df_mean_stdev_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[2],n_std_dev)
    df_mean_stdev_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[2],n_std_dev,\
        'Tcorr',comparison_type)

    # convert dataframe to 2-D array, data2, with pass/fail criteria
    num_rows=len(df_mean_stdev_tcorr_2)
    num_cols=len(df_mean_stdev_tcorr_2.columns)
    data_pf_EPOFF_recalc=[]
    if ( comparison_type == 'combined' ):
        header = [s.replace("_"," ") for s in df_mean_stdev_tcorr_2.columns.values]
    elif ( comparison_type == 'separate' ):
        header=['gas_standard','dry_res_mean','mean_upper_limit','mean_pass_or_fail',\
            'dry_res_stdev','stdev_upper_limit','stdev_pass_or_fail']
        header = [s.replace("_"," ") for s in header]
        header[2] = Paragraph('mean<br/>upper limit')
        header[3] = Paragraph('mean<br/>pass or fail')
        header[5] = Paragraph('stdev<br/>upper limit')
        header[6] = Paragraph('stdev<br/>pass or fail')
    data_pf_EPOFF_recalc.append(header)
    #print(df_mean_stdev_tcorr_2.columns)
    for idx, row in df_mean_stdev_tcorr_2.iterrows():
        if (comparison_type == 'combined'):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["stdev"]:.4f}',
                            row["pass_or_fail"],
                            f'{row["upper_limit"]:.4f}',
                            f'{row["margin"]:.4f}']
        elif ( comparison_type == 'separate' ):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["mean_upper_limit"]:.4f}',
                            row["mean_pass_or_fail"],
                            f'{row["stdev"]:.4f}',
                            f'{row["stdev_upper_limit"]:.4f}',
                            row["stdev_pass_or_fail"]]
        else:
            raise Exception(f'''undefined parameter {comparison_type} 
            in generate_bigger_validation_report()''')
        data_pf_EPOFF_recalc.append(row_as_list)
    
    t5=Table(data_pf_EPOFF_recalc)
    # t2.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
    #     ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
    #     ('TEXTCOLOR',(3,1),(3,num_rows), colors.green),\
    #     ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
    #     ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]))
    t5_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
    
    if comparison_type == 'combined':
        for idx, row in df_mean_stdev_tcorr_2.iterrows():
            if row["pass_or_fail"] == "PASS":
                t5_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t5_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
    elif comparison_type == 'separate':
        for idx, row in df_mean_stdev_tcorr_2.iterrows():
            if row["mean_pass_or_fail"] == "PASS":
                t5_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t5_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
        for idx, row in df_mean_stdev_tcorr_2.iterrows():
            if row["stdev_pass_or_fail"] == "PASS":
                t5_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.green))
            else:
                t5_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.red))
                any_single_failure_flag=True

    t5.setStyle(t5_table_style)
    document.append(t5)

    document.append(Spacer(6*inch,0.1*inch))
    document.append(Paragraph('EPOFF Pass/Fail results without recalculation (recalc):'))
    document.append(Spacer(6*inch,0.1*inch))

    # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    #df_mean_stdev_not_tcorr_2 = calculate_pf_df(df_mean_stdev_not_tcorr,n_std_dev,'not_Tcorr')
    #df_mean_stdev_not_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[3],n_std_dev,'not_Tcorr')
    df_mean_stdev_not_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[3],n_std_dev,\
        'not_Tcorr',comparison_type)

    # convert dataframe to 2-D array, data2, with pass/fail criteria
    num_rows=len(df_mean_stdev_not_tcorr_2)
    num_cols=len(df_mean_stdev_not_tcorr_2.columns)
    data_pf_EPOFF_no_recalc=[]
    if ( comparison_type == 'combined' ):
        header = [s.replace("_"," ") for s in df_mean_stdev_tcorr_2.columns.values]
    elif ( comparison_type == 'separate' ):
        header=['gas_standard','dry_res_mean','mean_upper_limit','mean_pass_or_fail',\
            'dry_res_stdev','stdev_upper_limit','stdev_pass_or_fail']
        header = [s.replace("_"," ") for s in header]
        header[2] = Paragraph('mean<br/>upper limit')
        header[3] = Paragraph('mean<br/>pass or fail')
        header[5] = Paragraph('stdev<br/>upper limit')
        header[6] = Paragraph('stdev<br/>pass or fail')
    data_pf_EPOFF_no_recalc.append(header)
    
    #print(df_mean_stdev_not_tcorr_2.columns)

    for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
        if (comparison_type == 'combined'):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["stdev"]:.4f}',
                            row["pass_or_fail"],
                            f'{row["upper_limit"]:.4f}',
                            f'{row["margin"]:.4f}']
        elif ( comparison_type == 'separate' ):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["mean_upper_limit"]:.4f}',
                            row["mean_pass_or_fail"],
                            f'{row["stdev"]:.4f}',
                            f'{row["stdev_upper_limit"]:.4f}',
                            row["stdev_pass_or_fail"]]
        else:
            raise Exception(f'''undefined parameter {comparison_type} 
            in generate_bigger_validation_report()''')
        data_pf_EPOFF_no_recalc.append(row_as_list)
    
    t6=Table(data_pf_EPOFF_no_recalc)

    t6_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
    
    # change from df_mean_stdev_tcorr_2 to df_mean_stdev_not_tcorr_2, 8/06/2021, Pascal
    if comparison_type == 'combined':
        for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
            if row["pass_or_fail"] == "PASS":
                t6_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t6_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
    elif comparison_type == 'separate':
        for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
            if row["mean_pass_or_fail"] == "PASS":
                t6_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t6_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
        for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
            if row["stdev_pass_or_fail"] == "PASS":
                t6_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.green))
            else:
                t6_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.red))
                any_single_failure_flag=True

    t6.setStyle(t6_table_style)
    document.append(t6)
    document.append(PageBreak())

    ##### 7th page #####
    document.append(Paragraph('Configuration Description for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))

    file_ptr=open(validation_text_filename, 'r')
    lines = file_ptr.readlines()
    seventh_page_text = ''

    start_line = 0
    line_is_empty=len(lines[start_line].strip()) == 0
    while line_is_empty:
        start_line += 1
        line_is_empty = len(lines[start_line].strip()) == 0
        
    end_line = start_line
    line_is_not_empty=len(lines[end_line].strip()) != 0
    while line_is_not_empty:
        end_line += 1
        line_is_not_empty = len(lines[end_line].strip()) != 0          

    for idx in range(start_line,end_line):
        seventh_page_text += lines[idx] + "<br/>"

    document.append(Paragraph(seventh_page_text))
    file_ptr.close()

    document.append(PageBreak())

    ##### 8th Page #####
    document.append(Paragraph('Description of Terms and Abbreviations',\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))
    #S<super rise=-4 size=6>1</super>
    description_of_terms='''
    <b>res</b> - residual, measured value - actual value<br/>
    <b>recalc</b> - recalculated according to temperature adjustment of S<sub>1</sub>,
    where S<sub>1</sub> is defined in the Appendix of the LI-830 and LI-850 user manual.<br/>
    For further details, see <font color=blue><link>
    https://github.com/NOAA-PMEL/EDD-ASVCO2_Automation/tree/develop</link></font><br/>
    <b>not recalc</b> - the S<sub>1</sub> coefficient is not adjusted for temperature<br/>
    <b>stdev</b> - the standard deviation<br/>
    <b>upper limit</b> - if a value exceeds this limit, then the unit has failed the test<br/>
    <b>ppm</b> - parts per million (ppm)<br/>
    <b>APOFF</b> - Air Pump OFF, this is a valve state in the ASVCO2 unit measuring the air<br/>
    <b>EPOFF</b> - Equilibrator Pump OFF, this is a valve state in the ASVCO2 unit measuring the equilibrator<br/>
    '''
    document.append(Paragraph(description_of_terms))

    # New feature, 9/21/2021, add in final text
    document.append(Spacer(6*inch,0.1*inch))
    document.append(Paragraph(final_text))

    #output_filename='demo_1006.pdf'
    if ( any_single_failure_flag ):
        last_piece_of_filename = "FAIL"
    else:
        last_piece_of_filename = "PASS"
    output_filename = output_folder + '/' + "Gas_Validation_" + sn + "_" + \
        date_range[0][0:8] + "_" + last_piece_of_filename + ".pdf"
    
    # SimpleDocTemplate(output_filename,pagesize=letter,\
    #     rightMargin=1*inch, leftMargin=1*inch,\
    #         topMargin=1*inch, bottomMargin=1*inch).build(document)

    doc = SimpleDocTemplate(output_filename,pagesize=letter,\
        rightMargin=1*inch, leftMargin=1*inch,\
        topMargin=1*inch, bottomMargin=1*inch)

    doc.build(document, onFirstPage=myFirstPage, onLaterPages=myLaterPages)

def generate_bigger_validation_report_reordered(output_folder, sn, date_range, figure_filenames_and_sizes,\
    tuple_of_df_4_tables,validation_text_filename,final_text=''):
    document = []
    
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ##### 1st page #####
    document.append(Image(PROJECT_ROOT + '/code/post_processing/config/ASVCO2_logo.png',3.87*inch,1.06*inch))
    #document.append(Spacer(6*inch,0.25*inch))
    document.append(Paragraph('Gas Validation for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))

    ##### 1st page content, previously 5th page content #####
    document.append(Paragraph('APOFF Pass/Fail Determination for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))

    #comparison_type = 'combined'  # pass/fail will be by abs(mean) + n_std_dev * std_dev
    comparison_type = 'separate'  # pass/fail will be by separate limits of mean and std_dev

    n_std_dev=1  # for combined only number of standard deviations from the mean to set pass fail criteria
    
    if ( comparison_type == 'combined'):
        fifth_page_text_above_fifth_page_table='''
        The ASVCO2 unit is credited with a passing result if the sum of the standard deviation,
        multiplied by a factor of ''' + f'{n_std_dev:.1f}' + ''', and the absolute value of the 
        mean is less than or equal to the upper limit in ppm. Otherwise, it is determined that 
        the ASVCO2 unit has failed the test. This is shown in the table below.
        '''
    elif ( comparison_type == 'separate'):
        fifth_page_text_above_fifth_page_table='''
        The ASVCO2 unit is credited with a passing result if the mean and the standard deviation
        of the residual are within their separate limits in ppm. Otherwise, it is determined that 
        the ASVCO2 unit has failed the test. This is shown in the table below.
        '''
    else:
        fifth_page_text_above_fifth_page_table = '''An undefined pass/fail criterion has been chosen
        and these pass/fail results might be invalid.'''

    document.append(Paragraph(fifth_page_text_above_fifth_page_table))
    document.append(Spacer(6*inch,0.1*inch))
    
    document.append(Paragraph('APOFF Recalculated (recalc) Pass/Fail results:'))
    document.append(Spacer(6*inch,0.1*inch))

    # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    #df_mean_stdev_tcorr_2 = calculate_pf_df(df_mean_stdev_tcorr,n_std_dev)
    #df_mean_stdev_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[0],n_std_dev)
    df_mean_stdev_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[0],n_std_dev,\
        'Tcorr',comparison_type)
    
    # convert dataframe to 2-D array, data2, with pass/fail criteria
    num_rows=len(df_mean_stdev_tcorr_2)
    num_cols=len(df_mean_stdev_tcorr_2.columns)
    data_pf_APOFF_recalc=[]
    if ( comparison_type == 'combined' ):
        header = [s.replace("_"," ") for s in df_mean_stdev_tcorr_2.columns.values]
    elif ( comparison_type == 'separate' ):
        header=['gas_standard','dry_mean','mean_upper_limit','mean_pass_or_fail',\
            'dry_stdev','stdev_upper_limit','stdev_pass_or_fail']
        header = [s.replace("_"," ") for s in header]
        header[2] = Paragraph('mean<br/>upper limit')
        header[3] = Paragraph('mean<br/>pass or fail')
        header[5] = Paragraph('stdev<br/>upper limit')
        header[6] = Paragraph('stdev<br/>pass or fail')
    data_pf_APOFF_recalc.append(header)
    #print(df_mean_stdev_tcorr_2.columns)
    #print(df_mean_stdev_tcorr_2.columns.values)
    for idx, row in df_mean_stdev_tcorr_2.iterrows():
        if (comparison_type == 'combined'):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["stdev"]:.4f}',
                            row["pass_or_fail"],
                            f'{row["upper_limit"]:.4f}',
                            f'{row["margin"]:.4f}']
        elif ( comparison_type == 'separate' ):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["mean_upper_limit"]:.4f}',
                            row["mean_pass_or_fail"],
                            f'{row["stdev"]:.4f}',
                            f'{row["stdev_upper_limit"]:.4f}',
                            row["stdev_pass_or_fail"]]
        else:
            raise Exception(f'''undefined parameter {comparison_type} 
            in generate_bigger_validation_report()''')
        data_pf_APOFF_recalc.append(row_as_list)
    
    t3=Table(data_pf_APOFF_recalc)
    # t2.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
    #     ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
    #     ('TEXTCOLOR',(3,1),(3,num_rows), colors.green),\
    #     ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
    #     ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]))
    t3_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
    
    any_single_failure_flag=False
    if comparison_type == 'combined':
        for idx, row in df_mean_stdev_tcorr_2.iterrows():
            if row["pass_or_fail"] == "PASS":
                t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
    elif comparison_type == 'separate':
        for idx, row in df_mean_stdev_tcorr_2.iterrows():
            if row["mean_pass_or_fail"] == "PASS":
                t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
        for idx, row in df_mean_stdev_tcorr_2.iterrows():
            if row["stdev_pass_or_fail"] == "PASS":
                t3_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.green))
            else:
                t3_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.red))
                any_single_failure_flag=True

    t3.setStyle(t3_table_style)
    document.append(t3)

    document.append(Spacer(6*inch,0.1*inch))
    document.append(Paragraph('APOFF Pass/Fail results without recalculation (recalc):'))
    document.append(Spacer(6*inch,0.1*inch))

    # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    #df_mean_stdev_not_tcorr_2 = calculate_pf_df(df_mean_stdev_not_tcorr,n_std_dev,'not_Tcorr')
    #df_mean_stdev_not_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[1],n_std_dev,'not_Tcorr')
    df_mean_stdev_not_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[1],n_std_dev,\
        'not_Tcorr',comparison_type)

    # convert dataframe to 2-D array, data2, with pass/fail criteria
    num_rows=len(df_mean_stdev_not_tcorr_2)
    num_cols=len(df_mean_stdev_not_tcorr_2.columns)
    data_pf_APOFF_no_recalc=[]
    if ( comparison_type == 'combined' ):
        header = [s.replace("_"," ") for s in df_mean_stdev_tcorr_2.columns.values]
    elif ( comparison_type == 'separate' ):
        header=['gas_standard','dry_mean','mean_upper_limit','mean_pass_or_fail',\
            'dry_stdev','stdev_upper_limit','stdev_pass_or_fail']
        header = [s.replace("_"," ") for s in header]
        header[2] = Paragraph('mean<br/>upper limit')
        header[3] = Paragraph('mean<br/>pass or fail')
        header[5] = Paragraph('stdev<br/>upper limit')
        header[6] = Paragraph('stdev<br/>pass or fail')
    data_pf_APOFF_no_recalc.append(header)
    #print(df_mean_stdev_not_tcorr_2.columns)
    for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
        if (comparison_type == 'combined'):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["stdev"]:.4f}',
                            row["pass_or_fail"],
                            f'{row["upper_limit"]:.4f}',
                            f'{row["margin"]:.4f}']
        elif ( comparison_type == 'separate' ):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["mean_upper_limit"]:.4f}',
                            row["mean_pass_or_fail"],
                            f'{row["stdev"]:.4f}',
                            f'{row["stdev_upper_limit"]:.4f}',
                            row["stdev_pass_or_fail"]]
        else:
            raise Exception(f'''undefined parameter {comparison_type} 
            in generate_bigger_validation_report()''')
        data_pf_APOFF_no_recalc.append(row_as_list)
    
    t4=Table(data_pf_APOFF_no_recalc)

    t4_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
   
    # change from df_mean_stdev_tcorr_2 to df_mean_stdev_not_tcorr_2, 7/15/2021, Pascal and Sophie
    if comparison_type == 'combined':
        for idx, row in df_mean_stdev_not_tcorr_2.iterrows(): 
            if row["pass_or_fail"] == "PASS":
                t4_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t4_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
    elif comparison_type == 'separate':
        for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
            if row["mean_pass_or_fail"] == "PASS":
                t4_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t4_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
        for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
            if row["stdev_pass_or_fail"] == "PASS":
                t4_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.green))
            else:
                t4_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.red))
                any_single_failure_flag=True

    t4.setStyle(t4_table_style)
    document.append(t4)
    document.append(PageBreak())
    ##### End of 1st page content, previously 5th page content #####

    ##### 2nd Page, previously 6th page content #####
    document.append(Paragraph('EPOFF Pass/Fail Determination for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))

    if ( comparison_type == 'combined'):
        sixth_page_text_above_sixth_page_table='''
        The ASVCO2 unit is credited with a passing result if the sum of the standard deviation,
        multiplied by a factor of ''' + f'{n_std_dev:.1f}' + ''', and the absolute value of the 
        mean is less than or equal to the upper limit in ppm. Otherwise, it is determined that 
        the ASVCO2 unit has failed the test. This is shown in the table below.
        '''
    elif ( comparison_type == 'separate'):
        sixth_page_text_above_sixth_page_table='''
        The ASVCO2 unit is credited with a passing result if the mean and the standard deviation
        of the residual are within their separate limits in ppm. Otherwise, it is determined that 
        the ASVCO2 unit has failed the test. This is shown in the table below.
        '''
    else:
        sixth_page_text_above_sixth_page_table = '''An undefined pass/fail criterion has been chosen
        and these pass/fail results might be invalid.'''
    document.append(Paragraph(sixth_page_text_above_sixth_page_table))
    document.append(Spacer(6*inch,0.1*inch))
    
    document.append(Paragraph('EPOFF Recalculated (recalc) Pass/Fail results:'))
    document.append(Spacer(6*inch,0.1*inch))

    # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    # df_mean_stdev_tcorr_2 = calculate_pf_df(df_mean_stdev_tcorr,n_std_dev)
    #df_mean_stdev_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[2],n_std_dev)
    df_mean_stdev_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[2],n_std_dev,\
        'Tcorr',comparison_type)

    # convert dataframe to 2-D array, data2, with pass/fail criteria
    num_rows=len(df_mean_stdev_tcorr_2)
    num_cols=len(df_mean_stdev_tcorr_2.columns)
    data_pf_EPOFF_recalc=[]
    if ( comparison_type == 'combined' ):
        header = [s.replace("_"," ") for s in df_mean_stdev_tcorr_2.columns.values]
    elif ( comparison_type == 'separate' ):
        header=['gas_standard','dry_res_mean','mean_upper_limit','mean_pass_or_fail',\
            'dry_res_stdev','stdev_upper_limit','stdev_pass_or_fail']
        header = [s.replace("_"," ") for s in header]
        header[2] = Paragraph('mean<br/>upper limit')
        header[3] = Paragraph('mean<br/>pass or fail')
        header[5] = Paragraph('stdev<br/>upper limit')
        header[6] = Paragraph('stdev<br/>pass or fail')
    data_pf_EPOFF_recalc.append(header)
    #print(df_mean_stdev_tcorr_2.columns)
    for idx, row in df_mean_stdev_tcorr_2.iterrows():
        if (comparison_type == 'combined'):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["stdev"]:.4f}',
                            row["pass_or_fail"],
                            f'{row["upper_limit"]:.4f}',
                            f'{row["margin"]:.4f}']
        elif ( comparison_type == 'separate' ):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["mean_upper_limit"]:.4f}',
                            row["mean_pass_or_fail"],
                            f'{row["stdev"]:.4f}',
                            f'{row["stdev_upper_limit"]:.4f}',
                            row["stdev_pass_or_fail"]]
        else:
            raise Exception(f'''undefined parameter {comparison_type} 
            in generate_bigger_validation_report()''')
        data_pf_EPOFF_recalc.append(row_as_list)
    
    t5=Table(data_pf_EPOFF_recalc)
    # t2.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
    #     ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
    #     ('TEXTCOLOR',(3,1),(3,num_rows), colors.green),\
    #     ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
    #     ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]))
    t5_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
    
    if comparison_type == 'combined':
        for idx, row in df_mean_stdev_tcorr_2.iterrows():
            if row["pass_or_fail"] == "PASS":
                t5_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t5_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
    elif comparison_type == 'separate':
        for idx, row in df_mean_stdev_tcorr_2.iterrows():
            if row["mean_pass_or_fail"] == "PASS":
                t5_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t5_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
        for idx, row in df_mean_stdev_tcorr_2.iterrows():
            if row["stdev_pass_or_fail"] == "PASS":
                t5_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.green))
            else:
                t5_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.red))
                any_single_failure_flag=True

    t5.setStyle(t5_table_style)
    document.append(t5)

    document.append(Spacer(6*inch,0.1*inch))
    document.append(Paragraph('EPOFF Pass/Fail results without recalculation (recalc):'))
    document.append(Spacer(6*inch,0.1*inch))

    # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    #df_mean_stdev_not_tcorr_2 = calculate_pf_df(df_mean_stdev_not_tcorr,n_std_dev,'not_Tcorr')
    #df_mean_stdev_not_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[3],n_std_dev,'not_Tcorr')
    df_mean_stdev_not_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[3],n_std_dev,\
        'not_Tcorr',comparison_type)

    # convert dataframe to 2-D array, data2, with pass/fail criteria
    num_rows=len(df_mean_stdev_not_tcorr_2)
    num_cols=len(df_mean_stdev_not_tcorr_2.columns)
    data_pf_EPOFF_no_recalc=[]
    if ( comparison_type == 'combined' ):
        header = [s.replace("_"," ") for s in df_mean_stdev_tcorr_2.columns.values]
    elif ( comparison_type == 'separate' ):
        header=['gas_standard','dry_res_mean','mean_upper_limit','mean_pass_or_fail',\
            'dry_res_stdev','stdev_upper_limit','stdev_pass_or_fail']
        header = [s.replace("_"," ") for s in header]
        header[2] = Paragraph('mean<br/>upper limit')
        header[3] = Paragraph('mean<br/>pass or fail')
        header[5] = Paragraph('stdev<br/>upper limit')
        header[6] = Paragraph('stdev<br/>pass or fail')
    data_pf_EPOFF_no_recalc.append(header)
    
    #print(df_mean_stdev_not_tcorr_2.columns)

    for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
        if (comparison_type == 'combined'):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["stdev"]:.4f}',
                            row["pass_or_fail"],
                            f'{row["upper_limit"]:.4f}',
                            f'{row["margin"]:.4f}']
        elif ( comparison_type == 'separate' ):
            row_as_list = [row["gas_standard"],
                            f'{row["mean"]:.4f}',
                            f'{row["mean_upper_limit"]:.4f}',
                            row["mean_pass_or_fail"],
                            f'{row["stdev"]:.4f}',
                            f'{row["stdev_upper_limit"]:.4f}',
                            row["stdev_pass_or_fail"]]
        else:
            raise Exception(f'''undefined parameter {comparison_type} 
            in generate_bigger_validation_report()''')
        data_pf_EPOFF_no_recalc.append(row_as_list)
    
    t6=Table(data_pf_EPOFF_no_recalc)

    t6_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
    
    # change from df_mean_stdev_tcorr_2 to df_mean_stdev_not_tcorr_2, 8/06/2021, Pascal
    if comparison_type == 'combined':
        for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
            if row["pass_or_fail"] == "PASS":
                t6_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t6_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
    elif comparison_type == 'separate':
        for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
            if row["mean_pass_or_fail"] == "PASS":
                t6_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.green))
            else:
                t6_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                    colors.red))
                any_single_failure_flag=True
        for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
            if row["stdev_pass_or_fail"] == "PASS":
                t6_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.green))
            else:
                t6_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                    colors.red))
                any_single_failure_flag=True

    t6.setStyle(t6_table_style)
    document.append(t6)
    document.append(Spacer(6*inch,0.1*inch))

    #### New stuff for range check####
    if ( re.search(r'.*The following problems were found in.*',final_text) ):
        document.append(Paragraph("<font color=\"orange\">Range Check: Some values were found to be out of range"\
            " please see the end of this report for details.</font>",\
                ParagraphStyle(name='Header12pt',fontSize=12)))
    else:
        document.append(Paragraph("Range Check: All values were found to be out in range",
                ParagraphStyle(name='Header12pt',fontSize=12)))

    document.append(PageBreak())
    #### End of 2nd page content, previously 6th page content ####

    ##### Previously 1st page Content ######
    document.append(Paragraph('--APOFF Summary--',ParagraphStyle(name='Header12pt',fontSize=12)))
    document.append(Spacer(6*inch,0.1*inch))
    
    ##### format start date and end date #####
    start_year = date_range[0][0:4]; end_year = date_range[0][0:4]
    start_month = date_range[0][4:6]; end_month = date_range[0][4:6]
    start_day = date_range[0][6:8]; end_day = date_range[0][6:8]
    start_str = start_month + "/" + start_day + "/" + start_year
    end_str = end_month + "/" + end_day + "/" + end_year

    first_page_text_above_first_figure='''
    The data shown in this report was collected between ''' + start_str + " and " + end_str + '''
    using ASVCO2 Gen2 with S/N ''' + sn + '''.
    The residuals shown in the figure below represent the measured carbon dioxide (CO2)
    gas concentration from the ASVCO2 test article in parts per million (ppm) subtracted from the
    standard gas concentration of CO2 in ppm. The colors represent the number of runs, or
    successive samples of measurement.'''
    document.append(Paragraph(first_page_text_above_first_figure))
    #document.append(Image('APOFF 1006 20210429.png',6*inch,18/5.0*inch))
    document.append(Image(figure_filenames_and_sizes[0][0],\
        figure_filenames_and_sizes[0][1]*inch,figure_filenames_and_sizes[0][2]*inch))
    first_page_text_below_first_figure='''
    As shown above, it is expected that there will be two regions of accuracy. One region,
    where the standard gases are below 1000ppm, have a tendency to show greater accuracy 
    (i.e. lower residuals) in the lower range as two of the three standard gases used for 
    calibrating the ASVCO2 test article (0ppm and 500ppm, approximately) occur in that range. 
    The other region, where the standard gases are above 1000ppm, have a tendency to show less 
    accuracy and the magnitude of the residual increases with increasing concentration in 
    the sense that a percent error may be observed. 
    '''
    document.append(Paragraph(first_page_text_below_first_figure))
    document.append(PageBreak())

    ##### Previously 2nd page content #####
    more_text='''Mathematical coefficients which determine the calculation of CO2 gas 
    concentration have been observed to be a function of temperature. It is
    expected that the residuals will be lower once these temperature corrections/adjustments
    are made. For further details, see <font color=blue><link>
    https://github.com/NOAA-PMEL/EDD-ASVCO2_Automation/tree/develop</link></font>'''

    document.append(Paragraph(more_text))
    #document.append(Image('830_830eq_res_all.png',6*inch,18/5.0*inch))
    document.append(Image(figure_filenames_and_sizes[1][0],\
        figure_filenames_and_sizes[1][1]*inch,figure_filenames_and_sizes[1][2]*inch))
    
    document.append(Paragraph('APOFF Statistical summaries of the residual, grouped by gas standard:'))
    document.append(Spacer(6*inch,0.1*inch))
    
    # convert dataframe to 2-D array, data1
    #df_4_comparison = df_mean_stdev_tcorr.copy()
    df_4_comparison = tuple_of_df_4_tables[0].copy() 
    df_4_comparison = df_4_comparison.rename(columns={'stdev':'dry_res_stdev_recalc','mean':'dry_res_mean_recalc'})
    # df_4_comparison["res_mean_not_recalc"] = df_mean_stdev_not_tcorr["mean"]
    # df_4_comparison["res_stdev_not_recalc"] = df_mean_stdev_not_tcorr["stdev"]
    df_4_comparison["dry_res_mean_not_recalc"] = tuple_of_df_4_tables[1]["mean"]  # Bug fix, 6/25/2021 due to Noah's comment
    df_4_comparison["dry_res_stdev_not_recalc"] = tuple_of_df_4_tables[1]["stdev"]  # Bug fix, 6/25/2021 due to Noah's comment
    num_rows=len(df_4_comparison)
    num_cols=len(df_4_comparison.columns)
    data_summary_APOFF=[]
    header = [s.replace("_"," ") for s in df_4_comparison.columns.values]
    data_summary_APOFF.append(header)
    #print(df_4_comparison.columns)
    for idx, row in df_4_comparison.iterrows():
        row_as_list = [row["gas_standard"],
                f'{row["dry_res_mean_recalc"]:.4f}',
                f'{row["dry_res_stdev_recalc"]:.4f}',
                f'{row["dry_res_mean_not_recalc"]:.4f}',
                f'{row["dry_res_stdev_not_recalc"]:.4f}']
        data_summary_APOFF.append(row_as_list)

    t1=Table(data_summary_APOFF)
    t1.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]))
    document.append(t1)

    document.append(PageBreak())

    ##### 3rd page #####
    document.append(Spacer(6*inch,0.1*inch))
    document.append(Paragraph('--EPOFF Summary--',ParagraphStyle(name='Header12pt',fontSize=12)))
    document.append(Spacer(6*inch,0.1*inch))
    
    ##### format start date and end date #####
    start_year = date_range[0][0:4]; end_year = date_range[0][0:4]
    start_month = date_range[0][4:6]; end_month = date_range[0][4:6]
    start_day = date_range[0][6:8]; end_day = date_range[0][6:8]
    start_str = start_month + "/" + start_day + "/" + start_year
    end_str = end_month + "/" + end_day + "/" + end_year

    third_page_text_above_third_figure='''
    The data shown in this report was collected between ''' + start_str + " and " + end_str + '''
    using ASVCO2 Gen2 with S/N ''' + sn + '''.
    The residuals shown in the figure below represent the measured carbon dioxide (CO2)
    gas concentration from the ASVCO2 test article in parts per million (ppm) subtracted from the
    standard gas concentration of CO2 in ppm. The colors represent the number of runs, or
    successive samples of measurement.'''
    document.append(Paragraph(third_page_text_above_third_figure))
    #document.append(Image('APOFF 1006 20210429.png',6*inch,18/5.0*inch))
    document.append(Image(figure_filenames_and_sizes[2][0],\
        figure_filenames_and_sizes[2][1]*inch,figure_filenames_and_sizes[2][2]*inch))
    third_page_text_below_third_figure='''
    As shown above, it is expected that there will be two regions of accuracy. One region,
    where the standard gases are below 1000ppm, have a tendency to show greater accuracy 
    (i.e. lower residuals) in the lower range as two of the three standard gases used for 
    calibrating the ASVCO2 test article (0ppm and 500ppm, approximately) occur in that range. 
    The other region, where the standard gases are above 1000ppm, have a tendency to show less 
    accuracy and the magnitude of the residual increases with increasing concentration in 
    the sense that a percent error may be observed. 
    '''
    document.append(Paragraph(third_page_text_below_third_figure))
    document.append(PageBreak())

    ##### 4th page #####
    more_text='''Mathematical coefficients which determine the calculation of CO2 gas 
    concentration have been observed to be a function of temperature. It is
    expected that the residuals will be lower once these temperature corrections/adjustments
    are made. For further details, see <font color=blue><link>
    https://github.com/NOAA-PMEL/EDD-ASVCO2_Automation/tree/develop</link></font>'''

    document.append(Paragraph(more_text))
    #document.append(Image('830_830eq_res_all.png',6*inch,18/5.0*inch))
    document.append(Image(figure_filenames_and_sizes[3][0],\
        figure_filenames_and_sizes[3][1]*inch,figure_filenames_and_sizes[3][2]*inch))
    
    document.append(Paragraph('EPOFF Statistical summaries of the residual, grouped by gas standard:'))
    document.append(Spacer(6*inch,0.1*inch))
    
    # convert dataframe to 2-D array, data1
    #df_4_comparison = df_mean_stdev_tcorr.copy()
    df_4_comparison = tuple_of_df_4_tables[2].copy()  # Bug fix, 6/25/2021 due to Noah's comment
    df_4_comparison = df_4_comparison.rename(columns={'stdev':'dry_res_stdev_recalc','mean':'dry_res_mean_recalc'})
    # df_4_comparison["res_mean_not_recalc"] = df_mean_stdev_not_tcorr["mean"]
    # df_4_comparison["res_stdev_not_recalc"] = df_mean_stdev_not_tcorr["stdev"]
    df_4_comparison["dry_res_mean_not_recalc"] = tuple_of_df_4_tables[3]["mean"]  # Bug fix, 6/25/2021 due to Noah's comment
    df_4_comparison["dry_res_stdev_not_recalc"] = tuple_of_df_4_tables[3]["stdev"] # Bug fix, 6/25/2021 due to Noah's comment
    num_rows=len(df_4_comparison)
    num_cols=len(df_4_comparison.columns)
    data_summary_EPOFF=[]
    header = [s.replace("_"," ") for s in df_4_comparison.columns.values]
    data_summary_EPOFF.append(header)
    #print(df_4_comparison.columns)
    for idx, row in df_4_comparison.iterrows():
        row_as_list = [row["gas_standard"],
                f'{row["dry_res_mean_recalc"]:.4f}',
                f'{row["dry_res_stdev_recalc"]:.4f}',
                f'{row["dry_res_mean_not_recalc"]:.4f}',
                f'{row["dry_res_stdev_not_recalc"]:.4f}']
        data_summary_EPOFF.append(row_as_list)

    t2=Table(data_summary_EPOFF)
    t2.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]))
    document.append(t2)

    document.append(PageBreak())


    # document.append(Paragraph('Here\'s another table below:'))
    # mydata=[['stuff',0.0],['more stuff',-2.6],\
    #     ['even more stuff',-10.9],['yet again more stuff',9999999.099999]]
    # t2=Table(mydata)
    # t2.setStyle(TableStyle([('ALIGN',(0,0),(2,3),'LEFT'), ('TEXTCOLOR',(0,0),(2,3), colors.black),\
    #     ('INNERGRID', (0,0), (2,3), 0.25, colors.black),('BOX', (0,0), (2,3), 0.25, colors.black)]))
    # document.append(t2)


    ##### 7th page #####
    document.append(Paragraph('Configuration Description for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))

    file_ptr=open(validation_text_filename, 'r')
    lines = file_ptr.readlines()
    seventh_page_text = ''

    start_line = 0
    line_is_empty=len(lines[start_line].strip()) == 0
    while line_is_empty:
        start_line += 1
        line_is_empty = len(lines[start_line].strip()) == 0
        
    end_line = start_line
    line_is_not_empty=len(lines[end_line].strip()) != 0
    while line_is_not_empty:
        end_line += 1
        line_is_not_empty = len(lines[end_line].strip()) != 0          

    for idx in range(start_line,end_line):
        seventh_page_text += lines[idx] + "<br/>"

    document.append(Paragraph(seventh_page_text))
    file_ptr.close()

    document.append(PageBreak())

    ##### 8th Page #####
    document.append(Paragraph('Description of Terms and Abbreviations',\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))
    #S<super rise=-4 size=6>1</super>
    description_of_terms='''
    <b>res</b> - residual, measured value - actual value<br/>
    <b>recalc</b> - recalculated according to temperature adjustment of S<sub>1</sub>,
    where S<sub>1</sub> is defined in the Appendix of the LI-830 and LI-850 user manual.<br/>
    For further details, see <font color=blue><link>
    https://github.com/NOAA-PMEL/EDD-ASVCO2_Automation/tree/develop</link></font><br/>
    <b>not recalc</b> - the S<sub>1</sub> coefficient is not adjusted for temperature<br/>
    <b>stdev</b> - the standard deviation<br/>
    <b>upper limit</b> - if a value exceeds this limit, then the unit has failed the test<br/>
    <b>ppm</b> - parts per million (ppm)<br/>
    <b>APOFF</b> - Air Pump OFF, this is a valve state in the ASVCO2 unit measuring the air<br/>
    <b>EPOFF</b> - Equilibrator Pump OFF, this is a valve state in the ASVCO2 unit measuring the equilibrator<br/>
    '''
    document.append(Paragraph(description_of_terms))

    # New feature, 9/21/2021, add in final text
    document.append(Spacer(6*inch,0.1*inch))
    document.append(Paragraph("Range Check Results:<br/>",
                ParagraphStyle(name='Header12pt',fontSize=12)))
    document.append(Paragraph(final_text))

    #output_filename='demo_1006.pdf'
    if ( any_single_failure_flag ):
        last_piece_of_filename = "FAIL"
    else:
        last_piece_of_filename = "PASS"
    output_filename = output_folder + '/' + "Gas_Validation_" + sn + "_" + \
        date_range[0][0:8] + "_" + last_piece_of_filename + ".pdf"
    
    # SimpleDocTemplate(output_filename,pagesize=letter,\
    #     rightMargin=1*inch, leftMargin=1*inch,\
    #         topMargin=1*inch, bottomMargin=1*inch).build(document)

    doc = SimpleDocTemplate(output_filename,pagesize=letter,\
        rightMargin=1*inch, leftMargin=1*inch,\
        topMargin=1*inch, bottomMargin=1*inch)

    doc.build(document, onFirstPage=myFirstPage, onLaterPages=myLaterPages)

def df_to_reportlab_table_with_pf(df_in, any_single_failure_flag, calc_type='Tcorr'):
    # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    #df_mean_stdev_tcorr_2 = calculate_pf_df(df_mean_stdev_tcorr,n_std_dev)
    #df_mean_stdev_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[0],n_std_dev)
    
    #df_mean_stdev_max_tcorr_2 = calculate_pf_df_v2(tuple_of_df_4_tables[0],'Tcorr')
    df_mean_stdev_max_2 = calculate_pf_df_v2(df_in,calc_type)
    
    print(df_mean_stdev_max_2)

    # convert dataframe to 2-D array, data2, with pass/fail criteria
    #"gas_standard_lower":[],"gas_standard_upper":[],\
    #    "mean":[],"stdev":[],"max":[]
    num_rows=len(df_mean_stdev_max_2)
    num_cols=len(df_mean_stdev_max_2.columns)
    data_pf_APOFF_recalc=[]

    header=['gas_standard_group','dry_mean','mean_upper_limit','mean_pass_or_fail',\
        'dry_stdev','stdev_upper_limit','stdev_pass_or_fail',\
        'dry_max','max_upper_limit','max_pass_or_fail']
    header = [s.replace("_"," ") for s in header]
    #reformat for multiple lines
    header[0] = Paragraph('gas<br/>standard<br/>group')
    header[2] = Paragraph('mean<br/>upper<br/>limit')
    header[3] = Paragraph('mean<br/>pass<br/>or fail')
    header[5] = Paragraph('stdev<br/>upper<br/>limit')
    header[6] = Paragraph('stdev<br/>pass<br/>or fail')
    header[5] = Paragraph('stdev<br/>upper<br/>limit')
    header[6] = Paragraph('stdev<br/>pass<br/>or fail')
    header[8] = Paragraph('max<br/>upper<br/>limit')
    header[9] = Paragraph('max<br/>upper<br/>limit')
    data_pf_APOFF_recalc.append(header)
    #print(df_mean_stdev_tcorr_2.columns)
    #print(df_mean_stdev_tcorr_2.columns.values)
    for idx, row in df_mean_stdev_max_2.iterrows():
        lower_ref_gas = row["gas_standard_lower"]
        upper_ref_gas = row["gas_standard_upper"]
        lower_ref_gas_txt1 = f'{lower_ref_gas:.1f}ppm'
        upper_ref_gas_txt2 = f'{upper_ref_gas:.1f}ppm'
        row_as_list = [Paragraph(lower_ref_gas_txt1 + \
                        '<br/>thru<br/>' + upper_ref_gas_txt2),
                        f'{row["mean"]:.2f}',
                        f'{row["mean_upper_limit"]:.2f}',
                        row["mean_pass_or_fail"],
                        f'{row["stdev"]:.2f}',
                        f'{row["stdev_upper_limit"]:.2f}',
                        row["stdev_pass_or_fail"],
                            f'{row["max"]:.2f}',
                        f'{row["max_upper_limit"]:.2f}',
                        row["max_pass_or_fail"]]
        data_pf_APOFF_recalc.append(row_as_list)
    
    t3=Table(data_pf_APOFF_recalc)
    # t2.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
    #     ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
    #     ('TEXTCOLOR',(3,1),(3,num_rows), colors.green),\
    #     ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
    #     ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]))
    t3_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
    
    #any_single_failure_flag=False

    for idx, row in df_mean_stdev_max_2.iterrows():
        if row["mean_pass_or_fail"] == "PASS":
            t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                colors.green))
        else:
            t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
                colors.red))
            any_single_failure_flag=True
    for idx, row in df_mean_stdev_max_2.iterrows():
        if row["stdev_pass_or_fail"] == "PASS":
            t3_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                colors.green))
        else:
            t3_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
                colors.red))
            any_single_failure_flag=True
    for idx, row in df_mean_stdev_max_2.iterrows():
        if row["max_pass_or_fail"] == "PASS":
            t3_table_style.append(('TEXTCOLOR',(9,idx+1),(9,idx+1),\
                colors.green))
        else:
            t3_table_style.append(('TEXTCOLOR',(9,idx+1),(9,idx+1),\
                colors.red))
            any_single_failure_flag=True

    t3.setStyle(t3_table_style)

    return t3, any_single_failure_flag

def generate_bigger_validation_report_reordered_Feb_2022(output_folder,sn,date_range,\
    figure_filenames_and_sizes,tuple_of_df_4_tables,validation_text_filename,final_text=''):
    document = []
    
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ##### 1st page #####
    document.append(Image(PROJECT_ROOT + '/code/post_processing/config/ASVCO2_logo.png',3.87*inch,1.06*inch))
    #document.append(Spacer(6*inch,0.25*inch))
    document.append(Paragraph('Gas Validation for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))

    ##### 1st page content, previously 5th page content #####
    document.append(Paragraph('APOFF Pass/Fail Determination for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))

    #comparison_type = 'combined'  # pass/fail will be by abs(mean) + n_std_dev * std_dev
    comparison_type = 'separate'  # pass/fail will be by separate limits of mean and std_dev

    #set any_single_failure_flag to false, used to title filename if there is any failure
    any_single_failure_flag=False

    #### Feb 2022, new stuff, vaguely IAW Adrienne Sutton's direction ####
    data_0_750_APOFF = []
    df_mean_w_95_conf_interval_APOFF = tuple_of_df_4_tables[4]
    header = ['range','mean residual with 95% confidence','upper limit','PASS/FAIL']
    res_mean = df_mean_w_95_conf_interval_APOFF.loc[0,'res_mean']
    res_conf_95 = df_mean_w_95_conf_interval_APOFF.loc[0,'conf_95']
    res_mean_95_txt = f'{res_mean:.2f} +/- {res_conf_95:.2f}'
    upper_limit_APOFF = 2.0
    if ( (res_mean+res_conf_95) > upper_limit_APOFF or \
        (res_mean-res_conf_95) < (-upper_limit_APOFF) ):
        APOFF_0_750_pf = "FAIL"
    else:
        APOFF_0_750_pf = "PASS"
    data_0_750_APOFF.append(header)
    data_0_750_APOFF.append(['0ppm thru 750ppm',res_mean_95_txt,\
        str(upper_limit_APOFF),APOFF_0_750_pf])

    t_0_750_APOFF=Table(data_0_750_APOFF)
    t_0_750_APOFF_table_style=[('ALIGN',(0,0),(4,2),'LEFT'),\
        ('TEXTCOLOR',(0,0),(4,2), colors.black),\
        ('INNERGRID', (0,0), (4,2), 0.25, colors.black),\
        ('BOX', (0,0), (4,2), 0.25, colors.black)]
    if ( APOFF_0_750_pf == "FAIL"):
        t_0_750_APOFF_table_style.append(('TEXTCOLOR',(3,1),(3,1),\
                    colors.red))
    else:
        t_0_750_APOFF_table_style.append(('TEXTCOLOR',(3,1),(3,1),\
                    colors.green))

    document.append(Paragraph('APOFF Pass/Fail results for 0ppm through 750ppm gas standard:'))
    document.append(Spacer(6*inch,0.1*inch))
    t_0_750_APOFF.setStyle(t_0_750_APOFF_table_style)
    document.append(t_0_750_APOFF)
    document.append(Spacer(6*inch,0.1*inch))

    n_std_dev=1  # for combined only number of standard deviations from the mean to set pass fail criteria
    
    if ( comparison_type == 'combined'):
        fifth_page_text_above_fifth_page_table='''
        The ASVCO2 unit is credited with a passing result if the sum of the standard deviation,
        multiplied by a factor of ''' + f'{n_std_dev:.1f}' + ''', and the absolute value of the 
        mean is less than or equal to the upper limit in ppm. Otherwise, it is determined that 
        the ASVCO2 unit has failed the test. This is shown in the table below.
        '''
    elif ( comparison_type == 'separate'):
        fifth_page_text_above_fifth_page_table='''
        The ASVCO2 unit is credited with a passing result if the mean and the standard deviation
        of the residual are within their separate limits in ppm. Otherwise, it is determined that 
        the ASVCO2 unit has failed the test. This is shown in the table below.
        '''
    else:
        fifth_page_text_above_fifth_page_table = '''An undefined pass/fail criterion has been chosen
        and these pass/fail results might be invalid.'''

    document.append(Paragraph(fifth_page_text_above_fifth_page_table))
    document.append(Spacer(6*inch,0.1*inch))
    
    document.append(Paragraph('APOFF Recalculated (recalc) Pass/Fail results:'))
    document.append(Spacer(6*inch,0.1*inch))

    # # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    # #df_mean_stdev_tcorr_2 = calculate_pf_df(df_mean_stdev_tcorr,n_std_dev)
    # #df_mean_stdev_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[0],n_std_dev)
    # df_mean_stdev_max_tcorr_2 = calculate_pf_df_v2(tuple_of_df_4_tables[0],'Tcorr')
    
    # # convert dataframe to 2-D array, data2, with pass/fail criteria
    # num_rows=len(df_mean_stdev_max_tcorr_2)
    # num_cols=len(df_mean_stdev_max_tcorr_2.columns)
    # data_pf_APOFF_recalc=[]
    # if ( comparison_type == 'combined' ):
    #     header = [s.replace("_"," ") for s in df_mean_stdev_tcorr_2.columns.values]
    # elif ( comparison_type == 'separate' ):
    #     header=['gas_standard_group','dry_mean','mean_upper_limit','mean_pass_or_fail',\
    #         'dry_stdev','stdev_upper_limit','stdev_pass_or_fail',\
    #         'dry_max','max_upper_limit','max_pass_or_fail']
    #     header = [s.replace("_"," ") for s in header]
    #     #reformat for multiple lines
    #     header[0] = Paragraph('gas<br/>stanard<br/>group')
    #     header[2] = Paragraph('mean<br/>upper<br/>limit')
    #     header[3] = Paragraph('mean<br/>pass<br/>or fail')
    #     header[5] = Paragraph('stdev<br/>upper<br/>limit')
    #     header[6] = Paragraph('stdev<br/>pass<br/>or fail')
    #     header[5] = Paragraph('stdev<br/>upper<br/>limit')
    #     header[6] = Paragraph('stdev<br/>pass<br/>or fail')
    #     header[8] = Paragraph('max<br/>upper<br/>limit')
    #     header[9] = Paragraph('max<br/>upper<br/>limit')
    # data_pf_APOFF_recalc.append(header)
    # #print(df_mean_stdev_tcorr_2.columns)
    # #print(df_mean_stdev_tcorr_2.columns.values)
    # for idx, row in df_mean_stdev_max_tcorr_2.iterrows():
    #     if (comparison_type == 'combined'):
    #         row_as_list = [row["gas_standard"],
    #                         f'{row["mean"]:.4f}',
    #                         f'{row["stdev"]:.4f}',
    #                         row["pass_or_fail"],
    #                         f'{row["upper_limit"]:.4f}',
    #                         f'{row["margin"]:.4f}']
    #     elif ( comparison_type == 'separate' ):
    #         lower_ref_gas = row["gas_standard_lower"]
    #         upper_ref_gas = row["gas_standard_upper"]
    #         lower_ref_gas_txt1 = f'{lower_ref_gas:.1f}ppm'
    #         upper_ref_gas_txt2 = f'{upper_ref_gas:.1f}ppm'
    #         row_as_list = [Paragraph(lower_ref_gas_txt1 + \
    #                         '<br/>thru<br/>' + upper_ref_gas_txt2),
    #                         f'{row["mean"]:.2f}',
    #                         f'{row["mean_upper_limit"]:.2f}',
    #                         row["mean_pass_or_fail"],
    #                         f'{row["stdev"]:.2f}',
    #                         f'{row["stdev_upper_limit"]:.2f}',
    #                         row["stdev_pass_or_fail"],
    #                             f'{row["max"]:.2f}',
    #                         f'{row["max_upper_limit"]:.2f}',
    #                         row["max_pass_or_fail"]]
    #     else:
    #         raise Exception(f'''undefined parameter {comparison_type} 
    #         in generate_bigger_validation_report()''')
    #     data_pf_APOFF_recalc.append(row_as_list)
    
    # t3=Table(data_pf_APOFF_recalc)
    # # t2.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
    # #     ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
    # #     ('TEXTCOLOR',(3,1),(3,num_rows), colors.green),\
    # #     ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
    # #     ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]))
    # t3_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
    #     ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
    #     ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
    #     ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
    
    # any_single_failure_flag=False
    # if comparison_type == 'combined':
    #     for idx, row in df_mean_stdev_tcorr_2.iterrows():
    #         if row["pass_or_fail"] == "PASS":
    #             t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.green))
    #         else:
    #             t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.red))
    #             any_single_failure_flag=True
    # elif comparison_type == 'separate':
    #     for idx, row in df_mean_stdev_max_tcorr_2.iterrows():
    #         if row["mean_pass_or_fail"] == "PASS":
    #             t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.green))
    #         else:
    #             t3_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.red))
    #             any_single_failure_flag=True
    #     for idx, row in df_mean_stdev_max_tcorr_2.iterrows():
    #         if row["stdev_pass_or_fail"] == "PASS":
    #             t3_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
    #                 colors.green))
    #         else:
    #             t3_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
    #                 colors.red))
    #             any_single_failure_flag=True
    #     for idx, row in df_mean_stdev_max_tcorr_2.iterrows():
    #         if row["max_pass_or_fail"] == "PASS":
    #             t3_table_style.append(('TEXTCOLOR',(9,idx+1),(9,idx+1),\
    #                 colors.green))
    #         else:
    #             t3_table_style.append(('TEXTCOLOR',(9,idx+1),(9,idx+1),\
    #                 colors.red))
    #             any_single_failure_flag=True

    # t3.setStyle(t3_table_style)

    t3, any_single_failure_flag = df_to_reportlab_table_with_pf(tuple_of_df_4_tables[0],\
        any_single_failure_flag,'Tcorr')
    document.append(t3)
    document.append(PageBreak())

    document.append(Spacer(6*inch,0.1*inch))
    document.append(Paragraph('APOFF Pass/Fail results without recalculation (recalc):'))
    document.append(Spacer(6*inch,0.1*inch))

    # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    #df_mean_stdev_not_tcorr_2 = calculate_pf_df(df_mean_stdev_not_tcorr,n_std_dev,'not_Tcorr')
    #df_mean_stdev_not_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[1],n_std_dev,'not_Tcorr')
    # df_mean_stdev_not_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[1],n_std_dev,\
    #     'not_Tcorr',comparison_type)

    # convert dataframe to 2-D array, data2, with pass/fail criteria
    # num_rows=len(df_mean_stdev_not_tcorr_2)
    # num_cols=len(df_mean_stdev_not_tcorr_2.columns)
    # data_pf_APOFF_no_recalc=[]
    # if ( comparison_type == 'combined' ):
    #     header = [s.replace("_"," ") for s in df_mean_stdev_tcorr_2.columns.values]
    # elif ( comparison_type == 'separate' ):
    #     header=['gas_standard','dry_mean','mean_upper_limit','mean_pass_or_fail',\
    #         'dry_stdev','stdev_upper_limit','stdev_pass_or_fail']
    #     header = [s.replace("_"," ") for s in header]
    #     header[2] = Paragraph('mean<br/>upper limit')
    #     header[3] = Paragraph('mean<br/>pass or fail')
    #     header[5] = Paragraph('stdev<br/>upper limit')
    #     header[6] = Paragraph('stdev<br/>pass or fail')
    # data_pf_APOFF_no_recalc.append(header)
    # #print(df_mean_stdev_not_tcorr_2.columns)
    # for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
    #     if (comparison_type == 'combined'):
    #         row_as_list = [row["gas_standard"],
    #                         f'{row["mean"]:.4f}',
    #                         f'{row["stdev"]:.4f}',
    #                         row["pass_or_fail"],
    #                         f'{row["upper_limit"]:.4f}',
    #                         f'{row["margin"]:.4f}']
    #     elif ( comparison_type == 'separate' ):
    #         row_as_list = [row["gas_standard"],
    #                         f'{row["mean"]:.4f}',
    #                         f'{row["mean_upper_limit"]:.4f}',
    #                         row["mean_pass_or_fail"],
    #                         f'{row["stdev"]:.4f}',
    #                         f'{row["stdev_upper_limit"]:.4f}',
    #                         row["stdev_pass_or_fail"]]
    #     else:
    #         raise Exception(f'''undefined parameter {comparison_type} 
    #         in generate_bigger_validation_report()''')
    #     data_pf_APOFF_no_recalc.append(row_as_list)
    
    # t4=Table(data_pf_APOFF_no_recalc)

    # t4_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
    #     ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
    #     ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
    #     ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
   
    # # change from df_mean_stdev_tcorr_2 to df_mean_stdev_not_tcorr_2, 7/15/2021, Pascal and Sophie
    # if comparison_type == 'combined':
    #     for idx, row in df_mean_stdev_not_tcorr_2.iterrows(): 
    #         if row["pass_or_fail"] == "PASS":
    #             t4_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.green))
    #         else:
    #             t4_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.red))
    #             any_single_failure_flag=True
    # elif comparison_type == 'separate':
    #     for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
    #         if row["mean_pass_or_fail"] == "PASS":
    #             t4_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.green))
    #         else:
    #             t4_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.red))
    #             any_single_failure_flag=True
    #     for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
    #         if row["stdev_pass_or_fail"] == "PASS":
    #             t4_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
    #                 colors.green))
    #         else:
    #             t4_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
    #                 colors.red))
    #             any_single_failure_flag=True

    # t4.setStyle(t4_table_style)

    t4, any_single_failure_flag = df_to_reportlab_table_with_pf(tuple_of_df_4_tables[1],\
        any_single_failure_flag,'not_Tcorr')
    document.append(t4)

    document.append(PageBreak())
    ##### End of 1st page content, previously 5th page content #####

    ##### 2nd Page, previously 6th page content #####
    document.append(Paragraph('EPOFF Pass/Fail Determination for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))

    #### Feb 2022, new stuff, vaguely IAW Adrienne Sutton's direction ####
    data_0_750_EPOFF = []
    df_mean_w_95_conf_interval_EPOFF = tuple_of_df_4_tables[5]
    header = ['range','mean residual with 95% confidence','upper limit','PASS/FAIL']
    res_mean = df_mean_w_95_conf_interval_EPOFF.loc[0,'res_mean']
    res_conf_95 = df_mean_w_95_conf_interval_EPOFF.loc[0,'conf_95']
    res_mean_95_txt = f'{res_mean:.2f} +/- {res_conf_95:.2f}'
    upper_limit_EPOFF = 2.0
    if ( (res_mean+res_conf_95) > upper_limit_EPOFF or \
        (res_mean-res_conf_95) < (-upper_limit_EPOFF) ):
        EPOFF_0_750_pf = "FAIL"
    else:
        EPOFF_0_750_pf = "PASS"
    data_0_750_EPOFF.append(header)
    data_0_750_EPOFF.append(['0ppm thru 750ppm',res_mean_95_txt,\
        str(upper_limit_EPOFF),EPOFF_0_750_pf])

    t_0_750_EPOFF=Table(data_0_750_EPOFF)
    t_0_750_EPOFF_table_style=[('ALIGN',(0,0),(4,2),'LEFT'),\
        ('TEXTCOLOR',(0,0),(4,2), colors.black),\
        ('INNERGRID', (0,0), (4,2), 0.25, colors.black),\
        ('BOX', (0,0), (4,2), 0.25, colors.black)]
    if ( EPOFF_0_750_pf == "FAIL"):
        t_0_750_EPOFF_table_style.append(('TEXTCOLOR',(3,1),(3,1),\
                    colors.red))
    else:
        t_0_750_EPOFF_table_style.append(('TEXTCOLOR',(3,1),(3,1),\
                    colors.green))

    document.append(Paragraph('EPOFF Pass/Fail results for 0ppm through 750ppm gas standard:'))
    document.append(Spacer(6*inch,0.1*inch))
    t_0_750_EPOFF.setStyle(t_0_750_EPOFF_table_style)
    document.append(t_0_750_EPOFF)
    document.append(Spacer(6*inch,0.1*inch))

    if ( comparison_type == 'combined'):
        sixth_page_text_above_sixth_page_table='''
        The ASVCO2 unit is credited with a passing result if the sum of the standard deviation,
        multiplied by a factor of ''' + f'{n_std_dev:.1f}' + ''', and the absolute value of the 
        mean is less than or equal to the upper limit in ppm. Otherwise, it is determined that 
        the ASVCO2 unit has failed the test. This is shown in the table below.
        '''
    elif ( comparison_type == 'separate'):
        sixth_page_text_above_sixth_page_table='''
        The ASVCO2 unit is credited with a passing result if the mean and the standard deviation
        of the residual are within their separate limits in ppm. Otherwise, it is determined that 
        the ASVCO2 unit has failed the test. This is shown in the table below.
        '''
    else:
        sixth_page_text_above_sixth_page_table = '''An undefined pass/fail criterion has been chosen
        and these pass/fail results might be invalid.'''
    document.append(Paragraph(sixth_page_text_above_sixth_page_table))
    document.append(Spacer(6*inch,0.1*inch))
    
    document.append(Paragraph('EPOFF Recalculated (recalc) Pass/Fail results:'))
    document.append(Spacer(6*inch,0.1*inch))

    # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    # df_mean_stdev_tcorr_2 = calculate_pf_df(df_mean_stdev_tcorr,n_std_dev)
    #df_mean_stdev_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[2],n_std_dev)
    # df_mean_stdev_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[2],n_std_dev,\
    #     'Tcorr',comparison_type)

    # convert dataframe to 2-D array, data2, with pass/fail criteria
    # num_rows=len(df_mean_stdev_tcorr_2)
    # num_cols=len(df_mean_stdev_tcorr_2.columns)
    # data_pf_EPOFF_recalc=[]
    # if ( comparison_type == 'combined' ):
    #     header = [s.replace("_"," ") for s in df_mean_stdev_tcorr_2.columns.values]
    # elif ( comparison_type == 'separate' ):
    #     header=['gas_standard','dry_res_mean','mean_upper_limit','mean_pass_or_fail',\
    #         'dry_res_stdev','stdev_upper_limit','stdev_pass_or_fail']
    #     header = [s.replace("_"," ") for s in header]
    #     header[2] = Paragraph('mean<br/>upper limit')
    #     header[3] = Paragraph('mean<br/>pass or fail')
    #     header[5] = Paragraph('stdev<br/>upper limit')
    #     header[6] = Paragraph('stdev<br/>pass or fail')
    # data_pf_EPOFF_recalc.append(header)
    # #print(df_mean_stdev_tcorr_2.columns)
    # for idx, row in df_mean_stdev_tcorr_2.iterrows():
    #     if (comparison_type == 'combined'):
    #         row_as_list = [row["gas_standard"],
    #                         f'{row["mean"]:.4f}',
    #                         f'{row["stdev"]:.4f}',
    #                         row["pass_or_fail"],
    #                         f'{row["upper_limit"]:.4f}',
    #                         f'{row["margin"]:.4f}']
    #     elif ( comparison_type == 'separate' ):
    #         row_as_list = [row["gas_standard"],
    #                         f'{row["mean"]:.4f}',
    #                         f'{row["mean_upper_limit"]:.4f}',
    #                         row["mean_pass_or_fail"],
    #                         f'{row["stdev"]:.4f}',
    #                         f'{row["stdev_upper_limit"]:.4f}',
    #                         row["stdev_pass_or_fail"]]
    #     else:
    #         raise Exception(f'''undefined parameter {comparison_type} 
    #         in generate_bigger_validation_report()''')
    #     data_pf_EPOFF_recalc.append(row_as_list)
    
    # t5=Table(data_pf_EPOFF_recalc)
    # # t2.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
    # #     ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
    # #     ('TEXTCOLOR',(3,1),(3,num_rows), colors.green),\
    # #     ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
    # #     ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]))
    # t5_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
    #     ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
    #     ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
    #     ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
    
    # if comparison_type == 'combined':
    #     for idx, row in df_mean_stdev_tcorr_2.iterrows():
    #         if row["pass_or_fail"] == "PASS":
    #             t5_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.green))
    #         else:
    #             t5_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.red))
    #             any_single_failure_flag=True
    # elif comparison_type == 'separate':
    #     for idx, row in df_mean_stdev_tcorr_2.iterrows():
    #         if row["mean_pass_or_fail"] == "PASS":
    #             t5_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.green))
    #         else:
    #             t5_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.red))
    #             any_single_failure_flag=True
    #     for idx, row in df_mean_stdev_tcorr_2.iterrows():
    #         if row["stdev_pass_or_fail"] == "PASS":
    #             t5_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
    #                 colors.green))
    #         else:
    #             t5_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
    #                 colors.red))
    #             any_single_failure_flag=True

    # t5.setStyle(t5_table_style)
    t5, any_single_failure_flag = df_to_reportlab_table_with_pf(tuple_of_df_4_tables[2],\
        any_single_failure_flag,'Tcorr')
    document.append(t5)
    document.append(PageBreak())

    #### Begin EPOFF Stuff ####
    # document.append(Paragraph('EPOFF Pass/Fail Determination for ASVCO2 Gen2, Serial Number: ' + sn,\
    #     ParagraphStyle(name='Title',fontSize=14)))
    # document.append(Spacer(6*inch,0.1*inch))

    document.append(Spacer(6*inch,0.1*inch))
    document.append(Paragraph('EPOFF Pass/Fail results without recalculation (recalc):'))
    document.append(Spacer(6*inch,0.1*inch))

    # calculate whether or not the results will pass or fail and store the result in df_mean_stdev_tcorr_2
    #df_mean_stdev_not_tcorr_2 = calculate_pf_df(df_mean_stdev_not_tcorr,n_std_dev,'not_Tcorr')
    #df_mean_stdev_not_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[3],n_std_dev,'not_Tcorr')
    # df_mean_stdev_not_tcorr_2 = calculate_pf_df(tuple_of_df_4_tables[3],n_std_dev,\
    #     'not_Tcorr',comparison_type)

    # # convert dataframe to 2-D array, data2, with pass/fail criteria
    # num_rows=len(df_mean_stdev_not_tcorr_2)
    # num_cols=len(df_mean_stdev_not_tcorr_2.columns)
    # data_pf_EPOFF_no_recalc=[]
    # if ( comparison_type == 'combined' ):
    #     header = [s.replace("_"," ") for s in df_mean_stdev_tcorr_2.columns.values]
    # elif ( comparison_type == 'separate' ):
    #     header=['gas_standard','dry_res_mean','mean_upper_limit','mean_pass_or_fail',\
    #         'dry_res_stdev','stdev_upper_limit','stdev_pass_or_fail']
    #     header = [s.replace("_"," ") for s in header]
    #     header[2] = Paragraph('mean<br/>upper limit')
    #     header[3] = Paragraph('mean<br/>pass or fail')
    #     header[5] = Paragraph('stdev<br/>upper limit')
    #     header[6] = Paragraph('stdev<br/>pass or fail')
    # data_pf_EPOFF_no_recalc.append(header)
    
    # #print(df_mean_stdev_not_tcorr_2.columns)

    # for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
    #     if (comparison_type == 'combined'):
    #         row_as_list = [row["gas_standard"],
    #                         f'{row["mean"]:.4f}',
    #                         f'{row["stdev"]:.4f}',
    #                         row["pass_or_fail"],
    #                         f'{row["upper_limit"]:.4f}',
    #                         f'{row["margin"]:.4f}']
    #     elif ( comparison_type == 'separate' ):
    #         row_as_list = [row["gas_standard"],
    #                         f'{row["mean"]:.4f}',
    #                         f'{row["mean_upper_limit"]:.4f}',
    #                         row["mean_pass_or_fail"],
    #                         f'{row["stdev"]:.4f}',
    #                         f'{row["stdev_upper_limit"]:.4f}',
    #                         row["stdev_pass_or_fail"]]
    #     else:
    #         raise Exception(f'''undefined parameter {comparison_type} 
    #         in generate_bigger_validation_report()''')
    #     data_pf_EPOFF_no_recalc.append(row_as_list)
    
    # t6=Table(data_pf_EPOFF_no_recalc)

    # t6_table_style=[('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
    #     ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
    #     ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
    #     ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black)]
    
    # # change from df_mean_stdev_tcorr_2 to df_mean_stdev_not_tcorr_2, 8/06/2021, Pascal
    # if comparison_type == 'combined':
    #     for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
    #         if row["pass_or_fail"] == "PASS":
    #             t6_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.green))
    #         else:
    #             t6_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.red))
    #             any_single_failure_flag=True
    # elif comparison_type == 'separate':
    #     for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
    #         if row["mean_pass_or_fail"] == "PASS":
    #             t6_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.green))
    #         else:
    #             t6_table_style.append(('TEXTCOLOR',(3,idx+1),(3,idx+1),\
    #                 colors.red))
    #             any_single_failure_flag=True
    #     for idx, row in df_mean_stdev_not_tcorr_2.iterrows():
    #         if row["stdev_pass_or_fail"] == "PASS":
    #             t6_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
    #                 colors.green))
    #         else:
    #             t6_table_style.append(('TEXTCOLOR',(6,idx+1),(6,idx+1),\
    #                 colors.red))
    #             any_single_failure_flag=True

    # t6.setStyle(t6_table_style)

    t6, any_single_failure_flag = df_to_reportlab_table_with_pf(tuple_of_df_4_tables[3],\
        any_single_failure_flag,'not_Tcorr')
    document.append(t6)
    document.append(Spacer(6*inch,0.1*inch))

    #### New stuff for range check####
    if ( re.search(r'.*The following problems were found in.*',final_text) ):
        document.append(Paragraph("<font color=\"orange\">Range Check: Some values were found to be out of range"\
            " please see the end of this report for details.</font>",\
                ParagraphStyle(name='Header12pt',fontSize=12)))
    else:
        document.append(Paragraph("Range Check: All values were found to be out in range",
                ParagraphStyle(name='Header12pt',fontSize=12)))

    document.append(PageBreak())
    #### End of 2nd page content, previously 6th page content ####

    ##### Previously 1st page Content ######
    document.append(Paragraph('--APOFF Summary--',ParagraphStyle(name='Header12pt',fontSize=12)))
    document.append(Spacer(6*inch,0.1*inch))
    
    ##### format start date and end date #####
    start_year = date_range[0][0:4]; end_year = date_range[1][0:4]
    start_month = date_range[0][4:6]; end_month = date_range[1][4:6]
    start_day = date_range[0][6:8]; end_day = date_range[1][6:8]
    start_str = start_month + "/" + start_day + "/" + start_year
    end_str = end_month + "/" + end_day + "/" + end_year

    first_page_text_above_first_figure='''
    The data shown in this report was collected between ''' + start_str + " and " + end_str + '''
    using ASVCO2 Gen2 with S/N ''' + sn + '''.
    The residuals shown in the figure below represent the measured carbon dioxide (CO2)
    gas concentration from the ASVCO2 test article in parts per million (ppm) subtracted from the
    standard gas concentration of CO2 in ppm. The colors represent the number of runs, or
    successive samples of measurement.'''
    document.append(Paragraph(first_page_text_above_first_figure))
    #document.append(Image('APOFF 1006 20210429.png',6*inch,18/5.0*inch))
    document.append(Image(figure_filenames_and_sizes[0][0],\
        figure_filenames_and_sizes[0][1]*inch,figure_filenames_and_sizes[0][2]*inch))
    first_page_text_below_first_figure='''
    As shown above, it is expected that there will be two regions of accuracy. One region,
    where the standard gases are below 1000ppm, have a tendency to show greater accuracy 
    (i.e. lower residuals) in the lower range as two of the three standard gases used for 
    calibrating the ASVCO2 test article (0ppm and 500ppm, approximately) occur in that range. 
    The other region, where the standard gases are above 1000ppm, have a tendency to show less 
    accuracy and the magnitude of the residual increases with increasing concentration in 
    the sense that a percent error may be observed. 
    '''
    document.append(Paragraph(first_page_text_below_first_figure))
    document.append(PageBreak())

    ##### Previously 2nd page content #####
    more_text='''Mathematical coefficients which determine the calculation of CO2 gas 
    concentration have been observed to be a function of temperature. It is
    expected that the residuals will be lower once these temperature corrections/adjustments
    are made. For further details, see <font color=blue><link>
    https://github.com/NOAA-PMEL/EDD-ASVCO2_Automation/tree/develop</link></font>'''

    document.append(Paragraph(more_text))
    #document.append(Image('830_830eq_res_all.png',6*inch,18/5.0*inch))
    document.append(Image(figure_filenames_and_sizes[1][0],\
        figure_filenames_and_sizes[1][1]*inch,figure_filenames_and_sizes[1][2]*inch))
    
    document.append(Paragraph('APOFF Statistical summaries of the residual, grouped by gas standard:'))
    document.append(Spacer(6*inch,0.1*inch))
    
    # convert dataframe to 2-D array, data1
    #df_4_comparison = df_mean_stdev_tcorr.copy()
    df_4_comparison = tuple_of_df_4_tables[0].copy() 
    df_4_comparison = df_4_comparison.rename(columns={'stdev':'dry_res_stdev_recalc','mean':'dry_res_mean_recalc'})
    df_4_comparison = df_4_comparison.drop(columns=['max'])
    # df_4_comparison["res_mean_not_recalc"] = df_mean_stdev_not_tcorr["mean"]
    # df_4_comparison["res_stdev_not_recalc"] = df_mean_stdev_not_tcorr["stdev"]
    df_4_comparison["dry_res_mean_not_recalc"] = tuple_of_df_4_tables[1]["mean"]  # Bug fix, 6/25/2021 due to Noah's comment
    df_4_comparison["dry_res_stdev_not_recalc"] = tuple_of_df_4_tables[1]["stdev"]  # Bug fix, 6/25/2021 due to Noah's comment
    num_rows=len(df_4_comparison)
    data_summary_APOFF=[]
    header = [Paragraph(s.replace("_","<br/>")) if idx > 1 else Paragraph("gas<br/>standard")\
         for idx, s in enumerate(df_4_comparison.columns.values)]
    header = header[1:]  #remove duplicate first entry
    num_cols=len(header)
    #print(f'num_cols = {num_cols}')
    data_summary_APOFF.append(header)
    #print(df_4_comparison.columns)
    for idx, row in df_4_comparison.iterrows():
        lower_ref_gas = row["gas_standard_lower"]
        upper_ref_gas = row["gas_standard_upper"]
        lower_ref_gas_txt1 = f'{lower_ref_gas:.1f}ppm'
        upper_ref_gas_txt2 = f'{upper_ref_gas:.1f}ppm'
        row_as_list = [Paragraph(lower_ref_gas_txt1 + \
                '<br/>thru<br/>' + upper_ref_gas_txt2),
                f'{row["dry_res_mean_recalc"]:.2f}',
                f'{row["dry_res_stdev_recalc"]:.2f}',
                f'{row["dry_res_mean_not_recalc"]:.2f}',
                f'{row["dry_res_stdev_not_recalc"]:.2f}']
        data_summary_APOFF.append(row_as_list)

    t1=Table(data_summary_APOFF,colWidths=[1.0*inch] * 5,repeatRows=1)
    t1.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('GRID', (0,0), (-1,-1), 1, colors.black)]))
    document.append(t1)

    document.append(PageBreak())

    ##### 3rd page #####
    document.append(Spacer(6*inch,0.1*inch))
    document.append(Paragraph('--EPOFF Summary--',ParagraphStyle(name='Header12pt',fontSize=12)))
    document.append(Spacer(6*inch,0.1*inch))
    
    ##### format start date and end date #####
    start_year = date_range[0][0:4]; end_year = date_range[1][0:4]
    start_month = date_range[0][4:6]; end_month = date_range[1][4:6]
    start_day = date_range[0][6:8]; end_day = date_range[1][6:8]
    start_str = start_month + "/" + start_day + "/" + start_year
    end_str = end_month + "/" + end_day + "/" + end_year

    third_page_text_above_third_figure='''
    The data shown in this report was collected between ''' + start_str + " and " + end_str + '''
    using ASVCO2 Gen2 with S/N ''' + sn + '''.
    The residuals shown in the figure below represent the measured carbon dioxide (CO2)
    gas concentration from the ASVCO2 test article in parts per million (ppm) subtracted from the
    standard gas concentration of CO2 in ppm. The colors represent the number of runs, or
    successive samples of measurement.'''
    document.append(Paragraph(third_page_text_above_third_figure))
    #document.append(Image('APOFF 1006 20210429.png',6*inch,18/5.0*inch))
    document.append(Image(figure_filenames_and_sizes[2][0],\
        figure_filenames_and_sizes[2][1]*inch,figure_filenames_and_sizes[2][2]*inch))
    third_page_text_below_third_figure='''
    As shown above, it is expected that there will be two regions of accuracy. One region,
    where the standard gases are below 1000ppm, have a tendency to show greater accuracy 
    (i.e. lower residuals) in the lower range as two of the three standard gases used for 
    calibrating the ASVCO2 test article (0ppm and 500ppm, approximately) occur in that range. 
    The other region, where the standard gases are above 1000ppm, have a tendency to show less 
    accuracy and the magnitude of the residual increases with increasing concentration in 
    the sense that a percent error may be observed. 
    '''
    document.append(Paragraph(third_page_text_below_third_figure))
    document.append(PageBreak())

    ##### 4th page #####
    more_text='''Mathematical coefficients which determine the calculation of CO2 gas 
    concentration have been observed to be a function of temperature. It is
    expected that the residuals will be lower once these temperature corrections/adjustments
    are made. For further details, see <font color=blue><link>
    https://github.com/NOAA-PMEL/EDD-ASVCO2_Automation/tree/develop</link></font>'''

    document.append(Paragraph(more_text))
    #document.append(Image('830_830eq_res_all.png',6*inch,18/5.0*inch))
    document.append(Image(figure_filenames_and_sizes[3][0],\
        figure_filenames_and_sizes[3][1]*inch,figure_filenames_and_sizes[3][2]*inch))
    
    document.append(Paragraph('EPOFF Statistical summaries of the residual, grouped by gas standard:'))
    document.append(Spacer(6*inch,0.1*inch))
    
    # convert dataframe to 2-D array, data1
    #df_4_comparison = df_mean_stdev_tcorr.copy()
    df_4_comparison = tuple_of_df_4_tables[2].copy()  # Bug fix, 6/25/2021 due to Noah's comment
    df_4_comparison = df_4_comparison.rename(columns={'stdev':'dry_res_stdev_recalc','mean':'dry_res_mean_recalc'})
    df_4_comparison = df_4_comparison.drop(columns=['max'])
    # df_4_comparison["res_mean_not_recalc"] = df_mean_stdev_not_tcorr["mean"]
    # df_4_comparison["res_stdev_not_recalc"] = df_mean_stdev_not_tcorr["stdev"]
    df_4_comparison["dry_res_mean_not_recalc"] = tuple_of_df_4_tables[3]["mean"]  # Bug fix, 6/25/2021 due to Noah's comment
    df_4_comparison["dry_res_stdev_not_recalc"] = tuple_of_df_4_tables[3]["stdev"] # Bug fix, 6/25/2021 due to Noah's comment
    num_rows=len(df_4_comparison)
    data_summary_EPOFF=[]
    header = [Paragraph(s.replace("_","<br/>")) if idx > 1 else Paragraph("gas<br/>standard")\
         for idx, s in enumerate(df_4_comparison.columns.values)]
    header = header[1:]  #remove duplicate first entry
    num_cols=len(header)
    #print(f'num_cols = {num_cols}')
    data_summary_EPOFF.append(header)
    #print(df_4_comparison.columns)
    for idx, row in df_4_comparison.iterrows():
        lower_ref_gas = row["gas_standard_lower"]
        upper_ref_gas = row["gas_standard_upper"]
        lower_ref_gas_txt1 = f'{lower_ref_gas:.1f}ppm'
        upper_ref_gas_txt2 = f'{upper_ref_gas:.1f}ppm'
        row_as_list = [Paragraph(lower_ref_gas_txt1 + \
                '<br/>thru<br/>' + upper_ref_gas_txt2),
                f'{row["dry_res_mean_recalc"]:.2f}',
                f'{row["dry_res_stdev_recalc"]:.2f}',
                f'{row["dry_res_mean_not_recalc"]:.2f}',
                f'{row["dry_res_stdev_not_recalc"]:.2f}']
        data_summary_EPOFF.append(row_as_list)

    t2=Table(data_summary_EPOFF,colWidths=[1.0*inch] * 5,repeatRows=1)
    t2.setStyle(TableStyle([('ALIGN',(0,0),(num_cols,num_rows),'LEFT'),\
        ('TEXTCOLOR',(0,0),(num_cols,num_rows), colors.black),\
        ('INNERGRID', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('BOX', (0,0), (num_cols,num_rows), 0.25, colors.black),\
        ('GRID', (0,0), (-1,-1), 1, colors.black)]))
    document.append(t2)

    document.append(PageBreak())


    # document.append(Paragraph('Here\'s another table below:'))
    # mydata=[['stuff',0.0],['more stuff',-2.6],\
    #     ['even more stuff',-10.9],['yet again more stuff',9999999.099999]]
    # t2=Table(mydata)
    # t2.setStyle(TableStyle([('ALIGN',(0,0),(2,3),'LEFT'), ('TEXTCOLOR',(0,0),(2,3), colors.black),\
    #     ('INNERGRID', (0,0), (2,3), 0.25, colors.black),('BOX', (0,0), (2,3), 0.25, colors.black)]))
    # document.append(t2)


    ##### 7th page #####
    document.append(Paragraph('Configuration Description for ASVCO2 Gen2, Serial Number: ' + sn,\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))

    file_ptr=open(validation_text_filename, 'r')
    lines = file_ptr.readlines()
    seventh_page_text = ''

    start_line = 0
    line_is_empty=len(lines[start_line].strip()) == 0
    while line_is_empty:
        start_line += 1
        line_is_empty = len(lines[start_line].strip()) == 0
        
    end_line = start_line
    line_is_not_empty=len(lines[end_line].strip()) != 0
    while line_is_not_empty:
        end_line += 1
        line_is_not_empty = len(lines[end_line].strip()) != 0          

    for idx in range(start_line,end_line):
        seventh_page_text += lines[idx] + "<br/>"

    document.append(Paragraph(seventh_page_text))
    file_ptr.close()

    document.append(PageBreak())

    ##### 8th Page #####
    document.append(Paragraph('Description of Terms and Abbreviations',\
        ParagraphStyle(name='Title',fontSize=14)))
    document.append(Spacer(6*inch,0.1*inch))
    #S<super rise=-4 size=6>1</super>
    description_of_terms='''
    <b>res</b> - residual, measured value - actual value<br/>
    <b>recalc</b> - recalculated according to temperature adjustment of S<sub>1</sub>,
    where S<sub>1</sub> is defined in the Appendix of the LI-830 and LI-850 user manual.<br/>
    For further details, see <font color=blue><link>
    https://github.com/NOAA-PMEL/EDD-ASVCO2_Automation/tree/develop</link></font><br/>
    <b>not recalc</b> - the S<sub>1</sub> coefficient is not adjusted for temperature<br/>
    <b>stdev</b> - the standard deviation<br/>
    <b>upper limit</b> - if a value exceeds this limit, then the unit has failed the test<br/>
    <b>ppm</b> - parts per million (ppm)<br/>
    <b>APOFF</b> - Air Pump OFF, this is a valve state in the ASVCO2 unit measuring the air<br/>
    <b>EPOFF</b> - Equilibrator Pump OFF, this is a valve state in the ASVCO2 unit measuring the equilibrator<br/>
    '''
    document.append(Paragraph(description_of_terms))

    # New feature, 9/21/2021, add in final text
    document.append(Spacer(6*inch,0.1*inch))
    document.append(Paragraph("Range Check Results:<br/>",
                ParagraphStyle(name='Header12pt',fontSize=12)))
    document.append(Paragraph(final_text))

    #output_filename='demo_1006.pdf'
    if ( any_single_failure_flag ):
        last_piece_of_filename = "FAIL"
    else:
        last_piece_of_filename = "PASS"
    output_filename = output_folder + '/' + "Gas_Validation_" + sn + "_" + \
        date_range[0][0:8] + "_" + last_piece_of_filename + ".pdf"
    
    # SimpleDocTemplate(output_filename,pagesize=letter,\
    #     rightMargin=1*inch, leftMargin=1*inch,\
    #         topMargin=1*inch, bottomMargin=1*inch).build(document)

    doc = SimpleDocTemplate(output_filename,pagesize=letter,\
        rightMargin=1*inch, leftMargin=1*inch,\
        topMargin=1*inch, bottomMargin=1*inch)

    doc.build(document, onFirstPage=myFirstPage, onLaterPages=myLaterPages)

# if __name__ == "__main__":
    #print(inch)
    # output_filename='demo_1006.pdf'
    # sn='1006'
    # figure_filenames_and_sizes=(('APOFF 1006 20210429.png',6,18/5.0),\
    #     ('830_830eq_res_all.png',6,4))
    # df_4_table=pd.DataFrame({'column1':[8.8,99,-22222,3736],\
    #     'column2':[-8.0,7999999,-22,34000],
    #     'column3':[22.9,99,-22222,6]})

    # generate_validation_report(output_filename,sn,figure_filenames_and_sizes,df_4_table)
