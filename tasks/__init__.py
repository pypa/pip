import invoke

from . import generate
from . import tests

ns = invoke.Collection(generate, tests)
