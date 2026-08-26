"""
merge_datasets_functions.py

Module dedicated to merging datasets used to build the modeling/analysis
dataset.

This module contains helpers to join site generation, gas burn, availability,
and YES Energy historical forecast/actual data into a single DataFrame.
"""
import pandas as pd


def _validate_required_columns(df: pd.DataFrame, required_columns: list[str], name: str) -> None:
    """Raise a clear error if a dataframe is missing required columns."""
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise KeyError(f"{name} is missing required columns: {missing}")


def _validate_no_duplicate_keys(df: pd.DataFrame, key_columns: list[str], name: str) -> None:
    """Raise an error if a join key produces duplicate rows in a dataset."""
    duplicates = df.duplicated(subset=key_columns).any()
    if duplicates:
        raise ValueError(f"{name} contains duplicate rows for join keys: {key_columns}")


def merge_historic_data(site_generation_df: pd.DataFrame, gas_burn_daily_df: pd.DataFrame,
                        site_generation_by_gas_day_df: pd.DataFrame, site_availability_df: pd.DataFrame,
                        yes_historical_forecast_cleaned_df: pd.DataFrame, yes_historical_actual_cleaned_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge the various historical data sources into a single DataFrame.

    Parameters:
        site_generation_df: DataFrame containing site-level generation (must include 'datetime' and 'site').
        gas_burn_daily_df: DataFrame with daily gas burn values (must include 'gas_day' and 'site').
        site_generation_by_gas_day_df: DataFrame aggregated by gas day (must include 'gas_day' and 'site').
        site_availability_df: DataFrame with site availability/metadata (must include 'datetime' and 'site').
        yes_historical_forecast_cleaned_df: Cleaned YES Energy forecast DataFrame (must include 'datetime').
        yes_historical_actual_cleaned_df: Cleaned YES Energy actuals DataFrame (must include 'datetime').

    Behavior:
        Performs successive left merges to preserve rows from site_generation_df:
        - merges gas_burn_daily_df and site_generation_by_gas_day_df on ['gas_day','site']
        - merges site_availability_df on ['datetime','site']
        - merges YES forecast and actuals on ['datetime']

    Returns:
        pandas.DataFrame: merged dataset containing columns from all inputs.
    """
    _validate_required_columns(site_generation_df, ['datetime', 'site'], 'site_generation_df')
    _validate_required_columns(gas_burn_daily_df, ['gas_day', 'site'], 'gas_burn_daily_df')
    _validate_required_columns(site_generation_by_gas_day_df, ['gas_day', 'site'], 'site_generation_by_gas_day_df')
    _validate_required_columns(site_availability_df, ['datetime', 'site'], 'site_availability_df')
    _validate_required_columns(yes_historical_forecast_cleaned_df, ['datetime'], 'yes_historical_forecast_cleaned_df')
    _validate_required_columns(yes_historical_actual_cleaned_df, ['datetime'], 'yes_historical_actual_cleaned_df')

    _validate_no_duplicate_keys(gas_burn_daily_df, ['gas_day', 'site'], 'gas_burn_daily_df')
    _validate_no_duplicate_keys(site_generation_by_gas_day_df, ['gas_day', 'site'], 'site_generation_by_gas_day_df')
    _validate_no_duplicate_keys(site_availability_df, ['datetime', 'site'], 'site_availability_df')

    merged_df = site_generation_df.merge(gas_burn_daily_df, how='left', on=['gas_day', 'site'])
    merged_df = merged_df.merge(site_generation_by_gas_day_df, how='left', on=['gas_day', 'site'])
    merged_df = merged_df.merge(site_availability_df, how='left', on=['datetime', 'site'])
    merged_df = merged_df.merge(yes_historical_forecast_cleaned_df, how='left', on=['datetime'])
    merged_df = merged_df.merge(yes_historical_actual_cleaned_df, how='left', on=['datetime'])

    return merged_df


def merge_data_to_forecast(future_site_availability_df: pd.DataFrame, future_yes_data_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge forecast availability data with YES Energy forecast inputs on datetime.

    Parameters:
        future_site_availability_df: DataFrame containing site availability observations
            for the forecast period. It must include a 'datetime' column.
        future_yes_data_df: DataFrame containing YES Energy forecast values for the
            same time range. It must also include a 'datetime' column.

    Returns:
        pandas.DataFrame: A left-joined DataFrame that keeps the availability data and
        appends forecast values aligned by timestamp.

    Notes:
        The YES forecast data does not include a site dimension, so the merge is
        intentionally performed on datetime only to align each site's availability
        record with the relevant market-level forecast values.
    """
    _validate_required_columns(future_site_availability_df, ['datetime'], 'future_site_availability_df')
    _validate_required_columns(future_yes_data_df, ['datetime'], 'future_yes_data_df')

    future_data_to_forecast_df = future_site_availability_df.merge(future_yes_data_df, how='left', on=['datetime'])

    return future_data_to_forecast_df
