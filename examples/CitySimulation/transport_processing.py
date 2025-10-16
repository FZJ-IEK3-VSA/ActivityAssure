"""Travel-related postprocessing of the city simulation"""

import json
from pathlib import Path
from collections import defaultdict
import logging
from dataclasses import asdict
import pickle

import pandas as pd
from tqdm import tqdm

from activityassure.preprocessing.lpg import travel_import, activity_profiles
from paths import SubDirs


def get_car_state_counts(city_result_dir: Path, output_dir: Path):
    """Counts how many cars are in which state (driving, charging, etc.)
    in each timestep.

    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the postpocessed data
    """
    # pattern of the LPG result files to aggregate
    file_prefix = "Carstate.Car"
    filepattern = f"Results/{file_prefix}*.json"

    # collect state files for all cars from all households
    houses_subdir = city_result_dir / "Houses"
    car_files = list(houses_subdir.rglob(filepattern))
    if len(car_files) == 0:
        logging.info("No CarState files found.")
        return

    # count how many cars are in which state, for each timestep
    logging.info("Collecting car state files")
    state_counts = []
    for file in tqdm(car_files):
        with open(file, "r", encoding="utf8") as f:
            data = json.load(f)
        states = data["Values"]
        if not state_counts:
            # init state counts list
            state_counts = [defaultdict(int) for _ in states]
        else:
            assert len(state_counts) == len(states), "Different car state lengths"
        for i, state in enumerate(states):
            state_counts[i][state] += 1

    # store the result as a csv file
    df = pd.DataFrame(state_counts)
    df.fillna(0, inplace=True)
    df.index.name = "Timestep"
    output_dir.mkdir(parents=True, exist_ok=True)
    result_file = output_dir / "car_state_counts.csv"
    df.to_csv(result_file)


def travel_statistics(hh_dbs: dict[str, Path], output_dir: Path):
    # collect all travels
    all_travels = []
    logging.info("Collecting travels")
    for id, hh_db in tqdm(hh_dbs.items()):
        travels = travel_import.load_travels_from_db(hh_db)
        all_travels.extend(travels)
    # store travel data
    filepath = output_dir / "travels.pkl"
    with open(filepath, "wb") as f:
        pickle.dump(all_travels, f)
    logging.debug(f"Created travels file: {filepath}")
    df = pd.DataFrame([asdict(d) for d in all_travels])
    print(df.describe())


def main(city_result_dir: Path, output_dir: Path, hh_dbs: dict[str, Path]):
    """Contains all travel postprocessing of the city simulation.

    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the postpocessed data
    """
    get_car_state_counts(city_result_dir, output_dir)
    travel_statistics(hh_dbs, output_dir)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    city_result_dir = Path(
        "/projects4/2022-d-neuroth-phd/results/scenario_julich_02_transport"
    )
    output_dir = city_result_dir / SubDirs.POSTPROCESSED_DIR / SubDirs.TRANSPORT

    hh_dbs = activity_profiles.collect_household_dbs(city_result_dir)

    main(city_result_dir, output_dir, hh_dbs)
