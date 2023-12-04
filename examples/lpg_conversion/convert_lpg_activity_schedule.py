from datetime import datetime, timedelta
import glob
import json
from pathlib import Path
import sqlite3

import pandas as pd

from activity_validator.hetus_data_processing import hetus_translations

# preliminary affordance mappings according to affordance categories
UNMAPPED_CATEGORY = "TODO"
CATEGORY_MAPPING = {
    "Active Entertainment (Computer, Internet etc)": "pc",
    "Entertainment": UNMAPPED_CATEGORY,
    "Office": "work",
    "Offline Entertainment": "other",
    "Outside recreation": "not at home",
    "Passive Entertainment (TV etc.)": UNMAPPED_CATEGORY,
    "child care": "other",
    "cleaning": UNMAPPED_CATEGORY,  # laundry is separate
    "cooking": "cook",
    "gardening and maintenance": "other",
    "hygiene": "personal care",
    "other": "other",
    "school": "education",
    "shopping": "not at home",
    "sleep": "sleep",
    "sports": UNMAPPED_CATEGORY,
    "work": "work",
}


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
    unmapped_affordances = {}
    for entry in parsed_json_list:
        start_date = datetime.fromisoformat(entry["DateTime"])
        affordance = entry["AffordanceName"]
        category = entry["Category"]
        if (
            affordance not in activity_mapping
            and affordance not in unmapped_affordances
        ):
            unmapped_affordances[affordance] = CATEGORY_MAPPING.get(
                category, UNMAPPED_CATEGORY
            )
        person = entry["PersonName"]
        start_step = entry["TimeStep"]["ExternalStep"]
        activity_entry = (start_step, start_date, affordance)
        rows_by_person.setdefault(person, []).append(activity_entry)

    if unmapped_affordances:
        print(f"Found {len(unmapped_affordances)} unmapped affordances")
        merged = activity_mapping | unmapped_affordances
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
