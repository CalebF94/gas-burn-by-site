import os
import pandas as pd
from pathlib import Path
from scripts.constants import NBPL_TEMPLATE, NEXT_DAY_GAS_BURN_TEMPLATE, OUTPUT_DIRS
from scripts.data_pull_functions import login_google_cloud
from scripts.gather_historic_data import gather_historic_data
from scripts.gather_data_to_forecast import gather_data_to_forecast
from scripts.model_training_functions import fit_xgboost_clarissa_version, generate_feed_forward_forecast
from scripts.create_output_functions import create_nbpl_file, create_next_day_gas_burn_file


def validate_env_vars() -> tuple[str, str]:
    """
    Validates that the required credentials for YES Energy API are present in the .env file

    Returns:
        tuple[str, str]: A tuple containing the YES Energy username and password.
    """
    yes_username = os.getenv('YES_USERNAME')
    yes_password = os.getenv('YES_PASSWORD')

    if not yes_username or not yes_username.strip():
        raise RuntimeError("Environment variable YES_USERNAME is missing or empty.")
    if not yes_password or not yes_password.strip():
        raise RuntimeError("Environment variable YES_PASSWORD is missing or empty.")

    return yes_username, yes_password


def validate_runtime_environment() -> None:
    """
    Validates that the runtime environment is correctly set up to run the gas burn forecasting pipeline. Checks for environment variables, required template files, and output directories.
    """
    yes_username, yes_password = validate_env_vars()

    required_paths = {
        'NBPL template': NBPL_TEMPLATE,
        'Next day gas burn template': NEXT_DAY_GAS_BURN_TEMPLATE,
    }

    for label, path in required_paths.items():
        if not path:
            raise RuntimeError(f"{label} path is not defined in scripts.constants.")
        resolved_path = Path(path)
        if not resolved_path.exists():
            raise FileNotFoundError(f"{label} not found at: {resolved_path}")

    required_dirs = [
        Path(OUTPUT_DIRS["Models"]),
        Path(OUTPUT_DIRS["Forecasts"]),
        Path(OUTPUT_DIRS["NBPL Submission Files"]),
        Path(OUTPUT_DIRS["Next Day Gas Burn Files"]),
    ]

    for directory in required_dirs:
        if not directory.exists():
            raise FileNotFoundError(f"Required output directory not found: {directory}")

    if not yes_username or not yes_password:
        raise RuntimeError("YES credentials are not configured.")

    return yes_username, yes_password


def main():
    print('Starting main.py')

    yes_username, yes_password = validate_runtime_environment()


    client = login_google_cloud(project_name="bepc-prj-energy-prod")

    # Use a single date convention throughout the pipeline: ISO 8601 (YYYY-MM-DD)
    # This avoids mixed MM-DD-YYYY and YYYY-MM-DD strings being compared against pandas datetimes.
    today = pd.Timestamp.today().normalize()
    today_ymd = today.strftime("%Y-%m-%d")
    test_start_date = (today - pd.Timedelta(days=8)).strftime("%Y-%m-%d")
    forecast_horizon_ymd = (today + pd.Timedelta(days=9)).strftime("%Y-%m-%d")
    nbpl_date_ymd = (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    lead_columns = ['datetime', 'site', 'year', 'month', 'day', 'hour', 'hour_end', 'day_of_week', 'gas_day', 'hourly_gas_burn_MMBtu', 'daily_gas_burn_MMBtu']


    model_df = gather_historic_data(
        start='2023-01-01', 
        end=today_ymd, #Exclusive end so date specified will not be included. For most purposes end should be today's date
        client=client, 
        lead_columns=lead_columns, 
        yes_username=yes_username,
        yes_password=yes_password,
        save_output=True
    )

    
    
    forward_df = gather_data_to_forecast(
        forecast_start=today_ymd,
        forecast_end=forecast_horizon_ymd,  # Exclusive end so date specified will not be included.
        yes_username=yes_username,
        yes_password=yes_password,
        save_output=True
    )


    # feel like this should be declared elsewhere
    features = ["availability_mw", "load_forecast", "net_load_forecast", "wind_forecast", "temperature_forecast", "wind_speed_forecast", "total_offline_forecast", 
           "offline_ng_forecast", "offline_coal_forecast", "hour", "day_of_week", "month", "gas_lag_1", "gas_lag_24", "gas_lag_168", "gas_roll_24", "gas_roll_168"]


    # test_start_date is just 8 days ago from today's date
    fit_results = fit_xgboost_clarissa_version(
        model_df,
        sites=model_df['site'].unique(),
        test_start_date=test_start_date,
        features=features,
        target=['hourly_gas_burn_MMBtu'],
        save_model_file = OUTPUT_DIRS["Models"] + f"/models {today_ymd}.joblib"
    )


    predictions = generate_feed_forward_forecast(
        historic_df=model_df, 
        forward_df=forward_df, 
        models=fit_results['models'], 
        features=features, 
        save_output=True, 
        save_file=OUTPUT_DIRS["Forecasts"] + f"/Hourly Gas Burn by Site Forecasts {today_ymd}.csv"
    )

    
    # file_date is typically tomorrow's date
    create_nbpl_file(
        predictions=predictions,
        template_file=NBPL_TEMPLATE,
        file_date=nbpl_date_ymd,
        save_file=OUTPUT_DIRS["NBPL Submission Files"] + f"/NBPL Forecast {today_ymd}.xlsm"
    )

    create_next_day_gas_burn_file(
        predictions=predictions, 
        template_file=NEXT_DAY_GAS_BURN_TEMPLATE, 
        save_file=OUTPUT_DIRS["Next Day Gas Burn Files"] + f"/Next Day Gas Burn {today_ymd}.xlsx"
    )



if __name__ == "__main__":
    main()