# Requirements and build directories

An `InstallRequirement` has `ensure_has_source_dir` that makes sure there's a
`source_dir`. This calls `ensure_build_location`, passing the directory
we want to put the source in.

As per the docstring of that function, "This will create a temporary build dir
if the name of the requirement isn't known yet". What that means in practice
is that if the requirement's `req` is not set, the provided build dir is ignored
and `source_dir` gets set to a temporay location. (It's possible that the source
gets relocated at some later point - that appears to have been something that
used to happen but no longer does, though).

So, as a consequence, when we `prepare` a requirement, it should have a `req`
set. It's unclear precisely what that `req` has to be, though. (In terms of
type, it's a `packaging.requirements.Requirement`, not one of the many other
things that call themselves a requirement...)

Other points identified as part of the research into this:

1. `prepare_linked_requirement` doesn't set the `prepared` flag on the
   requirement, the caller has to do that.
2. `prepare_linked_requirement` also doesn't set `successfully_downloaded`.
   It's not obvious what other code cares about this, though...
