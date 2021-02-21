# Custom install options

```{versionadded} 7.0
```

```{caution}
Using this mechanism `--global-option` and `--install-option` disables the use
of wheels *and* is incompatible with pip's current implementation for
interacting with the build-backend as described in PEP 517.
```

pip supports controlling the command line options given to `setup.py` via
requirements files. This disables the use of wheels (cached or otherwise) for
that package, as `setup.py` does not exist for wheels.

The `--global-option` and `--install-option` options are used to pass
options to `setup.py`. For example:

```text
FooProject >= 1.2 \
    --global-option="--no-user-cfg" \
    --install-option="--prefix='/usr/local'" \
    --install-option="--no-compile"
```

The above translates roughly into running FooProject's `setup.py`
script as:

```
python setup.py --no-user-cfg install --prefix='/usr/local' --no-compile
```

Note that the only way of giving more than one option to `setup.py`
is through multiple `--global-option` and `--install-option`
options, as shown in the example above. The value of each option is
passed as a single argument to the `setup.py` script. Therefore, a
line such as the following is invalid and would result in an
installation error.

```text
# THIS IS NOT VALID: use '--install-option' twice as shown above.
FooProject >= 1.2 --install-option="--prefix=/usr/local --no-compile"
```
