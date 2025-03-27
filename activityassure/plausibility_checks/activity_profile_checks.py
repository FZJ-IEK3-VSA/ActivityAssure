from activityassure.activity_profile import SparseActivityProfile
from activityassure.plausibility_checks.profile_report import (
    PlausibilityReport,
    ResultCollection,
)
from activityassure.plausibility_checks import sleep_checks


def check_activity_profile(profile: SparseActivityProfile):
    report = ResultCollection(description=f"profile {profile.filename}")
    sleep_checks.check_sleep_each_night(profile, report)
    print(report.get_str_report())
    return report


def check_activity_profiles(full_year_profiles):
    full_report = PlausibilityReport()
    for profile in full_year_profiles:
        report = check_activity_profile(profile)
        full_report.add_report(profile, report)

    test_rates = full_report.get_fail_rate_by_check()
    print(test_rates)
