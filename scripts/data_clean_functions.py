"""
Module containing functions for data cleaning
"""
import pandas as pd
import numpy as np
import time
import requests
from datetime import timedelta


def clean_generation_unit_data(df: pd.DataFrame):
    """
    Function that takes the unit generation data as input, creates a site variable, calculates gas day, and aggregates at different levels

    Parameters:
        df: dataframe containing hourly unit level generation data

    Returns: 
        A dictionary with cleaned generation dataframes at different aggregations. The four dictionary keys are:
        'hourly_unit_generation_df', 'hourly_site_generation_df', 'daily_site_generation_by_gas_day_df', 'daily_site_generation_df':
    """
    unit_df = df.copy()

    #adding a site column based on the loadshape name
    conditions = [
        unit_df["loadshape"].str.upper().str.contains("DCS"),
        unit_df["loadshape"].str.upper().str.contains("LCS"),
        unit_df["loadshape"].str.upper().str.contains("PGS"),
        unit_df["loadshape"].str.upper().str.contains("GGS"),
        unit_df["loadshape"].str.upper().str.contains("CULBERTSON")
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
    #print(hourly_unit_generation_df['hourly_mw'].sum()) # may take out


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
        .rename(columns={"hourly_mw": "daily_site_gen_mw"})
        .sort_values(by = ['site', 'gas_day'], ascending=[False, True])
    )
    #print(daily_site_generation_by_gas_day_df['hourly_site_gen_mw'].sum()) # may take out


    daily_site_generation_df = (
        hourly_unit_generation_df.groupby(["datetime", "site"], as_index=False)["hourly_mw"]
        .sum()
        .rename(columns={"hourly_mw": "daily_site_gen_mw"})
        .sort_values(by = ['site', 'datetime'], ascending=[False, True])
    )
    #print(daily_site_generation_df['hourly_site_gen_mw'].sum()) # may take out



    return {
        'hourly_unit_generation_df': hourly_unit_generation_df, 
        'hourly_site_generation_df': hourly_site_generation_df, 
        'daily_site_generation_by_gas_day_df': daily_site_generation_by_gas_day_df, 
        'daily_site_generation_df': daily_site_generation_df
    }


def clean_yes_forecast(df):
    """
    Function cleans the historical forecast from YES Energy

    Parameters:
        df: dataframe returned from the pull_yes_forecast_historical() function

    Returns:
        out: dataframe with cleaned and aggregated data
    """
    df = df.copy()

    #find datetime column
    datetime_col = [c for c in df.columns if "DATETIME" in c.upper()][0]

    df["datetime"] = pd.to_datetime(df[datetime_col], format="%m/%d/%Y %H:%M:%S", errors="coerce")
    df["datetime"] = df["datetime"] - pd.Timedelta(hours=1) #YES Energy uses 1:00 in the date time to represent HE1.

    #load 
    df["load_forecast"] = pd.to_numeric( df["SPPISO-East (LOAD_FORECAST)"], errors="coerce")

    #net load 
    df["net_load_forecast"] = pd.to_numeric(df["SPPISO-East (NET_LOAD_FORECAST_CURRENT)"], errors="coerce")

    #wind 
    wind_cols = [c for c in df.columns if "WINDFCST_HOURLY" in c]
    df["wind_forecast"] = df[wind_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)

    #outages 
    df["offline_ng_forecast"] = pd.to_numeric(df["SPPISO-East (NG_CAPACITY_OFFLINE)"], errors="coerce")

    df["offline_coal_forecast"] = pd.to_numeric(df["SPPISO-East (COAL_CAPACITY_OFFLINE)"], errors="coerce")

    #temperature avg of the zones (ask about this)
    temp_cols = [c for c in df.columns if "WSI_FC15_FEEL" in c]
    df["temperature_forecast"] = df[temp_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)

    #wind speed avg of the reserve zones (also ask)
    wind_speed_cols = [c for c in df.columns if "WSI_FC15_WIND" in c]
    df["wind_speed_forecast"] = df[wind_speed_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)

    #outage
    df["total_offline_forecast"] = df["offline_ng_forecast"] + df["offline_coal_forecast"]

    out = df[["datetime", "load_forecast", "net_load_forecast", "wind_forecast", "temperature_forecast", "wind_speed_forecast", "total_offline_forecast", "offline_ng_forecast", "offline_coal_forecast"]]#.dropna(subset=["datetime"])

    return out.sort_values("datetime").reset_index(drop=True)


def clean_yes_actual(df) -> pd.DataFrame:
    """
    Function used to clean the actual/historical data from the pull_yes_actual_historical() function

    Parameters:
        df: pandas dataframe as returned from the pull_yes_actual_historical() function

    Returns:
        dataframe with cleaned YES Energy data
    """
    df = df.copy()

    datetime_col = [c for c in df.columns if "DATETIME" in c.upper()][0]

    df["datetime"] = pd.to_datetime( df[datetime_col], errors="coerce")
    df["datetime"] = df["datetime"] - pd.Timedelta(hours=1) #YES Energy uses 1:00 in the date time to represent HE1.


    # load actual
    df["load_actual"] = pd.to_numeric(df["SPPISO-East (BIDCLOSE_LOAD_FORECAST)"], errors="coerce")

    # net load actual
    df["net_load_actual"] = pd.to_numeric( df["SPPISO-East (NET_LOAD_FORECAST_BID_CLOSE)"], errors="coerce")

    # wind actual
    wind_cols = [c for c in df.columns if "WINDGEN_HOURLY" in c]
    wind_numeric = (df[wind_cols].apply(pd.to_numeric, errors="coerce"))

    wind_sum = wind_numeric.sum(axis=1, min_count=1)

    all_zero = (wind_numeric.fillna(0).sum(axis=1).eq(0))

    df["wind_actual"] = wind_sum.mask(all_zero)

    # outage actual
    df["outage_ng"] = pd.to_numeric(df["SPPISO-East (NG_CAPACITY_OFFLINE)"], errors="coerce")
    df["outage_coal"] = pd.to_numeric( df["SPPISO-East (COAL_CAPACITY_OFFLINE)"], errors="coerce")

    # temperature actual
    temp_cols = [c for c in df.columns if "WSI_TRADER_FEELS_TEMP" in c]
    temp_numeric = (df[temp_cols].apply(pd.to_numeric, errors="coerce"))

    temp_avg = temp_numeric.mean(axis=1)

    all_zero_temp = (temp_numeric.fillna(0).sum(axis=1).eq(0))

    df["temperature_actual"] = temp_avg.mask(all_zero_temp)

    # windspeed actual
    wind_speed_cols = [c for c in df.columns if "WSI_TRADER_WIND" in c]
    df["wind_speed_actual"] = df[wind_speed_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)
    
    
    # outage actual
    df["total_outages"] = df["outage_ng"] + df["outage_coal"]

    out = df[["datetime", "load_actual", "net_load_actual", "wind_actual", "temperature_actual", "wind_speed_actual", "total_outages"]].dropna(subset=["datetime"])

    return out.sort_values("datetime").reset_index(drop=True)
