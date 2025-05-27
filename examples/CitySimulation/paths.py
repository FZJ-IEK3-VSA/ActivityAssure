"""Filepaths and directory names for city simulation postprocessing and analysis"""

#: subdirectory for all postprocessing results within the simulation result directory
POSTPROCESSED_DIR = "Postprocessed"

ACTIVITY_PROFILES = "activity_profiles"
LOADS_DIR = "loads"


class LoadFiles:
    """File names for aggregated load profile data"""

    TOTALS = "profile_sums.csv"
    SUMPROFILE = "sum_profile.csv"
    STATS = "stat_profiles.csv"
    MEANDAY = "mean_day_profile.csv"
    MEANDAY_STATS = "mean_day_stats.csv"


class DFColumns:
    """Column names for dataframes with load profiles"""

    TIME = "Time"
    LOAD = "Load [kWh]"
