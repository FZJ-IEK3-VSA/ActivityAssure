from collections import defaultdict
from datetime import timedelta
from typing import Iterable
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

    def __init__(
        self,
        profile: SparseActivityProfile,
        report: ResultCollection,
        sleep_name: str = "sleep",
        ignore: Iterable[str] = [],
    ):
        self.sleep_act = sleep_name
        self.profile = profile
        self.ignore = set(ignore)
        self.sleep_activities = [
            a for a in profile.activities if a.name == self.sleep_act
        ]
        self.report = report

    def check_sleep(self) -> None:
        if not self.sleep_activities:
            result: TestResult = FailedTestResult(
                "sleep", "Did not find a single sleep activity"
            )
            self.report.add(result)
            # abort: other tests cannot be concluded in a meaningful way
            return
        # conduct all sleep checks
        results = [
            self.check_overall_sleep_ratio(),
            self.check_sleep_durations(),
            self.check_awake_durations(),
        ]
        for result in results:
            self.report.add(result)

    def check_overall_sleep_ratio(self) -> TestResult:
        check = "sleep - overall ratio"
        sleep_duration = sum(a.duration for a in self.sleep_activities)
        sleep_share = sleep_duration / self.profile.length()
        if sleep_share < SleepChecks.MIN_SLEEP_SHARE:
            return FailedTestResult(
                check,
                f"Overall sleeping time is too low at {sleep_share * 100:.1f}%",
            )
        else:
            return SuccessfulTest(check)

    def check_sleep_durations(self) -> TestResult:
        check = "sleep - duration"
        too_long_sleep_durs = [
            duration
            for a in self.sleep_activities
            if (duration := a.duration * self.profile.resolution)
            > SleepChecks.MAX_SLEEP_TIME
        ]
        if too_long_sleep_durs:
            return FailedTestResult(
                check,
                f"Person slept for longer than {SleepChecks.MAX_SLEEP_TIME} (max.: {max(too_long_sleep_durs)})",
                len(too_long_sleep_durs),
                len(too_long_sleep_durs) / len(self.sleep_activities),
            )
        else:
            return SuccessfulTest(check)

    def check_awake_durations(self) -> TestResult:
        check = "sleep - time awake"
        wake_time: defaultdict[str, list[int]] = defaultdict(list)
        too_long_awake = []
        last_sleep_idx = -1
        for i, a in enumerate(self.profile.activities):
            if a.name == self.sleep_act:
                # check the duration of this awake period
                time_awake = (
                    a.start - self.profile.activities[last_sleep_idx].end()
                ) * self.profile.resolution
                if time_awake > SleepChecks.MAX_AWAKE_TIME:
                    # check if one of the activities to ignore occurred
                    ignore_this_occasion = False
                    for awake_act in self.profile.activities[last_sleep_idx + 1 : i]:
                        if awake_act.name in self.ignore:
                            ignore_this_occasion = True
                            break
                    if ignore_this_occasion:
                        # this awake period was caused by an activity like vacation that is ignored
                        continue

                    # person was awake for too long, check responsible activitites
                    too_long_awake.append(time_awake)
                    for wake_activity in self.profile.activities[
                        last_sleep_idx + 1 : i
                    ]:
                        wake_time[wake_activity.name].append(wake_activity.duration)
                last_sleep_idx = i
        # sort by activity duration
        wake_time_str = "\n".join(
            f"\t{k}: {sum(v) * self.profile.resolution} total, {sum(v) * self.profile.resolution / len(v)}"
            f" average, {max(v) * self.profile.resolution} max"
            for k, v in sorted(
                wake_time.items(), key=lambda pair: pair[1], reverse=True
            )
        )
        if len(too_long_awake) == 0:
            return SuccessfulTest(check)
        max_awake = max(too_long_awake)
        return FailedTestResult(
            check,
            f"Person was awake for longer than {SleepChecks.MAX_AWAKE_TIME} (max.: {max_awake})",
            len(too_long_awake),
            len(too_long_awake) / len(self.sleep_activities),
            f"Responsible activities:\n{wake_time_str}",
        )
