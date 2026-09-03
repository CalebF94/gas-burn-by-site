"""
Module containing functions for cleaning and preparing data from multiple sources:
- Generation data from BigQuery (unit and site level aggregations with gas day calculations)
- YES Energy historical forecasts and actuals (load, wind, temperature, outage data)
- Utility functions for column reordering
"""
import pandas as pd
import numpy as np


def clean_generation_unit_data(df: pd.DataFrame) -> dict:
    """
    Clean and aggregate unit-level generation data into multiple time/site aggregations.
    
    Takes raw unit generation data from BigQuery, extracts site identifiers from loadshape names,
    calculates gas day timestamps (offset by 10 hours), unpivots hourly data, and aggregates
    at unit, site, and daily levels.

    Parameters:
        df: DataFrame containing hourly unit-level generation data with hourly columns (he01-he24)
           and loadshape names that contain site identifiers (DCS, LCS, PGS, GGS, CULBERTSON)

    Returns:
        dict: Dictionary containing four DataFrames at different aggregation levels:
            - 'hourly_unit_generation_df': Hourly generation at individual unit level (MW)
            - 'hourly_site_generation_df': Hourly generation aggregated by site (MW)
            - 'daily_site_generation_by_gas_day_df': Daily generation by gas day (MW)
            - 'daily_site_generation_df': Daily generation by calendar day (MW)
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

    #Create hour (numeric column) for Datetime creation
    hourly_unit_generation_df["hour_num"] = hourly_unit_generation_df["hour"].str[-2:].astype(int)

    #create a datetime column and related gas_day column
    hourly_unit_generation_df["datetime"] = (pd.to_datetime(hourly_unit_generation_df["begtime"]) + pd.to_timedelta(hourly_unit_generation_df["hour_num"] - 0, unit="h"))
    hourly_unit_generation_df['gas_day'] = (pd.to_datetime(hourly_unit_generation_df["datetime"]) - pd.Timedelta(hours=10)).dt.date
    hourly_unit_generation_df['gas_day'] = pd.to_datetime(hourly_unit_generation_df['gas_day'])


    #Reordering columns for visual 
    hourly_unit_generation_df = (
        hourly_unit_generation_df[["datetime","gas_day", "hour", "site", "loadshape", "hourly_mw"]]
        .sort_values(by = ['site', 'datetime'], ascending=[False, True])
    )


    # Aggregating by site
    hourly_site_generation_df = (
        hourly_unit_generation_df.groupby(["datetime", "gas_day", "hour", "site"], as_index=False)["hourly_mw"]
        .sum()
        .rename(columns={"hourly_mw": "hourly_site_gen_mw"})
        .sort_values(by = ['site', 'datetime'], ascending=[False, True])
    )


    daily_site_generation_by_gas_day_df = (
        hourly_unit_generation_df.groupby(["gas_day", "site"], as_index=False)["hourly_mw"]
        .sum()
        .rename(columns={"hourly_mw": "daily_site_gen_mw"})
        .sort_values(by = ['site', 'gas_day'], ascending=[False, True])
    )


    daily_site_generation_df = (
        hourly_unit_generation_df.groupby(["datetime", "site"], as_index=False)["hourly_mw"]
        .sum()
        .rename(columns={"hourly_mw": "daily_site_gen_mw"})
        .sort_values(by = ['site', 'datetime'], ascending=[False, True])
    )



    return {
        'hourly_unit_generation_df': hourly_unit_generation_df, 
        'hourly_site_generation_df': hourly_site_generation_df, 
        'daily_site_generation_by_gas_day_df': daily_site_generation_by_gas_day_df, 
        'daily_site_generation_df': daily_site_generation_df
    }


def clean_yes_forecast(df) -> pd.DataFrame:
    """
    Clean and aggregate historical forecast data from YES Energy API.
    
    Extracts forecast values from API response columns, converts datetime to hour-ending format,
    aggregates wind forecasts across multiple zones, and aggregates temperature and wind speed
    from multiple weather stations.

    Parameters:
        df: DataFrame returned from pull_yes_forecast_historical() function containing raw API response data

    Returns:
        pd.DataFrame: Cleaned forecast data with columns: datetime, load_forecast, net_load_forecast,
                      wind_forecast, temperature_forecast, wind_speed_forecast, total_offline_forecast,
                      offline_ng_forecast, offline_coal_forecast. Sorted by datetime.
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

    temp_cols = [c for c in df.columns if "WSI_FC15_FEEL" in c]
    df["temperature_forecast"] = df[temp_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)

    wind_speed_cols = [c for c in df.columns if "WSI_FC15_WIND" in c]
    df["wind_speed_forecast"] = df[wind_speed_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)

    #outage
    df["total_offline_forecast"] = df["offline_ng_forecast"] + df["offline_coal_forecast"]

    out = df[["datetime", "load_forecast", "net_load_forecast", "wind_forecast", "temperature_forecast", "wind_speed_forecast", "total_offline_forecast", "offline_ng_forecast", "offline_coal_forecast"]]#.dropna(subset=["datetime"])

    return out.sort_values("datetime").reset_index(drop=True)


def clean_yes_actual(df) -> pd.DataFrame:
    """
    Clean and aggregate actual historical data from YES Energy API.
    
    Extracts actual values from API response columns, converts datetime to hour-ending format,
    aggregates wind actuals across multiple zones, and aggregates temperature and wind speed
    from multiple weather stations. Handles cases where all values are zero (masked as NaN).

    Parameters:
        df: DataFrame returned from pull_yes_actual_historical() function containing raw API response data

    Returns:
        pd.DataFrame: Cleaned actual data with columns: datetime, load_actual, net_load_actual,
                      wind_actual, temperature_actual, wind_speed_actual, total_outages.
                      Sorted by datetime with rows missing datetime values removed.
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


def reorder_columns(df: pd.DataFrame, lead_columns: list[str]) -> pd.DataFrame:
    """
    Move specified columns to the front of a DataFrame.

    Parameters:
        df: pandas DataFrame to reorder.
        lead_columns: list of column names to place at the front, in the given order.
            Any names not present in df are ignored.

    Returns:
        pandas DataFrame with columns reordered: the requested lead_columns first (in the
        order provided), followed by the remaining columns in their original order.
    """
    tail_columns = [cols for cols in list(df.columns) if (cols not in lead_columns)]

    df = df.loc[:, lead_columns +  tail_columns]

    return df
