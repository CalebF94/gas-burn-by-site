"""
Module containing functions for data gathering from Allegro/BigQuery, YES Energy APIs, and Unit Availability files. These functions will be used in the gather_historic_data.py orchestration script.
"""
import pandas as pd
import requests
from pathlib import Path
from google.cloud import bigquery
import pydata_google_auth
from scripts.constants import SITE_MAPPINGS, SITES_OR_LIST

def login_google_cloud(project_name: str = "") -> bigquery.Client:
    """
    Authenticate with Google Cloud and create a BigQuery client.

    Parameters:
        project_name: Name of the Google Cloud project to attach to the client.
            If left blank, the client will use the default project configuration
            available to the authenticated account.

    Returns:
        bigquery.Client: Authenticated BigQuery client configured for the supplied
        project and Google Cloud Platform access scope.

    Notes:
        This function launches a user-authentication flow using the Google Cloud
        OAuth credentials helper and requests access to the Cloud Platform APIs.
    """
    credentials = pydata_google_auth.get_user_credentials(
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
    auth_local_webserver=True
    )

    client = bigquery.Client(project=project_name, credentials=credentials)

    return client


def _run_date_parameterized_query(client: bigquery.Client, query_string: str, start: str, end: str, col_dtypes: dict = None):
    """
    Runs a query within a specified date range
    
    Parameters:
        client: active BigQuery client object as created by bigquery.Client() call
        query_string: SQL query 
        start: start date of SQL query
        end: end date of SQL query
        col_dtypes: column types of returned dataframe

    Returns:
        dataframe: result of query
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters = [
            bigquery.ScalarQueryParameter('start_date', 'DATETIME', start),
            bigquery.ScalarQueryParameter('end_date', 'DATETIME', end)
        ]
    )

    query_job = client.query(query_string, job_config=job_config)
    
    return query_job.to_dataframe(create_bqstorage_client=False, dtypes = col_dtypes)



def run_generation_query(client: bigquery.Client, query_strings: list, start: str, end: str, col_dtypes: dict = None) -> pd.DataFrame:
    """
    Function designed to pull generation data based on multiple SQL queries. SQL queries must contain the same column headers

    Parameters:
        client: Session bigquery.client object
        query_strings: SQL queries
        start: Earliest date of data to pull from database
        end: Latest date of data to pull from database
        col_dtype: dictionary containing column name to datatype mappings

     Returns: 
        Pandas dataframe with the results of the query. If multiple queries are supplied, the results will be concatenated into a single dataframe   
    """

    dfs = {}
    for idx, query in enumerate(query_strings):
    
        df_name = f'df{idx}'
        dfs[df_name] = _run_date_parameterized_query(client, query, start, end)
    
    dfs_appended = pd.concat(dfs, ignore_index=True)

    if col_dtypes: 
        dfs_appended = dfs_appended.astype(col_dtypes)

    return dfs_appended


def run_natural_gas_burn_query(client: bigquery.Client, query_strings: list, start: str, end: str, col_dtypes: dict = None) -> pd.DataFrame:
    """
    Function designed to pull natural gas burn data based on multiple SQL queries. SQL queries must contain the same column headers.

    Parameters:
        client: Session bigquery.client object
        query_strings: SQL queries
        start: Earliest date of data to pull from database
        end: Latest date of data to pull from database
        col_dtypes: Dictionary containing column name to datatype mappings

    Returns:
        pd.DataFrame: Combined dataframe from all queries with site mappings applied and columns
        renamed to 'gas_day', 'site', and 'daily_gas_burn_MMBtu'.
    """
        
    dfs = {}
    for idx, query in enumerate(query_strings):
    
        df_name = f'df{idx}'
        dfs[df_name] = _run_date_parameterized_query(client, query, start, end)
    
    dfs_appended = pd.concat(dfs, ignore_index=True)

    if col_dtypes: 
        dfs_appended = dfs_appended.astype(col_dtypes)

    dfs_appended['site'] = dfs_appended['marketarea'].replace(SITE_MAPPINGS)
    dfs_appended = dfs_appended[['gas_day', 'site', 'energy']].rename(columns={'energy': 'daily_gas_burn_MMBtu'})

    return dfs_appended


def pull_unit_availability(excel_files: list, csv_files: list, sheet: str='Sheet1', start_date: str = '1900-01-01', end_date: str = '2100-12-31')-> dict:
    """
    Function pulls unit availability data from files updated by Market Opps team. Function takes lists of Excel and CSV files and combines into a single dataframe

    Parameters:
        excel_files: list of Excel files to be loaded. List of files is found in the AVAILABILITY_FILES_XLSX variable in the constants.py script
        csv_files: list of CSV files to be loaded. List of files is found in the AVAILABILITY_FILES_CSV variable in the constants.py script
        sheet: For excel_files, names the sheet containing the data to pull
        start_date: Earliest date to return. Filtering occurs at end of processing and doesn't impact which files are imported.
        end_date: Latest date to return. Filtering occurs at end of processing and doesn't impact which files are imported.

    Returns:
        Returns a dict with two dataframes with availability data at different aggregation levels. The two dataframes returned are:
        "unit_availability_df", "site_availability_df"
    """
    excel_dfs = []
    for file in excel_files:
        df = pd.read_excel(file, sheet_name=sheet)
        df["source_file"] = file
        excel_dfs.append(df)

    excel_combined = pd.concat(excel_dfs, ignore_index=True) if excel_dfs else pd.DataFrame()

    csv_dfs = []
    for file in csv_files:
        df = pd.read_csv(file)
        df["source_file"] = file
        csv_dfs.append(df)

    csv_combined = pd.concat(csv_dfs, ignore_index=True) if csv_dfs else pd.DataFrame()

    #Concat the csvs and the excel files
    combined_df = pd.concat([excel_combined, csv_combined], ignore_index=True)

    #Making all column names lowercase and remove spaces
    combined_df.columns = (combined_df.columns.str.strip().str.lower())

    #Making datetime column in datetime format
    combined_df["datetime"] = pd.to_datetime( combined_df["datetime"], errors="coerce")

    #Sorting chronologically
    combined_df = (combined_df.sort_values("datetime").reset_index(drop=True))


    #Data cleaning and formatting
    combined_df.columns = combined_df.columns.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

    combined_df = combined_df.dropna(subset = ['datetime'], axis=0) # drops rows that don't have dates due to daylight savings shifts
    
    value_cols = [col for col in combined_df.columns if isinstance(col, str) and "high effective limit" in col]

    unit_availability_df = combined_df.melt(id_vars=["datetime"], value_vars=value_cols, var_name="unit", value_name="availability_mw")

    unit_availability_df["site"] = unit_availability_df["unit"].str.extract(r"^(cgs|dcs|ggs|lcs|pgs)", expand=False).str.strip().str.upper()
    unit_availability_df = unit_availability_df.sort_values(by=["site", "unit", "datetime"])[["datetime","site", "unit", "availability_mw"]]
    unit_availability_df = unit_availability_df[(unit_availability_df['datetime'] >= start_date) & (unit_availability_df['datetime'] <= end_date)]

    site_availability_df = unit_availability_df.groupby(["datetime", 'site']).agg({"availability_mw": "sum"}).reset_index()
    site_availability_df = site_availability_df.sort_values(by=["site", "datetime"])[["datetime","site", "availability_mw"]]
    site_availability_df = site_availability_df[(site_availability_df['datetime'] >= start_date) & (site_availability_df['datetime'] <= end_date)]

    return {
        "unit_availability_df": unit_availability_df,
        "site_availability_df": site_availability_df
        }


def _transpose_raw_unit_availability(raw_df: pd.DataFrame = None,
                                    datetimes: pd.DatetimeIndex = None,
                                    start_date = None,
                                    end_date = None):
    
    
    unit_availability_df = raw_df[ (raw_df['Name'].str.contains(SITES_OR_LIST, na=False)) & (raw_df['Name'].str.contains('High Effective Limit', na=False))].transpose()
    col_names = unit_availability_df.iloc[0,:]
    unit_availability_df = unit_availability_df.iloc[1:,:]
    unit_availability_df.columns = col_names
    unit_availability_df = unit_availability_df.reset_index(drop=True)
    unit_availability_df.insert(loc=0, column='datetime', value=datetimes)
    object_cols = unit_availability_df.select_dtypes(include=['object']).columns
    unit_availability_df[object_cols] = unit_availability_df[object_cols].apply(pd.to_numeric, errors='coerce')

    #replicating data cleaning for historic data
    #Sorting chronologically
    unit_availability_df = (unit_availability_df.sort_values("datetime").reset_index(drop=True))
    
    #Data cleaning and formatting
    unit_availability_df.columns = unit_availability_df.columns.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

    unit_availability_df = unit_availability_df.dropna(subset = ['datetime'], axis=0) # drops rows that don't have dates due to daylight savings shifts

    value_cols = [col for col in unit_availability_df.columns if isinstance(col, str) and "High Effective Limit" in col]

    unit_availability_df = unit_availability_df.melt(id_vars=["datetime"], value_vars=value_cols, var_name="unit", value_name="availability_mw")
    
    unit_availability_df["site"] = unit_availability_df["unit"].str.upper().str.extract(r"^(CGS|DCS|GGS|LCS|PGS)", expand=False).str.strip().str.upper()
    unit_availability_df = unit_availability_df.sort_values(by=["site", "unit", "datetime"])[["datetime","site", "unit", "availability_mw"]]
    unit_availability_df = unit_availability_df[(unit_availability_df['datetime'] >= start_date) & (unit_availability_df['datetime'] <= end_date)]

    
    site_availability_df = unit_availability_df.groupby(["datetime", 'site']).agg({"availability_mw": "sum"}).reset_index()
    site_availability_df = site_availability_df.sort_values(by=["site", "datetime"])[["datetime","site", "availability_mw"]]
    site_availability_df = site_availability_df[(site_availability_df['datetime'] >= start_date) & (site_availability_df['datetime'] <= end_date)]

    return {
        "unit_availability_df": unit_availability_df,
        "site_availability_df": site_availability_df
        }


def pull_and_transpose_raw_unit_availability(most_recent_file = 'G:\\Trading\\Forecasts\\Daily Gas Burn Forecast by Site\\Unit Availability Exports - Future',
                                             start_date = '2026-09-04',
                                             end_date = '2026-09-13'):


    #getting start and end dates from file name
    file_name_words = str(most_recent_file).removesuffix(".csv").split("_")
    start_time = file_name_words[-2]
    end_time = file_name_words[-1]

    # file name contains start and end times in YYYYMMDDHH format. Extracting that info and creating a datetime range
    datetime_start = pd.Timestamp(year=int(start_time[:4]), month=int(start_time[4:6]), day=int(start_time[6:8]), hour=int(start_time[8:10]))
    datetime_end = pd.Timestamp(year=int(end_time[:4]), month=int(end_time[4:6]), day=int(end_time[6:8]), hour=int(end_time[8:10]))
    datetimes = pd.date_range(start=datetime_start, end=datetime_end, freq='h')

    raw_df = pd.read_csv(most_recent_file).iloc[:, 1:]
    
    transposed_dfs = _transpose_raw_unit_availability(raw_df=raw_df, start_date=start_date, end_date=end_date, datetimes=datetimes)

    return transposed_dfs


def pull_yes_forecast_historical(user, password, start_date, end_date):
    """
    Function pulls forecast data from YES Energy via API. Note the hours here are hour ending which is different than Allegro.

    Parameters:
        user: YES Energy API username for authentication
        password: YES Energy API password for authentication
        start_date: First date of data to pull (will be converted to datetime)
        end_date: Last date of data to pull (will be converted to datetime)

    Returns:
        pd.DataFrame: Forecast data from YES Energy API containing hourly load, wind, and capacity information
    """
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    df_forecast = []



    #print(f"Pulling forecast: {start.date()} ---> {end.date()}")

    url = ( "https://services.yesenergy.com/PS/rest/timeseries/multiple.json?agglevel=hour&timezone=CPT"
        f"&startdate={start}"
        f"&enddate={end}"
        "&items="
        "LOAD_FORECAST:10017060648,"
        "NET_LOAD_FORECAST_CURRENT:10017060648,"
        "NG_CAPACITY_OFFLINE:10017060648,"
        "COAL_CAPACITY_OFFLINE:10017060648,"
        "WINDFCST_HOURLY:10004185377,"
        "WINDFCST_HOURLY:10004185378,"
        "WINDFCST_HOURLY:10004185379,"
        "WINDFCST_HOURLY:10004185380,"
        "WINDFCST_HOURLY:10004185381,"
        "WSI_FC15_FEEL:10000355230,"
        "WSI_FC15_FEEL:10000355704,"
        "WSI_FC15_FEEL:10000356081,"
        "WSI_FC15_WIND:10000355230,"
        "WSI_FC15_WIND:10000355704" )


    response = requests.get(url, auth=(user, password), verify=False, timeout=120)
    response.raise_for_status()
        
    # processing after successful data pull
    df_chunk = pd.DataFrame(response.json())
       
    df_chunk.columns = df_chunk.columns.map(lambda x: str(x).strip())

    df_forecast.append(df_chunk)

    return pd.concat(df_forecast, ignore_index=True)


def pull_yes_actual_historical(user, password, start_date, end_date) -> pd.DataFrame:
    """
    Function to pull actual historical data from the YES Energy API.

    Parameters:
        user: YES Energy API username for authentication
        password: YES Energy API password for authentication
        start_date: First date of data to pull (will be converted to datetime)
        end_date: Last date of data to pull (will be converted to datetime)

    Returns:
        pd.DataFrame: Actual data from YES Energy API containing hourly load, wind, temperature, and capacity information
    """

    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    df_actual = []


    #print(f"Pulling actuals: {start.date()} ---> {end.date()}")

    url = ("https://services.yesenergy.com/PS/rest/timeseries/multiple.json?agglevel=hour&timezone=CPT"
        f"&startdate={start.date()}"
        f"&enddate={end.date()}"
        "&items="
        #day ahead close so just in actual
        "BIDCLOSE_LOAD_FORECAST:10017060648,"
        "NET_LOAD_FORECAST_BID_CLOSE:10017060648,"
        "NG_CAPACITY_OFFLINE:10017060648,"
        "COAL_CAPACITY_OFFLINE:10017060648,"
        "WINDGEN_HOURLY:10004185377,"
        "WINDGEN_HOURLY:10004185378,"
        "WINDGEN_HOURLY:10004185379,"
        "WINDGEN_HOURLY:10004185380,"
        "WINDGEN_HOURLY:10004185381,"
        "WSI_TRADER_FEELS_TEMP:10000355230,"
        "WSI_TRADER_FEELS_TEMP:10000355704,"
        "WSI_TRADER_FEELS_TEMP:10000356081,"
        "WSI_TRADER_WIND:10000355230,"
        "WSI_TRADER_WIND:10000355704")


    response = requests.get(url, auth=(user, password), verify=False, timeout=120)
    #response.raise_for_status()


    df_chunk = pd.DataFrame(response.json())
    df_chunk.columns = df_chunk.columns.map(lambda x: str(x).strip())

    df_actual.append(df_chunk)

    return pd.concat(df_actual, ignore_index=True)


