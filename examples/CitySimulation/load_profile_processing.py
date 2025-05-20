"""Aggregates result load profiles produced by the city simulation to get
sum profiles for the whole city"""

from datetime import datetime, timedelta
import itertools
import logging
from pathlib import Path
from typing import Iterable

import psutil
import pandas as pd


class Files:
    """File names for aggregated load profile data"""

    STATS = "stat_profiles.csv"
    TOTALS = "total_load_per_house.csv"
    CITYSUM = "city_profile.csv"
    MEANDAY = "mean_day_profile.csv"
    MEANDAY_STATS = "mean_day_stats.csv"


def get_stats_df(data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates statistics profiles for the given dataframe.

    :param data: dataframe with all house load profiles of a city
    :return: statistics dataframe
    """
    stats = pd.DataFrame()
    stats.index = data.index
    stats["mean"] = data.mean(axis=1)
    stats["min"] = data.min(axis=1)
    stats["max"] = data.max(axis=1)
    stats["median"] = data.quantile(axis=1, q=0.5)
    stats["q1"] = data.quantile(axis=1, q=0.25)
    stats["q3"] = data.quantile(axis=1, q=0.75)
    return stats


def aggregate_house_load_profiles(data: pd.DataFrame, result_dir: Path):
    """
    Generate some aggregated profiles and statistics from a dataframe
    containing all house load profiles.

    :param data: dataframe with all house load profiles of a city
    :param result_dir: ouput directory for the aggregated data
    """
    # data.drop(columns="Electricity.Timestep", inplace=True)
    # data.drop(columns="Unnamed: 0", inplace=True)
    data.set_index("Time", inplace=True)

    totals = data.sum()
    totals.name = "Load [kWh]"
    totals.index.name = "House"
    totals.to_csv(result_dir / Files.TOTALS)
    city_profile = data.sum(axis=1)
    city_profile.name = "Load [kWh]"
    city_profile.to_csv(result_dir / Files.CITYSUM)

    stats = get_stats_df(data)
    stats.to_csv(result_dir / Files.STATS)

    meanday = data.groupby(data.index.time).mean()  # type: ignore
    meanday.to_csv(result_dir / Files.MEANDAY)


def combine_house_profiles_to_single_df(city_result_dir: Path, output_dir: Path):
    """
    Loads all house sum electricity profiles from a city simulation and merges them
    into a single dataframe. The resulting dataframe is saved to the output directory,
    along with some aggregated data.

    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the merged dataframe
    """
    dateformat_de = "%d.%m.%Y %H:%M"
    dateformat_en = "%m/%d/%Y %I:%M %p"
    dateformat = dateformat_de

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
    data.set_index("Electricity.Timestep", inplace=True)

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

    # also calculate and save agggregated values from the merged dataframe
    aggregate_house_load_profiles(data, output_dir)


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
    combine_house_profiles_to_single_df(city_result_dir, output_dir)
