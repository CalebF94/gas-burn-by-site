"""
Gather Historic Data

Module is designed to gather and join historic data from multiple sources and store it in a format that can be used for further engineering and analysis.
Data sources include:
- Allegro Database via GCP
- Yes Energy API
- Excel Files from Network Drive
"""

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery
import pandas as pd
import urllib3

from scripts.queries import GAS_BURN_QUERY, NON_PGS_GENERATION_QUERY, PGS_GENERATION_QUERY
from scripts.constants import SITE_MAPPINGS, SITE_BURN_DATATYPES, SITE_GENERATION_DATATYPES, AVAILABILITY_FILES_XLSX, AVAILABILITY_FILES_CSV
from scripts.data_pull_functions import run_natural_gas_burn_query, run_generation_query,  pull_unit_availability, pull_yes_forecast_historical, pull_yes_actual_historical
from scripts.data_clean_functions import clean_generation_unit_data, clean_yes_actual, clean_yes_forecast, reorder_columns
from scripts.merge_dataset_functions import merge_historic_data
from scripts.feature_engineering_functions import add_time_features, add_gas_burn_features

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def gather_historic_data(start: str = str(date.today()), end: str = str(date.today() - pd.Timedelta(1, unit='D')), 
                         client: bigquery.Client = None,  lead_columns: list[str] = ['datetime', 'site'], 
                         yes_username: str = os.getenv('YES_USERNAME'), yes_password: str = os.getenv('YES_PASSWORD'),
                         save_output: bool = False) -> pd.DataFrame:
    """
    Pull and combine historical generation, gas-burn, availability, and YES Energy
    data for a date range and return the merged dataset.

    This function acts as the orchestration layer for the historic-data pipeline. It
    fetches data from BigQuery, reads local availability files, requests YES Energy
    historical records, merges the sources together, adds engineered features, reorders
    the columns, and optionally saves the final dataframe to disk.

    Parameters:
        start: Earliest date to include in the pull, formatted as a date string.
        end: Latest date to include in the pull, formatted as a date string.
        client: Authenticated BigQuery client used for Allegro/GCP queries.
        lead_columns: Column order to place at the front of the final dataframe.
        yes_username: YES Energy username used for historical API requests.
        yes_password: YES Energy password used for historical API requests.
        save_output: If True, write the merged dataframe to
            ./data/processed-data/historic_data_df.csv.

    Returns:
        pd.DataFrame: The merged and cleaned historical dataset spanning the requested
        date window.

    Raises:
        ValueError: If no valid BigQuery client is supplied.
    """

    if client is None:
        raise ValueError("A valid BigQuery client is required.")

    gas_start = pd.to_datetime(start) - pd.Timedelta(1, unit='D')
    
    ######################
    ## Pulling Datasets ##
    ######################
    gas_burn_daily_df = run_natural_gas_burn_query(client, query_strings=[GAS_BURN_QUERY], start=gas_start, end=end, col_dtypes=SITE_BURN_DATATYPES)

    generation_df = run_generation_query(client, [PGS_GENERATION_QUERY, NON_PGS_GENERATION_QUERY], start, end, SITE_GENERATION_DATATYPES)
    cleaned_generation_outputs = clean_generation_unit_data(generation_df)
    site_generation_df = cleaned_generation_outputs['hourly_site_generation_df']
    site_generation_by_gas_day_df = cleaned_generation_outputs['daily_site_generation_by_gas_day_df']

    site_availability_df = pull_unit_availability(AVAILABILITY_FILES_XLSX, AVAILABILITY_FILES_CSV, 'Gas HEL Transposed', start, end)['site_availability_df']

    yes_historical_forecast_df = pull_yes_forecast_historical(yes_username, yes_password, start_date=start, end_date = end)
    yes_historical_forecast_cleaned_df = clean_yes_forecast(yes_historical_forecast_df)

    yes_historical_actual_df = pull_yes_actual_historical(yes_username, yes_password, start_date=start, end_date = end)
    yes_historical_actual_cleaned_df = clean_yes_actual(yes_historical_actual_df)


    ######################
    ## Merging Datasets ##
    ######################
    merged_df = merge_historic_data(site_generation_df, gas_burn_daily_df, site_generation_by_gas_day_df, site_availability_df, yes_historical_forecast_cleaned_df, yes_historical_actual_cleaned_df)


    ####################
    ## Adding columns ##
    ####################
    merged_df = add_time_features(merged_df)
    merged_df = add_gas_burn_features(merged_df)


    #########################
    ## Rearranging Columns ##
    #########################
    merged_df = reorder_columns(merged_df, lead_columns)


    ##################
    ## Confirmation ##
    ##################
    if save_output: 
        folder = Path("./data/processed-data/")
        if not folder.exists():
            folder.mkdir(parents=True)
        file_name = './data/processed-data/historic_data_df.csv'
        merged_df.to_csv(file_name, index=False)
        print(f'A file containing the merged data has been saved to {file_name}')

    return merged_df