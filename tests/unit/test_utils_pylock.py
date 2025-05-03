from textwrap import dedent

from pip._vendor import tomli_w

from pip._internal.models.pylock import Pylock
from pip._internal.utils.compat import tomllib
from pip._internal.utils.pylock import pylock_to_toml

# This is the PEP 751 example, with the following differences:
# - a minor modification to the 'environments' field to use double quotes
#   instead of single quotes, since that is what 'packaging' does when
#   serializing markers;
# - added an index field, which was not demonstrated in the PEP 751 example.

PEP751_EXAMPLE = dedent(
    """\
    lock-version = '1.0'
    environments = ["sys_platform == \\"win32\\"", "sys_platform == \\"linux\\""]
    requires-python = '==3.12'
    created-by = 'mousebender'

    [[packages]]
    name = 'attrs'
    version = '25.1.0'
    requires-python = '>=3.8'
    wheels = [
    {name = 'attrs-25.1.0-py3-none-any.whl', upload-time = 2025-01-25T11:30:10.164985+00:00, url = 'https://files.pythonhosted.org/packages/fc/30/d4986a882011f9df997a55e6becd864812ccfcd821d64aac8570ee39f719/attrs-25.1.0-py3-none-any.whl', size = 63152, hashes = {sha256 = 'c75a69e28a550a7e93789579c22aa26b0f5b83b75dc4e08fe092980051e1090a'}},
    ]
    [[packages.attestation-identities]]
    environment = 'release-pypi'
    kind = 'GitHub'
    repository = 'python-attrs/attrs'
    workflow = 'pypi-package.yml'

    [[packages]]
    name = 'cattrs'
    version = '24.1.2'
    requires-python = '>=3.8'
    dependencies = [
        {name = 'attrs'},
    ]
    index = 'https://pypi.org/simple'
    wheels = [
    {name = 'cattrs-24.1.2-py3-none-any.whl', upload-time = 2024-09-22T14:58:34.812643+00:00, url = 'https://files.pythonhosted.org/packages/c8/d5/867e75361fc45f6de75fe277dd085627a9db5ebb511a87f27dc1396b5351/cattrs-24.1.2-py3-none-any.whl', size = 66446, hashes = {sha256 = '67c7495b760168d931a10233f979b28dc04daf853b30752246f4f8471c6d68d0'}},
    ]

    [[packages]]
    name = 'numpy'
    version = '2.2.3'
    requires-python = '>=3.10'
    wheels = [
    {name = 'numpy-2.2.3-cp312-cp312-win_amd64.whl', upload-time = 2025-02-13T16:51:21.821880+00:00, url = 'https://files.pythonhosted.org/packages/42/6e/55580a538116d16ae7c9aa17d4edd56e83f42126cb1dfe7a684da7925d2c/numpy-2.2.3-cp312-cp312-win_amd64.whl', size = 12626357, hashes = {sha256 = '83807d445817326b4bcdaaaf8e8e9f1753da04341eceec705c001ff342002e5d'}},
    {name = 'numpy-2.2.3-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl', upload-time = 2025-02-13T16:50:00.079662+00:00, url = 'https://files.pythonhosted.org/packages/39/04/78d2e7402fb479d893953fb78fa7045f7deb635ec095b6b4f0260223091a/numpy-2.2.3-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl', size = 16116679, hashes = {sha256 = '3b787adbf04b0db1967798dba8da1af07e387908ed1553a0d6e74c084d1ceafe'}},
    ]

    [tool.mousebender]
    command = ['.', 'lock', '--platform', 'cpython3.12-windows-x64', '--platform', 'cpython3.12-manylinux2014-x64', 'cattrs', 'numpy']
    run-on = 2025-03-06T12:28:57.760769
    """  # noqa: E501
)


def test_toml_roundtrip() -> None:
    pylock_dict = tomllib.loads(PEP751_EXAMPLE)
    pylock = Pylock.from_dict(pylock_dict)
    # Check that the roundrip via Pylock dataclasses produces the same toml
    # output, modulo TOML serialization differences.
    assert pylock_to_toml(pylock) == tomli_w.dumps(pylock_dict)
