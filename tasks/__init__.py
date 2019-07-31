import invoke

from tools.automation import generate, vendoring

ns = invoke.Collection(generate, vendoring)
