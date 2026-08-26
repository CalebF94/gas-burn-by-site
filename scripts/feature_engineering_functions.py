"""
feature_engineering_functions.py

Module dedicated to performing feature engineering and creating new columns
"""
import pandas as pd
import numpy as np

def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add common time-based features to a DataFrame containing a datetime column.
    Note: modifies the input DataFrame in place and returns it

    Parameters:
        df: pandas DataFrame containing a 'datetime' column of dtype datetime64[ns] or convertible to datetime.

    Returns:
        pandas DataFrame with the following columns added:
            - hour: integer hour of the day (0-23)
            - day_of_week: integer day of week (Monday=0, Sunday=6)
            - day: day of month
            - month: month number (1-12)
            - year: four-digit year
            - gas_day: date representing the gas day (datetime shifted by -10 hours, cast to date)
            - hour_end: string label for the hour ending (e.g. 'HE1', 'HE2', ...)
    """

    if "datetime" not in df.columns:
        raise KeyError("DataFrame must contain a 'datetime' column.")

    df["hour"] = df["datetime"].dt.hour
    df["day_of_week"] = df["datetime"].dt.dayofweek
    df["day"] = df["datetime"].dt.day
    df["month"] = df["datetime"].dt.month
    df['year'] = df['datetime'].dt.year
    df['gas_day'] = (pd.to_datetime(df["datetime"], errors='raise') - pd.Timedelta(hours=10)).dt.date

    # datetime is hour beginning, so adding an hour to the hour extracted from datetime. Then adding formatting 
    df['hour_end'] = df['hour'] + 1
    df['hour_end'] = 'HE' + df['hour_end'].astype(str)

    return df


def add_gas_burn_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create an hourly gas burn estimate based on daily gas burn and generation shares.
    Note: modifies the input DataFrame in place and returns it

    The hourly gas burn in MMBtu is computed as:
        hourly_gas_burn_MMBtu = (daily_gas_burn_MMBtu / daily_site_gen_mw) * hourly_site_gen_mw

    Parameters:
        df: pandas DataFrame that must contain the following columns:
            - daily_gas_burn_MMBtu
            - daily_site_gen_mw
            - hourly_site_gen_mw

    Returns:
        pandas DataFrame with the column 'hourly_gas_burn_MMBtu' added. The function assumes
        daily_site_gen_mw is non-zero; results may contain inf or NaN if division by zero occurs.
    """

    required_cols = {'daily_gas_burn_MMBtu', 'daily_site_gen_mw', 'hourly_site_gen_mw'}
    missing_cols = required_cols - set(df.columns)

    if missing_cols:
        raise KeyError(f'The following required columns are missing from the input DataFrame {missing_cols}') 
    

    # If we don't have any generation (0 or NaN), spread the daily gas burn evenly across the 24 hours as a fallback rule
    df['hourly_gas_burn_MMBtu'] = np.where(df['daily_site_gen_mw'].eq(0) | df['daily_site_gen_mw'].isna(),
                                           df['daily_gas_burn_MMBtu'] / 24,
                                           (df['daily_gas_burn_MMBtu'] / df['daily_site_gen_mw']) * df['hourly_site_gen_mw']
                                           )

    return df