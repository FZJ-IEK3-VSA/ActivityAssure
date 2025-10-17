"""Geographic analyses showing various indicators on a map"""

import json
import logging
from pathlib import Path

from matplotlib.colors import LogNorm
import numpy as np
import pandas as pd

from paths import LoadFiles, SubDirs

import matplotlib.pyplot as plt
import contextily as ctx  # type: ignore

import geopandas as gpd  # type: ignore
from shapely.geometry import Point  # type: ignore

#: DataFrame column for number of persons
PERSON_COUNT_COL = "Number of persons"


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


def save_plot(filepath, fig):
    fig.tight_layout()
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(filepath)


def plot_map_data(df: gpd.GeoDataFrame, col: str, filepath: Path, markersize: int = 1):
    # compute aspect ratio of the map area
    x_range = df.geometry.x.max() - df.geometry.x.min()
    y_range = df.geometry.y.max() - df.geometry.y.min()
    aspect_ratio = y_range / x_range

    # set figure size accordingly
    fig_width = 12
    fig_height = fig_width * aspect_ratio  # make height proportional
    buff_for_cbar = 2
    fig, ax = plt.subplots(figsize=(fig_width + buff_for_cbar, fig_height), dpi=200)

    # create the map plot
    df.plot(
        ax=ax,
        column=col,
        markersize=markersize,
        cmap="jet",
        norm=LogNorm(),
        legend=True,
        legend_kwds={"shrink": 0.7, "label": col},  # modify colorbar
    )

    # Add basemap
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)  # type: ignore

    # save the plot
    save_plot(filepath, fig)


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
    geodf = get_house_geodf(scenario_dir)
    df = pd.concat([geodf, data], axis="columns")
    return df  # pyright: ignore[reportReturnType]


def add_poi_geodata(
    scenario_dir: Path, data: pd.DataFrame, remove_outliers: bool = True
) -> gpd.GeoDataFrame:
    geodf = get_poi_geodf(scenario_dir, remove_outliers)
    df = pd.concat([geodf, data], axis="columns")
    return df  # pyright: ignore[reportReturnType]


def get_person_count(scenario_dir):
    filepath = scenario_dir / "statistics/persons_per_house.json"
    with open(filepath, "r", encoding="utf8") as f:
        persons_per_house = json.load(f)
    persons_df = pd.DataFrame.from_dict(
        persons_per_house, "index", columns=[PERSON_COUNT_COL]
    )
    return persons_df


def visits_per_poi(scenario_dir: Path, city_result_dir: Path, output_dir: Path):
    filename = "total_visitor_counts.json"
    filepath = city_result_dir / SubDirs.POSTPROCESSED_DIR / SubDirs.POIS / filename
    with open(filepath, "r", encoding="utf8") as f:
        visitor_counts = json.load(f)
    col = "Number of visitor"
    visitors_df = pd.DataFrame.from_dict(visitor_counts, "index", columns=[col])
    df = add_poi_geodata(scenario_dir, visitors_df)
    plot_map_data(df, col, output_dir / "poi_visitors.svg", markersize=2)


def persons_per_house(scenario_dir: Path, city_result_dir: Path, output_dir: Path):
    persons_df = get_person_count(scenario_dir)
    df = add_house_geodata(scenario_dir, persons_df)

    plot_map_data(df, PERSON_COUNT_COL, output_dir / "persons_per_house.svg")
    # plot_hex_bins(df, PERSON_COUNT_COL, output_dir / "persons_per_house.svg")


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
    plot_map_data(df, demand_col, output_dir / "house_demand.svg")

    # now also plot average load per person
    persons_df = get_person_count(scenario_dir)
    df = pd.concat([df, persons_df], axis="columns")
    demand_pp = "Load per person [kWh]"
    df[demand_pp] = df[demand_col] / df[PERSON_COUNT_COL]
    plot_map_data(df, demand_pp, output_dir / "demand_per_person.svg")  # type: ignore


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
        plot_map_data(df, new_name, output_dir / f"house_load_{column}.svg")


def main(scenario_dir: Path, city_result_dir: Path, output_dir: Path):
    """Contains all geographic postprocessing of the city simulation.

    :param scenario_dir: directory with the city scenario
    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the postpocessed data
    """
    assert scenario_dir.is_dir() and city_result_dir.is_dir(), "Invalid input paths"
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    visits_per_poi(scenario_dir, city_result_dir, output_dir)
    persons_per_house(scenario_dir, city_result_dir, output_dir)
    total_house_demand(scenario_dir, city_result_dir, output_dir)
    load_profile_stats(scenario_dir, city_result_dir, output_dir)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    scenario_dir = Path("R:/phd_dir/city_scenarios/scenario_julich_02")
    city_result_dir = Path("R:/phd_dir/results/scenario_julich_02")
    output_dir = city_result_dir / SubDirs.POSTPROCESSED_DIR / SubDirs.MAPS
    main(scenario_dir, city_result_dir, output_dir)
