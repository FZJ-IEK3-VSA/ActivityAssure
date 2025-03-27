from datetime import timedelta
from activityassure.activity_profile import SparseActivityProfile
from activityassure.plausibility_checks.profile_report import (
    FailedTestResult,
    ProfileReport,
    SuccessfulTest,
    TestResult,
)


MAX_SLEEP_TIME = timedelta(hours=12)
MAX_AWAKE_TIME = timedelta(hours=24)
MIN_SLEEP_SHARE = 0.2


def check_error_list(
    check: str, error_message: str, errors: list, all_items: list
) -> TestResult:
    if errors:
        return FailedTestResult(
            False,
            check,
            error_message,
            len(errors),
            len(errors) / len(all_items),
        )
    else:
        return SuccessfulTest(True, check)


def check_sleep_each_night(profile: SparseActivityProfile, report: ProfileReport):
    sleep_activities = [a for a in profile.activities if a.name == "sleep"]
    if not sleep_activities:
        result: TestResult = FailedTestResult(
            False, "sleep", "Did not find a single sleep activity"
        )
        report.add(result)
        return

    sleep_duration = sum(a.duration for a in sleep_activities)
    sleep_share = sleep_duration / profile.length()
    if sleep_share < MIN_SLEEP_SHARE:
        result = FailedTestResult(
            False,
            "sleep",
            f"Overall sleeping time is too low at {sleep_share * 100:1f}%",
        )
        report.add(result)
        return

    too_long_sleeps = [
        a for a in sleep_activities if a.duration * profile.resolution > MAX_SLEEP_TIME
    ]
    result = check_error_list(
        "sleep - duration",
        f"Person slept for longer than {MAX_SLEEP_TIME}.",
        too_long_sleeps,
        sleep_activities,
    )
    report.add(result)

    time_awake = [
        (sleep_activities[i + 1].start - a.end()) * profile.resolution
        for i, a in enumerate(sleep_activities[:-1])
    ]
    too_long_awake = [t for t in time_awake if t > MAX_AWAKE_TIME]
    result = check_error_list(
        "sleep - time awake",
        f"Person was awake for longer than {MAX_AWAKE_TIME}.",
        too_long_awake,
        sleep_activities,
    )
    report.add(result)
