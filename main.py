from scripts.gather_historic_data import gather_historic_data
from scripts.gather_data_to_forecast import gather_data_to_forecast

def main():
    gather_historic_data(start='2026-08-01', end='2026-08-07', save_output=True)
    gather_data_to_forecast(forecast_start='2026-08-08', forecast_end='2026-08-12', save_output=True)



if __name__ == "__main__":
    main()
