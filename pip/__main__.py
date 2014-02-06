import os
import sys


def run_main():
    # Put the pip relative to this file first on sys.path so that it would be
    # run with first priority.
    base = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
    sys.path.insert(0, base)
    import pip
    sys.exit(pip.main())

if __name__ == '__main__':
    run_main()
