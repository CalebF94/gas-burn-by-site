"""
Gather Historic Data

Module is designed to gather and join historic data from multiple sources and store it in a format that can be used for further engineering and analysis.
Data sources include:
- Allegro Database via GCP
- Yes Energy API
- Excel Files from Network Drive
"""

import os
#import sys
from dotenv import load_dotenv
#import json
import pandas as pd
import numpy as np
from google.cloud import bigquery
import pydata_google_auth
#import requests
#import time
from datetime import date#, timedelta, datetime
import urllib3
#from pathlib import Path

from scripts.queries import GAS_BURN_QUERY, NON_PGS_GENERATION_QUERY, PGS_GENERATION_QUERY
from scripts.constants import SITE_MAPPINGS, SITE_BURN_DATATYPES, SITE_GENERATION_DATATYPES, AVAILABILITY_FILES_XLSX, AVAILABILITY_FILES_CSV
from scripts.data_pull_functions import  run_natural_gas_burn_query, run_generation_query,  pull_unit_availability, pull_yes_forecast_historical, pull_yes_actual_historical
from scripts.data_clean_functions import clean_generation_unit_data, clean_yes_actual, clean_generation_unit_data, clean_yes_forecast

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


#YES API Credentials
yes_username = os.getenv('YES_USERNAME')
yes_password = os.getenv('YES_PASSWORD')


# Google Cloud Credentials
credentials = pydata_google_auth.get_user_credentials(
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
    auth_local_webserver=True,
)

client = bigquery.Client(project="bepc-prj-energy-prod", credentials=credentials )


# Dates for data pulls
start = '2026-06-01'
end = str(date.today() - pd.Timedelta(1, unit='D'))

def gather_historic_data(start: str = start, end: str = end, save_output: bool = False):
    '''
    Wrapper function for gather historic data

    Parameters:
        start: earliest date to be pulled
        end: Latest date to be pulled

    Returns:
        merged_df: Dataframe for the time period between 'start' and 'end'
    '''
    gas_start = pd.to_datetime(start) - pd.Timedelta(1, unit='D')
    ######################
    ## Pulling Datasets ##
    ######################
    gas_burn_daily_df = run_natural_gas_burn_query(client, query_strings=[GAS_BURN_QUERY], start=gas_start, end=end, col_dtypes=SITE_BURN_DATATYPES)


    generation_df = run_generation_query(client, [PGS_GENERATION_QUERY, NON_PGS_GENERATION_QUERY], start, end, SITE_GENERATION_DATATYPES)
    site_generation_df = clean_generation_unit_data(generation_df)['hourly_site_generation_df']
    site_generation_by_gas_day_df = clean_generation_unit_data(generation_df)['daily_site_generation_by_gas_day_df']


    site_availability_df = pull_unit_availability(AVAILABILITY_FILES_XLSX, AVAILABILITY_FILES_CSV, 'Gas HEL Transposed', start, end)['site_availability_df']


    yes_historical_forecast_df = pull_yes_forecast_historical(yes_username, yes_password, start_date=start, end_date = end)
    yes_historical_forecast_cleaned_df = clean_yes_forecast(yes_historical_forecast_df)


    yes_historical_actual_df = pull_yes_actual_historical(yes_username, yes_password, start_date=start, end_date = end)
    yes_historical_actual_cleaned_df = clean_yes_actual(yes_historical_actual_df)


    ######################
    ## Merging Datasets ##
    ######################
    merged_df = site_generation_df.merge(gas_burn_daily_df, how='left', on=['gas_day', 'site'])
    merged_df = merged_df.merge(site_generation_by_gas_day_df, how='left', on=['gas_day', 'site'])
    merged_df = merged_df.merge(site_availability_df, how='left', on=['datetime', 'site'])
    merged_df = merged_df.merge(yes_historical_forecast_cleaned_df, how='left', on=['datetime'])
    merged_df = merged_df.merge(yes_historical_actual_cleaned_df, how='left', on=['datetime'])
    merged_df['hourly_gas_burn_MMBtu'] =  (merged_df['daily_gas_burn_MMBtu'] / merged_df['daily_site_gen_mw']) * merged_df['hourly_site_gen_mw']


    ##################
    ## Confirmation ##
    ##################
    if save_output: 
        file_name = './data/processed-data/historic_data_df.csv'
        merged_df.to_csv(file_name, index=False)
        print(f'A file containing the merged data has been saved to {file_name}')

