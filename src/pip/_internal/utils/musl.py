import operator
import os
import re
import struct
from typing import IO, Optional, Tuple


def _read_unpacked(f: IO[bytes], fmt: str) -> Tuple[int, ...]:
    return struct.unpack(fmt, f.read(struct.calcsize(fmt)))


def _parse_ld_musl_from_elf(f: IO[bytes]) -> Optional[str]:
    """Detect musl libc location by parsing the Python executable.

    Based on: https://gist.github.com/lyssdod/f51579ae8d93c8657a5564aefc2ffbca
    ELF header: https://refspecs.linuxfoundation.org/elf/gabi4+/ch4.eheader.html
    """
    f.seek(0)
    try:
        ident = _read_unpacked(f, "16B")
    except struct.error:
        return None
    if ident[:4] != tuple(b"\x7fELF"):  # Invalid magic, not ELF.
        return None
    f.seek(struct.calcsize("HHI"), 1)  # Skip file type, machine, and version.

    try:
        # e_fmt: Format for program header.
        # p_fmt: Format for section header.
        # p_idx: Indexes to find p_type, p_offset, and p_filesz.
        e_fmt, p_fmt, p_idx = {
            1: ("IIIIHHH", "IIIIIIII", (0, 1, 4)),  # 32-bit.
            2: ("QQQIHHH", "IIQQQQQQ", (0, 2, 5)),  # 64-bit.
        }[ident[4]]
    except KeyError:
        return None
    else:
        p_get = operator.itemgetter(*p_idx)

    # Find the interpreter section and return its content.
    try:
        _, e_phoff, _, _, _, e_phentsize, e_phnum = _read_unpacked(f, e_fmt)
    except struct.error:
        return None
    for i in range(e_phnum + 1):
        f.seek(e_phoff + e_phentsize * i)
        try:
            p_type, p_offset, p_filesz = p_get(_read_unpacked(f, p_fmt))
        except struct.error:
            return None
        if p_type != 3:  # Not PT_INTERP.
            continue
        f.seek(p_offset)
        interpreter = os.fsdecode(f.read(p_filesz)).strip("\0")
        if "musl" not in interpreter:
            return None
        return interpreter
    return None


def _parse_musl_version(output: str) -> Optional[Tuple[int, int]]:
    lines = [n for n in (n.strip() for n in output.splitlines()) if n]
    if len(lines) < 2 or lines[0][:4] != "musl":
        return None
    m = re.match(r"Version (\d+)\.(\d+)", lines[1])
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))
