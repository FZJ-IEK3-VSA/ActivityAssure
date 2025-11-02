"""Geographic analyses showing various indicators on a map"""

import json
import logging
from datetime import timedelta
from pathlib import Path

import contextily as ctx  # type: ignore
import geopandas as gpd  # type: ignore
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm
from shapely.geometry import Point  # type: ignore
import seaborn as sns

from activityassure.loadprofiles import utils
from paths import LoadFiles, SubDirs

#: DataFrame column for number of persons
PERSON_COUNT_COL = "Number of persons"

#: global min and max limits for load plots
LOAD_MIN, LOAD_MAX = None, None


# core city coordinate range for Jülich (including Koslar)
XLIM = 702500, 712500
YLIM = 6605000, 6610000
# whole city coordinate range for Jülich, including all buildings
XLIM_FULL = 698683.8054464592, 717455.3717942354
YLIM_FULL = 6600861.002313202, 6614854.611616367


def get_load_limits(city_result_dir: Path) -> tuple[float, float]:
    """Gets minimum and maximum of all occuring house loads.

    :param city_result_dir: city simulation result directory
    :return: minimum and maximum house load
    """
    filepath = (
        city_result_dir
        / SubDirs.POSTPROCESSED_DIR
        / SubDirs.LOADS_DIR
        / "aggregated_house"
        / LoadFiles.DAYPROFILESTATS
    )
    df_stats = pd.read_csv(filepath, index_col=0)
    vmin = df_stats.min(axis=None)
    vmax = df_stats.max(axis=None)
    return vmin, vmax  # pyright: ignore[reportReturnType]


def get_poi_geodf(scenario_dir: Path, remove_outliers: bool = True) -> gpd.GeoDataFrame:
    """Reads the POI coordinates and returns a GeoDataFrame with the
    appropriate geometry.

    :scenario_dir: the scenario directory
    :remove_outliers: if True, removes far away outlier POIs
    :return: a GeoDataFrame for all houses in the scenario
    """
    with open(scenario_dir / "city.json", "r", encoding="utf8") as f:
        city = json.load(f)
    pois = city["PointsOfInterest"]
    house_ids = list(pois.keys())
    coordinates = [
        Point(poi["Coordinates"]["Longitude"], poi["Coordinates"]["Latitude"])
        for poi in pois.values()
    ]
    df: gpd.GeoDataFrame = gpd.GeoDataFrame(geometry=coordinates, index=house_ids)

    # set the coordinate reference system to WGS 84 (EPSG:4326) and convert to Web Mercator
    df.set_crs("EPSG:4326", inplace=True)
    df.to_crs("EPSG:3857", inplace=True)  # type: ignore

    if remove_outliers:
        center = df.geometry.union_all().centroid
        distance_col = "distance_from_center"
        df[distance_col] = df.geometry.distance(center)
        original = len(df)
        df = df[df[distance_col] < 10000]
        df.drop(columns=[distance_col], inplace=True)
        logging.info(f"Removed {original - len(df)} outlier POIs.")
    return df


def get_house_geodf(scenario_dir: Path) -> gpd.GeoDataFrame:
    """Reads the house coordinates and returns a GeoDataFrame with the
    appropriate geometry.

    :scenario_dir: the scenario directory
    :return: a GeoDataFrame for all houses in the scenario
    """
    with open(scenario_dir / "house_coordinates.json", "r", encoding="utf8") as f:
        house_coordinates = json.load(f)
    house_ids = list(house_coordinates.keys())
    coordinates = [
        Point(c["Longitude"], c["Latitude"]) for c in house_coordinates.values()
    ]
    df: gpd.GeoDataFrame = gpd.GeoDataFrame(geometry=coordinates, index=house_ids)

    # set the coordinate reference system to WGS 84 (EPSG:4326) and convert to Web Mercator
    df.set_crs("EPSG:4326", inplace=True)
    df.to_crs("EPSG:3857", inplace=True)  # type: ignore
    return df


def save_plot(filepath: Path, fig):
    fig.tight_layout()
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(filepath, bbox_inches="tight")


def plot_map_data(
    df: gpd.GeoDataFrame,
    col: str,
    filepath: Path,
    is_load: bool = False,
    markersize: int = 1,
    title: str = "",
    xlim=None,
    ylim=None,
):
    # custom formatting to include whole JÜlich map area
    # xlim = XLIM_FULL
    # ylim = YLIM_FULL

    # compute aspect ratio of the map area
    x_range = df.geometry.x.max() - df.geometry.x.min()
    y_range = df.geometry.y.max() - df.geometry.y.min()

    # adapt map boundaries
    if not xlim and not ylim:
        # no specific boundaries set, so calculate the extent of the data
        xlim_data = (df.geometry.x.min(), df.geometry.x.max())
        ylim_data = (df.geometry.y.min(), df.geometry.y.max())

        # get the maximum extent of the data and the defined city area of XLIM/YLIM
        xlim_merged = (min(xlim_data[0], XLIM[0]), max(xlim_data[1], XLIM[1]))
        ylim_merged = (min(ylim_data[0], YLIM[0]), max(ylim_data[1], YLIM[1]))

        # use the merged range, unless the data extent is larger anyways, then leave it at None
        if xlim_data != xlim_merged:
            xlim = xlim_merged
        if ylim_data != ylim_merged:
            ylim = ylim_merged

    if xlim and ylim:
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]

    aspect_ratio = y_range / x_range

    # set figure size accordingly
    fig_width = 12
    fig_height = fig_width * aspect_ratio  # make height proportional
    buff_for_cbar = 2
    fig, ax = plt.subplots(figsize=(fig_width + buff_for_cbar, fig_height), dpi=200)

    # determine limits for a consistent color scale
    vmin, vmax = None, None
    if is_load:
        vmin, vmax = LOAD_MIN, LOAD_MAX

    # visual improvements for small data sets
    norm = LogNorm(vmin=vmin, vmax=vmax)
    edgecolor = None
    linewidth = 0
    if len(df) < 1000:
        # only very few points - highlight them, and no log scale
        norm = None
        markersize = 30
        edgecolor = "black"
        linewidth = 1

    # create the map plot
    df.plot(
        ax=ax,
        column=col,
        markersize=markersize,
        edgecolor=edgecolor,
        linewidth=linewidth,
        cmap="jet",
        norm=norm,
        legend=True,
        legend_kwds={"shrink": 0.7, "label": col},  # modify colorbar
    )

    if xlim or ylim:
        # apply the given spatial extent to get the same map part
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)

    if title:
        ax.set_title(title)

    # Add basemap
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)  # type: ignore

    # save the plot
    save_plot(filepath, fig)
    plt.close(fig)


def plot_hex_bins(df: gpd.GeoDataFrame, col: str, filepath: Path):
    x = df.geometry.x
    y = df.geometry.y
    values = df[col]

    fig, ax = plt.subplots(figsize=(10, 8))

    hb = ax.hexbin(
        x,
        y,
        C=values,
        gridsize=100,
        cmap="jet",
        norm=LogNorm(),
        reduce_C_function=np.sum,
        mincnt=1,  # ignore empty bins
    )
    # Add basemap
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)  # type: ignore

    cb = fig.colorbar(hb, ax=ax)
    cb.set_label(col)

    plt.show()
    save_plot(filepath, fig)


def add_house_geodata(scenario_dir: Path, data: pd.DataFrame) -> gpd.GeoDataFrame:
    """Adds geodata for every house in the DataFrame, turning the data
    into a GeoDataFrame.

    :param scenario_dir: scenario directory; required to get the house coordinates
    :param data: the data to add the geometry to; must have house IDs as index
    :return: the data as a GeoDataFrame with house coordinates
    """
    geodf = get_house_geodf(scenario_dir)
    df = pd.concat([geodf, data], axis="columns")
    df.dropna(inplace=True)
    return df  # pyright: ignore[reportReturnType]


def add_poi_geodata(
    scenario_dir: Path, data: pd.DataFrame, remove_outliers: bool = True
) -> gpd.GeoDataFrame:
    """Adds geodata for every POI in the DataFrame, turning the data
    into a GeoDataFrame.

    :param scenario_dir:  scenario directory; required to get the POI coordinates
    :param data: the data to add the geometry to; must have POI IDs as index
    :param remove_outliers: if True, removes far away outlier POIs, defaults to True
    :return: the data as a GeoDataFrame with POI coordinates
    """
    geodf = get_poi_geodf(scenario_dir, remove_outliers)
    df = pd.concat([geodf, data], axis="columns")
    df.dropna(inplace=True)
    return df  # pyright: ignore[reportReturnType]


def get_person_count(scenario_dir: Path) -> pd.DataFrame:
    """Returns the number of persons per house as a DataFrame.

    :param scenario_dir: scenario directory to load house data
    :return: number of persons per house; index contains house IDs
    """
    filepath = scenario_dir / "statistics/persons_per_house.json"
    with open(filepath, "r", encoding="utf8") as f:
        persons_per_house = json.load(f)
    persons_df = pd.DataFrame.from_dict(
        persons_per_house, "index", columns=[PERSON_COUNT_COL]
    )
    return persons_df


def visits_per_poi(
    scenario_dir: Path, city_result_dir: Path, output_dir: Path, filter: str = ""
):
    filename = "total_visitor_counts.json"
    filepath = city_result_dir / SubDirs.POSTPROCESSED_DIR / SubDirs.POIS / filename
    with open(filepath, "r", encoding="utf8") as f:
        visitor_counts = json.load(f)
    # filter pois by type
    visitor_counts_filt = {k: v for k, v in visitor_counts.items() if filter in k}
    filter_txt = f"_{filter}" if filter else ""
    if not visitor_counts_filt:
        logging.warning(f"Found no {filter} POIs in {filepath}")
    col = "Number of visitor"
    visitors_df = pd.DataFrame.from_dict(visitor_counts_filt, "index", columns=[col])
    df = add_poi_geodata(scenario_dir, visitors_df)

    xlim, ylim = None, None
    # if filter:
    #     # uncomment this to use coordinate range of the full POI set
    #     # create another GeoDF with all POIs, unfiltered
    #     all_pois_df = pd.DataFrame.from_dict(visitor_counts, "index", columns=[col])
    #     all_pois_df = add_poi_geodata(scenario_dir, all_pois_df)
    #     # determine the full coordinate range to show the same map part
    #     xlim = (all_pois_df.geometry.x.min(), all_pois_df.geometry.x.max())
    #     ylim = (all_pois_df.geometry.y.min(), all_pois_df.geometry.y.max())

    plot_map_data(
        df,
        col,
        output_dir / f"poi_visitors{filter_txt}.svg",
        markersize=2,
        xlim=xlim,
        ylim=ylim,
    )


def persons_per_house(
    scenario_dir: Path,
    city_result_dir: Path,
    output_dir: Path,
    house_list_file: Path | None = None,
):
    persons_df = get_person_count(scenario_dir)
    df = add_house_geodata(scenario_dir, persons_df)

    filename = "persons_per_house"
    if house_list_file:
        # only show houses contained in the house list file
        with open(house_list_file, "r", encoding="utf8") as f:
            houses = set(json.load(f))
            df = df[df.index.isin(houses)]
            filename += f"_only_{house_list_file.stem}"

    plot_map_data(df, PERSON_COUNT_COL, output_dir / f"{filename}.svg")
    # plot_hex_bins(df, PERSON_COUNT_COL, output_dir / "persons_per_house.svg")


def eplpo_selected_sites(
    model_result_dir: Path,
    existing_scenario: Path,
    output_dir: Path,
):
    """Shows selected sites from eplpo results, both POIs and residential
    buildings selected to be POIs.

    :param model_result_dir: directory with model result files
    :param existing_scenario: existing scenario dir to get house/POI geodata from
    :param output_dir: output directory for created maps
    """
    # if set, use the other scenario path to get house and POI geodata
    # model_result_dir = scenario_dir / "instances/results"
    output_dir.mkdir(parents=True, exist_ok=True)
    for result_file in model_result_dir.iterdir():
        if not result_file.is_file():
            continue
        # load selected sites
        with open(result_file, "r", encoding="utf8") as f:
            results = json.load(f)
        sites = results["selected_sites"]
        sites_df = pd.DataFrame({"Dummy": [1] * len(sites)}, index=sites)
        # join with both POIs and
        df_houses = add_house_geodata(existing_scenario, sites_df)
        df_houses["Source"] = "Residential"
        df_orig_pois = add_poi_geodata(existing_scenario, sites_df)
        df_orig_pois["Source"] = "Original POI"
        # merge both DFs
        joined: gpd.GeoDataFrame = pd.concat([df_houses, df_orig_pois])  # type: ignore
        if len(joined) < 2:
            logging.warning(f"Less than two selected sites in result: {result_file}")
            continue
        filename = f"eplpo_results_{result_file.stem}"
        plot_map_data(joined, "Source", output_dir / f"{filename}.svg")


def total_house_demand(scenario_dir: Path, city_result_dir: Path, output_dir: Path):
    filename = "total_demand_per_profile.csv"
    filepath = (
        city_result_dir
        / SubDirs.POSTPROCESSED_DIR
        / SubDirs.LOADS_DIR
        / "aggregated_house"
        / filename
    )
    df_loads = pd.read_csv(filepath)
    df_loads.set_index("House", inplace=True)

    df = add_house_geodata(scenario_dir, df_loads)
    demand_col = "Total demand [kWh]"
    plot_map_data(df, demand_col, output_dir / "house_demand.svg", is_load=False)

    # now also plot average load per person
    persons_df = get_person_count(scenario_dir)
    df = pd.concat([df, persons_df], axis="columns")
    demand_pp = "Load per person [kWh]"
    df[demand_pp] = df[demand_col] / df[PERSON_COUNT_COL]
    plot_map_data(df, demand_pp, output_dir / "demand_per_person.svg", is_load=False)  # type: ignore


def load_profile_stats(scenario_dir: Path, city_result_dir: Path, output_dir: Path):
    """Creates map plots for the load profile statistics (mean, max, ...) of the house
    load profiles.

    :param scenario_dir: directory with the city scenario
    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the map plots
    """
    filepath = (
        city_result_dir
        / SubDirs.POSTPROCESSED_DIR
        / SubDirs.LOADS_DIR
        / "aggregated_house"
        / LoadFiles.PROFILE_STATS
    )
    df_stats = pd.read_csv(filepath, index_col=0).T
    # add unit to column name
    df = add_house_geodata(scenario_dir, df_stats)

    output_dir /= "load_stats"
    output_dir.mkdir(parents=True, exist_ok=True)
    # create one map plot for every statistic
    for column in df_stats.columns:
        # rename column to get a better plot label
        new_name = f"Load profile {column} [W]"
        df = df.rename(columns={column: new_name})
        plot_map_data(
            df, new_name, output_dir / f"house_load_{column}.svg", is_load=True
        )


def sim_timesteps(scenario_dir: Path, city_result_dir: Path, output_dir: Path):
    """Creates map plots for every captured time point in the simulation.

    :param scenario_dir: directory with the city scenario
    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the map plots
    """
    timepoint_dir = (
        city_result_dir
        / SubDirs.POSTPROCESSED_DIR
        / SubDirs.LOADS_DIR
        / "sim_timesteps"
    )
    if not timepoint_dir.is_dir():
        logging.warning(f"No timestep directory found: {timepoint_dir}")
        return

    output_dir /= "sim_timesteps"
    output_dir.mkdir(parents=True, exist_ok=True)

    HOUSE_RES = timedelta(minutes=1)

    # plot a map for each captured time point
    for filepath in timepoint_dir.iterdir():
        df_step = pd.read_csv(filepath, index_col=0)
        # data has the datetime as column name
        col = "Load [W]"
        step_datetime = df_step.columns[0]
        df_step.columns = [col]

        df_step = utils.kwh_to_w(df_step, True, HOUSE_RES)
        # add unit to column name
        df = add_house_geodata(scenario_dir, df_step)

        name = filepath.stem
        plot_map_data(
            df, col, output_dir / f"{name}.svg", is_load=True, title=step_datetime
        )


def main(scenario_dir: Path, city_result_dir: Path, output_dir: Path):
    """Contains all geographic postprocessing of the city simulation.

    :param scenario_dir: directory with the city scenario
    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the postpocessed data
    """
    assert scenario_dir.is_dir() and city_result_dir.is_dir(), "Invalid input paths"
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    # determine min and max house loads to get a consistent scale across map plots
    global LOAD_MIN, LOAD_MAX
    LOAD_MIN, LOAD_MAX = get_load_limits(city_result_dir)

    # don't use seaborn style here, does not work well for map plots
    sns.reset_orig()

    visits_per_poi(scenario_dir, city_result_dir, output_dir)
    visits_per_poi(scenario_dir, city_result_dir, output_dir, "Pharmacy")
    persons_per_house(scenario_dir, city_result_dir, output_dir)
    total_house_demand(scenario_dir, city_result_dir, output_dir)
    load_profile_stats(scenario_dir, city_result_dir, output_dir)
    sim_timesteps(scenario_dir, city_result_dir, output_dir)

    # maps for random sites
    # filedir = scenario_dir / "custom_export"
    # for filepath in filedir.glob("random_residential_sites*"):
    #     persons_per_house(scenario_dir, city_result_dir, output_dir, filepath)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    city_result_dir = Path("R:/phd_dir/results/scenario_juelich_04_baseline")
    scenario_dir = city_result_dir / "scenario"
    assert scenario_dir.is_dir(), f"Missing scenario symlink: {scenario_dir}"
    output_dir = (
        city_result_dir / SubDirs.POSTPROCESSED_DIR / SubDirs.PLOTS / SubDirs.MAPS
    )
    main(scenario_dir, city_result_dir, output_dir)
    # results_path = Path("R:/phd_dir/pharmacy_data/results_mapped")
    # eplpo_selected_sites(results_path, scenario_dir, results_path / "maps")
