from __future__ import annotations

from typing import ClassVar

import rich.repr
from socx import Test
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen, ScreenResultType
from textual.widgets import Static, TextArea
from textual.widgets import Button

from socx_tui.regression.bindings.vim.mode import VimModes


class Dialog(Vertical):
    """Layout class for the main dialog area."""

    pass


class ReadOnlyOutputArea(TextArea, can_focus=True, inherit_bindings=True):
    """Read-only output viewer with keyboard navigation."""

    BINDINGS: ClassVar[list[BindingType]] = TextArea.BINDINGS + VimModes.Normal


@rich.repr.auto
class TestOutputDialog(ModalScreen[ScreenResultType]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding(
            key="escape",
            action="dismiss(None)",
            description="Dismiss the dialog.",
            show=False,
        ),
        Binding(
            key="q",
            action="dismiss(None)",
            description="Dismiss the dialog.",
            show=False,
        ),
    ]

    DEFAULT_CSS: ClassVar[str] = """
    TestOutputDialog {
        align: center middle;
    }

    #regression-output-dialog {
        width: 92%;
        height: 88%;
        border: thick $accent;
        background: $surface;
    }

    #regression-output-title {
        padding: 0 1;
        height: auto;
        text-style: bold;
    }

    #regression-output-area {
        height: 1fr;
    }
    """

    def __init__(self, model: Test, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._model = model
        self._output_view = ReadOnlyOutputArea(
            self._format_output(model),
            id="regression-output-area",
            language="bash",
            read_only=True,
            soft_wrap=False,
            show_cursor=True,
            show_line_numbers=True,
        )

    def compose(self) -> ComposeResult:
        with Dialog(
            id="regression-output-dialog",
            name="regression-output-dialog",
        ):
            yield Static(
                f"{self._model.name} stdout / stderr",
                id="regression-output-title",
            )
            yield self._output_view

    def on_mount(self) -> None:
        self._output_view.focus()

    def _format_output(self, model: Test) -> str:
        stdout = model.stdout or "<no stdout captured>"
        stderr = model.stderr or "<no stderr captured>"
        return "\n".join(
            [
                "===== STDOUT =====",
                stdout,
                "",
                "===== STDERR =====",
                stderr,
            ]
        )


class RestartSelectionDialog(ModalScreen[str | None]):
    """Modal dialog that asks which tests should be restarted."""

    DEFAULT_CSS: ClassVar[str] = """
    RestartSelectionDialog {
        align: center middle;
    }

    #restart-selection-dialog {
        width: 72;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    #restart-selection-actions {
        height: auto;
        layout: vertical;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "dismiss(None)", show=False),
        Binding("q", "dismiss(None)", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Dialog(id="restart-selection-dialog"):
            yield Static("Restart scope", id="restart-selection-title")
            with Vertical(id="restart-selection-actions"):
                yield Button("All tests", id="restart-scope-all")
                yield Button(
                    "Failing + cancelled", id="restart-scope-failed-cancelled"
                )
                yield Button("Only cancelled", id="restart-scope-cancelled")
                yield Button("Only failing", id="restart-scope-failed")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        mapping = {
            "restart-scope-all": "all",
            "restart-scope-failed-cancelled": "failed_or_cancelled",
            "restart-scope-cancelled": "cancelled",
            "restart-scope-failed": "failed",
        }
        self.dismiss(mapping.get(button_id))
