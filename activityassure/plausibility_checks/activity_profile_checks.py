import logging
from activityassure.activity_profile import SparseActivityProfile
from activityassure.plausibility_checks.profile_report import (
    PlausibilityReport,
    ResultCollection,
)
from activityassure.plausibility_checks import sleep_checks


def check_activity_profile(profile: SparseActivityProfile):
    report = ResultCollection(description=f"profile {profile.filename}")
    # TODO: check total profile duration = 1 year, max. activity duration < XY, number of activities > XY, max_duration per activity
    # basic_checks.OneYearChecks(profile, report)
    sleep = sleep_checks.SleepChecks(profile, report, ignore=["vacation"])
    sleep.check_sleep()
    logging.info(report.get_str_report(False))
    return report


def check_activity_profiles(full_year_profiles):
    logging.info(f"Starting plausibility check of {len(full_year_profiles)} profiles")
    full_report = PlausibilityReport()
    for profile in full_year_profiles:
        report = check_activity_profile(profile)
        full_report.add_report(profile, report)

    result_per_test = full_report.get_result_overview_per_test()
    logging.info(f"Failures per test:\n{result_per_test}")
