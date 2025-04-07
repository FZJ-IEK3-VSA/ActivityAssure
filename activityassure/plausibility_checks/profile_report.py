import abc
from collections import defaultdict
from dataclasses import dataclass, field

from activityassure.activity_profile import SparseActivityProfile


@dataclass(frozen=True)
class TestResult:
    check_id: str

    def get_message(self) -> str:
        result_str = "ok" if self.ok() else "failed"
        return f"Check '{self.check_id}': {result_str}"

    @abc.abstractmethod
    def ok(self) -> bool:
        pass


@dataclass(frozen=True)
class SuccessfulTest(TestResult):
    def ok(self) -> bool:
        return True


@dataclass(frozen=True)
class FailedTestResult(TestResult):
    message: str
    occurrences: int = -1
    share: float = -1
    details: str = ""

    def ok(self) -> bool:
        return False

    def get_message(self) -> str:
        m = super().get_message()
        if self.message:
            m += f" - {self.message}"
        if self.occurrences >= 0:
            m += f", {self.occurrences} occurrences"
        if self.share >= 0:
            m += f", {self.share * 100:.1f}% affected"
        if self.details:
            m += "\n" + self.details
        return m


@dataclass
class ResultCollection:
    errors: list[TestResult] = field(default_factory=list)
    successes: list[TestResult] = field(default_factory=list)
    description: str = ""

    def add(self, entry: TestResult):
        if entry.ok():
            self.successes.append(entry)
        else:
            self.errors.append(entry)

    def get_fail_rate(self) -> float:
        return len(self.errors) / (len(self.errors) + len(self.successes))

    def get_errors(self) -> list[TestResult]:
        return self.errors

    def get_results(self) -> list[TestResult]:
        return self.successes + self.errors

    def get_str_report(self, include_successful: bool = True):
        header = f"Test results for {self.description}:\n"
        report = ""
        if include_successful:
            for e in self.successes:
                report += e.get_message() + "\n"
        for e in self.errors:
            report += e.get_message() + "\n"
        if not include_successful and not report:
            return ""
        return header + report


@dataclass
class PlausibilityReport:
    profiles: list[SparseActivityProfile] = field(default_factory=list)
    reports: list[ResultCollection] = field(default_factory=list)

    def add_report(self, profile: SparseActivityProfile, report: ResultCollection):
        self.profiles.append(profile)
        self.reports.append(report)

    def get_results_by_check(self) -> dict[str, ResultCollection]:
        results: dict[str, ResultCollection] = defaultdict(ResultCollection)
        for report in self.reports:
            for result in report.get_results():
                results[result.check_id].add(result)
        for check, collection in results.items():
            collection.description = f"check '{check}'"
        return results

    def get_fail_rate_by_check(self) -> dict[str, float]:
        results = self.get_results_by_check()
        return {
            check: collection.get_fail_rate() for check, collection in results.items()
        }

    def get_result_overview_per_test(self) -> str:
        results = self.get_results_by_check()
        test_rates_str = "\n".join(
            f"{check}: {len(collection.get_errors())}, ({100 * collection.get_fail_rate():.1f}%)"
            for check, collection in results.items()
        )
        return test_rates_str
