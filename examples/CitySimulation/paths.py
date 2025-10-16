"""Filepaths and directory names for city simulation postprocessing and analysis"""


class SubDirs:
    """Subdirectory names for postprocessed data and plots"""

    POSTPROCESSED_DIR = "Postprocessed"
    SCENARIO = "scenario"
    PLOTS = "plots"
    ACTIVITY_PROFILES = "activity_profiles"
    RAW_ACTIVITY_STATS = "raw_activity_statistics"
    LOADS_DIR = "loads"
    MAPS = "maps"
    POIS = "pois"
    TRANSPORT = "transport"
    ACTIVITIES = "activities"
    ACTIVITYASSURE = "activityassure_statistics"


class LoadFiles:
    """File names for aggregated load profile data"""

    TOTALS = "total_demand_per_profile.csv"
    SUMPROFILE = "sum_profile.csv"
    STATS = "stat_profiles.csv"
    DAYPROFILESTATS = "day_profile_stats.csv"
    MEANDAY = "mean_day_profile.csv"
    MEANDAYTYPES = "mean_daytype_profiles.csv"
    MEANDAY_STATS = "mean_day_stats.csv"
    MEANDAYTYPE_STATS = "mean_daytype_stats.csv"
    SIMULTANEITY = "simultaneity.csv"


class DFColumnsLoad:
    """Column names for dataframes with load profiles"""

    TIME = "Time"
    LOAD = "Load [kWh]"
    TOTAL_LOAD = "Load [W]"
    TOTAL_DEMAND = "Total demand [kWh]"
    AVERAGE_LOAD = "Average load [W]"


class DFColumnsPoi:
    """Column names for dataframes with POI data"""

    TIMESTEP = "Timestep"
    DATETIME = "Datetime"
    PRESENCE = "People present"
    TRAVELING = "People traveling"
