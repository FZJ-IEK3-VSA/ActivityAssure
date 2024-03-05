"""
Loads activity profiles from the result database file of the LoadProfileGenerator
and creates csv files from them that can be used in the validation framework.
Also generates a preliminary activity mapping in the process using the activity
categories defined in the LoadProfileGenerators. Some categories cannot be
assigned an activity unambiguously, so the mapping file needs to be checked
and completed manually afterwards.
If a mapping file already exists, it is loaded and expanded if necessary.
"""

import argparse
from datetime import datetime
import glob
import json
from pathlib import Path
import sqlite3

import pandas as pd
import tqdm

from activity_validator import activity_mapping

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


def load_activity_profile_from_db(file: Path, result_dir: Path):
    """
    Converts LPG activity profiles to the target csv format.
    Also creates or extends the LPG activity mapping file.

    :param file: input database file
    :param result_dir: output folder for the created csv files
    """
    assert file.is_file(), f"File does not exist: {file}"

    # load activity mapping
    mapping_path = Path("examples/LoadProfileGenerator/activity_mapping_lpg.json")
    if mapping_path.is_file():
        # load the existent mapping to extend it
        mapping = activity_mapping.load_mapping(mapping_path)
    else:
        # initialize a new mapping
        mapping = {}

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
        if affordance not in mapping and affordance not in unmapped_affordances:
            unmapped_affordances[affordance] = CATEGORY_MAPPING.get(
                category, UNMAPPED_CATEGORY
            )
        person = entry["PersonName"]
        start_step = entry["TimeStep"]["ExternalStep"]
        activity_entry = (start_step, start_date, affordance)
        rows_by_person.setdefault(person, []).append(activity_entry)

    if unmapped_affordances:
        print(f"Found {len(unmapped_affordances)} unmapped affordances")
        merged = mapping | unmapped_affordances
        with open(mapping_path, "w") as f:
            # add unmapped affordances to mapping file
            json.dump(merged, f, indent=4)

    # store the activities in a DataFrame
    base_result_dir = Path(result_dir)
    base_result_dir.mkdir(parents=True, exist_ok=True)
    for person, rows in rows_by_person.items():
        data = pd.DataFrame(rows, columns=["Timestep", "Date", "Activity"])
        # result file pattern: "CHR01_142.sqlite"
        repetition = file.stem.split("_")[-1]
        # LPG person name pattern: "CHR01 Sami (25/Male)"
        person_id = person.split(" (")[0]
        result_path = base_result_dir / f"{person_id}_{repetition}.csv"
        data.to_csv(result_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        help="Root directory of the raw input data",
        default="data/lpg_simulations/raw",
        required=False,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Root directory for the preprocessed result data",
        default="data/lpg_simulations/preprocessed",
        required=False,
    )
    args = parser.parse_args()
    input_dir = Path(args.input)
    result_dir = Path(args.output)
    assert input_dir.is_dir(), f"Invalid path: {input_dir}"

    # process all sqlite files in the directory
    pattern = str(input_dir / "*" / "*.sqlite")
    for file in tqdm.tqdm(glob.glob(pattern)):
        load_activity_profile_from_db(Path(file), result_dir)
