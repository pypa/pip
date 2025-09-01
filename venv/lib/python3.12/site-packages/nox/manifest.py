# Copyright 2017 Alethea Katherine Flowers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import ast
import itertools
import operator
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, cast

from nox._decorators import Call, Func
from nox._resolver import CycleError, lazy_stable_topo_sort
from nox.sessions import Session, SessionRunner

if TYPE_CHECKING:
    import argparse
    from collections.abc import Iterable, Iterator, Sequence

__all__ = ["WARN_PYTHONS_IGNORED", "Manifest", "keyword_match"]


def __dir__() -> list[str]:
    return __all__


WARN_PYTHONS_IGNORED = "python_ignored"


def _unique_list(*args: str) -> list[str]:
    """Return a list without duplicates, while preserving order."""
    return list(OrderedDict.fromkeys(args))


class Manifest:
    """Session manifest.

    The session manifest provides the source of truth for the sequence of
    sessions that should be run by Nox.

    It is possible for this to be mutated during execution. This allows for
    useful use cases, such as for one session to "notify" another or
    "chain" to another.

    Args:
        session_functions (Mapping[str, function]): The registry of discovered
            session functions.
        global_config (.nox.main.GlobalConfig): The global configuration.
        module_docstring (Optional[str]): The user noxfile.py docstring.
            Defaults to `None`.
    """

    def __init__(
        self,
        session_functions: Mapping[str, Func],
        global_config: argparse.Namespace,
        module_docstring: str | None = None,
    ) -> None:
        self._all_sessions: list[SessionRunner] = []
        self._queue: list[SessionRunner] = []
        self._consumed: list[SessionRunner] = []
        self._config: argparse.Namespace = global_config
        self.module_docstring: str | None = module_docstring

        # Create the sessions based on the provided session functions.
        for name, func in session_functions.items():
            for session in self.make_session(name, func):
                self.add_session(session)

    def __contains__(self, needle: str | SessionRunner) -> bool:
        if needle in self._queue or needle in self._consumed:
            return True
        for session in self._queue + self._consumed:
            if session.name == needle or needle in session.signatures:
                return True
        return False

    def __iter__(self) -> Manifest:
        return self

    def __getitem__(self, key: str) -> SessionRunner:
        for session in self._queue + self._consumed:
            if session.name == key or key in session.signatures:
                return session
        raise KeyError(key)

    def __next__(self) -> SessionRunner:
        """Return the next item in the queue.

        Raises:
            StopIteration: If the queue has been entirely consumed.
        """
        if not len(self._queue):
            raise StopIteration
        session = self._queue.pop(0)
        self._consumed.append(session)
        return session

    def __len__(self) -> int:
        return len(self._queue) + len(self._consumed)

    def list_all_sessions(self) -> Iterator[tuple[SessionRunner, bool]]:
        """Yields all sessions and whether or not they're selected."""
        for session in self._all_sessions:
            yield session, session in self._queue

    @property
    def all_sessions_by_signature(self) -> dict[str, SessionRunner]:
        return {
            signature: session
            for session in self._all_sessions
            for signature in session.signatures
        }

    @property
    def parametrized_sessions_by_name(self) -> dict[str, list[SessionRunner]]:
        """Returns a mapping from names to all sessions that are parameterizations of
        the ``@session`` with each name.

        The sessions in each returned list will occur in the same order as they occur in
        ``self._all_sessions``.
        """
        parametrized_sessions = filter(operator.attrgetter("multi"), self._all_sessions)
        key = operator.attrgetter("name")
        # Note that ``sorted`` uses a stable sorting algorithm.
        return {
            name: list(sessions_parametrizing_name)
            for name, sessions_parametrizing_name in itertools.groupby(
                sorted(parametrized_sessions, key=key), key
            )
        }

    def add_session(self, session: SessionRunner) -> None:
        """Add the given session to the manifest.

        Args:
            session (~nox.sessions.Session): A session object, such as
                one returned from ``make_session``.
        """
        if session not in self._all_sessions:
            self._all_sessions.append(session)
        if session not in self._queue:
            self._queue.append(session)

    def filter_by_name(self, specified_sessions: Iterable[str]) -> None:
        """Filter sessions in the queue based on the user-specified names.

        Args:
            specified_sessions (Sequence[str]): A list of specified
                session names.

        Raises:
            KeyError: If any explicitly listed sessions are not found.
        """
        # Filter the sessions remaining in the queue based on
        # whether they are individually specified.
        self._queue = [
            session
            for session_name in specified_sessions
            for session in self._queue
            if _normalized_session_match(session_name, session)
        ]

        # If a session was requested and was not found, complain loudly.
        all_sessions = set(
            map(
                _normalize_arg,
                (
                    itertools.chain(
                        [x.name for x in self._all_sessions if x.name],
                        *[x.signatures for x in self._all_sessions],
                    )
                ),
            )
        )
        missing_sessions = [
            session_name
            for session_name in specified_sessions
            if _normalize_arg(session_name) not in all_sessions
        ]
        if missing_sessions:
            msg = f"Sessions not found: {', '.join(missing_sessions)}"
            raise KeyError(msg)

    def filter_by_default(self) -> None:
        """Filter sessions in the queue based on the default flag."""

        self._queue = [x for x in self._queue if x.func.default]

    def filter_by_python_interpreter(self, specified_pythons: Sequence[str]) -> None:
        """Filter sessions in the queue based on the user-specified
        python interpreter versions.

        Args:
            specified_pythons (Sequence[str]): A list of specified
                python interpreter versions.
        """
        self._queue = [x for x in self._queue if x.func.python in specified_pythons]

    def filter_by_keywords(self, keywords: str) -> None:
        """Filter sessions using pytest-like keyword expressions.

        Args:
            keywords (str): A Python expression of keywords which
                session names are checked against.
        """
        self._queue = [
            x
            for x in self._queue
            if keyword_match(keywords, [*x.signatures, *x.tags, x.name])
        ]

    def filter_by_tags(self, tags: Iterable[str]) -> None:
        """Filter sessions by their tags.

        Args:
            tags (list[str]): A list of tags which session names
                are checked against.
        """
        self._queue = [x for x in self._queue if set(x.tags).intersection(tags)]

    def add_dependencies(self) -> None:
        """Add direct and recursive dependencies to the queue.

        Raises:
            KeyError: If any depended-on sessions are not found.
            ~nox._resolver.CycleError: If a dependency cycle is encountered.
        """
        sessions_by_id = self.all_sessions_by_signature

        # For each session that was parametrized from a list of Pythons, create a fake
        # parent session that depends on it.
        parent_sessions: set[SessionRunner] = set()
        for (
            parent_name,
            parametrized_sessions,
        ) in self.parametrized_sessions_by_name.items():
            parent_func = _null_session_func.copy()
            parent_func.requires = [
                session.signatures[0] for session in parametrized_sessions
            ]
            parent_session = SessionRunner(
                parent_name, [], parent_func, self._config, self, multi=False
            )
            parent_sessions.add(parent_session)
            sessions_by_id[parent_name] = parent_session

        # Construct the dependency graph. Note that this is done lazily with iterators
        # so that we won't raise if a session that doesn't actually need to run declares
        # missing/improper dependencies.
        dependency_graph = {
            session: session.get_direct_dependencies(sessions_by_id)
            for session in sessions_by_id.values()
        }

        # Resolve the dependency graph.
        root = cast(SessionRunner, object())  # sentinel
        try:
            resolved_graph = list(
                lazy_stable_topo_sort({**dependency_graph, root: self._queue}, root)
            )
        except CycleError as exc:
            raise CycleError(
                "Sessions are in a dependency cycle: "
                + " -> ".join(session.name for session in exc.args[1])
            ) from exc

        # Remove fake parent sessions from the resolved graph.
        self._queue = [
            session for session in resolved_graph if session not in parent_sessions
        ]

    def make_session(
        self, name: str, func: Func, *, multi: bool = False
    ) -> list[SessionRunner]:
        """Create a session object from the session function.

        Args:
            name (str): The name of the session.
            func (function): The session function.
            multi (bool): Whether the function is a member of a set of sessions
                with different interpreters.

        Returns:
            Sequence[~nox.session.Session]: A sequence of Session objects
                bound to this manifest and configuration.
        """
        sessions = []

        # If the backend is "none", we won't parametrize `python`.
        backend = (
            self._config.force_venv_backend
            or func.venv_backend
            or self._config.default_venv_backend
        )
        if backend == "none" and isinstance(func.python, (list, tuple, set)):
            # we can not log a warning here since the session is maybe deselected.
            # instead let's set a flag, to warn later when session is actually run.
            func.should_warn[WARN_PYTHONS_IGNORED] = func.python
            func.python = False

        if self._config.extra_pythons:
            # If extra python is provided, expand the func.python list to
            # include additional python interpreters
            extra_pythons: list[str] = self._config.extra_pythons
            if isinstance(func.python, (list, tuple, set)):
                func.python = _unique_list(*func.python, *extra_pythons)
            elif not multi and func.python:
                # If this is multi, but there is only a single interpreter, it
                # is the reentrant case. The extra_python interpreter shouldn't
                # be added in that case. If func.python is False, the session
                # has no backend; if None, it uses the same interpreter as Nox.
                # Otherwise, add the extra specified python.
                assert isinstance(func.python, str)
                func.python = _unique_list(func.python, *extra_pythons)
            elif not func.python and self._config.force_pythons:
                # If a python is forced by the user, but the underlying function
                # has no version parametrised, add it as sole occupant to func.python
                func.python = _unique_list(*extra_pythons)

        # If the func has the python attribute set to a list, we'll need
        # to expand them.
        if isinstance(func.python, (list, tuple, set)):
            for python in func.python:
                single_func = func.copy()
                single_func.python = python
                sessions.extend(self.make_session(name, single_func, multi=True))

            return sessions

        # Simple case: If this function is not parametrized, then make
        # a simple session.
        if not hasattr(func, "parametrize"):
            long_names = []
            if not multi:
                long_names.append(name)
            if func.python:
                long_names.append(f"{name}-{func.python}")

            return [
                SessionRunner(name, long_names, func, self._config, self, multi=multi)
            ]

        # Since this function is parametrized, we need to add a distinct
        # session for each permutation.
        parametrize = func.parametrize
        calls = Call.generate_calls(func, parametrize)
        for call in calls:
            long_names = []
            if not multi or (
                self._config.force_pythons and call.python in self._config.extra_pythons
            ):
                long_names.append(f"{name}{call.session_signature}")

            if func.python:
                long_names.append(f"{name}-{func.python}{call.session_signature}")
                # Ensure that specifying session-python will run all parameterizations.
                long_names.append(f"{name}-{func.python}")

            sessions.append(
                SessionRunner(name, long_names, call, self._config, self, multi=multi)
            )

        # Edge case: If the parameters made it such that there were no valid
        # calls, add an empty, do-nothing session.
        if not calls:
            sessions.append(
                SessionRunner(
                    name, [], _null_session_func, self._config, self, multi=multi
                )
            )

        # Return the list of sessions.
        return sessions

    def next(self) -> SessionRunner:
        return next(self)

    def notify(
        self, session: str | SessionRunner, posargs: Iterable[str] | None = None
    ) -> bool:
        """Enqueue the specified session in the queue.

        If the session is already in the queue, or has been run already,
        then this is a no-op.

        Args:
            session (Union[str, ~nox.session.Session]): The session to be
                enqueued.
            posargs (Optional[List[str]]): If given, sets the positional
                arguments *only* for the queued session. Otherwise, the
                standard globally available positional arguments will be
                used instead.

        Returns:
            bool: Whether the session was added to the queue.

        Raises:
            ValueError: If the session was not found.
        """
        # Sanity check: If this session is already in the queue, this is
        # a no-op.
        if session in self:
            return False

        # Locate the session in the list of all sessions, and place it at
        # the end of the queue.
        for s in self._all_sessions:
            if s == session or s.name == session or session in s.signatures:  # noqa: PLR1714
                if posargs is not None:
                    s.posargs = list(posargs)
                self._queue.append(s)
                return True

        # The session was not found in the list of sessions.
        msg = f"Session {session} not found."
        raise ValueError(msg)


class KeywordLocals(Mapping[str, bool]):
    """Eval locals using keywords.

    When looking up a local variable the variable name is compared against
    the set of keywords. If the local variable name matches any *substring* of
    any keyword, then the name lookup returns True. Otherwise, the name lookup
    returns False.
    """

    def __init__(self, keywords: Iterable[str]) -> None:
        self._keywords = frozenset(keywords)

    def __getitem__(self, variable_name: str) -> bool:
        return any(variable_name in keyword for keyword in self._keywords)

    def __iter__(self) -> Iterator[str]:
        return iter(self._keywords)

    def __len__(self) -> int:
        return len(self._keywords)


def keyword_match(expression: str, keywords: Iterable[str]) -> Any:
    """See if an expression matches the given set of keywords."""
    # TODO: see if we can use ast.literal_eval here.
    locals = KeywordLocals(set(keywords))
    return eval(expression, {}, locals)  # noqa: S307


def _null_session_func_(session: Session) -> None:
    """A no-op session for parametrized sessions with no available params."""
    session.skip("This session had no parameters available.")


def _normalized_session_match(session_name: str, session: SessionRunner) -> bool:
    """Checks if session_name matches session."""
    if session_name == session.name or session_name in session.signatures:
        return True
    for name in session.signatures:
        equal_rep = _normalize_arg(session_name) == _normalize_arg(name)
        if equal_rep:
            return True
    # Exhausted
    return False


def _normalize_arg(arg: str) -> str:
    """Normalize arg for comparison."""
    try:
        return str(ast.dump(ast.parse(arg)))
    except (TypeError, SyntaxError):
        return arg


_null_session_func = Func(_null_session_func_, python=False)
