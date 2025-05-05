import logging
from pathlib import Path
from activityassure.activity_profile import SparseActivityProfile
from activityassure.plausibility_checks.activity_statistics import (
    ActivityStatistics,
    StatisticsCalculator,
)
from activityassure.plausibility_checks.profile_report import (
    PlausibilityReport,
    ResultCollection,
)
from activityassure.plausibility_checks import sleep_checks
from activityassure.plausibility_checks import statistics_plots


def run_activity_profile_checks(profile: SparseActivityProfile):
    report = ResultCollection(description=f"profile {profile.filename}")
    # TODO: check total profile duration = 1 year, max. activity duration < XY, number of activities > XY, max_duration per activity
    # basic_checks.OneYearChecks(profile, report)
    sleep = sleep_checks.SleepChecks(profile, report, ignore=["vacation"])
    sleep.check_sleep()
    report_message = report.get_str_report(False)
    if report_message:
        logging.info(report_message)
    return report


def run_checks_for_activity_profiles(
    full_year_profiles: list[SparseActivityProfile],
):
    logging.info(f"Starting plausibility check of {len(full_year_profiles)} profiles")
    full_report = PlausibilityReport()
    for profile in full_year_profiles:
        report = run_activity_profile_checks(profile)
        full_report.add_report(profile, report)

    result_per_test = full_report.get_result_overview_per_test()
    logging.info(f"Failures per test:\n{result_per_test}")


def collect_profile_stats(
    full_year_profiles: list[SparseActivityProfile],
    result_filepath: Path,
    activity: str,
):
    shares = []
    durations = []
    durations_without = []
    for profile in full_year_profiles:
        calc = StatisticsCalculator(profile, activity)
        shares.append(calc.overall_share())
        durations.extend(calc.durations())
        durations_without.extend(calc.durations_without_act())
    statistics = ActivityStatistics(activity, shares, durations, durations_without)
    statistics.save(result_filepath)


def plot_profile_stats(statistics_file: Path):
    statistics = ActivityStatistics.load(statistics_file)
    activity = statistics.activity
    output_dir = statistics_file.parent / "plots"
    statistics_plots.plot_distribution(
        statistics.shares, output_dir / f"{activity}_shares.png"
    )
    statistics_plots.plot_distribution_td(
        statistics.durations, output_dir / f"{activity}_durations.png"
    )
    statistics_plots.plot_distribution_td(
        statistics.durations_without, output_dir / f"{activity}_durations_without.png"
    )
