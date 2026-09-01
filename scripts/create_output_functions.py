"""
module for formatting outputs
"""

import pandas as pd
from datetime import datetime
from openpyxl import load_workbook

def create_nbpl_file(predictions: pd.DataFrame, file_date: str=None):
    """
    
    """

    # dynamically getting date based on first day with full gas day predictions
    if not file_date:
        daily_record_counts = predictions.groupby('gasday').count()['site'].reset_index()

        full_gas_days = daily_record_counts[daily_record_counts['site']==max(daily_record_counts['site'])]['gasday']
        full_gas_days = pd.to_datetime(full_gas_days)
        print(full_gas_days)
        file_date = min(full_gas_days).date()
    else:
        file_date = pd.to_datetime(file_date).date()

    
    template_file = r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Forecasts\Forecast template no links.xlsx"

    workbook = load_workbook(template_file, keep_vba=True, data_only=True)

    worksheet = workbook["Daily Burn Sheet"]

            
    # updating start and end date in the file
    worksheet["D11"] = file_date
    worksheet["F11"] = file_date
    
          
    site_to_columns = {'CGS': 6, 'DCS': 8, 'GGS': 10, 'LCS': 12, 'PGS': 14}
        
    for site, col in site_to_columns.items():

        site_predictions = predictions.loc[(predictions['site']==site) & (predictions['gasday']==file_date), 'hourly_gas_burn_MMBtu']
        for row in range(0, 24):
            
            excel_row = 30 + row
            #print(f'col {col}   row {row}   excel row {excel_row}')
            worksheet.cell(row=excel_row, column=col, value=site_predictions.values[row])   # F
            #worksheet.cell(row=excel_row, column=8, value=row["DCS"])   # H
            #worksheet.cell(row=excel_row, column=10, value=row["GGS"])  # J
            #worksheet.cell(row=excel_row, column=12, value=row["LCS"])  # L
            #worksheet.cell(row=excel_row, column=14, value=row["PGS"])  # N


    today_str = datetime.today().strftime("%m.%d.%Y")

    output_file = (rf"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Forecasts\Hourly Gas Burn Forecast for {today_str}.xlsm")

    workbook.save(output_file)

    print(output_file)

    return file_date