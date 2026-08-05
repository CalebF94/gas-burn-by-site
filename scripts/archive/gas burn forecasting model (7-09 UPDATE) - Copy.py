
#importing the libraries needed
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from datetime import timedelta
import os
from pathlib import Path
from sklearn.metrics import mean_squared_error
from mssql_python import connect
from nbdevAuto.functions import * 
import nbdevAuto.functions
import time 





#to make sure the variables for the api are on the local os  
YES_USER = os.getenv("YES_USER")
YES_PASS = os.getenv("YES_PASS")

print("YES_USER loaded:", YES_USER is not None)
print("YES_PASS loaded:", YES_PASS is not None)





# DB connection
SQL_CONNECTION_STRING = ( "Server=HDQv1958;" "Database=allegro;" "Trusted_Connection=yes;" "Encrypt=yes;" "TrustServerCertificate=yes;")

conn = connect(SQL_CONNECTION_STRING)




def load_burn():

    query = """
SELECT t.trade, p.marketarea, q.begtime, q.energy, q.quantitystatus

FROM trade t, position p, ngquantity q

WHERE p.bepc_strategy = 'Burn' and t.trade = p.trade and t.tradestatus <> 'Void' and p.position = q.position and q.posstatus = 1
AND q.begtime >= DATEADD(year, -2, GETDATE()) AND q.begtime <= GETDATE()

ORDER BY q.begtime"""

    df = pd.read_sql(query, conn)
    #df["datetime"] = pd.to_datetime(df["datetime"])

    return df[["begtime", "marketarea", "energy"]]

gas_daily_df = load_burn()






#defining market areas as sites
gas_daily_df["marketarea"] = gas_daily_df["marketarea"].str.upper().str.strip()

gas_daily_df = gas_daily_df[
    ~gas_daily_df["marketarea"].isin(["BISON", "COTTAGE GROVE"])]

site_map = {"DEER CREEK": "DCS", "LANARK": "CGS", "LONSOME CREEK": "LCS",  "STATELINE": "PGS", "GROTON": "GGS", "CULBERTSON": "CGS"}

gas_daily_df["site"] = gas_daily_df["marketarea"].replace(site_map)



# create gas day

gas_daily_df["gas_day"] = pd.to_datetime(gas_daily_df["begtime"])
gas_daily_df["gas_day"] = (gas_daily_df["gas_day"] - pd.Timedelta(hours=9)).dt.date


# aggregate on gas_day 
gas_daily_site = (gas_daily_df.groupby(["gas_day", "site"], as_index=False)["energy"].sum().rename(columns={"energy": "daily_gas_burn"}))

############### CheckPoint 1 (the above information) ###############

gas_daily_site.to_csv(r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Data Checks (csv numbered)\checkpoint1.csv", index=False)






def load_generation_nonpgs():

    query = """
    SELECT begtime, loadshape, he1, he2, he3, he4, he5, he6, he7, he8, he9, he10, he11, he12, he13, he14, he15, he16, he17, he18, he19, he20, he21, he22, he23, he24
    FROM dbo.loadshapeprofile
    WHERE begtime >= DATEADD(year, -3, GETDATE()) AND begtime <= GETDATE()
      AND loadshape IN ('WAUE.BEPM.DCS1 - Net Generation',
        'WAUE.BEPM.LCS1 - Net Generation', 'WAUE.BEPM.LCS2 - Net Generation', 'WAUE.BEPM.LCS3 - Net Generation', 'WAUE.BEPM.LCS4 - Net Generation', 'WAUE.BEPM.LCS5 - Net Generation',
        'WAUE.BEPM.LCS6 - Net Generation', 'WAUE.BEPM.GGS1 - Net Generation', 'WAUE.BEPM.GGS2 - Net Generation', 'WAUE.BEPM.CULBERTSON1 - Net Generation')
    """

    return pd.read_sql(query, conn)

df_nonpgs = load_generation_nonpgs()

############### CheckPoint 2 (the above information) ###############

df_nonpgs.to_csv(r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Data Checks (csv numbered)\checkpoint2.csv", index=False)






def load_generation_pgs():

    query = """SELECT begtime, loadshape, SUM(he1)  AS he1, SUM(he2)  AS he2, SUM(he3)  AS he3, SUM(he4)  AS he4, SUM(he5)  AS he5, SUM(he6)  AS he6, SUM(he7)  AS he7,
    SUM(he8)  AS he8, SUM(he9)  AS he9, SUM(he10) AS he10, SUM(he11) AS he11, SUM(he12) AS he12, SUM(he13) AS he13, SUM(he14) AS he14, SUM(he15) AS he15, SUM(he16) AS he16,
    SUM(he17) AS he17, SUM(he18) AS he18, SUM(he19) AS he19, SUM(he20) AS he20, SUM(he21) AS he21, SUM(he22) AS he22, SUM(he23) AS he23, SUM(he24) AS he24

    FROM dbo.loadshapeprofile

    WHERE loadshape LIKE '%PGS%' AND loadshape LIKE '%- Net Generation-5m' AND begtime >= DATEADD(year, -2, GETDATE()) AND begtime <= GETDATE()

    GROUP BY begtime, loadshape

    ORDER BY begtime;"""

    return pd.read_sql(query, conn)

df_pgs = load_generation_pgs()

############### CheckPoint 3 (the above information) ###############
df_pgs.to_csv(r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Data Checks (csv numbered)\checkpoint3.csv", index=False)






#combining pgs with other gen sites because pgs is measured differently


df_load_generation = pd.concat([df_nonpgs, df_pgs], ignore_index=True)

##################################### CHECKPOINT 4 ( the above information) ######################################################
df_load_generation.to_csv(r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Data Checks (csv numbered)\checkpoint4.csv", index=False)


# convert date using begtime
df_load_generation["begtime"] = pd.to_datetime(df_load_generation["begtime"])
df_load_generation["date"] = df_load_generation["begtime"].dt.date


# map site
df_load_generation["site"] = "N/A"
df_load_generation.loc[df_load_generation["loadshape"].str.contains("DCS"), "site"] = "DCS"
df_load_generation.loc[df_load_generation["loadshape"].str.contains("LCS"), "site"] = "LCS"
df_load_generation.loc[df_load_generation["loadshape"].str.contains("PGS"), "site"] = "PGS"
df_load_generation.loc[df_load_generation["loadshape"].str.contains("GGS"), "site"] = "GGS"
df_load_generation.loc[df_load_generation["loadshape"].str.contains("CULBERTSON"), "site"] = "CGS"

##################################### CHECKPOINT 5 ( the above information) ######################################################
df_load_generation.to_csv(r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Data Checks (csv numbered)\checkpoint5.csv", index=False)









# melt function instead of unpivot
# melt
hour_cols = [column for column in df_load_generation.columns if column.startswith("he")]

hourly_df = df_load_generation.melt(id_vars=["begtime", "site"], value_vars=hour_cols, var_name="hour", value_name="hourly_mw")

############### CheckPoint 6 (the above information) ###############

hourly_df.to_csv(r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Data Checks (csv numbered)\checkpoint6.csv", index=False)











#so not zero but not null?????????
#replace with previous value (use lag function)
# remove impossible generation spikes
hourly_df.loc[hourly_df["hourly_mw"] > 2000, "hourly_mw"] = -9999 
hourly_df.to_csv(r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Data Checks (csv numbered)\checkpoint7.csv", index=False)




# extract hour_num 
hourly_df["hour_num"] = hourly_df["hour"].str.extract(r"(\d+)").astype(int)

# build datetime
hourly_df["datetime"] = (pd.to_datetime(hourly_df["begtime"]) + pd.to_timedelta(hourly_df["hour_num"] - 0, unit="h"))


#collapse duplicates   # check if duplicates exist
hourly_df = (hourly_df.groupby(["datetime", "site"], as_index=False)["hourly_mw"].sum())
############### CheckPoint 7 (the above information) ###############

hourly_df.to_csv(r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Data Checks (csv numbered)\checkpoint7.csv", index=False)





##check this
# assign gas_day 
hourly_df["gas_day"] = (pd.to_datetime(hourly_df["datetime"]) - pd.Timedelta(hours=9)).dt.date

# extract hour #
hourly_df["hour"] = hourly_df["datetime"].dt.hour

hourly_df.to_csv(r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Data Checks (csv numbered)\checkpoint8.csv", index=False)




# build gas_day grid
gas_days = hourly_df["gas_day"].unique()
sites = hourly_df["site"].unique()
hours = np.arange(24)



full_grid = pd.MultiIndex.from_product( [gas_days, sites, hours], names=["gas_day", "site", "hour"])

hourly_df.to_csv(r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Data Checks (csv numbered)\checkpoint9.csv", index=False)






#this is where the code breaks down 
# apply grid
hourly_df = hourly_df[["datetime","gas_day", "hour", "site", "hourly_mw"]]

hourly_df.to_csv(r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Data Checks (csv numbered)\checkpoint10.csv", index=False)



# # DO NOT blindly zero-fill — use median by site/hour
# hourly_df["hourly_mw"] = hourly_df.groupby(["site", "hour"])["hourly_mw"].transform(lambda x: x.fillna(x.median()))

# # rebuild datetime from gas_day + hour
# hourly_df["datetime"] = (pd.to_datetime(hourly_df["gas_day"]) + pd.Timedelta(hours=9) + pd.to_timedelta(hourly_df["hour"], unit="h"))



# #daily total by site
# daily_site_gen = ( hourly_df.groupby(["gas_day","site"])["hourly_mw"].sum().reset_index())





# # merge df
# merged = merged.merge(daily_site_gen, on=["gas_day","site"], how="left")

# merged = merged.merge( gas_daily_site, on=["gas_day","site"], how="left")

# # not dividing by 0
# merged["daily_site_gen_mw"] = merged["daily_site_gen_mw"].replace(0, np.nan)


# merged["hourly_gas_burn"] = (merged["daily_gas_burn"] * merged["hourly_mw"] / merged["daily_site_gen_mw"])



# # final output of allegro data
# result_df = merged[[ "datetime", "gas_day", "site", "hourly_mw",  "daily_site_gen_mw", "daily_gas_burn", "hourly_gas_burn"]]


# #math for daily MMBtu per MWh
# result_df["gas_per_mw"] = (result_df["daily_gas_burn"] / result_df["daily_site_gen_mw"])




# # #confirmations
# # # should be 24 rows per gas_day per site
# check = result_df.groupby(["gas_day", "site"]).size()



# #Look into gen mw
# #pull in daily mmbtu from allegro(valuation table) 

# df_hr = hourly_df.copy()
# df_hr["datetime"] = pd.to_datetime(df_hr["datetime"])

# ### ensure shifting time stamp not inputting 0s after 
# df_hr["gas_day"] = (df_hr["datetime"] - pd.Timedelta(hours=9)).dt.date


# df_hr["daily_mw"] = (df_hr.groupby("gas_day")["hourly_mw"].transform("sum"))
# df_hr["daily_mw"] = df_hr["daily_mw"].replace(0, pd.NA)





# output_df = result_df.copy()

# # add date if you want calendar date separate from gas_day
# output_df["date"] = pd.to_datetime(output_df["datetime"]).dt.date

# output_df = output_df[[ "datetime", "gas_day", "date", "site", "daily_site_gen_mw", "hourly_mw", "daily_gas_burn", "hourly_gas_burn", "gas_per_mw"]]




# export_df = result_df.copy()

# export_df["date"] = export_df["datetime"].dt.date

# export_df["gas_per_mw"] = (export_df["daily_gas_burn"] / export_df["daily_site_gen_mw"]).replace([np.inf, - np.inf], np.nan)

# export_df = export_df[["datetime", "date", "gas_day", "site", "hourly_mw", "daily_site_gen_mw", "daily_gas_burn", "hourly_gas_burn", "gas_per_mw"]]
# export_df = export_df.sort_values(["site", "gas_day", "datetime"])

# export_df.to_csv( "hourly_gas_allocation.csv", index=False)




# #filter out major outliers
# # remove tiny generation days
# result_df = result_df[result_df["daily_site_gen_mw"] >= 50]


# result_df["daily_gas_burn"] = result_df.groupby( ["site", result_df["datetime"].dt.dayofweek])["daily_gas_burn"].transform(lambda x: x.fillna(x.median()))

# # copy df
# plot_df = export_df.copy()

# # ensuring data quality
# # 1. require meaningful generation (removes outages / partial days)
# plot_df = plot_df[plot_df["daily_site_gen_mw"] >= 100]

# # require gas exists
# plot_df = plot_df[plot_df["daily_gas_burn"].notna()]

# # recompute ratio 
# plot_df["gas_per_mw"] = (plot_df["daily_gas_burn"] / plot_df["daily_site_gen_mw"])

# # remove unrealistic values
# plot_df = plot_df[(plot_df["gas_per_mw"] >= 5) & (plot_df["gas_per_mw"] <= 20)]

# # site order
# site_order = (plot_df.groupby("site")["gas_per_mw"].median().sort_values().index)




# #factoring out the outliers
# outliers = export_df[ (export_df["gas_per_mw"] > 20) | (export_df["gas_per_mw"] < 5)]




# #debugging
# debug = export_df[[ "site", "gas_day", "daily_site_gen_mw", "daily_gas_burn", "gas_per_mw"]]

# debug = debug.sort_values("gas_per_mw", ascending=False)






# clean_df = export_df[
#     (export_df["daily_site_gen_mw"] > 300) & (export_df["gas_per_mw"] > 5) & (export_df["gas_per_mw"] < 20)]



# export_df["gas_per_mw"] = pd.to_numeric(export_df["gas_per_mw"], errors="coerce")











# #Results for hourly gas burns here
# result_df = merged[["datetime", "gas_day", "site", "daily_site_gen_mw", "hourly_mw", "daily_gas_burn", "hourly_gas_burn"]]









# # Defining the function
# # File lists (OUTSIDE function)

# excel_files = [
#     r"G:\Trading\Market Operations\Unit availability\2026\RT Unit availability 07.26.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2026\RT Unit availability 06.26.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2026\RT Unit availability 05.26.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2026\RT Unit availability 04.26.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2026\RT Unit availability 03.26.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2026\RT Unit availability 02.26.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2026\RT Unit availability 01.26.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2025\RT Unit availability 12.25.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2025\RT Unit availability 11.25.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2025\RT Unit availability 10.25.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2025\RT Unit availability 09.25.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2025\RT Unit availability 08.25.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2025\RT Unit availability 07.25.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2025\RT Unit availability 06.25.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2025\RT Unit availability 05.25 - UPDATE.xlsx",
#     r"G:\Trading\Market Operations\Unit availability\2025\RT Unit availability 04.25 - UPDATE.xlsx"]

# csv_files = [
#     r"G:\Trading\Market Operations\Unit availability\2025\dpm_BEPC_GROUPING_2025030100_2025033123 - March.csv",
#     r"G:\Trading\Market Operations\Unit availability\2025\transposed_dpm_BEPC_GROUPING_2025020100_2025022823 feb.csv",
#     r"G:\Trading\Market Operations\Unit availability\2025\transposed_dpm_BEPC_GROUPING_2025010100_2025013123.csv",
#     r"G:\Trading\Market Operations\Unit availability\2024\dpm_BEPC_GROUPING_2024120100_2024123123.csv",
#     r"G:\Trading\Market Operations\Unit availability\2024\dpm_BEPC_GROUPING_2024110100_2024113023.csv",
#     r"G:\Trading\Market Operations\Unit availability\2024\dpm_BEPC_GROUPING_2024100100_2024103123.csv",
#     r"G:\Trading\Market Operations\Unit availability\2024\dpm_BEPC_GROUPING_2024090100_2024093023.csv",
#     r"G:\Trading\Market Operations\Unit availability\2024\dpm_BEPC_GROUPING_2024080100_2024083123.csv",
#     r"G:\Trading\Market Operations\Unit availability\2024\dpm_BEPC_GROUPING_2024070100_2024073123.csv",
#     r"G:\Trading\Market Operations\Unit availability\2024\dpm_BEPC_GROUPING_2024060100_2024063023.csv",
#     r"G:\Trading\Market Operations\Unit availability\2024\dpm_BEPC_GROUPING_2024050100_2024053123.csv"]





# def pull_unit_availability(excel_files, csv_files):

#     # Excel
#     excel_dfs = []
#     for file in excel_files:
#         df = pd.read_excel(file, sheet_name="Gas HEL Transposed")
#         df["source_file"] = file
#         excel_dfs.append(df)

#     excel_combined = pd.concat(excel_dfs, ignore_index=True)

#     # CSV
#     csv_dfs = []
#     for file in csv_files:
#         df = pd.read_csv(file)
#         df["source_file"] = file
#         csv_dfs.append(df)

#     csv_combined = pd.concat(csv_dfs, ignore_index=True)

#     # Combine + defragment
#     combined_df = pd.concat([excel_combined, csv_combined], ignore_index=True)
#     combined_df = combined_df.copy() 

#     return combined_df





# # Calling the function

# df = pull_unit_availability(excel_files, csv_files)



# df = df.copy()





# #merging excel files to sql/allegro sources

# df = df.rename(columns={"DateTime": "datetime"})
# # force everything to string first, then parse
# df["datetime"] = pd.to_datetime(df["datetime"].astype(str), errors="coerce") 

# df = df.dropna(subset=["datetime"])




# # clean columns
# df.columns = df.columns.astype(str)  # <-- FIX HERE
# df.columns = df.columns.str.strip().str.replace(r"\s+", " ", regex=True)

# # datetime fix
# df = df.rename(columns={"DateTime": "datetime"})
# df["datetime"] = pd.to_datetime(df["datetime"].astype(str), errors="coerce")
# df = df.dropna(subset=["datetime"])

# #define value columns 
# value_cols = [col for col in df.columns if isinstance(col, str) and "High Effective" in col]



# # melt
# avail_long = df.melt(id_vars=["datetime"], value_vars=value_cols, var_name="unit", value_name="availability_mw")

# # extract site
# avail_long["site"] = avail_long["unit"].str.extract(r"^(CGS|DCS|GGS|LCS|PGS)")
# avail_long["site"] = avail_long["site"].str.strip().str.upper()

# # aggregate to site
# avail_site = (avail_long.groupby(["datetime", "site"], as_index=False)["availability_mw"].sum())

# # merge
# master_df = result_df.copy()

# master_df = master_df.merge(avail_site, on=["datetime", "site"], how="left")





# avail_df = master_df[master_df["availability_mw"].notna()]

# master_df["utilization"] = (master_df["hourly_mw"] / master_df["availability_mw"])

# master_df["utilization"] = master_df["utilization"].replace([np.inf, -np.inf], np.nan)








# master_df.loc[master_df["daily_site_gen_mw"].isna(), "hourly_mw"] = np.nan





# #cleaning out major outliers
# master_df.loc[master_df["hourly_mw"] > 1500, "hourly_mw"] = np.nan




# #api
# def load_unit_availability_by_site():
#     df = pull_unit_availability(excel_files, csv_files)

#     # Force column names to strings and strip whitespace
#     df.columns = df.columns.map(lambda x: str(x).strip())

#     df = df.rename(columns={"DateTime": "datetime"})

#     # force datetime to a single type
#     df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

#     # Only keep HEL columns
#     hel_cols = [c for c in df.columns if "High Effective Limit" in c]

#     df[hel_cols] = df[hel_cols].apply(pd.to_numeric, errors="coerce")

#     df_long = df.melt(id_vars="datetime", value_vars=hel_cols, var_name="unit", value_name="avail_mw")

#     df_long["site"] = df_long["unit"].str.extract(r"^([A-Z]+)")

#     availability_by_site = (df_long.groupby(["datetime", "site"], as_index=False).agg({"avail_mw": "sum"}))

#     return availability_by_site

# site_df = load_unit_availability_by_site()




# master_df = master_df.drop_duplicates(["datetime", "site"])






# master_df = master_df.drop_duplicates(["datetime", "site"])

# def pull_yes_forecast_historical(user, password, start_date, end_date):

#     start = pd.to_datetime(start_date)
#     end = pd.to_datetime(end_date)

#     dfs = []

#     while start <= end:

#         month_start = start.replace(day=1)
#         month_end = month_start + pd.offsets.MonthEnd(1)

#         if month_end > end:
#             month_end = end

#         print(f"Pulling forecast: {month_start.date()} → {month_end.date()}")

#         url = (
#             "https://services.yesenergy.com/PS/rest/timeseries/multiple.json"
#             "?agglevel=hour"
#             "&timezone=CPT"
#             f"&startdate={month_start.date()}"
#             f"&enddate={month_end.date()}"
#             "&items="
#             "LOAD_FORECAST:10017060648,"
#             "NET_LOAD_FORECAST_CURRENT:10017060648,"
#             "NG_CAPACITY_OFFLINE:10017060648,"
#             "COAL_CAPACITY_OFFLINE:10017060648,"
#             "WINDFCST_HOURLY:10004185377,"
#             "WINDFCST_HOURLY:10004185378,"
#             "WINDFCST_HOURLY:10004185379,"
#             "WINDFCST_HOURLY:10004185380,"
#             "WINDFCST_HOURLY:10004185381,"
#             "WSI_FC15_FEEL:10000355230,"
#             "WSI_FC15_FEEL:10000355704,"
#             "WSI_FC15_FEEL:10000356081,"
#             "WSI_FC15_WIND:10000355230,"
#             "WSI_FC15_WIND:10000355704" )

#         # retry block in case the api crashes
#         for attempt in range(3):
#             try:
#                 resp = requests.get(url, auth=(user, password), verify=False, timeout=120)
#                 resp.raise_for_status()
#                 break

#             except requests.exceptions.RequestException as e:
#                 print(f"Retry {attempt+1}/3 failed: {e}")
#                 time.sleep(5)

#                 if attempt == 2:
#                     raise e

#         # processing after successful data pull
#         df_chunk = pd.DataFrame(resp.json())
#         print(
#     month_start.date(),
#     month_end.date(),
#     len(df_chunk)
# )
#         df_chunk.columns = df_chunk.columns.map(lambda x: str(x).strip())

#         dfs.append(df_chunk)

#         time.sleep(6)  

#         start = month_end + timedelta(days=1)

#     return pd.concat(dfs, ignore_index=True)


# #call the API
# df_forecast_raw = pull_yes_forecast_historical( YES_USER, YES_PASS, start_date="2024-06-01", end_date = pd.to_datetime(result_df["datetime"]).max().date())



# def clean_yes_forecast(df):

#     df = df.copy()

#     # find datetime column
#     datetime_col = [c for c in df.columns if "DATETIME" in c.upper()][0]

#     df["datetime"] = pd.to_datetime(df[datetime_col], format="%m/%d/%Y %H:%M:%S", errors="coerce")

#     # --- load ---
#     df["load"] = pd.to_numeric( df["SPPISO-East (LOAD_FORECAST)"], errors="coerce")

#     # --- net load ---
#     df["net_load"] = pd.to_numeric(df["SPPISO-East (NET_LOAD_FORECAST_CURRENT)"], errors="coerce")

#     # --- wind ---
#     wind_cols = [c for c in df.columns if "WINDFCST_HOURLY" in c]
#     df["wind"] = df[wind_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)

#     # --- outages ---
#     df["outage_ng"] = pd.to_numeric(df["SPPISO-East (NG_CAPACITY_OFFLINE)"], errors="coerce")

#     df["outage_coal"] = pd.to_numeric(df["SPPISO-East (COAL_CAPACITY_OFFLINE)"], errors="coerce")

#     # --- temperature ---
#     temp_cols = [c for c in df.columns if "WSI_FC15_FEEL" in c]
#     df["temperature"] = df[temp_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)

#     # --- wind speed ---
#     wind_speed_cols = [c for c in df.columns if "WSI_FC15_WIND" in c]
#     df["wind_speed"] = df[wind_speed_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)

#     # --- derived ---
#     df["total_outages"] = df["outage_ng"] + df["outage_coal"]

#     out = df[["datetime", "load", "net_load", "wind", "temperature", "wind_speed", "total_outages"]].dropna(subset=["datetime"])

#     return out.sort_values("datetime").reset_index(drop=True)

# #now clean
# df_forecast_clean = clean_yes_forecast(df_forecast_raw)






# cols_to_drop = [c for c in master_df.columns if c.endswith("_forecast")]

# master_df = master_df.drop(columns=cols_to_drop, errors="ignore")

# #merge data to master df
# master_df = master_df.merge(df_forecast_clean, on="datetime", how="left", suffixes=("", "_forecast"))





# def pull_yes_actual_historical(user, password, start_date, end_date):

#     start = pd.to_datetime(start_date)
#     end = pd.to_datetime(end_date)

#     dfs = []

#     while start <= end:

#         month_start = start.replace(day=1)
#         month_end = month_start + pd.offsets.MonthEnd(1)

#         if month_end > end:
#             month_end = end

#         print(f"Pulling actuals: {month_start.date()} → {month_end.date()}")

#         url = (
#             "https://services.yesenergy.com/PS/rest/timeseries/multiple.json"
#             "?agglevel=hour"
#             "&timezone=CPT"
#             f"&startdate={month_start.date()}"
#             f"&enddate={month_end.date()}"
#             "&items="
#             #What day ahead close so just in actual
#             "BIDCLOSE_LOAD_FORECAST:10017060648,"
#             "NET_LOAD_FORECAST_BID_CLOSE:10017060648,"
#             "NG_CAPACITY_OFFLINE:10017060648,"
#             "COAL_CAPACITY_OFFLINE:10017060648,"
#             "WINDGEN_HOURLY:10004185377,"
#             "WINDGEN_HOURLY:10004185378,"
#             "WINDGEN_HOURLY:10004185379,"
#             "WINDGEN_HOURLY:10004185380,"
#             "WINDGEN_HOURLY:10004185381,"
#             "WSI_TRADER_FEELS_TEMP:10000355230,"
#             "WSI_TRADER_FEELS_TEMP:10000355704,"
#             "WSI_TRADER_FEELS_TEMP:10000356081,"
#             "WSI_TRADER_WIND:10000355230,"
#             "WSI_TRADER_WIND:10000355704")

#         for attempt in range(3):
#             try:
#                 resp = requests.get(url, auth=(user, password), verify=False, timeout=120)
#                 resp.raise_for_status()
#                 break

#             except requests.exceptions.RequestException as e:
#                 print(f"Retry {attempt+1}/3 failed: {e}")
#                 time.sleep(6)

#             if attempt == 2:
#                 raise e
            
            
#         df_chunk = pd.DataFrame(resp.json())
#         df_chunk.columns = df_chunk.columns.map(lambda x: str(x).strip())

#         dfs.append(df_chunk)
        
#         time.sleep(1)  

#         start = month_end + timedelta(days=1)

#     return pd.concat(dfs, ignore_index=True)




# def clean_yes_actual(df):
#     """
#     Clean YES Energy ACTUAL data into analysis-ready format.
#     """

#     df = df.copy()

#     datetime_col = [c for c in df.columns if "DATETIME" in c.upper()][0]

#     df["datetime"] = pd.to_datetime( df[datetime_col], errors="coerce")


#     # load actual
#     df["load_actual"] = pd.to_numeric(df["SPPISO-East (BIDCLOSE_LOAD_FORECAST)"], errors="coerce")

#     # net load actual
#     df["net_load_actual"] = pd.to_numeric( df["SPPISO-East (NET_LOAD_FORECAST_BID_CLOSE)"], errors="coerce")

#     # wind actual
#     wind_cols = [c for c in df.columns if "WINDGEN_HOURLY" in c]
#     wind_numeric = (df[wind_cols].apply(pd.to_numeric, errors="coerce"))
#     print(
#     wind_numeric.loc[
#         df["datetime"].between(
#             "2026-07-15 06:00:00",
#             "2026-07-16 08:00:00"
#         )
#     ]
# )

#     wind_sum = wind_numeric.sum(axis=1, min_count=1)

#     all_zero = (wind_numeric.fillna(0).sum(axis=1).eq(0))

#     df["wind_actual"] = wind_sum.mask(all_zero)

#     # outage actual
#     df["outage_ng"] = pd.to_numeric(df["SPPISO-East (NG_CAPACITY_OFFLINE)"], errors="coerce")
#     df["outage_coal"] = pd.to_numeric( df["SPPISO-East (COAL_CAPACITY_OFFLINE)"], errors="coerce")

#     # temperature actual
#     temp_cols = [c for c in df.columns if "WSI_TRADER_FEELS_TEMP" in c]
#     temp_numeric = (df[temp_cols].apply(pd.to_numeric, errors="coerce"))

#     temp_avg = temp_numeric.mean(axis=1)

#     all_zero_temp = (temp_numeric.fillna(0).sum(axis=1).eq(0))

#     df["temperature_actual"] = temp_avg.mask(all_zero_temp)

#     # windspeed actual
#     wind_speed_cols = [c for c in df.columns if "WSI_TRADER_WIND" in c]
#     df["wind_speed_actual"] = df[wind_speed_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)
    
    
    

    
    
    
#     # tot outage
#     df["total_outages"] = df["outage_ng"] + df["outage_coal"]

#     out = df[["datetime", "load_actual", "net_load_actual", "wind_actual", "temperature_actual", "wind_speed_actual", "total_outages"]].dropna(subset=["datetime"])

#     return out.sort_values("datetime").reset_index(drop=True)

# #call the API
# df_actual_raw = pull_yes_actual_historical( YES_USER, YES_PASS, start_date="2024-06-01", end_date = pd.to_datetime(result_df["datetime"]).max().date())
# if "error" in df_actual_raw.columns:
#     df_actual_raw = df_actual_raw[df_actual_raw["error"].isna()].copy()




# #now clean
# df_actual_clean = clean_yes_actual(df_actual_raw)




# datetime_col = [
#     c for c in df_actual_raw.columns
#     if "DATETIME" in c.upper()
# ][0]

# cols_to_drop = [c for c in master_df.columns if c.endswith("_actual")]

# master_df = master_df.drop(columns=cols_to_drop, errors="ignore")


# #merge data to master df
# master_df = master_df.merge(df_actual_clean, on="datetime", how="left", suffixes=("", "_actual"))
# master_df = master_df.drop_duplicates(["datetime", "site"])









# master_df["gas_per_mw"] = ( master_df["hourly_gas_burn"] / master_df["hourly_mw"])

# master_df["gas_per_mw"] = master_df["gas_per_mw"].replace([np.inf, -np.inf], np.nan)






# master_df["load_final"] = master_df["load_actual"].fillna(master_df["load"])
# master_df["wind_final"] = master_df["wind_actual"].fillna(master_df["wind"])
# master_df["temperature_final"] = master_df["temperature_actual"].fillna(master_df["temperature"])






# #clean and prep
# master_df["hourly_gas_burn"] = pd.to_numeric(master_df["hourly_gas_burn"], errors="coerce")

# # remove fake zeros (look into this)
# master_df.loc[ master_df["hourly_gas_burn"] == 0, "hourly_gas_burn"] = np.nan

# master_df = master_df.sort_values(["site", "datetime"])





# #adding time features

# master_df["hour"] = master_df["datetime"].dt.hour
# master_df["day_of_week"] = master_df["datetime"].dt.dayofweek
# master_df["month"] = master_df["datetime"].dt.month








# #adding lag features

# master_df["gas_lag_1"] = master_df.groupby("site")["hourly_gas_burn"].shift(1)

# master_df["gas_lag_24"] = master_df.groupby("site")["hourly_gas_burn"].shift(24)

# master_df["gas_roll_24"] = master_df.groupby("site")["hourly_gas_burn"].transform(lambda x: x.shift(1).rolling(24).mean())








# ## data set for model training

# model_df = master_df.copy()

# model_df = model_df.dropna(subset=["hourly_gas_burn", "gas_lag_1", "gas_lag_24", "gas_roll_24"])

# model_df.to_csv(r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Training Datasets\Model Input Data YES Forecast Added and shift update.csv", index=False)

# print(model_df.shape)



# #final dataset
# model_df = master_df.copy()



# model_df = model_df.dropna(subset=[ "hourly_gas_burn", "gas_lag_1", "gas_lag_24", "gas_roll_24"])
# model_df = model_df.sort_values(["site", "datetime"])


# model_export = model_df.copy()

# model_export = model_export.sort_values(  ["site", "datetime"])

# model_export.to_csv( r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\MASTER_MERGED_DATA.csv", index=False)

# print("Exported MODEL_INPUT_DATA.csv")
# print("Rows:", len(model_export))
# print("Columns:", len(model_export.columns))


# print("\n===== FINAL MODEL SUMMARY =====")

# print(model_df.groupby("site").size())

# print("\nMissing Values")
# print(model_df[[ "hourly_gas_burn", "availability_mw", "utilization", "gas_lag_1", "gas_lag_24", "gas_roll_24" ]].isna().sum())

# print("\nGas Per MW")
# print(model_df.groupby("site")["gas_per_mw"].describe())

# model_df["availability_mw"] = model_df.groupby("site")["availability_mw"].transform( lambda x: x.fillna(x.median()))




# #listing the features
# features = ["load_final", "wind_final", "temperature_final", "availability_mw", "utilization", "hour", "day_of_week", "month", "gas_lag_1", "gas_lag_24", "gas_roll_24"]



# #train models per site
# from xgboost import XGBRegressor
# from sklearn.metrics import mean_absolute_error

# models = {}
# results = {}

# split_date = "2025-01-01"

# for site in model_df["site"].unique():

#     print(f"\nTraining model for: {site}")

#     site_df = model_df[model_df["site"] == site].sort_values("datetime")

#     split_idx = int(len(site_df) * 0.8)

#     train = site_df.iloc[:split_idx]
#     test  = site_df.iloc[split_idx:]


#     print(site, "train:", len(train), "test:", len(test))
    
    
    
    
    
    


#     X_train = train[features]
#     y_train = train["hourly_gas_burn"]

#     X_test = test[features]
#     y_test = test["hourly_gas_burn"]

#     model = XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.05, random_state=42)

#     model.fit(X_train, y_train)

#     preds = model.predict(X_test)
#     mae = mean_absolute_error(y_test, preds)

#     print(f"{site} MAE:", mae)

#     models[site] = model
#     results[site] = mae

# # back test validation of the forecast model 

# for site in models:
#     site_df = model_df[model_df["site"] == site]
#     preds = models[site].predict(site_df[features])
    
#     mae = mean_absolute_error(site_df["hourly_gas_burn"], preds)
#     print(f"{site} Backtest MAE:", mae)
    
    
    
# # feature /drivers
# for site in models:
#     importances = pd.Series(models[site].feature_importances_, index=features).sort_values(ascending=False)

#     print(f"\nTop drivers for {site}")
#     print(importances.head(10))



# print("Rows in master_df:", len(master_df))
# print("Rows in model_df:", len(model_df))
# print("Unique sites:", model_df["site"].unique())



# #create future timestamp

# horizon = 168

# now = pd.Timestamp.now()

# forecast_start = ((now - pd.Timedelta(hours=9)).normalize() + pd.Timedelta(hours=9))

# future_dates = pd.date_range(start=forecast_start, periods=horizon, freq="h")



# #ADD in forward looking data
# #build future_df 

# sites = model_df["site"].unique()

# future_df = pd.MultiIndex.from_product([future_dates, sites], names=["datetime","site"]).to_frame(index=False)

# future_df["hour"] = future_df["datetime"].dt.hour
# future_df["day_of_week"] = future_df["datetime"].dt.dayofweek
# future_df["month"] = future_df["datetime"].dt.month


# # load and process availability
# import os
# from glob import glob

# forward_folder = r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\Transposed Forward Looking Data"

# print("Folder exists:", os.path.exists(forward_folder))

# try:
#     print("Directory contents:")
#     for f in os.listdir(forward_folder):
#         print(f)
# except Exception as e:
#     print("Error accessing folder:", e)

# # getting the forward looking HEL
# files = [ f for f in glob(os.path.join(forward_folder, "*forward*transposed*.xls*"))
#     if not os.path.basename(f).startswith("~$")]


# if not files:
#     raise FileNotFoundError("No forward-looking files matched pattern")

# # grab the most recent file
# forward_file = max(files, key=os.path.getctime)


# xls = pd.ExcelFile(forward_file)

# sheet_name = [s for s in xls.sheet_names if "transposed" in s.lower()][0]

# forward_df = pd.read_excel(xls, sheet_name=sheet_name)


# # cleaning the file
# forward_df.columns = [col.replace(" - High Effective Limit", "").strip()
#     for col in forward_df.columns]

# forward_df["datetime"] = pd.to_datetime(forward_df["datetime"])

# # melting data into a format that can be used
# forward_long = forward_df.melt( id_vars=["datetime"], var_name="unit", value_name="availability_mw")



# def map_unit_to_site(u):
#     if str(u).startswith("DCS"):
#         return "DCS"
#     elif str(u).startswith("LCS"):
#         return "LCS"
#     elif str(u).startswith("PGS"):
#         return "PGS"
#     elif str(u).startswith("GGS"):
#         return "GGS"
#     elif str(u).startswith("CGS"):
#         return "CGS"
#     return None

# forward_long["site"] = forward_long["unit"].apply(map_unit_to_site)
# forward_long = forward_long.dropna(subset=["site"])

# forward_site = (forward_long.groupby(["datetime","site"], as_index=False)["availability_mw"].sum())


# # merge availability 
# future_df = future_df.merge(forward_site, on=["datetime","site"], how="left")

# future_df["availability_mw"] = (future_df["availability_mw"].ffill().bfill())


# # add utilization
# util_lookup = master_df.groupby(["site","hour"])["utilization"].mean()

# future_df = future_df.merge(util_lookup.rename("utilization"), on=["site","hour"], how="left")


# # merge forecast data
# future_df = future_df.merge(df_forecast_clean, on="datetime", how="left")

# # cleaning up the naming 
# def safe_final(df, actual, forecast):
#     if actual in df.columns:
#         return df[actual].fillna(df[forecast])
#     return df[forecast]

# future_df["load_final"] = safe_final(future_df, "load_actual", "load")
# future_df["wind_final"] = safe_final(future_df, "wind_actual", "wind")
# future_df["temperature_final"] = safe_final(future_df, "temperature_actual", "temperature")









# #building forecasting loop
# #add site capacity CHECK THESE NUMBERS
# site_capacity = {"CGS": 200, "DCS": 300, "LCS": 800, "PGS": 500, "GGS": 150}

# gas_per_mw_lookup = master_df.groupby(["site", "hour"])["gas_per_mw"].median()

# # forecasting loop
# all_forecasts = []

# for site in models.keys():

#     print(f"\nForecasting for {site}")

#     model = models[site]

#     site_hist = master_df[master_df["site"] == site].sort_values("datetime")
#     site_hist = site_hist[site_hist["datetime"] < future_dates.min()]

#     history = site_hist.tail(48).copy()
#     future_preds = []

#     for dt in future_dates:

#         new_row = { "datetime": dt, "site": site, "hour": dt.hour, "day_of_week": dt.dayofweek, "month": dt.month}

#         api_row = future_df[
#             (future_df["datetime"] == dt) & 
#             (future_df["site"] == site)]

#         # forecast inputs
#         if len(api_row) > 0:
#             new_row["load_final"] = api_row["load_final"].values[0]
#             new_row["wind_final"] = api_row["wind_final"].values[0]
#             new_row["temperature_final"] = api_row["temperature_final"].values[0]
#             new_row["availability_mw"] = api_row["availability_mw"].values[0]
#         else:
#             new_row["load_final"] = history["load_final"].iloc[-1]
#             new_row["wind_final"] = history["wind_final"].iloc[-1]
#             new_row["temperature_final"] = history["temperature_final"].iloc[-1]
#             new_row["availability_mw"] = history["availability_mw"].iloc[-1]

#         # utilization
#         lookup_val = util_lookup.get((site, dt.hour), np.nan)

#         if not pd.isna(lookup_val):
#             new_row["utilization"] = lookup_val
#         else:
#             new_row["utilization"] = history["utilization"].dropna().iloc[-1]





# #look into this as well 
#         # lags
#         new_row["gas_lag_1"] = history["hourly_gas_burn"].iloc[-1]
#         new_row["gas_lag_24"] = history["hourly_gas_burn"].iloc[-24]
#         new_row["gas_roll_24"] = history["hourly_gas_burn"].iloc[-24:].mean()

#         # building the input
#         X_pred = pd.DataFrame([new_row])[features]

#         # prediction
#         pred = model.predict(X_pred)[0]

#         # availability constraint
#         cap = site_capacity.get(site, 200)

#         if new_row["availability_mw"] <= 1:
#             pred = 0
#         else:
#             scale = min(new_row["availability_mw"] / cap, 1)
#             pred *= scale





# #something to look into 
#         # minimum mw constraint
#         gas_per_mw = gas_per_mw_lookup.get((site, dt.hour), 8)
#         implied_mw = pred / gas_per_mw

#         if implied_mw < 0:
#             pred = 0

#         new_row["predicted_gas_burn"] = pred

#         # recursion
#         history = pd.concat(
#             [history, pd.DataFrame([{**new_row, "hourly_gas_burn": pred}])], ignore_index=True)

#         future_preds.append(new_row)

#     all_forecasts.append(pd.DataFrame(future_preds))




    
    
    

#     #combine all sites
# forecast_df = pd.concat(all_forecasts, ignore_index=True)



# # adding gas day
# forecast_df["gas_day"] = (pd.to_datetime(forecast_df["datetime"]) - pd.Timedelta(hours=9)).dt.date

# # and gas_per_mw lookup 
# gas_per_mw_lookup = master_df.groupby(["site", "hour"])["gas_per_mw"].median()

# # add hour for merge 
# forecast_df["hour"] = pd.to_datetime(forecast_df["datetime"]).dt.hour

# # then merge gas_per_mw 
# forecast_df = forecast_df.merge(gas_per_mw_lookup.rename("gas_per_mw"), on=["site", "hour"], how="left")

# forecast_df["implied_mw"] = forecast_df["predicted_gas_burn"] / forecast_df["gas_per_mw"]



# # final formatting here
# forecast_df = forecast_df[["datetime", "gas_day", "site", "predicted_gas_burn", "gas_per_mw", "implied_mw"]]

# # now daily aggregation
# daily_forecast = (forecast_df.groupby(["gas_day", "site"], as_index=False)["predicted_gas_burn"].sum())

# # and sort + format 
# forecast_df = forecast_df.sort_values(["site", "datetime"])







# #final formatting:
# forecast_df = forecast_df.drop_duplicates(subset=["datetime", "site"])
# forecast_df = forecast_df.sort_values(["site", "datetime"])
# forecast_df["datetime"] = forecast_df["datetime"].dt.strftime("%Y-%m-%d %H:%M")


# #export to excel
# file_path = r"G:\Trading\Forecasts\Daily Gas Burn Forecast by Site\forecast with historicals checked.xlsx"

# with pd.ExcelWriter(file_path, engine="openpyxl") as writer:

#     for site in forecast_df["site"].unique():
#         site_df = forecast_df[forecast_df["site"] == site]
#         site_df.to_excel(writer, sheet_name=site, index=False)

# print("File saved at:", file_path)