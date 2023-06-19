"""
Calculates additional attributes for households, persons or diary entries which can then 
be used for categorization
"""

import pandas as pd


def calc_work_status_from_diaries(
    data: pd.DataFrame, persondata: pd.DataFrame
) -> pd.DataFrame:
    data = data.copy()
    # Check other means beforehand: if num_earners = hh-size, then everyone is an earner
    
    # For each row, count the number of Work code occurrences and multiply by 10 minutes
    # for each diary entry, determine the work status depending on the worked hours
    # determine the state out of all entries for a person: weekends etc. don't matter,
    # if there are days with work, the person is a worker, all other days are then assumed to be free
    # if the working times differ, use the most frequent one. In doubt, maybe the total share of worked time may help?

    return data
