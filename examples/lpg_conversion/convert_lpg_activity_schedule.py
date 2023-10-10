from datetime import datetime, timedelta
import json
import os
import pathlib
import sqlite3
from typing import Dict, List, Tuple

import pandas as pd

from activity_validator.hetus_data_processing.activity_profile import (
    ActivityProfileEntryTime,
    ActivityProfile,
    ProfileType,
)
import activity_validator.hetus_data_processing.utils as utils


def load_activity_profile_from_db(file: str):
    # load person mapping file
    mapping_file = ".\\data\\lpg\\person_types.json"
    with open(mapping_file, encoding="utf-8") as f:
        mapping: dict[str, dict[str, str]] = json.load(f)

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
    profiles_per_person: Dict[str, List[ActivityProfileEntryTime]] = {}
    for person, activity_name, start_date_str in activity_info_list:
        start_date = datetime.fromisoformat(start_date_str)
        activity = ActivityProfileEntryTime(activity_name, start_date)
        profiles_per_person.setdefault(person, []).append(activity)

    # TODO apply activity mapping

    parent_dir = pathlib.Path(file).parent.absolute()
    result_dir = os.path.join(parent_dir, "processed")
    os.makedirs(result_dir, exist_ok=True)
    for person, activity_profile in profiles_per_person.items():
        assert person in mapping, f"No person type found for person {person}"
        person_type = ProfileType.from_dict(mapping[person])  # type: ignore
        profile = ActivityProfile(activity_profile, person_type)
        profile.calc_durations()
        # extract the actual person name (e.g. 'Rubi')
        short_name = person.split(" ")[1]
        result_path = os.path.join(parent_dir, "processed", short_name + ".json")
        with open(result_path, "w+", encoding="utf-8") as f:
            f.write(profile.to_json(indent=4))  # type: ignore


if __name__ == "__main__":
    directory = ".\\data\\lpg"
    file = "Results.HH1.sqlite"
    path = os.path.join(directory, file)
    load_activity_profile_from_db(path)


# Properties of activity profiles
# - for single person or whole household
# - arbitrary resolution
# - arbitrary time frame, usually 1 year
