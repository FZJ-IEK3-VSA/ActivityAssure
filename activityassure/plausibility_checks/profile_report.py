from dataclasses import dataclass, field
from enum import StrEnum


@dataclass(frozen=True)
class TestResult:
    ok: bool
    check_id: str

    def get_message(self) -> str:
        result_str = "ok" if self.ok else "failed"
        return f"Check '{self.check_id}': {result_str}"


@dataclass(frozen=True)
class SuccessfulTest(TestResult):
    pass


@dataclass(frozen=True)
class FailedTestResult(TestResult):
    message: str
    occurrences: int = -1
    share: float = -1

    def get_message(self) -> str:
        m = super().get_message()
        if self.message:
            m += f" - {self.message}"
        if self.occurrences >= 0:
            m += f", {self.occurrences} occurrences"
        if self.share >= 0:
            m += f", {self.share * 100:2f}% affected"
        return m


@dataclass
class ProfileReport:
    errors: list[TestResult] = field(default_factory=list)
    successes: list[TestResult] = field(default_factory=list)

    def add(self, entry: TestResult):
        if entry.ok:
            self.successes.append(entry)
        else:
            self.errors.append(entry)

    def get_failed_ratio(self) -> float:
        return len(self.errors) / (len(self.errors) + len(self.successes))

    def get_errors(self) -> list[TestResult]:
        return self.errors

    def get_str_report(self, include_successful: bool = True):
        report = ""
        if include_successful:
            for e in self.successes:
                report += e.get_message() + "\n"
        for e in self.errors:
            report += e.get_message() + "\n"
        return report
