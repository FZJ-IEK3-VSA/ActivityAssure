from collections import defaultdict
from datetime import timedelta
from activityassure.activity_profile import SparseActivityProfile
from activityassure.plausibility_checks.profile_report import (
    FailedTestResult,
    ResultCollection,
    SuccessfulTest,
    TestResult,
)


class SleepChecks:
    MAX_SLEEP_TIME = timedelta(hours=12)
    MAX_AWAKE_TIME = timedelta(hours=24)
    MIN_SLEEP_SHARE = 0.2

    def __init__(self, profile: SparseActivityProfile, report: ResultCollection):
        self.profile = profile
        self.sleep_activities = [a for a in profile.activities if a.name == "sleep"]
        self.report = report

    def check_sleep(self) -> None:
        if not self.sleep_activities:
            result: TestResult = FailedTestResult(
                "sleep", "Did not find a single sleep activity"
            )
            self.report.add(result)
            # abort: other tests cannot be concluded in a meaningful way
            return
        self.check_overall_sleep_ratio()
        self.check_sleep_durations()
        self.check_awake_durations()

    def check_overall_sleep_ratio(self) -> None:
        sleep_duration = sum(a.duration for a in self.sleep_activities)
        sleep_share = sleep_duration / self.profile.length()
        if sleep_share < SleepChecks.MIN_SLEEP_SHARE:
            result = FailedTestResult(
                "sleep - overall ratio",
                f"Overall sleeping time is too low at {sleep_share * 100:.1f}%",
            )
            self.report.add(result)

    def check_sleep_durations(self) -> None:
        too_long_sleeps = [
            a
            for a in self.sleep_activities
            if a.duration * self.profile.resolution > SleepChecks.MAX_SLEEP_TIME
        ]
        check = "sleep - duration"
        if too_long_sleeps:
            result: TestResult = FailedTestResult(
                check,
                f"Person slept for longer than {SleepChecks.MAX_SLEEP_TIME}.",
                len(too_long_sleeps),
                len(too_long_sleeps) / len(self.sleep_activities),
            )
        else:
            result = SuccessfulTest(check)
        self.report.add(result)

    def check_awake_durations(self) -> None:
        wake_time: defaultdict[str, int] = defaultdict(int)
        max_awake_timesteps = SleepChecks.MAX_AWAKE_TIME / self.profile.resolution
        too_long_awake = 0
        last_sleep_idx = -1
        for i, a in enumerate(self.profile.activities):
            if a.name == "sleep":
                # check the duration of this awake period
                if (
                    a.start - self.profile.activities[last_sleep_idx].end()
                    > max_awake_timesteps
                ):
                    too_long_awake += 1
                    # person was awake for too long, check responsible activitites
                    for wake_activity in self.profile.activities[
                        last_sleep_idx + 1 : i
                    ]:
                        wake_time[wake_activity.name] += wake_activity.duration
                last_sleep_idx = i
                continue
        # sort by activity duration
        wake_time_str = "\n".join(
            f"\t{k}: {v * self.profile.resolution}"
            for k, v in sorted(
                wake_time.items(), key=lambda pair: pair[1], reverse=True
            )
        )
        if too_long_awake == 0:
            self.report.add(SuccessfulTest("sleep - time awake"))
            return
        result = FailedTestResult(
            "sleep - time awake",
            f"Person was awake for longer than {SleepChecks.MAX_AWAKE_TIME}",
            too_long_awake,
            too_long_awake / len(self.sleep_activities),
            f"Responsible activities:\n{wake_time_str}",
        )
        self.report.add(result)
