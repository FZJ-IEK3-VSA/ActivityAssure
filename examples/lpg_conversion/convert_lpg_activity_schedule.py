from datetime import datetime, timedelta
import json
import os
import pathlib
import sqlite3
from typing import Dict, List, Tuple

import pandas as pd

from hetus_data_processing.datastructures import (
    ActivityProfileEntryTime,
    ActivityProfile,
)
import hetus_data_processing.utils


def load_activity_profile_from_db(file: str):
    assert os.path.isfile(file), f"File does not exist: {file}"
    con = sqlite3.connect(file)
    cur = con.cursor()

    query = "SELECT * FROM PerformedActions"
    results = cur.execute(query)
    activity_list: List[Tuple[str, str]] = results.fetchall()
    parsed_json_list = [json.loads(act) for name, act in activity_list]
    activity_info_list = [
        (j["PersonName"], j["AffordanceName"], j["DateTime"]) for j in parsed_json_list
    ]
    profiles_per_person: Dict[str, List[str]] = {}
    for person, activity_name, start_date_str in activity_info_list:
        start_date = datetime.fromisoformat(start_date_str)
        activity = ActivityProfileEntryTime(activity_name, start_date)
        profiles_per_person.setdefault(person, []).append(activity)

    # TODO apply activity mapping

    # Calculate the simulation end: simulation always ends at midnight
    # and no activity lasts a whole day, the end is the next midnight after
    # the last activity start date
    # Remark: this is not necessarily the end of the last activity
    simulation_end = start_date.date() + timedelta(days=1)

    parent_dir = pathlib.Path(file).parent.absolute()
    result_dir = os.path.join(parent_dir, "processed")
    hetus_data_processing.utils.ensure_dir_exists(result_dir)
    for person, activity_profile in profiles_per_person.items():
        profile = ActivityProfile(activity_profile, person)
        profile.calc_durations()
        # extract the actual person name (e.g. 'Rubi')
        short_name = person.split(" ")[1]
        result_path = os.path.join(parent_dir, "processed", short_name + ".json")
        with open(result_path, "w+", encoding="utf-8") as f:
            f.write(profile.to_json())


if __name__ == "__main__":
    directory = ".\\data\\lpg"
    file = "Results.HH1.sqlite"
    path = os.path.join(directory, file)
    load_activity_profile_from_db(path)


# Properties of activity profiles
# - for single person or whole household
# - arbitrary resolution
# - arbitrary time frame, usually 1 year
