# Providing an override to install packages with conflicting dependencies

## Problem

Currently, when a user has dependency conflicts in their project they may be unaware there is a problem, because pip will install conflicting packages without raising an error.

The new pip resolver is more strict and will no longer allow users to install packages that have conflicting dependencies.

As a result, some users may feel that newer versions of pip are "broken" when pip refuses to install conflicting packages.

For this reason, the pip team wanted to know if they should provide an override that allows users to install conflicting packages.

[Skip to recommendations](#recommendations)

## Research

We published a survey with the following introduction:

<blockquote>
Imagine you have packages tea and coffee:

tea 1.0.0 depends on water <1.12.<br>
coffee 1.0.0 depends on water>=1.12<br>

Installing tea 1.0.0 and coffee 1.0.0 will cause a conflict because they each rely on different versions of water - this is known as a "dependency conflict".

The pip team has recently changed the way that pip resolves dependency conflicts. The new implementation is stricter than before: pip will no longer install packages where there is a dependency conflict - instead it will show an error.

The purpose of this survey is to gather feedback on providing a way to override this behaviour.

All questions are optional - please provide as much information as you can.

</blockquote>

We then asked users:

- If pip should provide an override that allows users to install packages when there are dependency conflicts
- Why they answered yes or no
- For users that answered yes, we asked:
  - When they would use the override
  - How often they would use the override
  - How easy it would be to find a workaround, if pip did not provide an override
  - What syntax they prefer

## Results

In total, we received 415 responses to the survey.

An overwhelming majority (>70%) of respondents indicated that they want some kind of override that allows them to install packages when there are dependency conflicts. Despite desiring this feature, most respondents said if it exists they would use it "not often" — this indicates that it is an advanced feature that is not critical to day-to-day usage. Nevertheless, because it would be difficult or very difficult to find a workaround (>60%), we suggest that pip should offer a override feature (see recommendations, below).

Over half of the respondents said that `pip install tea coffee --ignore-conflicts` was the most ideal syntax for this command when installing multiple packages at once with a conflicting dependency. When using the `pip install --ignore-conflicts` command, a majority (>48%) of respondents said they would prefer pip to install to the most recent version of the conflicted dependency.

Most respondents suggested that installing the latest version by default is safer, because it could include security fixes or features that would be difficult to replicate on their own. They also trust that dependencies will be largely backwards-compatible. However, they said it was very important that it is necessary to have a way to override this default behavior, in case they need to use an older version of the conflicted package.

## Recommendations

Based on this research we recommend that the pip team:

- Implement an `--ignore-conflicts` option, that allows users to install packages with conflicting dependencies
- Ensure that `--ignore-conflicts` installs the most recent version of the conflicting package. For example, for conflicting package `water<1.1.2` and `water≥1.1.2`, pip should prefer to install `water≥1.1.2`.
- Allow users to override this default behavior by specifying the version of the conflicting packages. For example, `pip install tea coffee water==1.1.1 --ignore-conflicts`
- Warn users that they used the `--ignore-conflicts` flag and that this may cause unexpected behavior in their program
