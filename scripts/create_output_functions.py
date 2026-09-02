"""
module for formatting outputs
"""

import pandas as pd
#import warnings
from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook

#warnings.filterwarnings("ignore", category=ResourceWarning, module="openpyxl")

def earliest_full_gas_day_with_forecast(predictions: pd.DataFrame):
    """

    """
    daily_record_counts = predictions.groupby('gasday').count()['site'].reset_index()
    full_gas_days = daily_record_counts[daily_record_counts['site']==max(daily_record_counts['site'])]['gasday']
    full_gas_days = pd.to_datetime(full_gas_days)

    return full_gas_days

def create_nbpl_file(predictions: pd.DataFrame, template_file:Path=None, file_date: Path=None, save_file: Path=None):
    """
    
    """
    # cleaning up file specifications
    today_str = datetime.today().strftime("%m.%d.%Y")
    raw_template = template_file if template_file else Path(r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Forecasts\Forecast template no links.xlsx")
    raw_save_file = save_file if save_file else Path(rf"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Forecasts\Hourly Gas Burn Forecast for {today_str}.xlsm")

    template_path = Path(raw_template)
    save_path = Path(raw_save_file)


    # dynamically getting date based on first day with full gas day predictions
    if not file_date:
        full_gas_days = earliest_full_gas_day_with_forecast(predictions=predictions)
        file_date = min(full_gas_days).date()

    else:
        file_date = pd.to_datetime(file_date)

    
    #template_file = r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Forecasts\Forecast template no links.xlsx"


    try:
        workbook = load_workbook(template_path, keep_vba=True)
        worksheet = workbook["Daily Burn Sheet"]

        # updating start and end date in the file
        worksheet["D11"] = file_date
        worksheet["F11"] = file_date

        site_to_columns = {'CGS': 6, 'DCS': 8, 'GGS': 10, 'LCS': 12, 'PGS': 14}
            
        for site, col in site_to_columns.items():
            worksheet.cell(row=55, column=col, value=f'=SUM({chr(64+col)}30:{chr(64+col)}53)')
            site_predictions = predictions.loc[(predictions['site']==site) & (predictions['gasday']==file_date), 'hourly_gas_burn_MMBtu']
            for row in range(0, 24):
                
                excel_row = 30 + row
                worksheet.cell(row=excel_row, column=col, value=site_predictions.values[row])

        today_str = datetime.today().strftime("%m.%d.%Y")

        workbook.save(save_path)
        print(f'A file with the NBPL hourly forecasts is saved to {save_path}')

    finally:
        if hasattr(workbook, 'vba_archive') and workbook.vba_archive:
            workbook.vba_archive.close()
            
        workbook.close()

    


def create_next_day_gas_burn_file(predictions: pd.DataFrame, template_file: Path = None , save_file: Path = None):
    """

    """

    # cleaning up file specifications
    today_str = datetime.today().strftime("%m.%d.%Y")
    raw_template = template_file if template_file else Path('../output/next-day-gas-burn/next_day_gas_burn_template.xlsx')
    raw_save_file = save_file if save_file else Path(f'../output/next-day-gas-burn/next_day_gas_burn_{today_str}.xlsx')

    template_path = Path(raw_template)
    save_path = Path(raw_save_file)


    #load file
    try:
        next_day_gas_burn_wb = load_workbook(template_path, data_only=True)
        summary_ws = next_day_gas_burn_wb['Summary']
        hourly_gas_use_ws = next_day_gas_burn_wb['Hourly Gas Use']

        #identifies which days from predictions df will be on report
        forecasted_days = earliest_full_gas_day_with_forecast(predictions)
        forecasted_days = forecasted_days[forecasted_days >  pd.Timestamp.now()]


        #update summary tab
        formatted_predictions = (
        predictions
        .drop(columns=['datetime', 'date','HE'])
        .groupby(by=['gasday', 'gasday_of_week', 'site'])
        .sum()
        .reset_index()
        .pivot(columns='site', index=['gasday', 'gasday_of_week'], values='hourly_gas_burn_MMBtu')
        .round(0)
        .reset_index()
        )

        formatted_predictions = formatted_predictions.loc[formatted_predictions['gasday'].isin(forecasted_days)]
        formatted_predictions = formatted_predictions.reindex(columns=['gasday', 'gasday_of_week', 'DCS', 'GGS', 'CGS', 'PGS', 'LCS'])

        for df_row, excel_row in enumerate(range(3, 10)):
            for df_col, excel_col in enumerate(range(3, 10)):
                summary_ws.cell(row=excel_row, column=excel_col, value=formatted_predictions.iloc[df_row, df_col])
                #print(formatted_predictions.iloc[df_row, df_col])


        #update hourly gas use tab
        hourly_predictions_formatted = (
        predictions
        .drop(columns=['gasday', 'datetime', 'gasday_of_week'])
        .pivot(index=['site', 'date', 'effective_day_of_week'], columns = 'HE', values='hourly_gas_burn_MMBtu')
        .reset_index()
        .round(2)
        )

        site_start_row = {'GGS': 3, 'CGS': 13, 'DCS': 23, 'PGS': 33, 'LCS': 43}

        for site in site_start_row:
            site_predictions = hourly_predictions_formatted[hourly_predictions_formatted['site']==site]
            start_row = site_start_row[site]
            for df_row, excel_row in enumerate(range(start_row, start_row + site_predictions.shape[0])):
                
                for df_col, excel_col in enumerate(range(4, 30)):
                    #print(f'site: {site}    excel_row: {excel_row}   excel_col: {excel_col}   df_row: {hourly_predictions_formatted.iloc[df_row, df_col+1]}')
                    hourly_gas_use_ws.cell(row=excel_row, column=excel_col, value=site_predictions.iloc[df_row, df_col+1])
                    if excel_col == 4: 
                        hourly_gas_use_ws.cell(row=excel_row, column=excel_col).number_format = "mm/dd/yyyy"
                    else:  
                        hourly_gas_use_ws.cell(row=excel_row, column=excel_col).number_format = "#,##0.0"


        #widening columns
        for col in hourly_gas_use_ws.columns:
            max_len = 0
            col_letter = col[0].column_letter  # Get letter like 'A', 'B', etc.
            for cell in col:
                if cell.value is not None:
                    # Check length of the cell string
                    max_len = max(max_len, len(str(cell.value)))
                    
            # Add a little padding (e.g., +3) so it isn't too tight
            hourly_gas_use_ws.column_dimensions[col_letter].width = max(max_len + .1, 10)

        # saving file
        next_day_gas_burn_wb.save(save_path)
        print(f'A file with the next day gas burns is saved to {save_path}')

    finally:
        next_day_gas_burn_wb.close()
