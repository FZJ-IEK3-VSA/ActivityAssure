"""
Calculates additional attributes for diary entries which can then be used for categorization
"""

import pandas as pd

def calc_day_type(data: pd.DataFrame):
    # TODO: use HetusDayType; if not set, fall back to day of week and check if work is contained
    pass