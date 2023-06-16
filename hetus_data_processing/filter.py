"""
Functions for filtering HETUS data based on various criteria
"""


import functools
from typing import Dict, List, Union
import pandas as pd

import hetus_columns as col
from utils import HetusDayType, timing

#TODO: for separating dataframes instead of just dropping unmatching columns, groupby can be used

@timing
def filter_discrete(data: pd.DataFrame, column: str, allowed_values: List[int]) -> pd.DataFrame:
    return data[data[column].isin(allowed_values)]

def filter_by_weekday(data: pd.DataFrame, day_types: List[HetusDayType]) -> pd.DataFrame:
    return filter_discrete(data, col.Diary.WEEKDAY, day_types)


def filter_by_month(data: pd.DataFrame, months: List[int]) -> pd.DataFrame:
    return filter_discrete(data, col.Diary.MONTH, months)


@timing
def filter_combined(data: pd.DataFrame, conditions: Dict[str, List[int]]) -> pd.DataFrame:
    masks = [data[k].isin(v) for k, v in conditions.items()]
    combined_mask = functools.reduce(lambda m1, m2: m1 & m2, masks)
    return data[combined_mask]

# def filter_index(data: pd.DataFrame, conditions: Dict[str, List[Union[str, int]]]) -> pd.DataFrame:
#     masks = [data.index.get_level_values(k) in v for k, v in conditions.items()] # TODO: does not work
#     combined_mask = functools.reduce(lambda m1, m2: m1 & m2, masks)
#     return data.loc[combined_mask]

def filter_num_earners():
    # TODO: calculate total time spent working and categorize: >~6h --> full-time, <1h --> no worker, or similar
    pass


def filter_family_status():
    pass


#Klären: 25 % aller Mitglieder aus teilnehmenden Haushalte haben selbst nicht an der Umfrage teilgenommen (36 % der Haushalte sind 'unvollständig')
# --> soll hier auf Haushaltsebene oder auf Personenebene validiert werden
# Jannik validiert auf HH-Ebene (bspw. Wahrscheinlichkeitskurven); aber macht das Sinn, alle Aktivitäten einer Familie zu validieren, wenn nur der Earner an HETUS teilgenommen hat?