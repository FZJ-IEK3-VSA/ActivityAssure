"""Aggregates result load profiles produced by the city simulation to get
sum profiles for the whole city"""

from datetime import datetime, timedelta
import itertools
import logging
from pathlib import Path
from typing import Iterable

import psutil
import pandas as pd


def aggregate_load_sum_profiles(city_result_dir: Path, output_dir: Path):
    dateformat_de = "%d.%m.%Y %H:%M"
    dateformat_en = "%m/%d/%Y %I:%M %p"
    dateformat = dateformat_en

    # relative path of the LPG result file to aggregate
    filename = Path("Results/Overall.SumProfiles.Electricity.csv")
    data_col_name = "Sum [kWh]"

    houses_subdir = city_result_dir / "Houses"
    house_dirs = list(houses_subdir.iterdir())
    house_num = len(house_dirs)
    output_dir.mkdir(parents=True, exist_ok=True)
    result_file_path = output_dir / "City.SumProfiles.Electricity.csv"
    logging.info(f"Aggregating load profiles from {house_num} houses.")

    # parse first file completely, including time stamps
    data = pd.read_csv(
        house_dirs[0] / filename,
        sep=";",
        index_col=False,
        parse_dates=["Time"],
        date_format=dateformat,
        dtype={0: int, data_col_name: float},
    )
    data.rename(columns={data_col_name: house_dirs[0].name}, inplace=True)

    # parse the sum profiles from all other houses
    collected_profiles = []
    last_update = datetime.now()
    for i, house_dir in enumerate(house_dirs[1:]):
        profile_path = house_dir / filename
        profile = pd.read_csv(
            profile_path, sep=";", index_col=False, usecols=[data_col_name]
        )
        profile.rename(columns={data_col_name: house_dir.name}, inplace=True)
        collected_profiles.append(profile)

        # regularly combine all collected dataframes
        is_last_iteration = house_dir == house_dirs[-1]
        if i % 500 == 0 or is_last_iteration:
            if data is not None:
                # add the alread concatenated profiles
                all_profiles: Iterable[pd.DataFrame] = itertools.chain(
                    [data], collected_profiles
                )
            else:
                all_profiles = collected_profiles

            # concatenate the dataframes
            data = pd.concat(all_profiles, axis="columns")
            # reset the list
            collected_profiles = []

        # log progress
        if datetime.now() - last_update > timedelta(seconds=30):
            ram = round(psutil.Process().memory_info().rss / 1024**2)
            logging.info(
                f"Progress: {i}/{house_num} ({100 * i / house_num:.1f}%), RAM usage: {ram} MiB"
            )
            last_update = datetime.now()

    logging.info(
        f"Finished merging profiles, storing the resulting dataframe in {result_file_path}"
    )
    assert data is not None
    data.to_csv(result_file_path)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    city_result_dir = Path(
        "/fast/home/d-neuroth/city_simulation_results/scenario_city-julich_25"
    )
    # city_result_dir = Path("D:/LPG/Results/test")
    output_dir = Path(f"data/city/postprocessed/{city_result_dir.name}")
    aggregate_load_sum_profiles(city_result_dir, output_dir)
