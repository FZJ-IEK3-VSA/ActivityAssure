"""Load and analyze desire values from Desire csv files"""

import json
import logging
from pathlib import Path
import pickle
import pandas as pd
from tqdm import tqdm

from activityassure.raw_statistics import activity_statistics

import load_profile_processing


def load_desire_values(filepath: Path):
    with open(filepath, encoding="utf-8") as f:
        file_content = [line.rstrip(";\n") + "\n" for line in f]

    df = pd.read_csv(
        pd.io.common.StringIO("".join(file_content)),  # type: ignore
        sep=";",
        usecols=["Time", "Special / Pharmacy Visit"],
        index_col="Time",
        date_format=load_profile_processing.DATEFORMAT_EN,
    )
    return df


def main(city_result_dir: Path, visits_file: Path):

    with open(visits_file) as f:
        visits_per_person = json.load(f)

    # pattern of the LPG result files to aggregate
    file_prefix = "Desires."
    filepattern = f"{file_prefix}*.csv"

    # collect all household load profiles
    houses_subdir = city_result_dir / "Houses"
    files = list(houses_subdir.rglob(filepattern))

    dfs = {}
    for file in tqdm(files):
        house = file.parent.parent.name
        parts = file.stem.removeprefix(file_prefix).split(".")
        assert len(parts) == 2, f"Unexpected filename: {file.stem}"
        person, hh = parts
        person_id = f"{person}_{house}_{hh}"
        if True or visits_per_person[person_id] > 0:
            df = load_desire_values(file)
            df.rename({"Special / Pharmacy Visit": person_id}, inplace=True)
            dfs[person_id] = df

    logging.info(f"Loaded {len(dfs)} desire files of pharmacy visitors")

    # save the merged desires file
    merged = pd.concat(dfs.values(), axis="columns")
    with open(city_result_dir / "Postprocessed/merged_desires.pkl", "wb") as f:
        pickle.dump(merged, f)
    merged.to_csv(city_result_dir / "Postprocessed/merged_desires.csv")

    mean = merged.mean(axis="columns")
    mean.to_csv(city_result_dir / "Postprocessed/desires_mean.csv")


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # city_result_dir = Path("R:/phd_dir/results/scenario_juelich_04_eplpo_fair_100_1")
    city_result_dir = Path(
        "/fast/home/d-neuroth/phd_dir/results/scenario_juelich_04_eplpo_fair_100_1"
    )
    visits_file = (
        city_result_dir
        / "Postprocessed/raw_activity_statistics/visit-pharmacy/frequency_by_person.json"
    )

    main(city_result_dir, visits_file)
