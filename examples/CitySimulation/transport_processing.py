"""Travel-related postprocessing of the city simulation"""

import json
from pathlib import Path
from collections import defaultdict
import logging

import pandas as pd
from tqdm import tqdm

from paths import SubDirs


def get_car_state_counts(city_result_dir: Path, output_dir: Path):
    """Counts how many cars are in which state (driving, charging, etc.)
    in each timestep.

    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the postpocessed data
    """
    # pattern of the LPG result files to aggregate
    file_prefix = "CarState.Car"
    filepattern = f"Results/{file_prefix}*.json"

    # collect state files for all cars from all households
    houses_subdir = city_result_dir / "Houses"
    car_files = list(houses_subdir.rglob(filepattern))
    if len(car_files) == 0:
        logging.info("No CarState files found.")
        return

    # count how many cars are in which state, for each timestep
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
    df.index.name = "Timestep"
    output_dir.mkdir(parents=True, exist_ok=True)
    result_file = output_dir / "car_state_counts.csv"
    df.to_csv(result_file)


def main(city_result_dir: Path, output_dir: Path):
    """Contains all travel postprocessing of the city simulation.

    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the postpocessed data
    """
    get_car_state_counts(city_result_dir, output_dir)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    city_result_dir = Path("R:/phd_dir/results/scenario_julich_02")
    city_result_dir = Path(r"C:\LPG\Results\scenario_julich")
    output_dir = city_result_dir / SubDirs.POSTPROCESSED_DIR / SubDirs.TRANSPORT

    main(city_result_dir, output_dir)
