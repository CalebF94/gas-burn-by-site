"""
Module containing global constants, configuration paths, and mapping dictionaries for the gas burn forecasting pipeline.

Constants:
    - AVAILABILITY_FILES_XLSX: List of Excel files with unit availability data by month/year
    - AVAILABILITY_FILES_CSV: List of CSV files with unit availability data by month/year
    - NEXT_DAY_GAS_BURN_TEMPLATE: Path to Excel template for next-day gas burn reports
    - NBPL_TEMPLATE: Path to Excel template for NBPL forecast submissions
    - OUTPUT_DIRS: Dictionary of output directories for models, forecasts, and submission files
    
Mappings:
    - SITE_MAPPINGS: Maps site location names to site identifiers (e.g., "DEER CREEK" -> "DCS")
    - SITE_GENERATION_LIMITS: Maximum hourly generation capacity (MW) for each site
    - SITE_BURN_DATATYPES: Data types for gas burn query results
    - SITE_GENERATION_DATATYPES: Data types for generation query results (hourly columns + metadata)
"""

## Availability files - These will need to be updated every month as new files are saved
AVAILABILITY_FILES_XLSX = [
    "G:/Trading/Market Operations/Unit availability/2026/RT Unit availability 08.26.xlsx",
    "G:/Trading/Market Operations/Unit availability/2026/RT Unit availability 07.26.xlsx",
    "G:/Trading/Market Operations/Unit availability/2026/RT Unit availability 06.26.xlsx",
    "G:/Trading/Market Operations/Unit availability/2026/RT Unit availability 05.26.xlsx",
    "G:/Trading/Market Operations/Unit availability/2026/RT Unit availability 04.26.xlsx",
    "G:/Trading/Market Operations/Unit availability/2026/RT Unit availability 03.26.xlsx",
    "G:/Trading/Market Operations/Unit availability/2026/RT Unit availability 02.26.xlsx",
    "G:/Trading/Market Operations/Unit availability/2026/RT Unit availability 01.26.xlsx",
    "G:/Trading/Market Operations/Unit availability/2025/RT Unit availability 12.25.xlsx",
    "G:/Trading/Market Operations/Unit availability/2025/RT Unit availability 11.25.xlsx",
    "G:/Trading/Market Operations/Unit availability/2025/RT Unit availability 10.25.xlsx",
    "G:/Trading/Market Operations/Unit availability/2025/RT Unit availability 09.25.xlsx",
    "G:/Trading/Market Operations/Unit availability/2025/RT Unit availability 08.25.xlsx",
    "G:/Trading/Market Operations/Unit availability/2025/RT Unit availability 07.25.xlsx",
    "G:/Trading/Market Operations/Unit availability/2025/RT Unit availability 06.25.xlsx",
    "G:/Trading/Market Operations/Unit availability/2025/RT Unit availability 05.25 - UPDATE.xlsx",
    "G:/Trading/Market Operations/Unit availability/2025/RT Unit availability 04.25 - UPDATE.xlsx"]

AVAILABILITY_FILES_CSV = [
    "G:/Trading/Market Operations/Unit availability/2025/dpm_BEPC_GROUPING_2025030100_2025033123 - March.csv",
    "G:/Trading/Market Operations/Unit availability/2025/transposed_dpm_BEPC_GROUPING_2025020100_2025022823 feb.csv", 
    "G:/Trading/Market Operations/Unit availability/2025/transposed_dpm_BEPC_GROUPING_2025010100_2025013123.csv",
    "G:/Trading/Market Operations/Unit availability/2024/dpm_BEPC_GROUPING_2024120100_2024123123.csv",
    "G:/Trading/Market Operations/Unit availability/2024/dpm_BEPC_GROUPING_2024110100_2024113023.csv",
    "G:/Trading/Market Operations/Unit availability/2024/dpm_BEPC_GROUPING_2024100100_2024103123.csv",
    "G:/Trading/Market Operations/Unit availability/2024/dpm_BEPC_GROUPING_2024090100_2024093023.csv",
    "G:/Trading/Market Operations/Unit availability/2024/dpm_BEPC_GROUPING_2024080100_2024083123.csv",
    "G:/Trading/Market Operations/Unit availability/2024/dpm_BEPC_GROUPING_2024070100_2024073123.csv",
    "G:/Trading/Market Operations/Unit availability/2024/dpm_BEPC_GROUPING_2024060100_2024063023.csv",
    "G:/Trading/Market Operations/Unit availability/2024/dpm_BEPC_GROUPING_2024050100_2024053123.csv"]

## Template files
NEXT_DAY_GAS_BURN_TEMPLATE = "G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/Next Day Gas Burn Files/Next Day Gas Burn Template.xlsx"
NBPL_TEMPLATE = "G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/NBPL Submission Files/NBPL template no links.xlsx"

## Output directories
OUTPUT_DIRS = {
    "Models": "G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/Models",
    "Forecasts": "G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/Forecasts",
    "NBPL Submission Files": "G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/NBPL Submission Files",
    "Next Day Gas Burn Files": "G:/Trading/Forecasts/Daily Gas Burn Forecast by Site/Next Day Gas Burn Files"
}

## Site Identifiers
SITES_LIST = ["CGS", "DCS", "LCS", "PGS", "GGS"]
SITES_OR_LIST = '|'.join(SITES_LIST)

## Mapping dictionaries
SITE_MAPPINGS = {
    "DEER CREEK": "DCS", 
    "LANARK": "CGS", 
    "LONSOME CREEK": "LCS",  
    "STATELINE": "PGS", 
    "GROTON": "GGS", 
    "CULBERTSON": "CGS"
}

SITE_GENERATION_LIMITS = {
    "CGS": 95, 
    "DCS": 297, 
    "LCS": 270, 
    "PGS": 803.4, 
    "GGS": 190
}

SITE_BURN_DATATYPES = {
    'marketarea': 'str',
    'gas_day': 'datetime64[ns]',
    'energy': 'float64',
}

SITE_GENERATION_DATATYPES = {
    'he01': 'float64',
    'he02': 'float64',
    'he03': 'float64',
    'he04': 'float64',
    'he05': 'float64',
    'he06': 'float64',
    'he07': 'float64',
    'he08': 'float64',
    'he09': 'float64',
    'he10': 'float64',
    'he11': 'float64',
    'he12': 'float64',
    'he13': 'float64',
    'he14': 'float64',
    'he15': 'float64',
    'he16': 'float64',
    'he17': 'float64',
    'he18': 'float64',
    'he19': 'float64',
    'he20': 'float64',
    'he21': 'float64',
    'he22': 'float64',
    'he23': 'float64',
    'he24': 'float64',
    'begtime': 'datetime64[ns]',
    'loadshape': 'str'
}




