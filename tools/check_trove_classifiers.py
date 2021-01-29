import subprocess
import sys

from trove_classifiers import classifiers


def main() -> int:
    ours = subprocess.check_output(
        [sys.executable, "setup.py", "--classifiers"],
        encoding="utf-8",
        text=True,
    ).splitlines(keepends=False)

    wrong_lines = [line for line in ours if line not in classifiers]
    if not wrong_lines:
        return 0

    print("Invalid trove classifiers found:")
    for line in wrong_lines:
        print("   ", line)
    return len(wrong_lines)


if __name__ == "__main__":
    sys.exit(main())
