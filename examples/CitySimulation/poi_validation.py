"""
Analyze POI presence logs and create daily profiles.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
import json
import logging
from pathlib import Path

from matplotlib import pyplot as plt
from matplotlib import dates as mdates
import pandas as pd

from tqdm import tqdm

from paths import DFColumnsPoi, SubDirs

#: relevant POIs for validation and analysis
RELEVANT_POI_TYPES = ["Pharmacy", "Supermarket", "Doctors Office"]

#: file extentsion of the POI logs
PRESENCE_LOG_FILE_EXT = ".csv"

#: possible columns for a POI presence log (not all mandatory)
POI_PRESENCE_COLS = {
    DFColumnsPoi.TIMESTEP,
    DFColumnsPoi.DATETIME,
    DFColumnsPoi.PRESENCE,
    DFColumnsPoi.ARRIVE,
    DFColumnsPoi.LEAVE,
    # below columns are optional
    DFColumnsPoi.CANCEL,
}


@dataclass
class PoiLog:
    """
    Stores a POI presence log, consisting of datetimes and the corresponding number
    of visitors present.
    """

    poi_id: str
    data: pd.DataFrame
    poi_type: str = ""

    def get_presence(self) -> pd.Series:
        return self.data[DFColumnsPoi.PRESENCE]

    @staticmethod
    def poi_type_from_filename(filename: str) -> str:
        # assume the building ID does not contain a space, so everything behind the
        # last space is the ID, the rest is the POI type
        parts = filename.split(" ")
        return " ".join(parts[:-1])

    @staticmethod
    def load(poi_file: Path) -> "PoiLog":
        """
        Parse a POI log from file

        :param poi_file: path of the log file to load
        :return: the parsed POI log
        """
        df = pd.read_csv(poi_file, parse_dates=[1])
        poi_type = PoiLog.poi_type_from_filename(poi_file.stem)
        return PoiLog(poi_file.stem, df, poi_type)


@dataclass
class PoiDailyProfiles:
    """
    Stores a collection of daily presence profiles for one POI.
    """

    poi_id: str
    profiles_by_date: dict[date, pd.DataFrame]


def load_poi_logs(poi_log_path: Path, filter: str = "") -> dict[str, PoiLog]:
    """
    Loads POI logs from CitySimulation result files. These can be presence or
    queue logs.

    :param poi_log_path: path to the log directory
    :param filter: a filter to only load matching POI logs, defaults to ""
    :return: a dict of POI logs, using POI IDs as keys
    """
    poi_logs = {}
    pattern = f"*{filter}*" if filter else "*"
    filter_txt = f" of type {filter}" if filter else ""
    pattern += PRESENCE_LOG_FILE_EXT
    files = list(poi_log_path.glob(pattern))
    logging.info(
        f"Found {len(files)} POI log files{filter_txt} from {poi_log_path.name}"
    )
    skipped = 0
    for poi_file in tqdm(files):
        assert poi_file.is_file()
        if filter not in poi_file.stem:
            # skip this file
            continue
        poi_log = PoiLog.load(poi_file)

        if len(poi_log.data) == 0:
            # poi log is empty, skip it
            skipped += 1
            continue
        poi_logs[poi_log.poi_id] = poi_log
    if skipped > 0:
        logging.info(f"Skipped {skipped} empty POI log files{filter_txt}")
    return poi_logs


def get_daily_presence_profiles(poi_log: PoiLog) -> PoiDailyProfiles:
    """
    Resample a POI presence log to fixed 1-minute resolution and split it into
    daily profiles.
    :param poi_log: the POI presence log to resample
    :return: a PoiDailyProfiles object containing the daily profiles
    """
    # create a presence dataframe with datetime index
    df = poi_log.data.set_index(DFColumnsPoi.DATETIME)[[DFColumnsPoi.PRESENCE]]
    # resample to daily frequency and sum the presence values
    daily_profile = df.resample("1min").ffill()

    # Create a "time of day" column
    daily_profile["Time"] = daily_profile.index.time  # type: ignore
    # Group by date
    grouped = daily_profile.groupby(daily_profile.index.date)  # type: ignore

    groups: dict[date, pd.DataFrame] = dict(iter(grouped))
    return PoiDailyProfiles(poi_log.poi_id, groups)  # type: ignore


def plot_daily_profiles(
    plot_dir: Path, profiles: PoiDailyProfiles, max_presence: int | None = None
):
    """
    Plots the daily profiles as line plots in a single chart.

    :param plot_dir: directory to save the plots
    :param profiles: the profiles to plot
    :param max_presence: maximum presence value to get uniform y-axes, defaults to None
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    for group_date, group in profiles.profiles_by_date.items():
        # times = matplotlib.dates.date2num(group["time"])
        times = [datetime.combine(date(2025, 1, 1), t) for t in group["time"]]
        ax.plot(times, group[DFColumnsPoi.PRESENCE], label=str(group_date))  # type: ignore
    ax.set_ylim(None, max_presence)
    ax.set_xlabel("Time of Day")
    ax.set_ylabel("Visitor Count")
    ax.set_title("Daily 24h Curves")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.legend()
    subdir = plot_dir / "daily_visit_profiles"
    subdir.mkdir(exist_ok=True, parents=True)
    fig.savefig(subdir / f"{profiles.poi_id}.png")
    plt.close(fig)


def plot_daily_visitors_histogram(dir: Path, profiles: PoiDailyProfiles):
    """
    Histogram showing the distribution of the number of visitors per day.

    :param dir: directory to save the plots
    :param profiles: the profiles to plot
    """
    fig, ax = plt.subplots()
    visitors_per_day = []
    for group_date, group in profiles.profiles_by_date.items():
        diff = group[DFColumnsPoi.PRESENCE].diff()
        posdiff = diff[diff > 0]  # type: ignore
        total = posdiff.sum()
        visitors_per_day.append(total)
    hist_ax = pd.Series(visitors_per_day).plot.hist()
    hist_ax.set_xlabel("Number of Visitors per Day")
    subdir = dir / "daily_visitors_hist"
    subdir.mkdir(exist_ok=True, parents=True)
    fig.savefig(subdir / f"{profiles.poi_id}_visitors_per_day.png")
    plt.close(fig)


def create_poi_presence_plots(poi_type_subdir, max_presence, poi):
    daily = get_daily_presence_profiles(poi)
    plot_daily_visitors_histogram(poi_type_subdir, daily)
    plot_daily_profiles(poi_type_subdir, daily, max_presence)


def count_total_visitors_old(poi_log: PoiLog) -> int:
    """Old function for estimating visitor count, for when
    the "People arriving" column is still missing"""
    presence: pd.Series[int] = poi_log.get_presence()
    # sum increases in visitor numbers
    diff = presence.diff()
    positive = diff[diff >= 0]
    total = positive.sum()

    # if the visitor number stays the same, at least one person left and another
    # came; as an estimate, count one visitor for each such case
    zero_diffs = len(diff[diff == 0])
    total += zero_diffs
    if zero_diffs > 0:
        logging.debug(f"0 Diffs for {poi_log.poi_id}: {zero_diffs}")
    return int(total)


def get_col_sum_per_poi(
    poi_logs: Iterable[PoiLog], col: str = DFColumnsPoi.ARRIVE
) -> dict[str, int]:
    """Gets the sum of the specified column for every POI. For example,
    the sum of arrivals yields total visit numbers.

    :param poi_logs: the POI logs to process
    :param col: the column to sum
    :return: a dict containing the resulting value for every POI
    """
    return {
        poi_log.poi_id: int(poi_log.data[col].sum())
        for poi_log in poi_logs
        if col in poi_log.data
    }


def check_poi_presence_data(poi_logs: Iterable[PoiLog]) -> None:
    """Checks if the POI logs have the expected format.

    :param poi_logs: the POI logs to check
    """
    for poi_log in poi_logs:
        # check if the presence data has the expected format
        assert set(poi_log.data.columns).issubset(
            POI_PRESENCE_COLS
        ), f"Unexpected POI presence columns for {poi_log.poi_id}: {poi_log.data.columns}"


def process_poi_presence(city_result_dir: Path, output_dir: Path, plot_dir: Path):
    # collect all POI logs
    poi_log_path = city_result_dir / SubDirs.LOGS / SubDirs.POI_PRESENCE
    poi_logs = load_poi_logs(poi_log_path)
    if not poi_logs:
        logging.warning(f"Found no POI logs in {poi_log_path}")
        return
    check_poi_presence_data(poi_logs.values())

    # group all POIs by type
    pois_by_type: defaultdict[str, list[PoiLog]] = defaultdict(list)
    for poi in poi_logs.values():
        pois_by_type[poi.poi_type].append(poi)

    # calculate some aggregated statistics
    visitor_counts = get_col_sum_per_poi(poi_logs.values(), DFColumnsPoi.ARRIVE)
    with open(output_dir / "total_visitor_counts.json", "w", encoding="utf8") as f:
        json.dump(visitor_counts, f, indent=4)
    cancel_counts = get_col_sum_per_poi(poi_logs.values(), DFColumnsPoi.CANCEL)
    with open(output_dir / "total_cancel_counts.json", "w", encoding="utf8") as f:
        json.dump(cancel_counts, f, indent=4)

    # create plots for all relevant POI types
    for poi_type in RELEVANT_POI_TYPES:
        if poi_type not in pois_by_type:
            logging.warning(f"No POI of type {poi_type} found")
        pois_of_type = pois_by_type[poi_type]
        # get the maximum presence to have a common axis for all POIs of the same type
        max_presence = max(p.get_presence().max() for p in pois_of_type)
        poi_type_subdir = plot_dir / poi_type
        for poi in pois_of_type:
            create_poi_presence_plots(poi_type_subdir, max_presence, poi)


def process_poi_queues(city_result_dir: Path, output_dir: Path, plot_dir: Path):
    # collect all POI logs
    poi_log_path = city_result_dir / SubDirs.LOGS / SubDirs.POI_QUEUE
    poi_logs = load_poi_logs(poi_log_path)
    if not poi_logs:
        logging.warning(f"Found no POI logs in {poi_log_path}")
        return

    # calculate some aggregated statistics
    avg_wait_time = {
        poi_log.poi_id: int(poi_log.data[DFColumnsPoi.WAITING].mean())
        for poi_log in poi_logs.values()
    }
    with open(output_dir / "average_waiting_times.json", "w", encoding="utf8") as f:
        json.dump(avg_wait_time, f, indent=4)


def main(city_result_dir: Path, plot_dir: Path):
    output_dir = city_result_dir / SubDirs.POSTPROCESSED_DIR / SubDirs.POIS
    output_dir.mkdir(parents=True, exist_ok=True)
    process_poi_presence(city_result_dir, output_dir, plot_dir)
    process_poi_queues(city_result_dir, output_dir, plot_dir)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # city_result_dir = Path("R:/phd_dir/results/scenario_juelich_03_1month")
    city_result_dir = Path("R:/phd_dir/results/archive/scenario_juelich_100_pharmacy")
    plot_dir = city_result_dir / "Postprocessed/plots/pois"
    main(city_result_dir, plot_dir)
