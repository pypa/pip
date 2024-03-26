Convert numerous internal classes to dataclasses for readability and stricter
enforcement of immutability across the codebase. A conservative approach was
taken in selecting which classes to convert. Classes which did not convert
cleanly into a dataclass or were "too complex" (e.g. maintains interconnected
state) were left alone.
