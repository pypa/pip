import invoke

from . import generate
from . import vendoring

ns = invoke.Collection(generate, vendoring)
