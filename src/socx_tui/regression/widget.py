from __future__ import annotations
from textual.widgets.tree import TreeNode

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

import rich.repr
from rich.text import Text
from socx import Regression, Test, TestBase, TestResult, settings
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container
from textual.widget import Widget
from textual.widgets import Button, Tree
from textual_fspicker import FileOpen

from socx_tui.regression.details import RegressionDetails
from socx_tui.regression.dialog import RestartSelectionDialog, TestOutputDialog
from socx_tui.regression.tree import VimTree


logger = logging.getLogger(__name__)


@rich.repr.auto
class RegressionWidget(Widget, can_focus=False, inherit_bindings=True):
    """Render loaded regressions as an expandable tree and details pane."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding(
            key="o",
            show=False,
            action="load_regression_from_file()",
            description="Load regression from file",
        ),
        Binding(
            key="ctrl+o",
            action="load_regression_from_file()",
            description="Load regression from file",
            key_display="o / ctrl+o",
        ),
        Binding("s", "start_selected()", "Start", show=False),
        Binding("r", "resume_selected()", "Resume", show=False),
        Binding("p", "pause_selected()", "Pause", show=False),
        Binding("x", "pause_selected()", "Pause", show=False),
        Binding("P", "stop_selected()", "Stop", show=False),
        Binding("X", "stop_selected()", "Stop", show=False),
        Binding("R", "prompt_restart_selected()", "Restart", show=False),
    ]
    ALLOW_MAXIMIZE: ClassVar[bool] = True

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.loaded_regression: Regression | None = None
        self.node_map: dict[str, TreeNode] = {}
        self.regression_tree = VimTree("Regressions", id="regression-tree")
        self.details_view = RegressionDetails(id="regression-details")
        self.content = Container(
            self.regression_tree,
            self.details_view,
            id="regression-content",
        )
        self.button_layout = Container(
            Button(
                "Start\n(s)",
                "success",
                id="start-button",
                name="start-button",
                classes="button",
            ),
            Button(
                "Resume\n(r)",
                "primary",
                id="resume-button",
                name="resume-button",
                classes="button",
            ),
            Button(
                "Pause/Suspend\n(x/p)",
                "warning",
                id="pause-button",
                name="pause-button",
                classes="button",
            ),
            Button(
                " Stop/Kill\n(X/P)",
                "error",
                id="stop-button",
                name="pause-button",
                classes="button",
            ),
            Button(
                "Restart\n(R)",
                "default",
                id="restart-button",
                name="restart-button",
                classes="button",
            ),
            id="button-layout",
            name="button-layout",
            classes="layout",
        )

    @property
    def selected_model(self) -> TestBase | None:
        node = self.regression_tree.cursor_node
        data = getattr(node, "data", None)
        return data if isinstance(data, TestBase) else None

    def compose(self) -> ComposeResult:
        yield self.content
        yield self.button_layout

    async def on_mount(self) -> None:
        self.regression_tree.focus()
        self._refresh_timer = self.set_interval(
            name="referesh_timer",
            callback=self._refresh_tree_state,
            interval=1 / 2,
        )

    def show_details(self, model: TestBase | None) -> None:
        self.details_view.model = model

    async def action_load_regression_from_file(self) -> None:
        self.load_regression_from_file()

    async def action_start_selected(self) -> None:
        model = self.selected_model
        if model is None:
            self._no_model_selected_notification()
            return
        self._start_model(model)

    async def action_pause_selected(self) -> None:
        model = self.selected_model
        if model is None:
            self._no_model_selected_notification()
            return
        self._pause_model(model)

    async def action_stop_selected(self) -> None:
        model = self.selected_model
        if model is None:
            self._no_model_selected_notification()
            return
        self._stop_model(model)

    async def action_resume_selected(self) -> None:
        model = self.selected_model
        if model is None:
            self._no_model_selected_notification()
            return
        self._resume_model(model)

    async def action_restart_selected(self) -> None:
        model = self.selected_model
        if model is None:
            self._no_model_selected_notification()
            return
        self._restart_model(model, "all")

    async def action_prompt_restart_selected(self) -> None:
        model = self.selected_model
        if model is None:
            self._no_model_selected_notification()
            return
        if not isinstance(model, Regression):
            self._restart_model(model, "all")
            return

        self.app.push_screen(
            RestartSelectionDialog(),
            callback=lambda scope: self._on_restart_scope_selected(model, scope),
        )

    @on(VimTree.OpenCursorNode)
    async def on_vim_tree_open_cursor_node(
        self, event: VimTree.OpenCursorNode
    ) -> None:
        model = getattr(event.node, "data", None)
        if not isinstance(model, Test):
            return

        event.stop()
        self.app.push_screen(TestOutputDialog(model))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "start-button":
                self.app.call_next(self.action_start_selected)
            case "stop-button":
                self.app.call_next(self.action_stop_selected)
            case "pause-button":
                self.app.call_next(self.action_pause_selected)
            case "resume-button":
                self.app.call_next(self.action_resume_selected)
            case "restart-button":
                self.app.call_next(self.action_prompt_restart_selected)


    def _on_restart_scope_selected(
        self, model: Regression, scope: str | None
    ) -> None:
        if scope is None:
            return
        self._restart_model(model, scope)

    @work(exclusive=False)
    async def load_regression_from_file(self) -> None:
        """Open a file selection dialog and load selection as regression."""
        await self.action_stop_selected()
        self.set_loading(True)

        try:
            await self._load_regression_from_file()
        finally:
            self.set_loading(False)
            self._refresh_tree_state()

    @work(exclusive=False)
    async def _start_model(self, model: TestBase) -> None:
        await model.start()
        self._refresh_tree_state()

    @work(exclusive=False)
    async def _pause_model(self, model: TestBase) -> None:
        await model.pause()
        self._refresh_tree_state()

    @work(exclusive=False)
    async def _stop_model(self, model: TestBase) -> None:
        await model.stop()
        self._refresh_tree_state()

    @work(exclusive=False)
    async def _resume_model(self, model: TestBase) -> None:
        await model.resume()
        self._refresh_tree_state()

    @work(exclusive=False)
    async def _restart_model(self, model: TestBase) -> None:
        await model.restart()
        self._refresh_tree_state()


    async def _restart_regression_by_scope(
        self, regression: Regression, scope: str
    ) -> None:
        if scope == "all":
            await regression.restart()
            return

        if scope == "failed_or_cancelled":
            selector = lambda t: t.failed or t.terminated
        elif scope == "cancelled":
            selector = lambda t: t.terminated
        elif scope == "failed":
            selector = lambda t: t.finished and t.result is TestResult.Failed
        else:
            selector = lambda t: False

        for test in regression.iter_leaf_tests():
            if selector(test):
                test.soft_reset()

        regression.soft_reset()
        await regression.start()

    async def load_regression_from_path(self, path: Path) -> Regression:
        """Load regressions or saved state from ``path`` into the tree."""
        regression = Regression.load(path=path)
        if regression.output_dir is None:
            regression.assign_output_dir(
                self._create_session_output_dir(regression)
            )

        self.loaded_regression = regression
        self._populate_tree(regression)
        self._refresh_tree_state()
        self.details_view.refresh()
        self.regression_tree.focus()
        return regression

    def persist_loaded_regression_state(self) -> Path | None:
        if self.loaded_regression is None:
            return None

        file = self.loaded_regression.dump_state()
        self.log.info(f"Saved regression state to '{file}'.")
        return file

    async def _load_regression_from_file(self) -> None:
        file = await self._open_file_dialog()

        if file is None:
            msg = "Operation cancelled."
            self.notify(msg, severity="information", title="Load regression")
            self.log.info(msg)
            return

        self.log.info(f"Loading regression from file '{file}'...")
        try:
            regression = await self.load_regression_from_path(file)
        except Exception as exc:
            msg = f"Failed to load regression: {exc}"
            self.notify(msg, title="Load regression", severity="error")
            logger.exception(msg)
            return

        msg = f"Regression '{regression.name}' loaded successfully."
        self.notify(msg, title="Load regression", severity="information")
        self.log.info(msg)
        self.regression_tree.focus()

    async def _open_file_dialog(self) -> Path | None:
        return await self.app.push_screen_wait(
            FileOpen(open_button="Open", cancel_button="Cancel")
        )

    def on_tree_node_highlighted(
        self, event: Tree.NodeHighlighted[object]
    ) -> None:
        model = event.node.data
        if isinstance(model, TestBase):
            self.show_details(model)

    def on_tree_node_selected(self, event: Tree.NodeSelected[object]) -> None:
        model = event.node.data
        if isinstance(model, TestBase):
            self.show_details(model)

    def _populate_tree(self, regression: Regression) -> None:
        root = self.regression_tree.root
        root.remove_children()
        root.set_label(regression.name)
        root.expand()
        self.node_map.clear()

        first_node = None
        for item in self._top_level_regressions(regression):
            node = self._add_regression_node(root, item)
            if first_node is None:
                first_node = node

        if first_node is None:
            self.show_details(regression)
        else:
            self.regression_tree.move_cursor(first_node)
            self.show_details(first_node.data)

        self._refresh_tree_state()

    def _top_level_regressions(
        self, regression: Regression
    ) -> list[Regression]:
        tests = regression.tests
        if tests and all(isinstance(test, Regression) for test in tests):
            return list(tests)  # ty:ignore[invalid-return-type]
        return [regression]

    def _add_regression_node(
        self,
        parent,
        regression: Regression,
    ):
        node = parent.add(
            self._format_regression_label(regression),
            data=regression,
            allow_expand=bool(regression.tests),
        )
        self.node_map[str(regression.id)] = node
        for test in regression.tests:
            if isinstance(test, Regression):
                self._add_regression_node(node, test)
                continue
            test_node = node.add(
                self._format_test_label(test),
                data=test,
                allow_expand=False,
            )
            self.node_map[str(test.id)] = test_node
        return node

    def _refresh_tree_state(self) -> None:
        if not self.is_on_screen:
            return
        regression = self.loaded_regression
        if regression is None:
            return
        model = self.selected_model
        if self.details_view.model != model:
            self.details_view.model = model
        labels_changed = False
        for node in self.node_map.values():
            model = getattr(node, "data", None)
            if isinstance(model, TestBase):
                label = self._format_label(model)
                if node.label != label:
                    node.set_label(label)
                    labels_changed = True
        if labels_changed:
            self.details_view.refresh()

    def _create_session_output_dir(self, regression: Regression) -> Path:
        now = datetime.now().astimezone()
        output_root = settings.regression.run.output.directory
        base_dir = (
            Path(output_root) if isinstance(output_root, str) else output_root
        )
        return (
            base_dir
            / regression.name
            / now.strftime("%Y-%m-%d")
            / now.strftime("%H-%M-%S")
            / regression.name
        )

    def _format_label(self, model: TestBase) -> Text:
        if isinstance(model, Test):
            return self._format_test_label(model)
        elif isinstance(model, Regression):
            return self._format_regression_label(model)
        else:
            return Text("")

    def _format_regression_label(self, regression: Regression) -> Text:
        return Text.assemble(
            f"⚗️ {regression.name} ",
            self._format_regression_status_label(regression),
            style="dim italic"
            if not regression.started
            else "italic green"
            if regression.result is TestResult.Passed
            else "italic red"
            if regression.result is TestResult.Failed
            else "italic yellow",
        )

    def _format_regression_status_label(self, regression: Regression) -> Text:
        kind = (
            "regressions"
            if self._contains_regressions(regression)
            else "tests"
        )
        return Text.assemble(
            f"({len(regression.tests)} {kind}) ",
            self._format_test_status_label(regression),
            style="dim italic white"
            if not regression.started
            else "bold italic green"
            if regression.passed
            else "bold italic red"
            if regression.failed
            else "bold italic yellow",
        )

    def _contains_regressions(self, regression: Regression) -> bool:
        return bool(regression.tests) and any(
            isinstance(test, Regression) for test in regression.tests
        )

    def _format_test_label(self, test: TestBase) -> Text:
        return Text.assemble(
            (f"🧪 {test.name} ", "bold"),
            self._format_test_status_label(test),
            style="dim italic white"
            if not test.started
            else "bold italic green"
            if test.passed
            else "bold italic red"
            if test.failed or test.terminated
            else "bold italic yellow1",
        )

    def _format_test_status_label(self, test: TestBase) -> Text:
        status = f"💡 {self.details_view.format_status(test.status)}"
        result = f"🚩 {self.details_view.format_result(test.result)}"
        return Text.assemble("[", "|".join([status, result]), "]")

    def _no_model_selected_notification(self) -> None:
        msg = "Select a regression or test first."
        self.notify(msg, severity="warning")
