Finding and choosing files (``index.py`` and ``PackageFinder``)
---------------------------------------------------------------

The ``index.py`` module is a top-level module in pip responsible for deciding
what file to download and from where, given a requirement for a project. The
module's functionality is largely exposed through and coordinated by the
module's ``PackageFinder`` class.


.. _index-py-overview:

Overview
********

Here is a rough description of the process that pip uses to choose what
file to download for a package, given a requirement:

1. Access the various network and file system locations configured for pip
   that contain package files. These locations can include, for example,
   pip's :ref:`--index-url <--index-url>` (with default
   https://pypi.org/simple/ ) and any configured
   :ref:`--extra-index-url <--extra-index-url>` locations.
   Each of these locations is a `PEP 503`_ "simple repository" page, which
   is an HTML page of anchor links.
2. Collect together all of the links (e.g. by parsing the anchor links
   from the HTML pages) and create ``Link`` objects from each of these.
   The :ref:`LinkCollector <link-collector-class>` class is responsible
   for both this step and the previous.
3. Determine which of the links are minimally relevant, using the
   :ref:`LinkEvaluator <link-evaluator-class>` class.  Create an
   ``InstallationCandidate`` object (aka candidate for install) for each
   of these relevant links.
4. Further filter the collection of ``InstallationCandidate`` objects (using
   the :ref:`CandidateEvaluator <candidate-evaluator-class>` class) to a
   collection of "applicable" candidates.
5. If there are applicable candidates, choose the best candidate by sorting
   them (again using the :ref:`CandidateEvaluator
   <candidate-evaluator-class>` class).

The remainder of this section is organized by documenting some of the
classes inside ``index.py``, in the following order:

* the main :ref:`PackageFinder <package-finder-class>` class,
* the :ref:`LinkCollector <link-collector-class>` class,
* the :ref:`LinkEvaluator <link-evaluator-class>` class,
* the :ref:`CandidateEvaluator <candidate-evaluator-class>` class,
* the :ref:`CandidatePreferences <candidate-preferences-class>` class, and
* the :ref:`BestCandidateResult <best-candidate-result-class>` class.


.. _package-finder-class:

The ``PackageFinder`` class
***************************

The ``PackageFinder`` class is the primary way through which code in pip
interacts with ``index.py``. It is an umbrella class that encapsulates and
groups together various package-finding functionality.

The ``PackageFinder`` class is responsible for searching the network and file
system for what versions of a package pip can install, and also for deciding
which version is most preferred, given the user's preferences, target Python
environment, etc.

The pip commands that use the ``PackageFinder`` class are:

* :ref:`pip download`
* :ref:`pip install`
* :ref:`pip list`
* :ref:`pip wheel`

The pip commands requiring use of the ``PackageFinder`` class generally
instantiate ``PackageFinder`` only once for the whole pip invocation. In
fact, pip creates this ``PackageFinder`` instance when command options
are first parsed.

With the excepton of :ref:`pip list`, each of the above commands is
implemented as a ``Command`` class inheriting from ``RequirementCommand``
(for example :ref:`pip download` is implemented by ``DownloadCommand``), and
the ``PackageFinder`` instance is created by calling the
``RequirementCommand`` class's ``_build_package_finder()`` method. ``pip
list``, on the other hand, constructs its ``PackageFinder`` instance by
calling the ``ListCommand`` class's ``_build_package_finder()``. (This
difference may simply be historical and may not actually be necessary.)

Each of these commands also uses the ``PackageFinder`` class for pip's
"self-check," (i.e. to check whether a pip upgrade is available). In this
case, the ``PackageFinder`` instance is created by the
``self_outdated_check.py`` module's ``pip_self_version_check()`` function.

The ``PackageFinder`` class is responsible for doing all of the things listed
in the :ref:`Overview <index-py-overview>` section like fetching and parsing
`PEP 503`_ simple repository HTML pages, evaluating which links in the simple
repository pages are relevant for each requirement, and further filtering and
sorting by preference the candidates for install coming from the relevant
links.

One of ``PackageFinder``'s main top-level methods is
``find_best_candidate()``. This method does the following two things:

1. Calls its ``find_all_candidates()`` method, which gathers all
   possible package links by reading and parsing the index URL's and
   locations provided by the user (the :ref:`LinkCollector
   <link-collector-class>` class's ``collect_links()`` method), constructs a
   :ref:`LinkEvaluator <link-evaluator-class>` object to filter out some of
   those links, and then returns a list of ``InstallationCandidates`` (aka
   candidates for install). This corresponds to steps 1-3 of the
   :ref:`Overview <index-py-overview>` above.
2. Constructs a ``CandidateEvaluator`` object and uses that to determine
   the best candidate. It does this by calling the ``CandidateEvaluator``
   class's ``compute_best_candidate()`` method on the return value of
   ``find_all_candidates()``. This corresponds to steps 4-5 of the Overview.


.. _link-collector-class:

The ``LinkCollector`` class
***************************

The :ref:`LinkCollector <link-collector-class>` class is the class
responsible for collecting the raw list of "links" to package files
(represented as ``Link`` objects). An instance of the class accesses the
various `PEP 503`_ HTML "simple repository" pages, parses their HTML,
extracts the links from the anchor elements, and creates ``Link`` objects
from that information. The ``LinkCollector`` class is "unintelligent" in that
it doesn't do any evaluation of whether the links are relevant to the
original requirement; it just collects them.

The ``LinkCollector`` class takes into account the user's :ref:`--find-links
<--find-links>`, :ref:`--extra-index-url <--extra-index-url>`, and related
options when deciding which locations to collect links from. The class's main
method is the ``collect_links()`` method. The :ref:`PackageFinder
<package-finder-class>` class invokes this method as the first step of its
``find_all_candidates()`` method.

The ``LinkCollector`` class is the only class in the ``index.py`` module that
makes network requests and is the only class in the module that depends
directly on ``PipSession``, which stores pip's configuration options and
state for making requests.


.. _link-evaluator-class:

The ``LinkEvaluator`` class
***************************

The ``LinkEvaluator`` class contains the business logic for determining
whether a link (e.g. in a simple repository page) satisfies minimal
conditions to be a candidate for install (resulting in an
``InstallationCandidate`` object). When making this determination, the
``LinkEvaluator`` instance uses information like the target Python
interpreter as well as user preferences like whether binary files are
allowed or preferred, etc.

Specifically, the ``LinkEvaluator`` class has an ``evaluate_link()`` method
that returns whether a link is a candidate for install.

Instances of this class are created by the ``PackageFinder`` class's
``make_link_evaluator()`` on a per-requirement basis.


.. _candidate-evaluator-class:

The ``CandidateEvaluator`` class
********************************

The ``CandidateEvaluator`` class contains the business logic for evaluating
which ``InstallationCandidate`` objects should be preferred. This can be
viewed as a determination that is finer-grained than that performed by the
``LinkEvaluator`` class.

In particular, the ``CandidateEvaluator`` class uses the whole set of
``InstallationCandidate`` objects when making its determinations, as opposed
to evaluating each candidate in isolation, as ``LinkEvaluator`` does. For
example, whether a pre-release is eligible for selection or whether a file
whose hash doesn't match is eligible depends on properties of the collection
as a whole.

The ``CandidateEvaluator`` class uses information like the list of `PEP 425`_
tags compatible with the target Python interpreter, hashes provided by the
user, and other user preferences, etc.

Specifically, the class has a ``get_applicable_candidates()`` method.
This accepts the ``InstallationCandidate`` objects resulting from the links
accepted by the ``LinkEvaluator`` class's ``evaluate_link()`` method, and
it further filters them to a list of "applicable" candidates.

The ``CandidateEvaluator`` class also has a ``sort_best_candidate()`` method
that orders the applicable candidates by preference, and then returns the
best (i.e. most preferred).

Finally, the class has a ``compute_best_candidate()`` method that calls
``get_applicable_candidates()`` followed by ``sort_best_candidate()``, and
then returning a :ref:`BestCandidateResult <best-candidate-result-class>`
object encapsulating both the intermediate and final results of the decision.

Instances of ``CandidateEvaluator`` are created by the ``PackageFinder``
class's ``make_candidate_evaluator()`` method on a per-requirement basis.


.. _candidate-preferences-class:

The ``CandidatePreferences`` class
**********************************

The ``CandidatePreferences`` class is a simple container class that groups
together some of the user preferences that ``PackageFinder`` uses to
construct ``CandidateEvaluator`` objects (via the ``PackageFinder`` class's
``make_candidate_evaluator()`` method).

A ``PackageFinder`` instance has a ``_candidate_prefs`` attribute whose value
is a ``CandidatePreferences`` instance. Since ``PackageFinder`` has a number
of responsibilities and options that control its behavior, grouping the
preferences specific to ``CandidateEvaluator`` helps maintainers know which
attributes are needed only for ``CandidateEvaluator``.


.. _best-candidate-result-class:

The ``BestCandidateResult`` class
*********************************

The ``BestCandidateResult`` class is a convenience "container" class that
encapsulates the result of finding the best candidate for a requirement.
(By "container" we mean an object that simply contains data and has no
business logic or state-changing methods of its own.) It stores not just the
final result but also intermediate values used to determine the result.

The class is the return type of both the ``CandidateEvaluator`` class's
``compute_best_candidate()`` method and the ``PackageFinder`` class's
``find_best_candidate()`` method.


.. _`PEP 425`: https://www.python.org/dev/peps/pep-0425/
.. _`PEP 503`: https://www.python.org/dev/peps/pep-0503/
