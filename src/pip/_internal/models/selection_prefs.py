from dataclasses import dataclass
from typing import Optional

from pip._internal.models.format_control import FormatControl


@dataclass(frozen=True)
class SelectionPreferences:
    """
    Encapsulates the candidate selection preferences for downloading
    and installing files.

    :param allow_yanked: Whether files marked as yanked (in the sense
        of PEP 592) are permitted to be candidates for install.
    :param format_control: A FormatControl object or None. Used to control
        the selection of source packages / binary packages when consulting
        the index and links.
    :param prefer_binary: Whether to prefer an old, but valid, binary
        dist over a new source dist.
    :param ignore_requires_python: Whether to ignore incompatible
        "Requires-Python" values in links. Defaults to False.
    """

    # Don't include an allow_yanked default value to make sure each call
    # site considers whether yanked releases are allowed. This also causes
    # that decision to be made explicit in the calling code, which helps
    # people when reading the code.
    allow_yanked: bool
    allow_all_prereleases: bool = False
    format_control: Optional[FormatControl] = None
    prefer_binary: bool = False
    ignore_requires_python: Optional[bool] = False
