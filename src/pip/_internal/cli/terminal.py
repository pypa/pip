"""Text styling and serialized terminal output used by pip."""

from __future__ import annotations

import builtins
import json
import os
import re
import reprlib
import shutil
import sys
import threading
import traceback
import unicodedata
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, TextIO, runtime_checkable

from pip._internal.utils.compat import override

if TYPE_CHECKING:
    from types import TracebackType

    from typing_extensions import Self

_CARRIAGE_RETURN = "\r"
# CSI (ESC [) introduces a VT control sequence. EL's default parameter erases
# from the cursor to the end of the line.
# https://learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#text-modification
_CSI = "\x1b["
_ERASE_TO_END = _CSI + "K"
# DECTCEM hides/shows the cursor around an active live display.
# https://learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#cursor-visibility
_HIDE_CURSOR = _CSI + "?25l"
_SHOW_CURSOR = _CSI + "?25h"
# SGR parameter 0 restores the default text attributes.
# https://learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#text-formatting
_RESET_STYLE = _CSI + "0m"
# Extended SGR foreground parameters: RGB components or a palette index.
# https://learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#extended-colors
_RGB_FOREGROUND = (38, 2)
_PALETTE_FOREGROUND = (38, 5)
_MIN_WINDOWS_TRUECOLOR_BUILD = 15063
_FALLBACK_ENCODING = "utf-8"
_ENCODING_ERRORS = "backslashreplace"
_DIAGNOSTIC_SYMBOLS = "\N{MULTIPLICATION SIGN}│╰─>"
# Interpret VT output without clearing the console's existing mode flags.
# https://learn.microsoft.com/en-us/windows/console/setconsolemode
_ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

_JSON_KEY_STYLE = "bold blue"
_JSON_STRING_STYLE = "green"
_JSON_NUMBER_STYLE = "bold cyan"
_JSON_BRACE_STYLE = "bold"
_JSON_LITERAL_STYLES = {
    "true": "italic bright_green",
    "false": "italic bright_red",
    "null": "italic magenta",
}

# RGB, 256-color and standard-color equivalents of the progress theme.
# Example of a progress theme:
# https://github.com/Textualize/rich/blob/v15.0.0/rich/default_styles.py#L126-L128
_PROGRESS_COLORS = {
    "progress_remaining": ((58, 58, 58), 237, 90),
    "progress_filled": ((249, 38, 114), 197, 91),
    "progress_finished": ((114, 156, 31), 70, 90),
}

if sys.platform == "win32":
    import ctypes
    import msvcrt
    from ctypes import wintypes

    def _enable_windows_vt(file: TextIO) -> bool:
        """Enable ANSI output when the Windows console supports it."""
        # Console APIs need an OS handle, not Python's C runtime descriptor.
        # https://docs.python.org/3/library/msvcrt.html#msvcrt.get_osfhandle
        try:
            handle = msvcrt.get_osfhandle(file.fileno())
        except (OSError, ValueError):
            return False

        # WinDLL selects the stdcall convention used by Windows console APIs.
        # https://docs.python.org/3/library/ctypes.html#ctypes.WinDLL
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)

        # HANDLE types avoid ctypes' default C int conversion on 64-bit Windows.
        # https://docs.python.org/3/library/ctypes.html#specifying-the-required-argument-types-function-prototypes
        kernel.GetConsoleMode.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel.GetConsoleMode.restype = wintypes.BOOL

        kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.SetConsoleMode.restype = wintypes.BOOL

        # GetConsoleMode writes the current flags through a DWORD pointer.
        # https://learn.microsoft.com/en-us/windows/console/getconsolemode
        mode = wintypes.DWORD()

        # Preserve other console flags; pipes fail the mode query.
        # https://learn.microsoft.com/en-us/windows/console/setconsolemode
        # Example of console mode setup:
        # https://github.com/tartley/colorama/blob/0.4.6/colorama/winterm.py#L166-L182
        return bool(
            kernel.GetConsoleMode(handle, ctypes.byref(mode))
            and kernel.SetConsoleMode(
                handle, mode.value | _ENABLE_VIRTUAL_TERMINAL_PROCESSING
            )
        )

else:

    def _enable_windows_vt(_file: TextIO) -> bool:
        return False


_SGR_FOREGROUND = 30

# Named styles use basic SGR colors; the bar theme also has RGB equivalents.
# https://learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#text-formatting
_STYLES = {
    "bold": (1,),
    "dim": (2,),
    "italic": (3,),
    "underline": (4,),
    "red": (31,),
    "green": (32,),
    "yellow": (33,),
    "blue": (34,),
    "magenta": (35,),
    "cyan": (36,),
    "bright_red": (91,),
    "bright_green": (92,),
    "optparse.shortargs": (32,),
    "optparse.longargs": (36,),
    "optparse.groups": (1, 34),
    "optparse.metavar": (33,),
}
_JSON_TOKEN = re.compile(
    r'"|(?P<brace>[\[\]{}])|(?<!\w)(true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\b'
)
_TAG = re.compile(r"\\([\\\[])|\[([^\[\]\n]*)\]")
_STRIP_CONTROL = str.maketrans("", "", "\a\b\v\f\r")


def escape(text: str) -> str:
    """Quote brackets in text inserted into a styled message."""
    # Literal bracket escaping: https://rich.readthedocs.io/en/stable/markup.html#escaping
    return text.replace("\\", "\\\\").replace("[", r"\[")


class StyledText:
    """Literal text with the small set of styles used in pip diagnostics."""

    def __init__(self, text: str = "", style: str = "") -> None:
        self.parts: list[tuple[str, str]] = [(text, style)]

    @classmethod
    def from_markup(cls, text: str) -> StyledText:
        """Parse pip's finite style vocabulary, keeping unknown brackets literal."""
        result = cls()
        styles: list[str] = []
        start = 0

        for match in _TAG.finditer(text):
            escaped, tag = match.groups()
            result.parts.append((text[start : match.start()], " ".join(styles)))
            start = match.end()

            # Quote backslashes and brackets independently of surrounding markup.
            if escaped is not None:
                result.parts.append((escaped, " ".join(styles)))
            elif tag == "reset":
                styles.clear()
            elif tag == "/":
                if styles:
                    styles.pop()
            elif tag and all(
                word in _STYLES or word in _PROGRESS_COLORS for word in tag.split()
            ):
                styles.append(tag)
            else:
                result.parts.append((match[0], " ".join(styles)))

        result.parts.append((text[start:], " ".join(styles)))
        return result

    @classmethod
    def from_parts(cls, *parts: str | StyledText | tuple[str, str]) -> StyledText:
        result = cls()

        for part in parts:
            if isinstance(part, tuple):
                result.parts.append(part)
            elif isinstance(part, StyledText):
                result.parts.extend(part.parts)
            else:
                result.parts.append((part, ""))

        return result

    def append(self, text: str) -> None:
        self.parts.append((text, ""))

    def __add__(self, other: StyledText) -> StyledText:
        return self.from_parts(self, other)

    @override
    def __str__(self) -> str:
        return "".join(text for text, _ in self.parts)

    @override
    def __repr__(self) -> str:
        return f"StyledText({str(self)!r})"

    def format(self, terminal: Terminal) -> str:
        # Prefixing a diagnostic line must not reset the next line's style.
        return "".join(
            (
                text
                if not style or not terminal.styled
                else "\n".join(terminal.style(line, style) for line in text.split("\n"))
            )
            for text, style in self.parts
        )


@runtime_checkable
class Renderable(Protocol):
    def format(self, terminal: Terminal) -> str: ...


def _write(file: TextIO, text: str) -> None:
    """Write text with the stream's encoding and escape unrepresentable characters."""
    encoding = file.encoding or _FALLBACK_ENCODING
    file.write(text.encode(encoding, _ENCODING_ERRORS).decode(encoding))


def _environment_flag(name: str) -> bool | None:
    """Read a 0/1 terminal override, leaving other values automatic."""
    value = os.environ.get(name)
    if value == "1":
        return True
    if value == "0":
        return False
    return None


class Display:
    """Coordinate streams that share a terminal cursor."""

    def __init__(self) -> None:
        # Nested writes can acquire the display lock again on the same thread.
        # https://docs.python.org/3/library/threading.html#rlock-objects
        self.lock = threading.RLock()
        # Keep outer lines so finishing a nested operation can restore them.
        self.lines: list[LiveLine] = []
        self.drawn: Terminal | None = None
        self.cursor_hidden: Terminal | None = None

    def show_cursor(self) -> None:
        """Restore the cursor once, including after a failed live-line write."""
        owner = self.cursor_hidden
        self.cursor_hidden = None
        if owner is not None:
            owner.write(_SHOW_CURSOR)

    def clear(self) -> None:
        """Clear the active line under the caller's display lock."""
        if self.drawn is not None:
            # Return to column zero, then erase the remainder of the previous frame.
            # https://learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#text-modification
            self.drawn.write(_CARRIAGE_RETURN + _ERASE_TO_END)
            self.drawn = None

    def paint(self) -> None:
        """Paint the innermost line under the caller's display lock."""
        if not self.lines:
            return

        line = self.lines[-1]
        owner = line.terminal
        if not owner.interactive:
            return

        # Leave the last column empty so a repaint never wraps.
        width = max(shutil.get_terminal_size().columns - 1, 0)
        encoding = owner.file.encoding or _FALLBACK_ENCODING
        suffix = line.suffix.encode(encoding, _ENCODING_ERRORS).decode(encoding)
        suffix = fit_line(suffix, width)
        remaining = width - sum(_cell_width(char) for char in suffix)
        value = line.text
        if not isinstance(value, (str, StyledText)):
            value = value()
        parts = value.parts if isinstance(value, StyledText) else [(value, "")]
        rendered: list[str] = []

        for text, style in parts:
            text = text.encode(encoding, _ENCODING_ERRORS).decode(encoding)
            clipped = fit_line(text, remaining)
            rendered.append(owner.style(clipped, style))
            remaining -= sum(_cell_width(char) for char in clipped)
            if len(clipped) < len(text):
                break

        rendered.append(suffix)

        # Overwrite before erasing any remainder, without flushing a blank line.
        remainder = _ERASE_TO_END if self.drawn is not None else ""
        owner.write(_CARRIAGE_RETURN + "".join(rendered) + remainder)
        self.drawn = owner


class Terminal:
    """Own writes and a stack of progress lines for one output stream."""

    def __init__(
        self,
        file: TextIO | None = None,
        *,
        no_color: bool = False,
        color: bool | None = None,
    ) -> None:
        self.file = file if file is not None else sys.stdout
        tty = self.file.isatty()

        # Color-capable CI streams need not support cursor animation.
        # https://rich.readthedocs.io/en/stable/console.html#environment-variables
        compatible = _environment_flag("TTY_COMPATIBLE")
        capable = os.environ.get("TERM", "").lower() not in {"dumb", "unknown"}
        capable = capable and compatible is not False
        if os.name == "nt" and tty:
            capable = capable and _enable_windows_vt(self.file)

        # An empty FORCE_COLOR explicitly disables automatic styling.
        forced = os.environ.get("FORCE_COLOR")
        self.styled = (
            color
            if color is not None
            else (compatible is True or (tty if forced is None else bool(forced)))
            and capable
        )

        # NO_COLOR suppresses colors while retaining emphasis such as bold text.
        # https://no-color.org/
        self.color = (
            self.styled and not no_color and os.environ.get("NO_COLOR", "") == ""
        )

        if sys.platform == "win32":
            version = sys.getwindowsversion()
            self._truecolor = version.major > 10 or (
                version.major == 10 and version.build >= _MIN_WINDOWS_TRUECOLOR_BUILD
            )
            self._palette_color = True
        else:
            self._truecolor = os.environ.get("COLORTERM", "").strip().lower() in {
                "truecolor",
                "24bit",
            }
            self._palette_color = (
                os.environ.get("TERM", "").lower().endswith("-256color")
            )

        interactive = _environment_flag("TTY_INTERACTIVE")
        self.interactive = capable and (
            interactive is True or (tty and interactive is not False)
        )

        self.ascii_only = False
        try:
            _DIAGNOSTIC_SYMBOLS.encode(self.file.encoding or _FALLBACK_ENCODING)
        except UnicodeEncodeError:
            self.ascii_only = True

        self.display = Display()

    def style(self, text: str, style: str) -> str:
        if not text or not style or not self.styled:
            return text

        codes: set[int] = set()
        foreground: tuple[int, ...] | None = None

        for word in style.split():
            if word in _PROGRESS_COLORS:
                rgb, palette, standard = _PROGRESS_COLORS[word]
                foreground = (
                    (*_RGB_FOREGROUND, *rgb)
                    if self._truecolor
                    else (
                        (*_PALETTE_FOREGROUND, palette)
                        if self._palette_color
                        else (standard,)
                    )
                )
                continue

            for code in _STYLES[word]:
                if code >= _SGR_FOREGROUND:
                    foreground = (code,)
                else:
                    codes.add(code)

        # A nested foreground replaces the enclosing color.
        parameters = sorted(codes)
        if self.color and foreground is not None:
            parameters.extend(foreground)
        if not parameters:
            return text

        return f"{_CSI}{';'.join(map(str, parameters))}m{text}{_RESET_STYLE}"

    def format(self, value: str | Renderable) -> str:
        if isinstance(value, str):
            value = StyledText.from_markup(value)

        return value.format(self)

    def share_display(self, other: Terminal) -> None:
        """Share live-line state when both streams point at the same terminal."""
        if self.file is other.file:
            self.display = other.display
        elif self.interactive and other.interactive:
            # stdout and stderr may have different descriptors for the same terminal.
            try:
                first = os.fstat(self.file.fileno())
                second = os.fstat(other.file.fileno())
                # Windows pipes can all report zero identities.
                same = first.st_ino != 0 and os.path.samestat(first, second)
                if os.name == "nt" and not same:
                    # Native stdout/stderr use the process's attached console.
                    # https://learn.microsoft.com/en-us/windows/console/attachconsole
                    same = (
                        self.file.isatty()
                        and other.file.isatty()
                        and _enable_windows_vt(self.file)
                        and _enable_windows_vt(other.file)
                    )
            except (OSError, ValueError):
                same = False

            if same:
                self.display = other.display

    def write(self, text: str) -> None:
        """Write and flush terminal output through the stream owner's error policy."""
        _write(self.file, text)
        self.file.flush()

    def print(self, value: str | Renderable = "", *, indent: int = 0) -> None:
        text = self.format(value).translate(_STRIP_CONTROL)
        if indent:
            text = "\n".join(" " * indent + line for line in text.split("\n"))

        # Clear, write and repaint as one operation across shared streams.
        # Example of suspending and repainting around a write:
        # https://tqdm.github.io/docs/tqdm/#external_write_mode
        with self.display.lock:
            self.display.clear()
            self.write(text + "\n")
            self.display.paint()


class LiveLine:
    """Temporarily own the active progress line, restoring an outer line on exit."""

    def __init__(
        self,
        terminal: Terminal,
        *,
        limiter: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self.terminal = terminal
        # Inject scheduling to keep terminal output independent of animation.
        self._limiter = limiter
        self.text: str | StyledText | Callable[[], StyledText] = ""
        self.suffix = ""

    def __enter__(self) -> Self:
        with self.terminal.display.lock:
            self.terminal.display.clear()
            if not self.terminal.display.lines and self.terminal.interactive:
                self.terminal.write(_HIDE_CURSOR)
                self.terminal.display.cursor_hidden = self.terminal
            self.terminal.display.lines.append(self)

        return self

    def update(
        self,
        text: str | StyledText | Callable[[], StyledText],
        *,
        suffix: str = "",
    ) -> None:
        with self.terminal.display.lock:
            self.text = text
            self.suffix = suffix

            # Hidden outer lines retain their newest frame without repainting.
            if self.terminal.display.lines[-1] is self and self.terminal.interactive:
                if self._limiter is None:
                    self.terminal.display.paint()
                else:
                    self._limiter(self.terminal.display.paint)

    def __exit__(self, *exc: object) -> None:
        with self.terminal.display.lock:
            try:
                self.terminal.display.clear()
            finally:
                self.terminal.display.lines.remove(self)
                if not self.terminal.display.lines:
                    # Cursor cleanup must not replace an earlier write failure.
                    failed = sys.exc_info()[0] is not None
                    try:
                        self.terminal.display.show_cursor()
                    except Exception:
                        if not failed:
                            raise
            self.terminal.display.paint()


def _cell_width(char: str) -> int:
    return (
        0
        if unicodedata.combining(char)
        else (2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1)
    )


def fit_line(text: str, width: int, *, suffix: str = "") -> str:
    """Keep a progress line inside the terminal without embedded controls."""
    # Approximate terminal cells using Unicode combining and width properties.
    # https://docs.python.org/3/library/unicodedata.html#unicodedata.east_asian_width
    if suffix:
        # Keep the animation visible when its label needs truncating. Reserve
        # cells at paint time so nested line restoration also follows resizes.
        suffix = fit_line(suffix, width)
        width -= sum(_cell_width(char) for char in suffix)

    result = []

    for char in text:
        if not char.isprintable():
            continue

        cells = _cell_width(char)
        if cells > width:
            break

        result.append(char)
        width -= cells

    return "".join(result) + suffix


def print_json(data: object, terminal: Terminal) -> None:
    """Write indented JSON, with token colors on color-enabled streams."""
    text = json.dumps(data, indent=2, ensure_ascii=False)

    # Text-stream backslash replacement can produce invalid JSON escapes.
    try:
        text.encode(terminal.file.encoding or _FALLBACK_ENCODING)
    except UnicodeEncodeError:
        text = json.dumps(data, indent=2, ensure_ascii=True)

    if not terminal.styled:
        terminal.print(StyledText(text))
        return

    decoder = json.JSONDecoder()

    # JSON tokens have no literal LF; each role can share one wrapper per document.
    # https://www.rfc-editor.org/rfc/rfc8259#section-7
    styles = {
        style: terminal.style("%s", style)
        for style in (
            _JSON_KEY_STYLE,
            _JSON_STRING_STYLE,
            _JSON_NUMBER_STYLE,
            _JSON_BRACE_STYLE,
            *_JSON_LITERAL_STYLES.values(),
        )
    }

    parts: list[str] = []
    start = 0

    while match := _JSON_TOKEN.search(text, start):
        parts.append(text[start : match.start()])
        if match[0] == '"':
            # The decoder skips escaped strings without regex backtracking state.
            # https://docs.python.org/3/library/json.html#json.JSONDecoder.raw_decode
            end = decoder.raw_decode(text, match.start())[1]
            style = (
                _JSON_KEY_STYLE if text[end : end + 1] == ":" else _JSON_STRING_STYLE
            )
        else:
            end = match.end()
            style = (
                _JSON_BRACE_STYLE
                if match["brace"] is not None
                else _JSON_LITERAL_STYLES.get(match[0], _JSON_NUMBER_STYLE)
            )

        parts.append(styles[style] % text[match.start() : end])
        start = end

    parts.append(text[start:])
    text = "".join(parts)

    # Drop token fragments before the stream's encoding copies.
    del parts

    terminal.print(StyledText(text))


def _traceback_locals(
    rendered: traceback.TracebackException,
    exc: BaseException,
    tb: TracebackType | None,
) -> None:
    """Attach abbreviated locals to the native exception chain and group summaries."""
    # Retain native exception formatting while replacing only captured locals.
    # https://docs.python.org/3/library/traceback.html#traceback.FrameSummary
    pending = [(rendered, exc, tb)]

    while pending:
        summary, original, original_tb = pending.pop()

        for frame_summary, (frame, _) in zip(
            summary.stack, traceback.walk_tb(original_tb), strict=False
        ):
            # Abbreviate builtin strings and containers before taking their repr.
            # https://docs.python.org/3/library/reprlib.html#reprlib.repr
            frame_summary.locals = {
                name: reprlib.repr(value) for name, value in frame.f_locals.items()
            }

        if summary.__cause__ is not None and original.__cause__ is not None:
            cause = original.__cause__
            pending.append((summary.__cause__, cause, cause.__traceback__))

        if summary.__context__ is not None and original.__context__ is not None:
            context = original.__context__
            pending.append((summary.__context__, context, context.__traceback__))

        if (
            sys.version_info >= (3, 11)
            and isinstance(original, builtins.BaseExceptionGroup)
            and summary.exceptions is not None
        ):
            pending.extend(
                (child_summary, child, child.__traceback__)
                for child_summary, child in zip(
                    summary.exceptions, original.exceptions, strict=True
                )
            )


def debug_traceback(
    exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None
) -> None:
    """Show exception chains and abbreviated local variables in debug mode."""
    rendered = traceback.TracebackException(exc_type, exc, tb, capture_locals=False)

    try:
        _traceback_locals(rendered, exc, tb)
    except Exception:
        # Unusual local representations must not hide the original exception.
        rendered = traceback.TracebackException(exc_type, exc, tb, capture_locals=False)

    sys.stderr.write("".join(rendered.format()))
