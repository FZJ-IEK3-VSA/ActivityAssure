"""
Analyze POI presence logs and create daily profiles.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta
import json
import logging
from pathlib import Path

from matplotlib import pyplot as plt
from matplotlib import dates as mdates
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns
import pandas as pd

from tqdm import tqdm

from paths import DFColumnsPoi, SubDirs

#: relevant POIs for validation and analysis
RELEVANT_POI_TYPES = ["Pharmacy", "Supermarket", "Doctors Office"]

#: file extentsion of the POI logs
PRESENCE_LOG_FILE_EXT = ".csv"

#: time of day column for dataframes
TIME_COL = "Time"

#: time resolution of the simulation
TIME_RES = timedelta(minutes=1)

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
    Stores a collection of daily POI profiles for one POI.
    """

    poi_id: str
    day_profiles: pd.DataFrame


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
    logging.info(f"Found {len(files)} POI log files{filter_txt} in {poi_log_path.name}")
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
    df_res = df.resample("1min").ffill()
    assert isinstance(df_res.index, pd.DatetimeIndex), f"Unexpected data format: {df}"

    def dt_to_time_index(ts: pd.Series):
        ts.index = ts.index.time  # type: ignore

    # Group by date to get one column per day and one row per time
    df_res["date"] = df_res.index.date  # extract day
    df_res[TIME_COL] = df_res.index.time
    reshaped = df_res.pivot(
        index=TIME_COL, columns="date", values=DFColumnsPoi.PRESENCE
    )

    # fill missing values (before first and after last POI presence log entry)
    reshaped.fillna(0, inplace=True)
    return PoiDailyProfiles(poi_log.poi_id, reshaped)  # type: ignore


def raster_plot(
    plot_dir: Path, daily_presence: PoiDailyProfiles, max_presence: int | None = None
):
    df = daily_presence.day_profiles
    fig, ax = plt.subplots()  # (figsize=(15, 6), dpi=400)
    im = ax.imshow(df, aspect="auto", origin="upper", cmap="viridis")

    # Add colorbar
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Anzahl anwesender Kunden")

    # draw major ticks, but label minor ticks to put each label between two major ticks
    date_formatter = mdates.DateFormatter("%b")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(ticker.NullFormatter())
    ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonthday=16))
    ax.xaxis.set_minor_formatter(date_formatter)
    # remove the minor ticks
    for tick in ax.xaxis.get_minor_ticks():
        tick.tick1line.set_markersize(0)
        tick.tick2line.set_markersize(0)
        tick.label1.set_horizontalalignment("center")

    vals_per_day = len(df.index)

    # define y-ticks (time)
    def hour_formatter(x, pos):
        x = x * 24 / vals_per_day
        h = int(x)
        m = int((x - h) * 60)
        return f"{h % 24:02d}:{m:02d}"

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(hour_formatter))
    ax.set_yticks(np.linspace(0, vals_per_day, num=7))

    # Labels and title
    # ax.set_xlabel(f"{daily_presence.index[0].year}")
    ax.set_ylabel("Uhrzeit")
    fig.tight_layout()
    subdir = plot_dir / "visitors_raster"
    subdir.mkdir(exist_ok=True, parents=True)
    fig.savefig(
        subdir / f"{daily_presence.poi_id}_raster.svg", transparent=True, dpi="figure"
    )


def plot_daily_mean_histogram(
    dir: Path,
    poi_log: PoiLog,
    col: str = DFColumnsPoi.ARRIVE,
    stat_name: str = "Anzahl Besucher pro Tag",
):
    """
    Histogram showing the distribution of the number of visitors per day.

    :param dir: directory to save the plots
    :param poi_log: the PoiLog to plot
    """
    df = poi_log.data.set_index(DFColumnsPoi.DATETIME)
    assert isinstance(df.index, pd.DatetimeIndex), f"Unexpected data format: {df}"
    vals_per_day = df.groupby(df.index.date).mean()[col]

    fig, ax = plt.subplots()
    pd.Series(vals_per_day).plot.hist(ax=ax)
    ax.set_xlabel(stat_name)
    subdir = dir / f"hist_{col}"
    subdir.mkdir(exist_ok=True, parents=True)
    fig.savefig(subdir / f"{poi_log.poi_id}_{col}.svg")


def waiting_times_histogram(plot_subdir, poi_log):
    fig, ax = plt.subplots()
    poi_log.data[DFColumnsPoi.WAITING].plot.hist(ax=ax)
    ax.set_xlabel("Verteilung der Wartedauer [min]")
    subdir = plot_subdir / "waiting_hist"
    subdir.mkdir(parents=True, exist_ok=True)
    fig.savefig(subdir / f"{poi_log.poi_id}_waiting_hist.svg")


def violin_plot_per_hour(
    plot_subdir: Path,
    poi_log: PoiLog,
    daily_presence: PoiDailyProfiles,
    max_wait_time: int | None,
):
    df = poi_log.data
    hour = "Stunde"

    # make sure hours 0-23 are plotted, even if not in the data
    df[hour] = df[DFColumnsPoi.DATETIME].dt.hour
    hour_range = list(range(24))
    df[hour] = pd.Categorical(df[hour], categories=hour_range, ordered=True)

    fig, ax = plt.subplots()
    sns.violinplot(
        data=df,
        x=hour,
        y=DFColumnsPoi.WAITING,
        inner="quartile",  # shows median + quartiles
        cut=0,  # avoid extending violins beyond data range
        # scale="width",  # all violins same width for clarity
        palette="coolwarm",
        ax=ax,
    )
    ax.set_ylim(bottom=0, top=max_wait_time)
    ax.set_xlabel("Uhrzeit")
    ax.set_ylabel("Wartedauer [min]")
    ax.set_xticks(hour_range)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    # --- Line plot (secondary y-axis) ---
    mean_day_curve = daily_presence.day_profiles.mean(axis="columns")
    mean_hours = np.array([t.hour + t.minute / 60 for t in mean_day_curve.index])
    ax2 = ax.twinx()
    color = "tab:red"
    ax2.plot(
        mean_hours,
        mean_day_curve.values,  # type: ignore
        color=color,
        # linewidth=2,
        label="Durchschnittliche Anzahl Kunden",
    )
    ax2.set_ylabel("Durchschnittliche Anzahl Kunden", color=color)
    ax2.tick_params(axis="y", labelcolor=color)
    ax2.legend()
    # ax2.legend(loc='upper right')

    fig.tight_layout()
    # fig.show()
    subdir = plot_subdir / "waiting_violins"
    subdir.mkdir(parents=True, exist_ok=True)
    fig.savefig(subdir / f"{poi_log.poi_id}_waiting_violins.svg")


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


def group_pois_by_type(poi_logs: Iterable[PoiLog]) -> dict[str, list[PoiLog]]:
    """Groups POI logs by POI type.

    :param poi_logs: the POI logs
    :return: a dict of lists of POI logs, one list per POI type
    """
    pois_by_type: defaultdict[str, list[PoiLog]] = defaultdict(list)
    for poi in poi_logs:
        pois_by_type[poi.poi_type].append(poi)
    return pois_by_type


class PoiPlotter:
    """Helper class for creating POI plots"""

    def __init__(self, city_result_dir, plot_dir) -> None:
        self.city_result_dir = city_result_dir
        self.plot_dir = plot_dir
        self.output_dir = city_result_dir / SubDirs.POSTPROCESSED_DIR / SubDirs.POIS
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.presence_daily: dict[str, PoiDailyProfiles] = {}

    def create_poi_presence_plots(
        self, plot_subdir: Path, poi_log: PoiLog, max_presence: int | None
    ):
        # create daily presence profiles and store them
        daily = get_daily_presence_profiles(poi_log)
        self.presence_daily[poi_log.poi_id] = daily
        # plot_daily_profiles(plot_subdir, daily, max_presence)
        raster_plot(plot_subdir, daily, max_presence)

        # plot histograms of daily means
        plot_daily_mean_histogram(plot_subdir, poi_log)
        if DFColumnsPoi.CANCEL in poi_log.data:
            plot_daily_mean_histogram(
                plot_subdir,
                poi_log,
                DFColumnsPoi.CANCEL,
                "Anzahl abgewiesener Kunden pro Tag",
            )

    def create_poi_queue_plots(
        self, plot_subdir: Path, poi_log: PoiLog, max_wait_time: int | None
    ):
        plot_subdir.mkdir(parents=True, exist_ok=True)
        waiting_times_histogram(plot_subdir, poi_log)
        daily_presence = self.presence_daily[poi_log.poi_id]
        violin_plot_per_hour(plot_subdir, poi_log, daily_presence, max_wait_time)

    def process_poi_presence(self, poi_type: str = ""):
        # collect all POI logs
        poi_log_path = self.city_result_dir / SubDirs.LOGS / SubDirs.POI_PRESENCE
        self.poi_presence = load_poi_logs(poi_log_path, poi_type)
        if not self.poi_presence:
            logging.warning(f"Found no POI logs in {poi_log_path}")
            return
        check_poi_presence_data(self.poi_presence.values())

        # calculate some aggregated statistics
        visitor_counts = get_col_sum_per_poi(
            self.poi_presence.values(), DFColumnsPoi.ARRIVE
        )
        with open(
            self.output_dir / "total_visitor_counts.json", "w", encoding="utf8"
        ) as f:
            json.dump(visitor_counts, f, indent=4)
        cancel_counts = get_col_sum_per_poi(
            self.poi_presence.values(), DFColumnsPoi.CANCEL
        )
        with open(
            self.output_dir / "total_cancel_counts.json", "w", encoding="utf8"
        ) as f:
            json.dump(cancel_counts, f, indent=4)

        # create plots for all relevant POI types
        pois_by_type = group_pois_by_type(self.poi_presence.values())
        for poi_type in RELEVANT_POI_TYPES:
            if poi_type not in pois_by_type:
                logging.warning(f"No POI of type {poi_type} found")
                continue
            pois_of_type = pois_by_type[poi_type]
            # get the maximum presence to have a common axis for all POIs of the same type
            max_presence = max(p.get_presence().max() for p in pois_of_type)
            poi_type_subdir = self.plot_dir / poi_type
            for poi in pois_of_type:
                self.create_poi_presence_plots(poi_type_subdir, poi, max_presence)

    def process_poi_queues(self, poi_type: str = ""):
        # collect all POI queue logs
        poi_log_path = self.city_result_dir / SubDirs.LOGS / SubDirs.POI_QUEUE
        self.poi_queues = load_poi_logs(poi_log_path, poi_type)
        if not self.poi_queues:
            logging.warning(f"Found no POI queue logs in {poi_log_path}")
            return

        # calculate some aggregated statistics
        avg_wait_time = {
            poi_log.poi_id: int(poi_log.data[DFColumnsPoi.WAITING].mean())
            for poi_log in self.poi_queues.values()
        }
        with open(
            self.output_dir / "average_waiting_times.json", "w", encoding="utf8"
        ) as f:
            json.dump(avg_wait_time, f, indent=4)

        # create plots for all POI types
        pois_by_type = group_pois_by_type(self.poi_queues.values())
        for poi_type, pois_of_type in pois_by_type.items():
            # get the maximum waiting time to have a common axis for all POIs of the same type
            max_wait_time = max(
                p.data[DFColumnsPoi.WAITING].max() for p in pois_of_type
            )
            poi_type_subdir = self.plot_dir / poi_type
            for poi in pois_of_type:
                self.create_poi_queue_plots(poi_type_subdir, poi, max_wait_time)


def main(city_result_dir: Path, plot_dir: Path):
    poiplotter = PoiPlotter(city_result_dir, plot_dir)
    poi_type = "Pharmacy"
    poiplotter.process_poi_presence(poi_type)
    poiplotter.process_poi_queues(poi_type)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    city_result_dir2 = Path("R:/phd_dir/results/scenario_juelich_03_1month")
    # city_result_dir2 = Path("R:/phd_dir/results/archive/scenario_juelich_100_pharmacy")
    plot_dir2 = city_result_dir2 / "Postprocessed/plots/pois"
    main(city_result_dir2, plot_dir2)
