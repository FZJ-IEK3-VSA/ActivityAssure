"""
Loads activity profiles from the result database file of the LoadProfileGenerator
and creates csv files from them that can be used in the validation framework.
Also generates a preliminary activity mapping in the process using the activity
categories defined in the LoadProfileGenerator. Some categories cannot be
assigned an activity unambiguously, so the mapping file needs to be checked
and completed manually afterwards.
If a mapping file already exists, it is loaded and expanded if necessary.
"""

import argparse
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import sqlite3

import pandas as pd
import tqdm

from activityassure import activity_mapping

import create_lpg_person_characteristics as create_lpg_char


#: used as a placeholder for ambiguous categories
UNMAPPED_CATEGORY = "TODO"
#: preliminary affordance mappings according to affordance categories
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


def load_activity_profile_from_db(database_file: Path) -> dict[str, pd.DataFrame]:
    """
    Converts LPG activity profiles to the target csv format.
    Also creates or extends the LPG activity mapping file.

    :param db_file: the database file to load
    """
    assert database_file.is_file(), f"Database file not found: {database_file}"

    # load activity mapping
    mapping_path = Path("examples/LoadProfileGenerator/activity_mapping_lpg.json")
    if mapping_path.is_file():
        # load the existent mapping to extend it
        mapping = activity_mapping.load_mapping(mapping_path)
    else:
        # initialize a new mapping
        mapping = {}

    # get all activities from LPG result database
    con = sqlite3.connect(str(database_file))
    with con:
        cur = con.cursor()
        query = "SELECT * FROM PerformedActions"
        results = cur.execute(query)
        activity_list: list[tuple[str, str]] = results.fetchall()
    # parse the json info column for each activity
    parsed_json_list = [json.loads(act) for name, act in activity_list]
    # the list contains activities of all persons, so they need to be grouped
    rows_by_person: dict[str, list[tuple[int, datetime, str]]] = defaultdict(list)
    unmapped_affordances = {}
    for entry in parsed_json_list:
        start_date = datetime.fromisoformat(entry["DateTime"])
        affordance = entry["AffordanceName"]
        category = entry["Category"]
        # check for unmapped affordances
        if affordance not in mapping and affordance not in unmapped_affordances:
            unmapped_affordances[affordance] = CATEGORY_MAPPING.get(
                category, UNMAPPED_CATEGORY
            )
        # store the relevant information for each activity
        person = entry["PersonName"]
        start_step = entry["TimeStep"]["ExternalStep"]
        activity_entry = (start_step, start_date, affordance)
        rows_by_person[person].append(activity_entry)

    if unmapped_affordances:
        print(f"Found {len(unmapped_affordances)} unmapped affordances")
        merged = mapping | unmapped_affordances
        with open(mapping_path, "w") as f:
            # add unmapped affordances to mapping file
            json.dump(merged, f, indent=4, encoding="utf8")

    # store the activities in one DataFrame per person
    profiles = {
        person: pd.DataFrame(rows, columns=["Timestep", "Date", "Activity"])
        for person, rows in rows_by_person.items()
    }
    return profiles


def convert_activity_profile_from_db_to_csv(
    db_file: Path, result_dir: Path, id: str, template: str
):
    """
    Loads a single LPG result database file and converts the contained activity
    profiles to csv files. Writes any new, still uncategorized affordances into the
    mapping file.

    :param raw_data_dir: LPG result directory containing the database file
    :param result_dir: output folder for the created csv files
    :param hh_key: household key of the file to load, defaults to "HH1"

    :param db_file: the database file to load
    :param result_dir: the result directory to store the csv files
    :param id: ID of the calculation to distinguish results for the same template
    :param template: the household template name
    """
    # get the profiles as dataframes
    profile_per_person = load_activity_profile_from_db(db_file)

    # store each dataframe as a csv file
    result_dir.mkdir(parents=True, exist_ok=True)
    for person, data in profile_per_person.items():
        # LPG person name pattern: "CHR01 Sami (25/Male)"
        person_name = person.split(" (")[0]
        person_id = create_lpg_char.get_person_id(person_name, template)
        result_path = result_dir / f"{person_id}_{id}.csv"
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

    # subdirectory where error messages from failed conversions are stored
    errors_dir = "errors"

    # expected directory structure: one directory per LPG template
    for template_dir in tqdm.tqdm(Path(input_dir).iterdir()):
        assert template_dir.is_dir(), f"Unexpected file found: {template_dir}"
        if template_dir.name == errors_dir:
            # skip the errors directory
            continue
        # each template directory contains one subdirectory per iteration
        for iteration_dir in template_dir.iterdir():
            assert iteration_dir.is_dir(), f"Unexpected file found: {iteration_dir}"
            # parse the template and calculation iteration from the directory
            id = iteration_dir.name
            template = iteration_dir.parent.name
            # determine the database filepath
            db_file = iteration_dir / "Results.HH1.sqlite"
            try:
                convert_activity_profile_from_db_to_csv(
                    db_file, result_dir, id, template
                )
            except Exception as e:
                print(f"An error occurred while processing '{iteration_dir}': {e}")
                # if the LPG created a log file, move that to the errors directory
                logfile = iteration_dir / "Log.CommandlineCalculation.txt"
                if logfile.is_file():
                    logfile.rename(
                        input_dir
                        / errors_dir
                        / f"{template_dir.name}_{iteration_dir.name}_error.txt"
                    )
