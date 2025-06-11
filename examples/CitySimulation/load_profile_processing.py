"""Aggregates result load profiles produced by the city simulation to get
sum profiles for the whole city"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import itertools
import logging
from pathlib import Path
from typing import Iterable, TypeVar

import numpy as np
import psutil
import pandas as pd

from paths import DFColumns, LoadFiles

#: defines the date format used in the csv files
DATEFORMAT_DE = "%d.%m.%Y %H:%M"
DATEFORMAT_EN = "%m/%d/%Y %I:%M %p"
DATEFORMATS = [DATEFORMAT_EN, DATEFORMAT_DE]

#: type annotation for a dataframe or series
T_PD_DATA = TypeVar("T_PD_DATA", pd.Series, pd.DataFrame)


def rename_suffix(data: T_PD_DATA, old_suffix: str, new_suffix: str) -> None:
    """Replaces a suffix in all column names of a pandas data object inplace, where it
    occurs.

    :param data: the str to change
    :param old_suffix: the suffix to replace
    :param new_suffix: the new suffix to use instead
    """
    # define a function to replace the suffix in an str if it is present
    def replace_name(col):
        return (
            col.removesuffix(old_suffix) + new_suffix
            if col.endswith(old_suffix)
            else col
        )

    # apply the replacement function to the data
    if isinstance(data, pd.DataFrame):
        data.rename(
            columns=replace_name,
            inplace=True,
        )
    else:
        data.name = replace_name(data.name)


def timedelta_to_hours(td: timedelta) -> float:
    """Convert a timedelta to a float value in hours"""
    return td.total_seconds() / 3600


def get_resolution(data: pd.DataFrame | pd.Series) -> pd.Timedelta:
    """Returns the resolution of a pandas data object with a time index.
    Checks whether the resolution is consistent.

    :param data: the data object
    :return: the temporal resolution of the data
    """
    time_differences = data.index.diff().dropna()  # type: ignore
    assert len(set(time_differences)) == 1, "Index of data is not equidistant"
    return time_differences[0]


def kwh_to_w(data: T_PD_DATA, rename: bool = True) -> T_PD_DATA:
    """Convert

    :param data: _description_
    :param rename: _description_, defaults to True
    :return: _description_
    """
    resolution = get_resolution(data)
    res_in_h = timedelta_to_hours(resolution)
    factor = 1000 / res_in_h
    converted = data * factor
    if rename:
        rename_suffix(converted, "[kWh]", "[W]")
    return converted


@dataclass
class ProfileInfo:
    """Information to identify and load a profile from a csv file"""

    id: str
    path: Path


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


def calc_simultaneity(data: pd.DataFrame, permutations: int = 1) -> pd.DataFrame:
    """
    Calculates the simultaneity of the given load profiles.

    :param data: dataframe with all house load profiles of a city
    :param permutations: number of different random column permutations to calculate
                         simultaneity for to check how robust the simultaneity is
    :return: dataframe with simultaneity values
    """
    simultaneity_list = []
    for i in range(permutations):
        simultaneity = pd.Series(
            [
                data.iloc[:, :n].sum(axis=1).max() / data.iloc[:, :n].max().sum()
                for n in range(1, data.shape[1] + 1)
            ]
        )
        simultaneity_list.append(simultaneity)
        # shuffle the columns to get another simultaneity curve for more robust results
        data = data[np.random.permutation(data.columns)]
    simultaneity_curves = pd.concat(simultaneity_list, axis="columns")
    logging.info(f"Simultaneity value: {simultaneity_curves.iloc[-1, 0]}")
    return simultaneity_curves


def aggregate_load_profiles(
    data: pd.DataFrame, result_dir: Path, object_type: str = "Household"
):
    """
    Generate some aggregated profiles and statistics from a dataframe
    containing all house load profiles.

    :param data: dataframe with all house load profiles of a city
    :param result_dir: ouput directory for the aggregated data
    :param object_type: name of the object type, used as column header
    """
    result_dir = result_dir / f"aggregated_{object_type.lower()}"
    result_dir.mkdir(parents=True, exist_ok=True)

    data.set_index(DFColumns.TIME, inplace=True)
    data = kwh_to_w(data)

    totals = data.sum()
    totals.name = DFColumns.LOAD
    totals.index.name = object_type
    totals.to_csv(result_dir / LoadFiles.TOTALS)
    city_profile = data.sum(axis=1)
    city_profile.name = DFColumns.LOAD
    city_profile.to_csv(result_dir / LoadFiles.SUMPROFILE)

    stats = get_stats_df(data)
    stats.to_csv(result_dir / LoadFiles.STATS)

    # calc mean day profiles and statistics
    meanday = data.groupby(data.index.time).mean()  # type: ignore
    meanday.to_csv(result_dir / LoadFiles.MEANDAY)
    meanday_stats = get_stats_df(meanday)
    meanday_stats.to_csv(result_dir / LoadFiles.MEANDAY_STATS)

    # calc mean day profiles for each day type
    meandaytype = data.groupby([data.index.weekday, data.index.time]).mean()  # type: ignore
    meandaytype.to_csv(result_dir / LoadFiles.MEANDAYTYPES)
    meandaytype_stats = get_stats_df(meandaytype)
    meandaytype_stats.to_csv(result_dir / LoadFiles.MEANDAYTYPE_STATS)

    # calc simultaneity
    simultaneity = calc_simultaneity(data, 3)
    simultaneity.to_csv(result_dir / LoadFiles.SIMULTANEITY)


def combine_dataframes(profiles: list[ProfileInfo], data_col, result_file_path: Path):
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
            parse_dates=[DFColumns.TIME],
            date_format=dateformat,
            dtype={0: int, data_col: float},
        )
        if data[DFColumns.TIME].dtype == "datetime64[ns]":
            # data successfully parsed
            break

        # wrong date format, try again with the next format
        logging.warning(
            f"Time column not parsed correctly, trying again with dateformat {dateformat}."
        )
        dateformat = DATEFORMAT_DE
        assert data[DFColumns.TIME].dtype != "datetime64[ns]", (
            f"Time column not parsed correctly (first value: {data['Time'][0]}, specified dateformat: {dateformat})"
        )
    assert data is not None, f"Could not load the data file {profiles[0].path}."

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
    data.to_csv(result_file_path)
    return data


def combine_house_profiles_to_single_df(city_result_dir: Path, output_dir: Path):
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

    result_file_path = output_dir / "City.HouseSums.Electricity.csv"
    data = combine_dataframes(files, data_col_name, result_file_path)

    # also calculate and save agggregated values from the merged dataframe
    aggregate_load_profiles(data, output_dir, "House")


def combine_household_profiles_to_single_df(city_result_dir: Path, output_dir: Path):
    """
    Loads all house sum electricity profiles from a city simulation and merges them
    into a single dataframe. The resulting dataframe is saved to the output directory,
    along with some aggregated data.

    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the merged dataframe
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
            f"{house_dir.name}_"
            + str(d.stem).removeprefix(file_prefix).removesuffix(file_suffix),
            d,
        )
        for house_dir in houses_subdir.iterdir()
        for d in house_dir.glob(filepattern)
    ]

    result_file_path = output_dir / "City.HouseholdSums.Electricity.csv"
    data = combine_dataframes(files, data_col_name, result_file_path)

    # also calculate and save agggregated values from the merged dataframe
    aggregate_load_profiles(data, output_dir, "Household")


def main(city_result_dir: Path, output_dir: Path):
    """
    Contains all postprocessing steps of load profiles generated by the city simulation.

    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the postpocessed data
    """
    combine_household_profiles_to_single_df(city_result_dir, output_dir)
    combine_house_profiles_to_single_df(city_result_dir, output_dir)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    city_result_dir = Path(
        "/fast/home/d-neuroth/city_simulation_results/scenario_city-julich_25"
    )
    # city_result_dir = Path("D:/LPG/Results/scenario_julich-grosse-rurstr")
    output_dir = city_result_dir / "Postprocessed/loads"

    main(city_result_dir, output_dir)
