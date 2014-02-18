import sys

# If we are running from a wheel, add the wheel to sys.path
# This allows the usage python pip-*.whl/pip install pip-*.whl
if __package__ == '':
    import os
    path = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, path)

import pip

if __name__ == '__main__':
    sys.exit(pip.main())
