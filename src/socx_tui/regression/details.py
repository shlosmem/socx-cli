from __future__ import annotations
from socx_tui.regression.bindings import VimModes
from textual.containers import ScrollableContainer

from datetime import datetime
from typing import ClassVar
from textwrap import dedent

from rich.markdown import Markdown
from textual.reactive import reactive
from textual.app import RenderResult
from textual.widgets import Static
from socx import Test, Regression, TestBase, TestResult, TestStatus, Script


class RegressionDetails(
    ScrollableContainer, can_focus=True, inherit_bindings=True
):
    BINDINGS = ScrollableContainer.BINDINGS + VimModes.Normal
    ALLOW_MAXIMIZE: ClassVar[bool] = True

    model: reactive[TestBase | None] = reactive(None)

    @property
    def details(self) -> RegressionStaticDetails:
        return self.query_exactly_one(RegressionStaticDetails)

    def compose(self):
        yield RegressionStaticDetails(id="regression-static-details")

    def watch_model(self, model: TestBase) -> None:
        self.details.model = model


class RegressionStaticDetails(Static):
    model: reactive[TestBase | None] = reactive(None)

    def render(self) -> RenderResult:
        return self.format_details(self.model)

    def watch_model(self, model: TestBase) -> None:
        self.refresh()

    def show_details(self, model: TestBase | None) -> None:
        self.model = model
        self.refresh()

    def format_details(self, model: TestBase | None = None) -> RenderResult:
        if model is None:
            return Markdown(
                dedent("""
                    **No regression selected.**

                    Use `o` or `ctrl-o` to select a file to load regressions
                    from.

                    Supported file formats are: `.yaml`, `.yml`, `.toml`,
                    and `.json`.

                    Regression file example:

                    ```yaml
                    my_regression:
                      - name: foo_test
                        exec: |
                          #!/bin/bash
                          /my/custom/run_script --test foo_test

                      - name: bar_test
                        exec: |
                          #!/bin/bash
                          /my/custom/run_script --test bar_test
                    ```
                """)
            )

        if isinstance(model, Regression):
            kind = (
                "regressions" if self.contains_regressions(model) else "tests"
            )
            text = "\n\n".join(
                [
                    self.format_header(model),
                    f"👨‍👩‍👧‍👦 Children: {len(model.tests)} {kind}",
                    f"❌ Failed: {self.count_results(model, TestResult.Failed)}",  # noqa: E501
                    f"✅ Passed: {self.count_results(model, TestResult.Passed)}",  # noqa: E501
                    f"💡 Status: {self.format_status(model.status)}",
                    f"🚩 Result: {self.format_result(model.result)}",
                    f"⌛ Elapsed Time: {self.format_timedelta(model.elapsed_time)}",  # noqa: E501
                    f"⌛ Started Time: {self.format_time(model.started_time)}",
                    f"⌛ Finished Time: {self.format_time(model.finished_time)}",  # noqa: E501
                    f"📊 Progress: `{self.format_progress(model)}`",
                    f"⏳ ETA: {self.format_timedelta(model.estimated_remaining_time)}",  # noqa: E501
                ]
            )
        elif isinstance(model, Test):
            text = "\n\n".join(
                [
                    self.format_header(model),
                    f"💡 Status: {self.format_status(model.status)}",
                    f"🚩 Result: {self.format_result(model.result)}",
                    f"⌛ Elapsed Time: {self.format_timedelta(model.elapsed_time)}",  # noqa: E501
                    f"⌛ Started Time: {self.format_time(model.started_time)}",
                    f"⌛ Finished Time: {self.format_time(model.finished_time)}",  # noqa: E501
                    self.format_script(model.exec),
                ]
            )
        else:
            text = ""
        return Markdown(text)

    def contains_regressions(self, regression: Regression) -> bool:
        return bool(regression.tests) and any(
            isinstance(test, Regression) for test in regression.tests
        )

    def format_header(self, model: TestBase) -> str:
        if isinstance(model, Test):
            icon = "🧪 "
        elif isinstance(model, Regression):
            icon = "⚗️ "
        return f"# {icon}{model.name} ({type(model).__name__})"

    def format_script(self, script: Script | None) -> str:
        script_str = str(script or "")
        return "\n\n".join(
            ["## 📜 Command/Script", "```bash", script_str, "```"]
        )

    def format_result(self, result: TestResult | str) -> str:
        if isinstance(result, TestResult):
            return result.value
        return str(result)

    def format_status(self, status: int | str | TestStatus) -> str:
        if isinstance(status, int):
            status = TestStatus(status)
        if isinstance(status, str):
            status = TestStatus[status.strip().lower().title()]
        return status.name.lower()

    def format_time(self, value: float | None) -> str:
        if value is None:
            return "n/a"

        try:
            if value >= 946684800:
                return (
                    datetime.fromtimestamp(value)
                    .astimezone()
                    .strftime("%Y-%m-%d %H:%M:%S %Z")
                )
        except (OverflowError, OSError, ValueError):
            pass

        return f"{value:.3f}s"

    def format_timedelta(self, value: int | float | None) -> str:
        if value is None:
            return "n/a"
        total_seconds = int(value)
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        return f"{hours:02}h:{minutes:02}m:{seconds:02}s"

    def count_results(self, regression: Regression, result: TestResult) -> int:
        return sum(
            1 for test in regression.iter_leaf_tests() if test.result is result
        )

    def format_progress(self, regression: Regression, width: int = 24) -> str:
        total = regression.total_test_count
        completed = regression.completed_test_count
        ratio = regression.progress_ratio
        filled = min(width, round(ratio * width))
        bar = "#" * filled + "-" * (width - filled)
        percent = int(ratio * 100)
        return f"[{bar}] {completed}/{total} ({percent}%)"
