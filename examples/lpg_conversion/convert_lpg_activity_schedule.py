from datetime import datetime, timedelta
import glob
import json
from pathlib import Path
import sqlite3

import pandas as pd

from activity_validator.hetus_data_processing import hetus_translations


TIMESTEP_DURATION = timedelta(minutes=1)


def load_activity_profile_from_db(file: Path):
    assert file.is_file(), f"File does not exist: {file}"

    # load activity mapping
    mapping_path = Path("examples/activity_mapping_lpg.json")
    activity_mapping = hetus_translations.load_mapping(mapping_path)

    # get all activities from LPG result database
    con = sqlite3.connect(str(file))
    with con:
        cur = con.cursor()
        query = "SELECT * FROM PerformedActions"
        results = cur.execute(query)
        activity_list: list[tuple[str, str]] = results.fetchall()
    # parse the json info column for each activity
    parsed_json_list = [json.loads(act) for name, act in activity_list]
    # sort activities by person
    rows_by_person: dict[str, list[tuple[int, datetime, str]]] = {}
    unmapped_affordances = set()
    for entry in parsed_json_list:
        start_date = datetime.fromisoformat(entry["DateTime"])
        affordance = entry["AffordanceName"]
        if affordance not in activity_mapping:
            unmapped_affordances.add(affordance)
        person = entry["PersonName"]
        start_step = entry["TimeStep"]["ExternalStep"]
        activity_entry = (start_step, start_date, affordance)
        rows_by_person.setdefault(person, []).append(activity_entry)

    if unmapped_affordances:
        print(f"Found {len(unmapped_affordances)} unmapped affordances")
        d = {a: "TODO" for a in unmapped_affordances}
        merged = activity_mapping | d
        with open(mapping_path, "w") as f:
            # add unmapped affordances to mapping file
            json.dump(merged, f, indent=4)

    # store the activities in a DataFrame
    base_result_dir = Path("data/lpg/preprocessed")
    base_result_dir.mkdir(parents=True, exist_ok=True)
    for person, rows in rows_by_person.items():
        data = pd.DataFrame(rows, columns=["Timestep", "Date", "Activity"])
        short_name = person.split(" ")[1]
        result_path = base_result_dir / f"{short_name}_{file.stem}.csv"
        data.to_csv(result_path)


if __name__ == "__main__":
    directory = Path("data/lpg/raw/")
    pattern = str(directory / "*" / "*.sqlite")
    for file in glob.glob(pattern):
        load_activity_profile_from_db(Path(file))
