"""
Analyze POI presence logs and create daily profiles.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta, time
import functools
import json
import logging
from pathlib import Path

from matplotlib import pyplot as plt
from matplotlib import dates as mdates
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns
import pandas as pd
from cmcrameri import cm

from tqdm import tqdm

from activityassure import utils
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

sns.set_theme()


def poi_type_from_filename(filename: str) -> str:
    # assume the building ID does not contain a space, so everything behind the
    # last space is the ID, the rest is the POI type
    parts = filename.split(" ")
    return " ".join(parts[:-1])


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
    def load(poi_file: Path, index=None) -> "PoiLog":
        """
        Parse a POI log from file

        :param poi_file: path of the log file to load
        :return: the parsed POI log
        """
        df = pd.read_csv(poi_file, parse_dates=[1], index_col=index)
        df.drop(columns=[DFColumnsPoi.TIMESTEP], inplace=True)
        poi_type = poi_type_from_filename(poi_file.stem)
        return PoiLog(poi_file.stem, df, poi_type)


def combine_poi_presence_logs(logs: list[PoiLog]) -> PoiLog:
    dfs = [p.data for p in logs]
    merged = functools.reduce(lambda left, right: left.add(right, fill_value=0), dfs)
    return PoiLog("all", merged, logs[0].poi_type)


def combine_poi_queue_logs(logs: list[PoiLog]) -> PoiLog:
    dfs = [p.data for p in logs]
    merged = pd.concat(dfs, ignore_index=True)
    return PoiLog("all", merged, logs[0].poi_type)


@dataclass
class PoiDailyProfiles:
    """
    Stores a collection of daily POI profiles for one POI.
    """

    poi_id: str
    day_profiles: pd.DataFrame
    column: str


def load_poi_logs(
    poi_log_path: Path, filter: str = "", index_col: str | None = None
) -> dict[str, PoiLog]:
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
        poi_log = PoiLog.load(poi_file, index_col)

        if len(poi_log.data) == 0:
            # poi log is empty, skip it
            skipped += 1
            continue
        poi_logs[poi_log.poi_id] = poi_log
    if skipped > 0:
        logging.info(f"Skipped {skipped} empty POI log files{filter_txt}")
    return poi_logs


def add_mean_median_to_hist(data_col: pd.Series, ax):
    """Adds a mean and median line to a plot.

    :param data_col: the data series to calculate statistics for
    :param ax: the plot ax object to add the lines to
    """
    mean_val = data_col.mean()
    ax.axvline(
        mean_val,
        color="tab:red",
        linestyle="-",
        linewidth=3,
        label=f"Mittelwert = {mean_val:.1f}",
    )

    # show median as well
    median_val = data_col.median()
    ax.axvline(
        median_val,
        color="tab:orange",
        linestyle="--",
        linewidth=3,
        label=f"Median = {median_val:.1f}",
    )


def get_daily_profiles(
    poi_log: PoiLog, col: str, ffill: bool = False
) -> PoiDailyProfiles:
    """
    Resample a POI presence log to fixed 1-minute resolution and split it into
    daily profiles.
    :param poi_log: the POI presence log to resample
    :return: a PoiDailyProfiles object containing the daily profiles
    """
    # create a presence dataframe with datetime index
    df = poi_log.data[[col]]
    # resample to daily frequency and sum the presence values
    df_res = df.resample("1min")
    if ffill:
        df_res = df_res.ffill()
    else:
        df_res = df_res.asfreq(0)

    assert isinstance(df_res.index, pd.DatetimeIndex), f"Unexpected data format: {df}"

    # Group by date to get one column per day and one row per time
    df_res["date"] = df_res.index.date  # extract day
    df_res[TIME_COL] = df_res.index.time
    reshaped = df_res.pivot(index=TIME_COL, columns="date", values=col)

    # fill missing values (before first and after last POI presence log entry)
    reshaped.fillna(0, inplace=True)
    return PoiDailyProfiles(poi_log.poi_id, reshaped, col)  # type: ignore


def raster_plot(
    plot_dir: Path, daily_profile: PoiDailyProfiles, max_presence: int | None = None
):
    # don't use seaborn style here, looks bad for raster plots
    with sns.axes_style("ticks"):

        df = daily_profile.day_profiles

        # only show the relevant time frame
        df = df.loc[time(7, 0) : time(18, 59), :]

        fig, ax = plt.subplots()  # (figsize=(15, 6), dpi=400)
        im = ax.imshow(
            df,
            aspect="auto",
            origin="upper",
            cmap=cm.batlow,  # type: ignore
            vmax=max_presence,
            interpolation="none",
        )

        # Add colorbar
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Anzahl anwesender Kunden")

        # define x-axis ticks and labels
        # one tick for each Monday; suitable for short time frames, e.g., one month
        # mondays = [i for i, col in enumerate(df.columns) if col.weekday() == 0]  # type: ignore
        # ax.set_xticks(mondays)
        # xlabels = [df.columns[i].strftime("%a, %d.%m.") for i in mondays]  # type: ignore
        # ax.set_xticklabels(xlabels, rotation=90)
        # plt.xticks(rotation=90)

        # alternative: months ticks for a full-year plot
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

    # define y-ticks (time)
    vals_per_day = len(df.index)
    start_hour = df.index.min().hour
    hour_range = df.index.max().hour - start_hour + 1

    def hour_formatter(x, pos):
        x = x * hour_range / vals_per_day + start_hour
        h = int(x)
        m = int((x - h) * 60)
        return f"{h % 24:02d}:{m:02d}"

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(hour_formatter))
    ax.set_yticks(np.linspace(0, vals_per_day, num=7))

    # Labels and title
    # ax.set_xlabel(f"{daily_presence.index[0].year}")
    ax.set_ylabel("Uhrzeit")
    fig.tight_layout()
    col_txt = utils.slugify(daily_profile.column)
    subdir = plot_dir / f"raster_{col_txt}"
    subdir.mkdir(exist_ok=True, parents=True)
    fig.savefig(
        subdir / f"{daily_profile.poi_id}_{col_txt}_raster.svg",
        transparent=True,
        dpi="figure",
    )
    plt.close(fig)


def plot_daily_sum_histogram(
    dir: Path,
    poi_log: PoiLog,
    col: str = DFColumnsPoi.ARRIVE,
    stat_name: str = "Anzahl Besucher pro Tag",
):
    """
    Histogram showing the distribution of the number of visitors per day, or of
    another sum per day.

    :param dir: directory to save the plots
    :param poi_log: the PoiLog to plot
    """
    df = poi_log.data
    assert isinstance(df.index, pd.DatetimeIndex), f"Unexpected data format: {df}"
    vals_per_day = df.groupby(df.index.date).sum()[col]

    fig, ax = plt.subplots()
    pd.Series(vals_per_day).plot.hist(ax=ax)
    ax.set_xlabel(stat_name)

    # add stats as lines
    add_mean_median_to_hist(vals_per_day, ax)
    ax.legend()

    subdir = dir / f"hist_{col}"
    subdir.mkdir(exist_ok=True, parents=True)
    fig.savefig(subdir / f"{poi_log.poi_id}_{col}.svg")
    plt.close(fig)


def waiting_times_histogram(plot_subdir, poi_log):
    fig, ax = plt.subplots()
    poi_log.data[DFColumnsPoi.WAITING].plot.hist(ax=ax)
    ax.set_xlabel("Verteilung der Wartedauer [min]")
    add_mean_median_to_hist(poi_log.data[DFColumnsPoi.WAITING], ax)
    ax.legend()
    subdir = plot_subdir / "waiting_hist"
    subdir.mkdir(parents=True, exist_ok=True)
    fig.savefig(subdir / f"{poi_log.poi_id}_waiting_hist.svg")
    plt.close(fig)


def violin_plot_per_hour(
    plot_subdir: Path,
    poi_log: PoiLog,
    daily_presence: PoiDailyProfiles,
    max_wait_time: int | None,
):
    sns.set_theme()
    df = poi_log.data
    hour = "Stunde"

    # calculate average number of visitors per time
    mean_pres = daily_presence.day_profiles.mean(axis="columns")

    # get the hours during which attendance is >0
    relevant_times = mean_pres[mean_pres > 0].index
    start_hour = relevant_times.min().hour
    end_hour = relevant_times.max().hour
    hour_range_mean = list(range(start_hour, end_hour + 1))

    # get the hour range for the waiting time data (violins)
    df[hour] = df[DFColumnsPoi.DATETIME].dt.hour
    hour_range_wait = sorted(df[hour].unique())

    df[hour] += 0.5

    # combine both into a joint hour range to show all relevant data
    hour_range = sorted(set(hour_range_mean + hour_range_wait))

    # uncomment these two lines to include all 24h in the plot
    # hour_range = list(range(24))
    # df[hour] = pd.Categorical(df[hour], categories=hour_range, ordered=True)

    # limit the mean presence data to the selected hours
    mean_pres = mean_pres[[x.hour in hour_range for x in mean_pres.index]]

    # define colors
    # Ideas: use Color cycle colors from here https://seaborn.pydata.org/tutorial/properties.html#color-properties
    violin_fill = "#F4A1A1"  # soft pastel red
    violin_edge = (0.55, 0.15, 0.15, 0.6)  # darker red edge with alpha
    line_color = "#1B3B6D"

    fig, ax = plt.subplots()
    sns.violinplot(
        data=df,
        x=hour,
        y=DFColumnsPoi.WAITING,
        inner="quartile",  # shows median + quartiles
        cut=0,  # avoid extending violins beyond data range
        density_norm="width",
        # palette="coolwarm",
        color=violin_fill,
        linewidth=1.8,
        edgecolor=violin_edge,
        ax=ax,
    )
    ax.set_ylim(bottom=0, top=max_wait_time)
    ax.set_xlabel("Uhrzeit")
    ax.set_ylabel("Wartedauer [min]")
    # ax.set_xlim(min(hour_range), max(hour_range))
    # ax.set_xticks(range(len(hour_range)), hour_range)  # type: ignore

    # add a label for the hour at the end of the time span
    ext_hours = hour_range + [max(hour_range) + 1]
    ax.set_xticks(np.arange(-0.5, stop=len(hour_range) + 0.5), ext_hours)  # type: ignore

    # --- Line plot (secondary y-axis) ---
    start_hour = min(hour_range)

    # the violins are always at x=0, 1, 2 etc.
    # calculate matching x values for the mean curve
    xstart = min(hour_range_mean) - min(hour_range_mean) - 0.5
    length = len(hour_range_wait) + 1
    # mean_x = np.array([t.hour + t.minute / 60 - start_hour for t in mean_pres.index])
    mean_x = np.linspace(xstart, xstart + length, len(mean_pres))

    # use another style to avoid white grid line above the violins
    with sns.axes_style(
        "ticks",
        rc={
            "axes.spines.left": False,
            "axes.spines.bottom": False,
            "axes.spines.right": False,
            "axes.spines.top": False,
        },
    ):
        ax2 = ax.twinx()
        ax2.plot(
            mean_x,
            mean_pres.values,  # type: ignore
            color=line_color,
            alpha=0.6,
            linewidth=1.8,
        )
        ax2.set_ylabel("Durchschnittliche Anzahl Kunden", color=line_color)
        ax2.tick_params(axis="y", labelcolor=line_color)
        ax2.set_ylim(bottom=0)  # TODO: align mean curve axes across POIs as well?
        # ax2.legend()
        # ax2.set_xlim(min(hour_range), max(hour_range))

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
        self, plot_subdir: Path, poi_log: PoiLog, max_presence: int | None = None
    ):
        # create daily profiles and store them
        daily_pres = get_daily_profiles(poi_log, DFColumnsPoi.PRESENCE, True)
        self.presence_daily[poi_log.poi_id] = daily_pres
        raster_plot(plot_subdir, daily_pres, max_presence)

        daily_arrive = get_daily_profiles(poi_log, DFColumnsPoi.ARRIVE)
        raster_plot(plot_subdir, daily_arrive)

        if DFColumnsPoi.CANCEL in poi_log.data:
            # additional plot for queue POIs
            daily_cancel = get_daily_profiles(poi_log, DFColumnsPoi.CANCEL)
            raster_plot(plot_subdir, daily_cancel)

        sns.set_theme()  # reenable seaborn theme

        # plot histograms of daily means
        plot_daily_sum_histogram(plot_subdir, poi_log)
        if DFColumnsPoi.CANCEL in poi_log.data:
            plot_daily_sum_histogram(
                plot_subdir,
                poi_log,
                DFColumnsPoi.CANCEL,
                "Anzahl abgewiesener Kunden pro Tag",
            )

    def create_poi_queue_plots(
        self, plot_subdir: Path, poi_log: PoiLog, max_wait_time: int | None = None
    ):
        plot_subdir.mkdir(parents=True, exist_ok=True)
        waiting_times_histogram(plot_subdir, poi_log)
        daily_presence = self.presence_daily[poi_log.poi_id]
        violin_plot_per_hour(plot_subdir, poi_log, daily_presence, max_wait_time)

    def process_poi_presence(self, poi_type: str = ""):
        # collect all POI logs
        poi_log_path = self.city_result_dir / SubDirs.LOGS / SubDirs.POI_PRESENCE
        self.poi_presence = load_poi_logs(poi_log_path, poi_type, DFColumnsPoi.DATETIME)
        if not self.poi_presence:
            logging.warning(f"Found no POI logs in {poi_log_path}")
            return
        check_poi_presence_data(self.poi_presence.values())

        # calculate some aggregated statistics
        visitor_counts = get_col_sum_per_poi(
            self.poi_presence.values(), DFColumnsPoi.ARRIVE
        )
        utils.create_json_file(
            self.output_dir / "total_visitor_counts.json", visitor_counts
        )
        cancel_counts = get_col_sum_per_poi(
            self.poi_presence.values(), DFColumnsPoi.CANCEL
        )
        utils.create_json_file(
            self.output_dir / "total_cancel_counts.json", cancel_counts
        )
        cancels_per_vis = {k: c / visitor_counts[k] for k, c in cancel_counts.items()}
        utils.create_json_file(
            self.output_dir / "cancels_per_visit.json", cancels_per_vis
        )

        # create plots for all relevant POI types
        pois_by_type = group_pois_by_type(self.poi_presence.values())
        poi_type_sums: dict[str, PoiLog] = {}
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
            combined = combine_poi_presence_logs(pois_of_type)
            poi_type_sums[poi_type] = combined
            self.create_poi_presence_plots(poi_type_subdir, combined)

        # calculate aggregated statistics per POI type
        visitors = {
            p: pl.data[DFColumnsPoi.ARRIVE].sum() for p, pl in poi_type_sums.items()
        }
        utils.create_json_file(self.output_dir / "visit_counts_by_type.json", visitors)
        cancels = {
            p: pl.data[DFColumnsPoi.CANCEL].sum()
            for p, pl in poi_type_sums.items()
            if DFColumnsPoi.CANCEL in pl.data
        }
        utils.create_json_file(self.output_dir / "cancel_counts_by_type.json", cancels)
        cancels_per_vis = {k: c / visitors[k] for k, c in cancels.items()}
        utils.create_json_file(
            self.output_dir / "cancels_per_visit_by_type.json", cancels_per_vis
        )

    def process_poi_queues(self, poi_type: str = ""):
        # collect all POI queue logs
        poi_log_path = self.city_result_dir / SubDirs.LOGS / SubDirs.POI_QUEUE
        self.poi_queues = load_poi_logs(poi_log_path, poi_type)
        if not self.poi_queues:
            logging.warning(f"Found no POI queue logs in {poi_log_path}")
            return

        # calculate some aggregated statistics
        avg_wait_time = {
            poi_log.poi_id: poi_log.data[DFColumnsPoi.WAITING].mean()
            for poi_log in self.poi_queues.values()
        }
        with open(
            self.output_dir / "average_waiting_times.json", "w", encoding="utf8"
        ) as f:
            json.dump(avg_wait_time, f, indent=4)

        # create plots for all POI types
        pois_by_type = group_pois_by_type(self.poi_queues.values())
        combined_logs: dict[str, PoiLog] = {}
        for poi_type in RELEVANT_POI_TYPES:
            if poi_type not in pois_by_type:
                continue
            pois_of_type = pois_by_type[poi_type]
            # get the maximum waiting time to have a common axis for all POIs of the same type
            max_wait_time = max(
                p.data[DFColumnsPoi.WAITING].max() for p in pois_of_type
            )
            poi_type_subdir = self.plot_dir / poi_type
            for poi in pois_of_type:
                self.create_poi_queue_plots(poi_type_subdir, poi, max_wait_time)
            combined = combine_poi_queue_logs(pois_of_type)
            combined_logs[poi_type] = combined
            self.create_poi_queue_plots(poi_type_subdir, combined)

        # calculate some aggregated statistics by POI type
        avg_wait_time_by_type = {
            poi_log.poi_type: poi_log.data[DFColumnsPoi.WAITING].mean()
            for poi_log in combined_logs.values()
        }
        with open(
            self.output_dir / "average_waiting_times_by_type.json", "w", encoding="utf8"
        ) as f:
            json.dump(avg_wait_time_by_type, f, indent=4)


def main(city_result_dir: Path, plot_dir: Path):
    poiplotter = PoiPlotter(city_result_dir, plot_dir)
    poi_type = ""  # "Pharmacy"
    poiplotter.process_poi_presence(poi_type)
    poiplotter.process_poi_queues(poi_type)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    city_result_dir2 = Path("R:/phd_dir/results/scenario_juelich_04_eplpo_fair_100_1")
    plot_dir2 = city_result_dir2 / "Postprocessed/plots/pois"
    main(city_result_dir2, plot_dir2)
