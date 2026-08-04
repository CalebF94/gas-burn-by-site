"""
Module contains non confidential variables and mapping dictionaries
"""

## Mapping dictionaries
SITE_MAPPINGS = {
    "DEER CREEK": "DCS", 
    "LANARK": "CGS", 
    "LONSOME CREEK": "LCS",  
    "STATELINE": "PGS", 
    "GROTON": "GGS", 
    "CULBERTSON": "CGS"
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