# New resolver error messages


## Incompatible requirements

Most resolver error messages are due to incompatible requirements.
That is, the dependency tree contains conflicting versions of the same
package.  Take the example:

    base:
      available:
        - A 1.0.0; depends B == 1.0.0, C == 2.0.0
        - B 1.0.0; depends C == 1.0.0
        - C 1.0.0
        - C 2.0.0

Here, `A` cannot be installed because it depends on `B` (which depends on
a different version of `C` than `A` itself.  In real world examples, the
conflicting version are not so easy to spot. I'm suggesting an error
message which looks something like this:

    A 1.0.0 -> B 1.0.0 -> C 1.0.0
    A 1.0.0 -> C 2.0.0

That is, for the conflicting package, we show the user where exactly the
requirement came from.


## Double requirement

I've noticed that in many cases the old resolver messages are more
informative.  For example, in the simple example:

    base:
      available:
        - B 1.0.0
        - B 2.0.0

Now if we want to install both version of `B` at the same time,
i.e. the requirement `B==1.0.0 B==2.0.0`, we get:

    ERROR: Could not find a version that satisfies the requirement B==1.0.0
    ERROR: Could not find a version that satisfies the requirement B==2.0.0
    No matching distribution found for b, b

Even though both version are actually available and satisfy each requirement,
just not at once.  When trying to install a version of `B` which does not
exist, say requirement `B==1.5.0`, you get the same type of error message:

    Could not find a version that satisfies the requirement B==1.5.0
    No matching distribution found for b

For this case, the old error message was:

    Could not find a version that satisfies the requirement B==1.5.0 (from versions: 1.0.0, 2.0.0)
    No matching distribution found for B==1.5.0

And the old error message for the requirement `B==1.0.0 B==2.0.0`:

    Double requirement given: B==2.0.0 (already in B==1.0.0, name='B')
