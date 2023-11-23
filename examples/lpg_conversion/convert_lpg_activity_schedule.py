from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sqlite3

import pandas as pd


TIMESTEP_DURATION = timedelta(minutes=1)


def load_activity_profile_from_db(file: Path):
    assert file.is_file(), f"File does not exist: {file}"
    # get all activities from LPG result database
    con = sqlite3.connect(str(file))
    cur = con.cursor()
    query = "SELECT * FROM PerformedActions"
    results = cur.execute(query)
    activity_list: list[tuple[str, str]] = results.fetchall()
    # parse the json info column for each activity
    parsed_json_list = [json.loads(act) for name, act in activity_list]
    # sort activities by person
    rows_by_person: dict[str, list[tuple[int, datetime, str]]] = {}
    for entry in parsed_json_list:
        start_date = datetime.fromisoformat(entry["DateTime"])
        affordance = entry["AffordanceName"]
        person = entry["PersonName"]
        start_step = entry["TimeStep"]["ExternalStep"]
        activity_entry = (start_step, start_date, affordance)
        rows_by_person.setdefault(person, []).append(activity_entry)

    # store the activities in a DataFrame
    parent_dir = file.parent / "processed" / "test"
    parent_dir.mkdir(parents=True, exist_ok=True)
    for person, rows in rows_by_person.items():
        data = pd.DataFrame(rows, columns=["Timestep", "Date", "Activity"])
        short_name = person.split(" ")[1]
        result_path = parent_dir / f"{short_name}_{file.stem}.csv"
        data.to_csv(result_path)


if __name__ == "__main__":
    directory = Path("data/lpg/lpg_template_results/CHR01")
    for file in directory.iterdir():
        load_activity_profile_from_db(directory / file)
