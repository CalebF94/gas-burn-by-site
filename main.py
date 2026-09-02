import os
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook
from scripts.data_pull_functions import login_google_cloud
from scripts.gather_historic_data import gather_historic_data
from scripts.gather_data_to_forecast import gather_data_to_forecast
from scripts.model_training_functions import fit_xgboost_clarissa_version, generate_feed_forward_forecast
from scripts.create_output_functions import create_nbpl_file, create_next_day_gas_burn_file

def main():
    client = login_google_cloud(project_name="bepc-prj-energy-prod")

    today_mdy = datetime.today().strftime("%m-%d-%Y")
    today_ymd = datetime.today().strftime("%Y-%m-%d")
    forecast_horizon_mdy = (datetime.today() + pd.Timedelta(value=9, unit='D')).strftime("%m-%d-%Y")

    lead_columns = ['datetime', 'site', 'year', 'month', 'day', 'hour', 'hour_end', 'day_of_week', 'gas_day', 'hourly_gas_burn_MMBtu', 'daily_gas_burn_MMBtu']

    model_df = gather_historic_data(
        start='2023-01-01', 
        end=today_ymd, #Exclusive end so date specified will not be included. End should be today's date for most purposes
        client=client, 
        lead_columns=lead_columns, 
        yes_username=os.getenv('YES_USERNAME'), 
        yes_password = os.getenv('YES_PASSWORD'), 
        save_output=True
        )

    
    
    forward_df = gather_data_to_forecast(
        forecast_start=today_ymd, 
        forecast_end=forecast_horizon_mdy, #Exclusive end so date specified will not be included.
        yes_username=os.getenv('YES_USERNAME'), 
        yes_password=os.getenv('YES_PASSWORD'), 
        save_output=True
        )


    # feel like this should be declared elsewhere
    features = ["availability_mw", "load_forecast", "net_load_forecast", "wind_forecast", "temperature_forecast", "wind_speed_forecast", "total_offline_forecast", 
           "offline_ng_forecast", "offline_coal_forecast", "hour", "day_of_week", "month", "gas_lag_1", "gas_lag_24", "gas_lag_168", "gas_roll_24", "gas_roll_168"]


    # test_start_date is just 8 days ago from the today's date
    fit_results = fit_xgboost_clarissa_version(
        model_df, 
        sites=model_df['site'].unique(), 
        test_start_date='2026-08-25', 
        features=features, 
        target = 'hourly_gas_burn_MMBtu', 
        save_model_file=f"G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/Models/models {today_ymd}.joblib")


    predictions = generate_feed_forward_forecast(
        historic_df=model_df, 
        forward_df=forward_df, 
        models=fit_results['models'], 
        features=features, 
        save_output=True, 
        save_file=f"G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/Forecasts/Hourly Gas Burn by Site Forecasts {today_ymd}.csv"
        )

    
    # file_date is typically tomorrow's date
    create_nbpl_file(
        predictions=predictions, 
        template_file='G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/NBPL Submission Files/NBPL template no links.xlsx', 
        file_date='2026-09-03', 
        save_file=f"G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/NBPL Submission Files/NBPL Forecast {today_ymd}.xlsm"
        )

    create_next_day_gas_burn_file(
        predictions=predictions, 
        template_file="G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/Next Day Gas Burn Files/Next Day Gas Burn Template.xlsx", 
        save_file=f"G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/Next Day Gas Burn Files/Next Day Gas Burn {today_ymd}.xlsx"
        )





if __name__ == "__main__":
    main()