"""
Module for modelling data
"""
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

from scripts.feature_engineering_functions import add_lag_features, add_rolling_features


def earliest_full_gas_day_with_forecast(predictions: pd.DataFrame):
    """
    """
    daily_record_counts = predictions.groupby('gasday').count()['site'].reset_index()
    full_gas_days = daily_record_counts[daily_record_counts['site']==max(daily_record_counts['site'])]['gasday']
    full_gas_days = pd.to_datetime(full_gas_days)

    return full_gas_days


def fit_xgboost_clarissa_version(df: pd.DataFrame, sites = ['CGS', 'DCS', 'GGS', 'LCS', 'PGS'], test_start_date: str='2026-08-27', features: list=[], target: list=[], save_model_file: Path=None):
    """
    Train XGBoost regression models for each site with specified hyperparameters.
    
    Splits data into training and test sets based on a test start date, trains an XGBoost
    model for each site, and evaluates model performance using MAE, RMSE, and R² metrics.
    
    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe containing historical data with 'site', 'datetime', and feature columns.
    sites : list, optional
        List of site identifiers to build models for. Default is ['CGS', 'DCS', 'GGS', 'LCS', 'PGS'].
    test_start_date : str, optional
        Date string (format: 'YYYY-MM-DD') marking the split between training and test data.
        Data before this date is used for training, data from this date onward is used for testing.
        Default is '2026-08-27'.
    features : list, optional
        List of feature column names to use as input variables for model training. Default is [].
    target : list, optional
        List containing the target variable name to predict. Default is [].
    
    Returns
    -------
    dict
        Dictionary with two keys:
        - 'models': dict mapping site identifiers to fitted XGBRegressor objects
        - 'results': dict mapping site identifiers to dicts containing:
          - 'mae': Mean Absolute Error on test set
          - 'rmse': Root Mean Squared Error on test set
          - 'r2': R² (coefficient of determination) on test set
    
    Notes
    -----
    Sites could potentially reference constants.py file once it is moved to a .py script.
    XGBoost hyperparameters are fixed: n_estimators=500, max_depth=6, learning_rate=0.03,
    subsample=0.8, colsample_bytree=0.8, random_state=42.
    """
    models = {}
    results = {}
    
    for site in sites:

        site_df = df[df["site"] == site].copy()

        #train on the past and test on the future
        train = site_df[site_df["datetime"] < test_start_date].copy()

        test = site_df[site_df["datetime"] >= test_start_date].copy()

        #Build the model
        model = XGBRegressor(n_estimators=500, max_depth=6, learning_rate=0.03, subsample=0.8, colsample_bytree=0.8, random_state=42)

        #Fit the model
        model.fit(train[features], train[target])

        models[site] = model
        
        #generate predictions 
        prediction = model.predict(test[features])


        #evaluate 
        mean_abs_error = mean_absolute_error(test[target], prediction)

        root_mean_squared_error = np.sqrt(mean_squared_error(test[target], prediction))

        r2 = r2_score(test[target], prediction)


        results[site] = {"mae": mean_abs_error, "rmse": root_mean_squared_error, "r2": r2}

    if save_model_file:
        today_ymd = datetime.today().strftime("%Y-%m-%d")
        joblib.dump(models, f"G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/Models/models {today_ymd}.joblib", compress=3)
        print(f'The model details are saved to G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/Models/models {today_ymd}.joblib')



    return {'models': models, 'results': results}



def generate_feed_forward_forecast(historic_df: pd.DataFrame=[], forward_df: pd.DataFrame=[], models: list[XGBRegressor]=[], features: list[str]=[], save_output=False, save_file=None):
    """
    Generate sequential forecasts using a feed-forward approach with lag and rolling features.
    
    Combines historic and forecast data, then iteratively generates predictions for future dates.
    For each prediction, recalculates lag and rolling features using the accumulated data (including
    previous predictions) to ensure features reflect the full history up to the prediction point.
    
    Parameters
    ----------
    historic_df : pd.DataFrame, optional
        Dataframe containing historical data with actual observations. Must include columns:
        'site', 'datetime', 'hourly_gas_burn_MMBtu', and all feature columns.
        Default is [].
    forward_df : pd.DataFrame, optional
        Dataframe with future dates and feature values to generate forecasts for.
        Must include 'site', 'datetime', and all feature columns. Default is [].
    models : list[XGBRegressor], optional
        Dictionary mapping site identifiers to fitted XGBRegressor model objects.
        Default is [].
    features : list[str], optional
        List of feature column names used as input to the models. Default is [].
    
    Returns
    -------
    pd.DataFrame
        Dataframe with predicted gas burn values containing columns:
        - 'site': Site identifier
        - 'datetime': Prediction datetime
        - 'gasday': Gas day (calculated as datetime minus 10 hours)
        - 'hourly_gas_burn_MMBtu': Predicted hourly gas burn value
    
    Notes
    -----
    Predictions are set to 0 if availability is <= 1 MW.
    Lag and rolling features are recalculated for each prediction to incorporate previous predictions
    in the feature values, enabling truly forward-looking forecasts.
    Uses a windowed approach (up to 336 hours/14 days of recent history) for efficiency.
    """

    predictions_by_site = []
    sites = historic_df['site'].unique()
    forward_dates = forward_df['datetime'].unique()
    full_df = pd.concat([historic_df, forward_df])

    for site in sites:
        site_model = models[site]

        # filter to site and set datetime as the index for quicker look up
        site_full_df = full_df.loc[full_df['site']==site, ['site','datetime','hourly_gas_burn_MMBtu'] + features]
        site_full_df = site_full_df.set_index('datetime')
        site_full_df = site_full_df.sort_index()


        # only looping through future dates
        for date in forward_dates:

            # need to calculate the lag and rolling features each time a new datapoint (i.e. prediction) is added the site_full_df
            # Want to avoid updating the entire dataframe, so going to only update a 'window' of it using only the most recent records that are needed to get rolling/lag values from up to 2 weeks ago
            #site_full_df.to_csv(Path('../data/output-data/site_full_check.csv')) ################## Remove after testing
            current_index = site_full_df.index.get_loc(date)
            start_index = max(0, current_index-336)
            window_df = site_full_df.iloc[start_index: current_index + 1].copy()

            window_df = add_lag_features(window_df)
            window_df = add_rolling_features(window_df)

            # Need to replace the current values with the updated window versions
            for col in features:
                if col in window_df.columns:
                    site_full_df.loc[date, col] = window_df.loc[date, col]


            # Limiting to only the single datetime that is to be predicted. If the availability for that time <1 set forecast to 0
            record_to_predict = site_full_df.loc[[date], features]
            prediction =  0 if record_to_predict['availability_mw'].values <=1 else max(0, site_model.predict(record_to_predict)[0])


            prediction_row = {
                'site': site,
                'datetime': date,
                'gasday': (pd.to_datetime(date)- pd.Timedelta(hours=9)).date(),
                'hourly_gas_burn_MMBtu': prediction 
            }

            # feeding the predicted gas burn back into the site df
            # The predicted value will then be fed forward to calculate the lag and rolling values for the next future time period
            site_full_df.loc[date, 'hourly_gas_burn_MMBtu'] = prediction_row['hourly_gas_burn_MMBtu']
            

            predictions_by_site.append(prediction_row)

    predictions_by_site_df = pd.DataFrame(predictions_by_site)
    predictions_by_site_df['HE'] = 'HE' + (predictions_by_site_df['datetime'] + pd.Timedelta(value=1, unit='h')).dt.strftime('%H')
    predictions_by_site_df['HE'] = np.where(predictions_by_site_df['HE'] == 'HE00', 'HE24', predictions_by_site_df['HE'])
    predictions_by_site_df['date'] = predictions_by_site_df['datetime'].dt.date
    predictions_by_site_df['gasday'] = predictions_by_site_df['gasday'].astype('datetime64[us]')
    predictions_by_site_df['gasday_of_week'] = predictions_by_site_df['gasday'].dt.strftime('%a')
    predictions_by_site_df['effective_day_of_week'] = predictions_by_site_df['datetime'].dt.strftime('%a')
    prediction_by_site_df = predictions_by_site_df.reindex(['site', 'datetime','date', 'effective_day_of_week', 'HE', 'gasday', 'gasday_of_week', 'hourly_gas_burn_MMBtu' ])

    ##################
    ## Confirmation ##
    ##################
    if save_output: 
        file_name = save_file if save_file else f"G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/Forecasts/Hourly Gas Burn by Site Forecasts - {datetime.now().strftime('%Y-%m-%d')}.csv"
        #if not folder.exists():
        #    folder.mkdir(parents=True, exist_ok=True)
        #file_date = datetime.now().date()
        #file_name = folder / f"Hourly Gas Burn by Site Forecasts - {datetime.now().strftime('%Y-%m-%d')}.csv"
        predictions_by_site_df.to_csv(file_name, index=False)
        print(f'A file containing predictions has been saved to {file_name}')

    return predictions_by_site_df
