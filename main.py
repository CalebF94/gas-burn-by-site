import os
import numpy as np
import pandas as pd
from datetime import datetime
from openpyxl import load_workbook
from xgboost import XGBRegressor # likely move to modelling module
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scripts.data_pull_functions import login_google_cloud
from scripts.gather_historic_data import gather_historic_data
from scripts.gather_data_to_forecast import gather_data_to_forecast
from scripts.model_training_functions import fit_xgboost_clarissa_version, generate_feed_forward_forecast
from scripts.create_output_functions import create_nbpl_file

def main():
    client = login_google_cloud(project_name="bepc-prj-energy-prod")

    lead_columns = ['datetime', 'site', 'year', 'month', 'day', 'hour', 'hour_end', 'day_of_week', 'gas_day', 'hourly_gas_burn_MMBtu', 'daily_gas_burn_MMBtu']

    model_df = gather_historic_data(start='2023-01-01', end='2026-08-28', 
                         client=client, lead_columns=lead_columns, 
                         yes_username=os.getenv('YES_USERNAME'), yes_password = os.getenv('YES_PASSWORD'), 
                         save_output=True
                        )

    
    
    forward_df = gather_data_to_forecast(forecast_start='2026-07-01', forecast_end='2026-09-10', # make sure the dates for these are dynamic. Will cause error if not updated
                            yes_username=os.getenv('YES_USERNAME'), yes_password=os.getenv('YES_PASSWORD'), 
                            save_output=True
                            )


    #model_df = pd.read_csv("./data/processed-data/historic_data_df.csv")
    #model_df["datetime"] = pd.to_datetime(model_df["datetime"])

    #forward_df = pd.read_csv("./data/processed-data/data_to_forecast_df.csv")
    #forward_df["datetime"] = pd.to_datetime(forward_df["datetime"])


    features = ["availability_mw", "load_forecast", "net_load_forecast", "wind_forecast", "temperature_forecast", "wind_speed_forecast", "total_offline_forecast", 
           "offline_ng_forecast", "offline_coal_forecast", "hour", "day_of_week", "month", "gas_lag_1", "gas_lag_24", "gas_lag_168", "gas_roll_24", "gas_roll_168"]

    fit_results = fit_xgboost_clarissa_version(model_df, sites=model_df['site'].unique(), test_start_date='2026-08-21', features=features, target = 'hourly_gas_burn_MMBtu')

    site_models = fit_results['models']

    predictions = generate_feed_forward_forecast(historic_df=model_df, forward_df=forward_df, models=site_models, features=features, save_output=True)

    #print(predictions[predictions['site']=='PGS'].head(24)['hourly_gas_burn_MMBtu'].sum())
    create_nbpl_file(predictions=predictions, file_date='2026-08-29')



if __name__ == "__main__":
    main()