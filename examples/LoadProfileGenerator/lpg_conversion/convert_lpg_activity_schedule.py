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
import json
from pathlib import Path
import sqlite3

import pandas as pd
import tqdm

from activity_validator import activity_mapping

import generate_lpg_person_characteristics as gen_lpg_char


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


def load_activity_profile_from_db(raw_data_dir: Path, result_dir: Path):
    """
    Converts LPG activity profiles to the target csv format.
    Also creates or extends the LPG activity mapping file.

    :param raw_data_dir: input raw data directory from one LPG calculation
    :param result_dir: output folder for the created csv files
    """
    assert raw_data_dir.is_dir(), f"Raw data directory does not exist: {raw_data_dir}"

    # load activity mapping
    mapping_path = Path("examples/LoadProfileGenerator/activity_mapping_lpg.json")
    if mapping_path.is_file():
        # load the existent mapping to extend it
        mapping = activity_mapping.load_mapping(mapping_path)
    else:
        # initialize a new mapping
        mapping = {}

    main_db_file = raw_data_dir / "Results.HH1.sqlite"
    assert main_db_file.is_file(), f"Result file does not exist: {main_db_file}"

    # parse LPG template and calulcation iteration from directory names
    iteration = raw_data_dir.name
    assert iteration.isdigit(), f"Unexpected iteration number {iteration}"
    template = raw_data_dir.parent.name

    # get all activities from LPG result database
    con = sqlite3.connect(str(main_db_file))
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
        # LPG person name pattern: "CHR01 Sami (25/Male)"
        person_name = person.split(" (")[0]
        person_id = gen_lpg_char.get_person_id(person_name, template)
        result_path = base_result_dir / f"{person_id}_{iteration}.csv"
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

    # expected directory structure: one directory per LPG template
    for template_dir in tqdm.tqdm(Path(input_dir).iterdir()):
        assert template_dir.is_dir(), f"Unexpected file found: {template_dir}"
        # each template directory contains one subdirectory per iteration
        for iteration_dir in template_dir.iterdir():
            assert iteration_dir.is_dir(), f"Unexpected file found: {iteration_dir}"
            load_activity_profile_from_db(iteration_dir, result_dir)
