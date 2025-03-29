import logging
from activityassure.activity_profile import SparseActivityProfile
from activityassure.plausibility_checks.profile_report import (
    PlausibilityReport,
    ResultCollection,
)
from activityassure.plausibility_checks import sleep_checks


def check_activity_profile(profile: SparseActivityProfile):
    report = ResultCollection(description=f"profile {profile.filename}")
    sleep = sleep_checks.SleepChecks(profile, report)
    sleep.check_sleep()
    logging.info(report.get_str_report())
    return report


def check_activity_profiles(full_year_profiles):
    logging.info(f"Starting plausibility check of {len(full_year_profiles)} profiles")
    full_report = PlausibilityReport()
    for profile in full_year_profiles:
        report = check_activity_profile(profile)
        full_report.add_report(profile, report)

    test_rates = full_report.get_fail_rate_by_check()
    test_rates_str = "\n".join(f"{k}: {100 * v:.1f}%" for k, v in test_rates.items())
    logging.info(f"Failure rates per test:\n{test_rates_str}")
