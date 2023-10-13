from datetime import datetime, timedelta
import json
import os
import pathlib
import sqlite3
from typing import Dict, List, Tuple

import pandas as pd


TIMESTEP_DURATION = timedelta(minutes=1)


def load_activity_profile_from_db(file: str):
    assert os.path.isfile(file), f"File does not exist: {file}"
    # get all activities from LPG result database
    con = sqlite3.connect(file)
    cur = con.cursor()
    query = "SELECT * FROM PerformedActions"
    results = cur.execute(query)
    activity_list: List[Tuple[str, str]] = results.fetchall()
    # parse the json info column for each activity
    parsed_json_list = [json.loads(act) for name, act in activity_list]
    # sort activities by person
    rows_by_person: Dict[str, list[tuple[int, datetime, str]]] = {}
    for entry in parsed_json_list:
        start_date = datetime.fromisoformat(entry["DateTime"])
        affordance = entry["AffordanceName"]
        person = entry["PersonName"]
        start_step = entry["TimeStep"]["ExternalStep"]
        activity_entry = (start_step, start_date, affordance)
        rows_by_person.setdefault(person, []).append(activity_entry)

    # store the activities in a DataFrame
    parent_dir = pathlib.Path(file).parent / "processed"
    parent_dir.mkdir(parents=True, exist_ok=True)
    for person, rows in rows_by_person.items():
        data = pd.DataFrame(rows, columns=["Timestep", "Date", "Activity"])
        short_name = person.split(" ")[1]
        result_path = parent_dir / (short_name + ".csv")
        data.to_csv(result_path)


if __name__ == "__main__":
    directory = ".\\data\\lpg"
    file = "Results.HH1.sqlite"
    path = os.path.join(directory, file)
    load_activity_profile_from_db(path)
