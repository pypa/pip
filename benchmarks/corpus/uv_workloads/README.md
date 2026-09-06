# uv benchmark workloads

These compiled lockfiles are copied from
[`astral-sh/uv/test/requirements/compiled`](https://github.com/astral-sh/uv/tree/main/test/requirements/compiled)
at commit `79bbface771210df216b738e9bdc7df95e5a9e6b`.

They're pinned, real-world dependency sets (Airflow, Black, Boto3, Jupyter,
Trio, scispaCy, Flyte, ...) used here as parsing-benchmark input: unlike the
`.in` source files, they need no resolution or network access to read.

uv is distributed under the Apache-2.0 and MIT licenses. See the upstream
[`LICENSE-APACHE`](https://github.com/astral-sh/uv/blob/main/LICENSE-APACHE)
and [`LICENSE-MIT`](https://github.com/astral-sh/uv/blob/main/LICENSE-MIT)
files.
