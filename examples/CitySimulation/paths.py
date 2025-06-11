"""Filepaths and directory names for city simulation postprocessing and analysis"""

#: subdirectory for all postprocessing results within the simulation result directory
POSTPROCESSED_DIR = "Postprocessed"

ACTIVITY_PROFILES = "activity_profiles"
LOADS_DIR = "loads"


class LoadFiles:
    """File names for aggregated load profile data"""

    TOTALS = "total_demand_per_profile.csv"
    SUMPROFILE = "sum_profile.csv"
    STATS = "stat_profiles.csv"
    MEANDAY = "mean_day_profile.csv"
    MEANDAYTYPES = "mean_daytype_profiles.csv"
    MEANDAY_STATS = "mean_day_stats.csv"
    MEANDAYTYPE_STATS = "mean_daytype_stats.csv"
    SIMULTANEITY = "simultaneity.csv"


class DFColumns:
    """Column names for dataframes with load profiles"""

    TIME = "Time"
    LOAD = "Load [kWh]"
    TOTAL_DEMAND = "Total demand [kWh]"
    AVERAGE_LOAD = "Average load [W]"
