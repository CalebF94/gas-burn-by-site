"""
Gather Data to Forecast

Module is intended to pull and assemble a dataframe containing data that needs to be forecasted.

Process:
    1. Gathers site availability data from latest forward looking file ('G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/Transposed Forward Looking Data') or from a user provided file
    2. Gathers Yes Energy forecast data using the pull_yes_forecast_historical() function from the data_pull_functions.py module
    3. Merges the site availability data and the Yes Energy data based on datetime
    4. Constructs date time attributes
    5. Optional -  Limits columns returned to align with 'feature_names_in_' used in the predictive model
"""

import os
import pandas as pd
import urllib3
from pathlib import Path
from dotenv import load_dotenv

from scripts.data_pull_functions import pull_yes_forecast_historical, pull_unit_availability
from scripts.data_clean_functions import clean_yes_forecast
from scripts.feature_engineering_functions import add_time_features
from scripts.merge_dataset_functions import merge_data_to_forecast

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def gather_data_to_forecast(forecast_start, forecast_end, 
                            availability_file: str = "", forecast_features: list = None, 
                            yes_username: str = os.getenv('YES_USERNAME'), yes_password:str = os.getenv('YES_PASSWORD'),
                            save_output: bool = False) -> pd.DataFrame:
    """
    Function pulls data based on a date range that is intended to be forecasted.

    Parameters:
        forecast_start: first date to be included in the data
        forecast_end: last date to be included in the data
        availability_file: file location containing hourly unit level MW availability. If left blank, function will default to the most recently created file in the Transposed Forward Looking Data folder
        forecast_features: list of column names that should be returned. Will likely need to align with the 'feature_names_in_' attribute from the predictive model

    Returns:
        dataframe containing data to be forecasted
    """

    #####################################################################
    ## Load Availability Data                                          ##
    ## Defaults to Transposed Forward Lookin Data if no file specified ##
    #####################################################################
    if availability_file:
        latest_file = availability_file
    else:
        directory = Path('G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/Transposed Forward Looking Data')
        latest_file = str(max(directory.glob('*'), key=lambda f: f.stat().st_birthtime))

    future_site_availability_df = pull_unit_availability(excel_files=[latest_file], csv_files=[], sheet='Transposed', start_date=forecast_start, end_date=forecast_end)['site_availability_df']


    #############################
    ## Loading Yes Energy data ##
    #############################
    future_yes_data_df = pull_yes_forecast_historical(yes_username, yes_password, forecast_start, forecast_end)
    future_yes_data_df = clean_yes_forecast(future_yes_data_df)


    ###############################
    ## Merging based on datetime ##
    ###############################
    future_data_to_forecast_df = merge_data_to_forecast(future_site_availability_df, future_yes_data_df)


    #####################################
    ## Adding common datetime features ##
    ##################################### 
    future_data_to_forecast_df = add_time_features(future_data_to_forecast_df)
    future_data_to_forecast_df = future_data_to_forecast_df.loc[:, forecast_features] if forecast_features else future_data_to_forecast_df


    ##################
    ## Confirmation ##
    ##################
    if save_output: 
        folder = Path("./data/processed-data/")
        if not folder.exists():
            folder.mkdir(parents=True)
        file_name = './data/processed-data/data_to_forecast_df.csv'
        future_data_to_forecast_df.to_csv(file_name, index=False)
        print(f'The forecasting dataframe is saved to {file_name}')


    return future_data_to_forecast_df
