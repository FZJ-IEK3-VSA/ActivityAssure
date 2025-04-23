"""
Analyze POI presence logs and create daily profiles.
"""

from dataclasses import dataclass
from datetime import date, datetime
import logging
from pathlib import Path

from matplotlib import pyplot as plt
from matplotlib import dates as mdates
import pandas as pd

from tqdm import tqdm


@dataclass
class PoiLog:
    """
    Stores a POI presence log, consisting of datetimes and the corresponding number
    of visitors present.
    """

    poi_id: str
    dates: list[datetime]
    presence: list[int]


@dataclass
class PoiDailyProfiles:
    """
    Stores a collection of daily presence profiles for one POI. The profiles are
    """

    poi_id: str
    profiles_by_date: dict[date, pd.DataFrame]


def parse_date_de(index_str: str) -> datetime:
    """Parse a datetime from the index part of a POI log entry, German format"""
    index_parts = index_str.split(" ")
    assert len(index_parts) == 3
    date_str = f"{index_parts[1]} {index_parts[2]}"
    parsed_datetime = datetime.strptime(date_str, "%d.%m.%Y %H:%M:%S")
    return parsed_datetime


def parse_date_en(index_str: str) -> datetime:
    """Parse a datetime from the index part of a POI log entry, US format"""
    index_parts = index_str.split(" ")
    assert len(index_parts) >= 3
    date_str = " ".join(index_parts[1:])
    parsed_datetime = datetime.strptime(date_str, "%m/%d/%Y %I:%M:%S %p")
    return parsed_datetime


def parse_poi_logfile(poi_file: Path) -> PoiLog:
    """
    Parse a single POI presence log from file.

    :param poi_file: path to the POI presence log file
    :return: the loaded POI log
    """
    with open(poi_file, "r") as f:
        lines = f.readlines()
    dates = []
    presences = []
    for line in lines:
        # line format: 003497 31.12.2019 10:17:00 - 1
        line = line.strip()
        parts = line.split(" - ")
        assert len(parts) == 2
        index = parts[0]
        presences.append(int(parts[1]))

        dt = parse_date_en(index)
        dates.append(dt)
    return PoiLog(poi_file.stem, dates, presences)


def load_poi_logs(poi_log_path: Path, filter: str = "") -> dict[str, PoiLog]:
    """
    Loads POI presence logs from CitySimulation result files.

    :param poi_log_path: path to the presence log directory
    :param filter: a filter to only load matching POI logs, defaults to ""
    :return: a dict of POI presence logs, using POI IDs as keys
    """
    poi_logs = {}
    files = list(poi_log_path.glob(f"*{filter}*.txt"))
    logging.info(f"Found {len(files)} POI log files")
    for poi_file in tqdm(files):
        assert poi_file.is_file()
        if filter not in poi_file.stem:
            # skip this file
            continue
        poi_log = parse_poi_logfile(poi_file)
        poi_logs[poi_log.poi_id] = poi_log
    return poi_logs


def get_daily_profiles(poi_log: PoiLog) -> PoiDailyProfiles:
    """
    Resample a POI presence log to fixed 1-minute resolution and split it into
    daily profiles.
    :param poi_log: the POI presence log to resample
    :return: a PoiDailyProfiles object containing the daily profiles
    """
    # create a dataframe with the dates as index and the presence as column
    df = pd.DataFrame({"dates": poi_log.dates, "presence": poi_log.presence})
    df.set_index("dates", inplace=True)
    # resample to daily frequency and sum the presence values
    daily_profile = df.resample("1min").ffill()

    # Create a "time of day" column
    daily_profile["time"] = daily_profile.index.time  # type: ignore
    # Group by date
    grouped = daily_profile.groupby(daily_profile.index.date)  # type: ignore

    groups = dict(iter(grouped))

    # Plot each day's data as a separate line
    plt.figure(figsize=(12, 6))
    return PoiDailyProfiles(poi_log.poi_id, groups)  # type: ignore


def plot_daily_profiles(
    dir: Path, profiles: PoiDailyProfiles, max_presence: int | None = None
):
    """
    Plots the daily profiles as line plots in a single chart.

    :param dir: directory to save the plots
    :param profiles: the profiles to plot
    :param max_presence: maximum presence value to get uniform y-axes, defaults to None
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    for group_date, group in profiles.profiles_by_date.items():
        # times = matplotlib.dates.date2num(group["time"])
        times = [datetime.combine(date(2025, 1, 1), t) for t in group["time"]]
        ax.plot(times, group["presence"], label=str(group_date))  # type: ignore
    ax.set_ylim(None, max_presence)
    ax.set_xlabel("Time of Day")
    ax.set_ylabel("Visitor Count")
    ax.set_title("Daily 24h Curves")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.legend()
    subdir = dir / "daily_visit_profiles"
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
        diff = group["presence"].diff()
        posdiff = diff[diff > 0]  # type: ignore
        total = posdiff.sum()
        visitors_per_day.append(total)
    hist_ax = pd.Series(visitors_per_day).plot.hist()
    hist_ax.set_xlabel("Number of Visitors per Day")
    subdir = dir / "daily_visitors_hist"
    subdir.mkdir(exist_ok=True, parents=True)
    fig.savefig(subdir / f"{profiles.poi_id}_visitors_per_day.png")
    plt.close(fig)


def main():
    # city_result_dir = Path("D:/LPG/Results/scenario_city-julich-street-grosse-rurstr")
    city_result_dir = Path("R:/city_simulation_results/scenario_city-julich_25")
    poi_log_path = city_result_dir / "Logs/poi_presence"

    poi_type = "Doctors Office"
    poi_logs = load_poi_logs(poi_log_path, poi_type)

    plot_dir = Path("./POI_plots") / poi_type

    max_presence = max(max(p.presence) for p in poi_logs.values())

    for poi in poi_logs.values():
        daily = get_daily_profiles(poi)
        plot_daily_visitors_histogram(plot_dir, daily)
        plot_daily_profiles(plot_dir, daily, max_presence)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
