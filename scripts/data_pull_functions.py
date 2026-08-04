"""
Module containing functions for data gathering from Allegro/BigQuery
"""
import pandas as pd
from google.cloud import bigquery


def run_date_parameterized_query(client: bigquery.Client, query_string: str, start: str, end: str, col_dtypes: dict = None):
    """
    Runs a query within a specified date range
    
    Parameters:
        client: active BigQuery client object as created by bigquery.Client() call
        query_string: SQL query 
        start: start date of SQL query
        end: end date of SQL query
        col_types: column types of returned dataframe

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



def run_generation_query(client: bigquery.Client, query_strings: list, start: str, end: str, col_dtypes: dict = None):
    """
    Function designed to pull generation data based on multiple SQL queries. SQL queries must contain the same column headers

    Parameters:
        client: Session bigquery.client object
        query_strings: SQL queries
        start: Earliest date of data to pull from database
        end: Latest date of data to pull from database
        col_type: dictionary containing column name to datatype mappings

    """

    dfs = {}
    for idx, query in enumerate(query_strings):
    
        df_name = f'df{idx}'
        dfs[df_name] = run_date_parameterized_query(client, query, start, end)
    
    dfs_appended = pd.concat(dfs, ignore_index=True)

    if col_dtypes: 
        dfs_appended = dfs_appended.astype(col_dtypes)

    return dfs_appended



def clean_generation_unit_data(df: pd.DataFrame):
    """
    Function that takes the unit generation data as input, creates a site variable, calculates gas day, and aggregates at different levels

    Parameters:
        df: dataframe containing hourly unit level generation data

    Returns: 
        A dictionary with cleaned generation data at different aggregations
    """
    unit_df = df.copy()

    #adding a site column based on the loadshape name
    conditions = [
        unit_df["loadshape"].str.upper().str.contains("DCS"),
        unit_df["loadshape"].str.upper().str.contains("LCS"),
        unit_df["loadshape"].str.upper().str.contains("PGS"),
        unit_df["loadshape"].str.upper().str.contains("GGS"),
        unit_df["loadshape"].str.upper().str.contains("CGS")
    ]

    choices = ["DCS", "LCS", "PGS", "GGS", "CGS"]

    unit_df['site'] = np.select(conditions, choices, default="N/A")

    #Unpivoting columns using melt() function
    hour_cols = [column for column in unit_df.columns if column.startswith("he")]
    hourly_unit_generation_df = unit_df.melt(id_vars=["begtime", "site", "loadshape"], value_vars=hour_cols, var_name="hour", value_name="hourly_mw")
    #print(hourly_unit_generation_df['hourly_mw'].sum()) # may take out

    #Create hour (numeric column) for Datetime creation
    hourly_unit_generation_df["hour_num"] = hourly_unit_generation_df["hour"].str[-2:].astype(int)

    #create a datetime column and related gas_day column
    hourly_unit_generation_df["datetime"] = (pd.to_datetime(hourly_unit_generation_df["begtime"]) + pd.to_timedelta(hourly_unit_generation_df["hour_num"] - 0, unit="h"))
    hourly_unit_generation_df['gas_day'] = (pd.to_datetime(hourly_unit_generation_df["datetime"]) - pd.Timedelta(hours=10)).dt.date
    hourly_unit_generation_df['gas_day'] = pd.to_datetime(hourly_unit_generation_df['gas_day'])
    #print(hourly_unit_generation_df['hourly_mw'].sum()) # may take out


    #Reordering columns for visual 
    hourly_unit_generation_df = (
        hourly_unit_generation_df[["datetime","gas_day", "hour", "site", "loadshape", "hourly_mw"]]
        .sort_values(by = ['site', 'datetime'], ascending=[False, True])
    )
    print(hourly_unit_generation_df['hourly_mw'].sum()) # may take out


    # Aggregating by site
    hourly_site_generation_df = (
        hourly_unit_generation_df.groupby(["datetime", "gas_day", "hour", "site"], as_index=False)["hourly_mw"]
        .sum()
        .rename(columns={"hourly_mw": "hourly_site_gen_mw"})
        .sort_values(by = ['site', 'datetime'], ascending=[False, True])
    )
    #print(hourly_site_generation_df['hourly_site_gen_mw'].sum()) # may take out


    daily_site_generation_by_gas_day_df = (
        hourly_unit_generation_df.groupby(["gas_day", "site"], as_index=False)["hourly_mw"]
        .sum()
        .rename(columns={"hourly_mw": "hourly_site_gen_mw"})
        .sort_values(by = ['site', 'gas_day'], ascending=[False, True])
    )
    #print(daily_site_generation_by_gas_day_df['hourly_site_gen_mw'].sum()) # may take out


    daily_site_generation_df = (
        hourly_unit_generation_df.groupby(["datetime", "site"], as_index=False)["hourly_mw"]
        .sum()
        .rename(columns={"hourly_mw": "hourly_site_gen_mw"})
        .sort_values(by = ['site', 'datetime'], ascending=[False, True])
    )
    #print(daily_site_generation_df['hourly_site_gen_mw'].sum()) # may take out



    return {
        'hourly_unit_generation_df': hourly_unit_generation_df, 
        'hourly_site_generation_df': hourly_site_generation_df, 
        'daily_site_generation_by_gas_day_df': daily_site_generation_by_gas_day_df, 
        'daily_site_generation_df': daily_site_generation_df
    }
