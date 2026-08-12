import os
from scripts.data_pull_functions import login_google_cloud
from scripts.gather_historic_data import gather_historic_data
from scripts.gather_data_to_forecast import gather_data_to_forecast

def main():
    client = login_google_cloud(project_name="bepc-prj-energy-prod")

    lead_columns = ['datetime', 'site', 'year', 'month', 'day', 'hour', 'hour_end', 'day_of_week', 'gas_day', 'hourly_gas_burn_MMBtu', 'daily_gas_burn_MMBtu']

    gather_historic_data(start='2023-01-01', end='2026-08-07', 
                         client=client, lead_columns=lead_columns, 
                         yes_username=os.getenv('YES_USERNAME'), yes_password = os.getenv('YES_PASSWORD'), 
                         save_output=True
                        )
    
    gather_data_to_forecast(forecast_start='2026-07-01', forecast_end='2026-08-12', 
                            yes_username=os.getenv('YES_USERNAME'), yes_password=os.getenv('YES_PASSWORD'), 
                            save_output=True
                            )



if __name__ == "__main__":
    main()