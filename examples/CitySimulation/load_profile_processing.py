"""Aggregates result load profiles produced by the city simulation to get
sum profiles for the whole city"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
import itertools
import logging
from pathlib import Path
import pickle
from typing import Iterable

import numpy as np
import psutil
import pandas as pd

from activityassure import utils
from activityassure.loadprofiles import utils as loadutils

from paths import DFColumnsLoad, LoadFiles


#: defines the date format used in the csv files
DATEFORMAT_DE = "%d.%m.%Y %H:%M"
DATEFORMAT_EN = "%m/%d/%Y %I:%M %p"
DATEFORMATS = [DATEFORMAT_EN, DATEFORMAT_DE]


class ObjectType(StrEnum):
    """object type for which there are load profiles"""

    HOUSE = "House"
    HOUSEHOLD = "Household"


@dataclass
class ProfileInfo:
    """Information to identify and load a profile from a csv file"""

    id: str
    path: Path


def get_stats_df(data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates statistics profiles for the given dataframe. The statistics
    are calculated per timestep, so the max column, e.g., contains the
    maximum load out of all houses in each timestep.

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


@utils.timing
def calc_simultaneity(
    data: pd.DataFrame, permutations: int = 1
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculates the simultaneity of the given load profiles.
    Formula for a single simultaneity value: max of sumprofile / sum of profile maxs

    Also returns the maximums of cumulative sumprofiles, which is an intermediate step
    and the curve used by DIN 18015-1 Anhang A as basis for assessment of main lines.

    :param data: dataframe with all house load profiles of a city
    :param permutations: number of different random column permutations to calculate
                         simultaneity for to check how robust the simultaneity is
    :return: tuple containing dataframe with simultaneity values and dataframe with
             the max of cumulative sums
    """
    simultaneity_list, max_of_sumprofiles_list = [], []
    # determine the maximum load of each house/household
    hh_maximums = data.max(axis=0)
    for i in range(permutations):
        # determine a new random column order
        col_order = np.random.permutation(data.columns)

        # get cumulative house/household sums per timestep
        cumsum_per_timestep = data[col_order].cumsum(axis=1)
        # get the maximum of each of the cumulative sum profiles
        maxs_of_sumprofiles = cumsum_per_timestep.max(axis=0)
        # get the cumulative sum of house/household maximums
        sums_of_maxs = hh_maximums[col_order].cumsum()

        simultaneity = maxs_of_sumprofiles / sums_of_maxs

        # drop the index to avoid reordering during concatenation below
        maxs_of_sumprofiles.reset_index(drop=True, inplace=True)
        max_of_sumprofiles_list.append(maxs_of_sumprofiles)
        simultaneity.reset_index(drop=True, inplace=True)
        simultaneity_list.append(simultaneity)

    max_of_sumprofiles_df = pd.concat(max_of_sumprofiles_list, axis="columns")
    simultaneity_curves = pd.concat(simultaneity_list, axis="columns")
    logging.info(f"Simultaneity value: {simultaneity_curves.iloc[-1, 0]}")
    return simultaneity_curves, max_of_sumprofiles_df


@utils.timing
def aggregate_load_profiles(data_kwh: pd.DataFrame, result_dir: Path, object_type: str):
    """
    Generate some aggregated profiles and statistics from a dataframe
    containing all house load profiles.

    :param data: dataframe with all house load profiles of a city in kWh
    :param result_dir: ouput directory for the aggregated data
    :param object_type: name of the object type, used as column header
    """
    result_dir = result_dir / f"aggregated_{object_type.lower()}"
    result_dir.mkdir(parents=True, exist_ok=True)

    data_kwh.set_index(DFColumnsLoad.TIME, inplace=True)
    data_w = loadutils.kwh_to_w(data_kwh)

    # store total demand (in kWh) and average load (the same in W) in one file
    total_demands = data_kwh.sum()
    average_loads = data_w.mean()
    total = pd.concat(
        {
            DFColumnsLoad.TOTAL_DEMAND: total_demands,
            DFColumnsLoad.AVERAGE_LOAD: average_loads,
        },
        axis=1,
    )
    total.index.name = object_type
    total.to_csv(result_dir / LoadFiles.TOTALS)

    city_profile = data_w.sum(axis=1)
    city_profile.name = DFColumnsLoad.TOTAL_LOAD
    city_profile.to_csv(result_dir / LoadFiles.SUMPROFILE)

    # calc statistics per profile
    profile_stats = data_w.describe()
    profile_stats.to_csv(result_dir / LoadFiles.PROFILE_STATS)

    # calc statistics per timestep, across profiles
    stats = get_stats_df(data_w)
    stats.to_csv(result_dir / LoadFiles.STAT_PROFILES)

    dayprofiles = split_cols_into_single_days(data_w)
    daystats = get_stats_df(dayprofiles)
    daystats.to_csv(result_dir / LoadFiles.DAYPROFILESTATS)

    # calc mean day profiles and statistics
    meanday = data_w.groupby(data_w.index.time).mean()  # type: ignore
    meanday.to_csv(result_dir / LoadFiles.MEANDAY)
    meanday_stats = get_stats_df(meanday)
    meanday_stats.to_csv(result_dir / LoadFiles.MEANDAY_STATS)

    # calc mean day profiles for each day type
    meandaytype = data_w.groupby([data_w.index.weekday, data_w.index.time]).mean()  # type: ignore
    meandaytype.to_csv(result_dir / LoadFiles.MEANDAYTYPES)
    meandaytype_stats = get_stats_df(meandaytype)
    meandaytype_stats.to_csv(result_dir / LoadFiles.MEANDAYTYPE_STATS)

    # calc simultaneity
    simultaneity, sum_maxs_curves = calc_simultaneity(data_w, 3)
    sum_maxs_curves.to_csv(result_dir / LoadFiles.CUMSUMMAXS)
    simultaneity.to_csv(result_dir / LoadFiles.SIMULTANEITY)


def split_cols_into_single_days(data: pd.DataFrame) -> pd.DataFrame:
    """
    If a dataframe spans multiple days, this splits up each column into multiple
    new columns, one for each day. The new index consist only of the time of day.

    :param data: data to split up
    :return: the split up profiles
    """
    data = data.copy()
    assert isinstance(data.index, pd.DatetimeIndex), "Data must have a DatetimeIndex"
    data["time"] = data.index.time
    data["date"] = data.index.date
    dayprofiles = data.pivot(index="time", columns="date")
    return dayprofiles


@utils.timing
def combine_dataframes(
    profiles: list[ProfileInfo],
    data_col,
    result_file_path: Path,
):
    """
    Loads all specified load profiles from csv files and merges them into a single
    dataframe.

    :param profiles: specifications of the profiles to load
    :param data_col: title of the data column to load
    :param result_file_path: filepath to save the resulting dataframe to
    :return: the merged dataframe
    """
    profile_num = len(profiles)
    logging.info(f"Combining {profile_num} load profiles.")

    # parse first file completely, including time stamps
    # try different date formats, as timestamps from the LPG depend on the locale
    data = None
    for dateformat in DATEFORMATS:
        data = pd.read_csv(
            profiles[0].path,
            sep=";",
            index_col=False,
            parse_dates=[DFColumnsLoad.TIME],
            date_format=dateformat,
            dtype={0: int, data_col: float},
        )
        if data[DFColumnsLoad.TIME].dtype == "datetime64[ns]":
            # data successfully parsed
            break

        # wrong date format, try again with the next format
        logging.warning(
            f"Time column not parsed correctly with dateformat {dateformat}, trying again."
        )
    assert data is not None, f"Could not load the data file {profiles[0].path}."
    assert (
        data[DFColumnsLoad.TIME].dtype == "datetime64[ns]"
    ), f"Time column could not be parsed correctly (first value: {data['Time'][0]}"

    TIMESTEP_COL = "Electricity.Timestep"
    data.set_index(TIMESTEP_COL, inplace=True)
    data.rename(columns={data_col: profiles[0].id}, inplace=True)

    # parse all other profiles
    collected_profiles = []
    last_update = datetime.now()
    for i, profile_info in enumerate(profiles[1:]):
        profile = pd.read_csv(
            profile_info.path,
            sep=";",
            index_col=False,
            usecols=[TIMESTEP_COL, data_col],
        )
        profile.set_index(TIMESTEP_COL, inplace=True)
        profile.rename(columns={data_col: profile_info.id}, inplace=True)
        collected_profiles.append(profile)

        # regularly combine all collected dataframes
        is_last_iteration = profile_info == profiles[-1]
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
                f"Progress: {i}/{profile_num} ({100 * i / profile_num:.1f}%), RAM usage: {ram} MiB"
            )
            last_update = datetime.now()

    logging.info(
        f"Finished merging profiles, storing the resulting dataframe in {result_file_path}"
    )
    result_file_path.parent.mkdir(parents=True, exist_ok=True)
    # determine result format
    match result_file_path.suffix:
        case ".csv":
            data.to_csv(result_file_path)
        case _:
            with open(result_file_path, "wb") as f:
                pickle.dump(data, f)
    return data


@utils.timing
def combine_house_profiles_to_single_df(
    city_result_dir: Path, result_file_path: Path
) -> pd.DataFrame:
    """
    Loads all house sum electricity profiles from a city simulation and merges them
    into a single dataframe. The resulting dataframe is saved to the output directory,
    along with some aggregated data.

    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the merged dataframe
    """

    # relative path of the LPG result file to aggregate
    filename = Path("Results/Overall.SumProfiles.Electricity.csv")
    data_col_name = "Sum [kWh]"

    # collect all house sum load profiles
    houses_subdir = city_result_dir / "Houses"
    files = [ProfileInfo(d.name, d / filename) for d in houses_subdir.iterdir()]

    data = combine_dataframes(files, data_col_name, result_file_path)
    return data


@utils.timing
def combine_household_profiles_to_single_df(
    city_result_dir: Path, result_file_path: Path
) -> pd.DataFrame:
    """
    Loads all house sum electricity profiles from a city simulation and merges them
    into a single dataframe. The resulting dataframe is saved to the output directory,
    along with some aggregated data.

    :param city_result_dir: result directory of the city simulation
    :param result_file_path: result file path for the merged dataframe
    """
    # pattern of the LPG result files to aggregate
    file_prefix = "SumProfiles_600s."
    file_suffix = ".Electricity"
    filepattern = f"Results/{file_prefix}HH*{file_suffix}.csv"
    data_col_name = "Sum [kWh]"

    # collect all household load profiles
    houses_subdir = city_result_dir / "Houses"
    files = [
        ProfileInfo(
            f"{file.parent.parent.name}_"
            + str(file.stem).removeprefix(file_prefix).removesuffix(file_suffix),
            file,
        )
        for file in houses_subdir.rglob(filepattern)
    ]

    data = combine_dataframes(files, data_col_name, result_file_path)
    return data


def process_profiles(city_result_dir: Path, output_dir: Path, object_type: ObjectType):
    """Processes all house or household profiles, merging and aggregating them.

    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the postpocessed data
    :param object_type: type of profile to process
    """
    # merge all profile files, or load an existing merged dataframe
    merged_df_path = output_dir / f"City.{object_type}s.Electricity.pickle"
    if merged_df_path.is_file():
        logging.warning(
            f"Reusing existing merged {object_type} dataframe file: {merged_df_path}"
        )
        with open(merged_df_path, "rb") as f:
            data = pickle.load(f)
    else:
        # collect and merge the profiles depending on the object type
        match object_type:
            case ObjectType.HOUSE:
                data = combine_house_profiles_to_single_df(
                    city_result_dir, merged_df_path
                )
            case ObjectType.HOUSEHOLD:
                data = combine_household_profiles_to_single_df(
                    city_result_dir, merged_df_path
                )
            case _:
                raise Exception(f"Unknown object type: {object_type}")

    # calculate and save agggregated values from the merged dataframe
    aggregate_load_profiles(data, output_dir, object_type)


@utils.timing
def main(city_result_dir: Path, output_dir: Path):
    """
    Contains all postprocessing steps of load profiles generated by the city simulation.

    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the postpocessed data
    """
    process_profiles(city_result_dir, output_dir, ObjectType.HOUSEHOLD)
    process_profiles(city_result_dir, output_dir, ObjectType.HOUSE)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    city_result_dir = Path(
        "/fast/home/d-neuroth/city_simulation_results/scenario_city-julich_25"
    )
    city_result_dir = Path("R:/phd_dir/results/scenario_juelich_100_3kW")
    output_dir = city_result_dir / "Postprocessed/loads"

    main(city_result_dir, output_dir)
