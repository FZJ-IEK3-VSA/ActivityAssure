"""
Functions for categorizing all persons or households in HETUS data sets using
different criteria
"""

from typing import Any, Dict
import pandas as pd


def categorize_households(hhdata: pd.DataFrame) -> Dict[Any, pd.DataFrame]:
    #TODO: split hhdata into several separate dataframes, depending on the criteria
    #      Alternatively, a "category" column might be added to hhdata
    return {"singles": hhdata}