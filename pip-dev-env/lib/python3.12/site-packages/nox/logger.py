# Copyright 2016 Alethea Katherine Flowers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import logging
from typing import Any, cast

from colorlog import ColoredFormatter

__all__ = ["OUTPUT", "SUCCESS", "logger", "setup_logging"]


def __dir__() -> list[str]:
    return __all__


SUCCESS = 25
OUTPUT = logging.DEBUG - 1


def _get_format(*, colorlog: bool, add_timestamp: bool) -> str:
    if colorlog:
        if add_timestamp:
            return "%(cyan)s%(name)s > [%(asctime)s] %(log_color)s%(message)s"
        return "%(cyan)s%(name)s > %(log_color)s%(message)s"

    if add_timestamp:
        return "%(name)s > [%(asctime)s] %(message)s"

    return "%(name)s > %(message)s"


class NoxFormatter(logging.Formatter):
    def __init__(self, *, add_timestamp: bool = False) -> None:
        super().__init__(fmt=_get_format(colorlog=False, add_timestamp=add_timestamp))
        self._simple_fmt = logging.Formatter("%(message)s")

    def format(self, record: Any) -> str:
        if record.levelname == "OUTPUT":
            return self._simple_fmt.format(record)
        return super().format(record)


class NoxColoredFormatter(ColoredFormatter):
    def __init__(
        self,
        *,
        datefmt: Any = None,
        style: Any = None,
        log_colors: Any = None,
        reset: bool = True,
        secondary_log_colors: Any = None,
        add_timestamp: bool = False,
    ) -> None:
        super().__init__(
            fmt=_get_format(colorlog=True, add_timestamp=add_timestamp),
            datefmt=datefmt,
            style=style,
            log_colors=log_colors,
            reset=reset,
            secondary_log_colors=secondary_log_colors,
        )
        self._simple_fmt = logging.Formatter("%(message)s")

    def format(self, record: Any) -> str:
        if record.levelname == "OUTPUT":
            return self._simple_fmt.format(record)
        return super().format(record)


class LoggerWithSuccessAndOutput(logging.getLoggerClass()):  # type: ignore[misc]
    def __init__(self, name: str, level: int = logging.NOTSET):
        super().__init__(name, level)
        logging.addLevelName(SUCCESS, "SUCCESS")
        logging.addLevelName(OUTPUT, "OUTPUT")

    def success(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(SUCCESS):  # pragma: no cover
            self._log(SUCCESS, msg, args, **kwargs)

    def output(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(OUTPUT):  # pragma: no cover
            self._log(OUTPUT, msg, args, **kwargs)


logging.setLoggerClass(LoggerWithSuccessAndOutput)
logger = cast(LoggerWithSuccessAndOutput, logging.getLogger("nox"))


def _get_formatter(*, color: bool, add_timestamp: bool) -> logging.Formatter:
    if color:
        return NoxColoredFormatter(
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "blue",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
                "SUCCESS": "green",
            },
            style="%",
            secondary_log_colors=None,
            add_timestamp=add_timestamp,
        )
    return NoxFormatter(add_timestamp=add_timestamp)


def setup_logging(
    *, color: bool, verbose: bool = False, add_timestamp: bool = False
) -> None:  # pragma: no cover
    """Setup logging.

    Args:
        color (bool): If true, the output will be colored using
            colorlog. Otherwise, it will be plaintext.
    """
    root_logger = logging.getLogger()
    if verbose:
        root_logger.setLevel(OUTPUT)
    else:
        root_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()

    handler.setFormatter(_get_formatter(color=color, add_timestamp=add_timestamp))
    root_logger.addHandler(handler)

    # Silence noisy loggers
    logging.getLogger("sh").setLevel(logging.WARNING)
