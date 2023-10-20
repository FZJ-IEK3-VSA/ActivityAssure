import json
import os
import sqlite3
from activity_validator.hetus_data_processing import activity_profile
from activity_validator.hetus_data_processing.attributes.person_attributes import (
    Sex,
    WorkStatus,
)


def define_person_mapping(path: str):
    # TODO: (automatically?) create complete mapping for all persons/households
    mapping = {
        "Rubi": activity_profile.ProfileType("DE", Sex.female, WorkStatus.full_time),
        "Sami": activity_profile.ProfileType("DE", Sex.male, WorkStatus.full_time),
    }
    dict_mapping = {n: p.to_dict() for n, p in mapping.items()}  # type: ignore

    path = os.path.join(path)
    with open(path, "w+", encoding="utf-8") as f:
        json.dump(dict_mapping, f, indent=4)


def generate_raw_activity_mapping(database_path: str, output_file):
    con = sqlite3.connect(database_path)
    cur = con.cursor()
    query = "SELECT Name, AffCategory FROM tblAffordances"
    results = cur.execute(query)
    rows: list[tuple] = results.fetchall()

    # define preliminary mapping based on affordance category
    # categories mapped to None are ambiguous and need manual assignment
    category_mapping = {
        "Active Entertainment (Computer, Internet etc)": "pc",
        "Entertainment": None,
        "Office": "work",
        "Offline Entertainment": "other",
        "Outside recreation": "not at home",
        "Passive Entertainment (TV etc.)": None,
        "child care": "other",
        "cleaning": None,  # laundry is separate
        "cooking": "cook",
        "gardening and maintenance": "other",
        "hygiene": "personal care",
        "other": "other",
        "school": "education",
        "shopping": "not at home",
        "sleep": "sleep",
        "sports": None,
        "work": "work",
    }
    affordances = [(row[0], row[1]) for row in rows]
    mapping = {name: category_mapping[category] for name, category in affordances}
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=4)


if __name__ == "__main__":
    person_file = "data/lpg/person_characteristics.json"
    define_person_mapping(person_file)

    lpg_main_db = "data/lpg/profilegenerator.db3"
    output_file = "examples/activity_mapping_lpg.json"
    generate_raw_activity_mapping(lpg_main_db, output_file)
