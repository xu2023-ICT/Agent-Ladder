"""Generic terminal chat frontend shared by every step's interactive demo.

Renders whatever a step's `turn(user_text)` generator yields. Knows nothing
about any specific step or model call -- conversation state (if any) is
each step's own responsibility, kept in that step's `run.py`.
"""

from dataclasses import dataclass
from typing import Callable, Iterator, Union

from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown, Static


@dataclass
class TextEvent:
    content: str


@dataclass
class ToolCallEvent:
    name: str
    args: dict


@dataclass
class ToolResultEvent:
    output: str


Event = Union[TextEvent, ToolCallEvent, ToolResultEvent]
TurnFn = Callable[[str], Iterator[Event]]


class AgentChatApp(App):
    CSS = """
    #log {
        padding: 1 2;
    }
    """

    def __init__(self, turn: TurnFn):
        super().__init__()
        self._turn = turn

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="log")
        yield Input(placeholder="Type a message and press Enter...")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        text = message.value.strip()
        if not text:
            return

        input_widget = self.query_one(Input)
        input_widget.value = ""
        input_widget.disabled = True

        log = self.query_one("#log", VerticalScroll)
        await log.mount(Markdown(f"**you:** {text}"))
        log.scroll_end()

        self._run_turn(text)

    @work(thread=True)
    def _run_turn(self, text: str) -> None:
        try:
            for event in self._turn(text):
                self.call_from_thread(self._render_event, event)
        except Exception as exc:  # surfaced in the log, not swallowed
            self.call_from_thread(self._render_error, exc)
        finally:
            self.call_from_thread(self._unlock_input)

    async def _render_event(self, event: Event) -> None:
        if isinstance(event, TextEvent):
            widget = Markdown(event.content)
        elif isinstance(event, ToolCallEvent):
            widget = Static(f"[bold cyan]tool call[/] {event.name}({event.args})")
        elif isinstance(event, ToolResultEvent):
            widget = Static(f"[dim]{event.output}[/]")
        else:
            raise TypeError(f"unknown event type: {type(event)!r}")

        log = self.query_one("#log", VerticalScroll)
        await log.mount(widget)
        log.scroll_end()

    async def _render_error(self, exc: Exception) -> None:
        log = self.query_one("#log", VerticalScroll)
        await log.mount(Static(f"[bold red]error:[/] {exc}"))
        log.scroll_end()

    def _unlock_input(self) -> None:
        input_widget = self.query_one(Input)
        input_widget.disabled = False
        input_widget.focus()
